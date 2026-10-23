#!/usr/bin/env python3
"""Export five raw ORT CPU frames, or measure independent BASE TRT recurrence.

No tolerance is defined: a complete TRT comparison always exits 3, even when
all errors are zero. CUDA/TRT and ORT imports occur only in their respective
mode. This tool never downloads, builds, installs, starts a daemon or uses USB.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import importlib
import json
from pathlib import Path
import zipfile

import numpy as np

import build_trt_v3 as verify
import jetson_m1 as isolation
import jetson_m1_recurrent as recurrent

FRAMES, SEED = 5, 73


def plain_path(path):
    path = Path(path).absolute()
    if path != path.resolve():
        raise ValueError('reference/output path contains a symlink or escape')
    return path


def new_directory(path):
    path = plain_path(path)
    if not path.parent.is_dir() or path == Path(path.anchor):
        raise ValueError('fresh output needs a dedicated existing parent')
    path.mkdir(exist_ok=False)
    return path


def export_sequence(run, contract, output, ort_version, providers):
    """Numerical loop shared by the real CPU session and CPU boundary tests."""
    output = new_directory(output)
    state, files = {}, []
    names = list(contract['outputs'])
    for frame in range(FRAMES):
        feeds = verify.frame_inputs(contract['inputs'], frame, SEED)
        for name, value in state.items(): np.copyto(feeds[name], value, casting='no')
        values = run(feeds)
        verify.validate_outputs(values, contract['outputs'])
        verify.advance_state(feeds, values)
        state = {n: value.copy() for n, value in feeds.items() if n.startswith('state_')}
        filename = f'frame-{frame:04d}.npz'
        path = output / filename
        with path.open('xb') as stream:
            # Arrays only. Consumers reject object dtypes and use allow_pickle=False.
            np.savez(stream, **{n: values[n] for n in names})
        files.append({'frame': frame, 'name': filename, **verify.file_identity(path),
                      'tensors': contract['outputs']})
    manifest = {'schema': 1, 'kind': 'cinque-v3-ort-cpu-reference',
                'status': 'ORT_REFERENCE_COMPLETE', 'source': isolation.V3_IDENTITY,
                'frames': FRAMES, 'seed': SEED, 'mode': 'independent-recurrent',
                'contract': contract, 'files': files,
                'input_generator': verify.file_identity(Path(verify.__file__)),
                'runtime': {'onnxruntime': ort_version, 'python': sys.version,
                            'providers': list(providers), 'requested_provider': 'CPUExecutionProvider'},
                'acceptance': 'REFERENCE_ONLY: no TRT result or tolerance'}
    with (output / 'manifest.json').open('x', encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return manifest


def read_arrays(path, outputs):
    """Check archive names and NPY headers before allocating any array."""
    with zipfile.ZipFile(path) as archive:
        entries = archive.infolist()
        if (len(entries) != len(outputs)
                or {entry.filename for entry in entries} != {n + '.npy' for n in outputs}):
            raise ValueError('reference array names/duplicates mismatch')
        for name, info in outputs.items():
            entry = archive.getinfo(name + '.npy')
            nbytes = int(np.prod(info['shape'])) * np.dtype(info['dtype']).itemsize
            if entry.compress_type != zipfile.ZIP_STORED or not nbytes <= entry.file_size <= nbytes + 4096:
                raise ValueError('unexpected reference compression/array size')
            with archive.open(entry) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=4096)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream, max_header_size=4096)
                else:
                    raise ValueError('unsupported reference NPY format')
                if shape != tuple(info['shape']) or dtype != np.dtype(info['dtype']) or dtype.hasobject:
                    raise ValueError('reference array header shape/dtype mismatch')
    with np.load(path, allow_pickle=False, max_header_size=4096) as archive:
        arrays = {name: archive[name].copy() for name in outputs}
    verify.validate_outputs(arrays, outputs)
    return arrays


def validate_reference(directory, contract):
    """Validate every file before any GPU session is opened."""
    directory = plain_path(directory)
    manifest = json.loads(plain_path(directory / 'manifest.json').read_text())
    if (not isinstance(manifest, dict) or manifest.get('schema') != 1
            or manifest.get('kind') != 'cinque-v3-ort-cpu-reference'
            or manifest.get('status') != 'ORT_REFERENCE_COMPLETE'
            or manifest.get('source') != isolation.V3_IDENTITY
            or type(manifest.get('frames')) is not int or manifest['frames'] != FRAMES
            or type(manifest.get('seed')) is not int or manifest['seed'] != SEED
            or manifest.get('mode') != 'independent-recurrent'
            or manifest.get('contract') != contract
            or manifest.get('input_generator') != verify.file_identity(Path(verify.__file__))):
        raise ValueError('reference manifest identity/sequence/contract mismatch')
    runtime = manifest.get('runtime')
    if (not isinstance(runtime, dict) or not isinstance(runtime.get('onnxruntime'), str)
            or runtime.get('providers') != ['CPUExecutionProvider']
            or runtime.get('requested_provider') != 'CPUExecutionProvider'):
        raise ValueError('reference did not use explicit ORT CPU provider')
    files = manifest.get('files')
    if not isinstance(files, list) or len(files) != FRAMES:
        raise ValueError('reference frame list incomplete')
    for frame, entry in enumerate(files):
        if (not isinstance(entry, dict) or type(entry.get('frame')) is not int or entry['frame'] != frame
                or entry.get('name') != f'frame-{frame:04d}.npz'
                or entry.get('tensors') != contract['outputs']):
            raise ValueError('reference frame identity/contract mismatch')
        path = plain_path(directory / entry['name'])
        if verify.file_identity(path) != {k: entry.get(k) for k in ('sha256', 'nbytes')}:
            raise ValueError('reference file hash/size mismatch')
        read_arrays(path, contract['outputs'])
    return manifest


def validate_base_report(path, engine_identity, contract):
    report = json.loads(Path(path).read_text())
    if (not isinstance(report, dict) or report.get('status') != 'PASS'
            or report.get('evidence') != 'TRT_REAL/SYNTHETIC'
            or report.get('mode') != 'BASE/all-state-host-roundtrip/no-CUDA-graph'
            or report.get('engine') != engine_identity or report.get('source') != isolation.V3_IDENTITY
            or report.get('contract') != contract
            or any(report.get(field) is not True for field in (
                'all_outputs_exact_contract_and_finite', 'reset_first_frame_exact', 'reload_first_frame_exact'))
            or report.get('smoke', {}).get('frames', 0) < 10
            or report.get('stress', {}).get('frames', 0) < 1000):
        raise ValueError('BASE PASS evidence missing or bound to another engine/contract')
    return report


def measure_sequence(factory, contract, reference, manifest):
    """Run only the TRT's own state; never feed ORT reference state into TRT."""
    generation = recurrent.Generation(factory(), contract)
    rows, first, previous = [], None, None
    try:
        for frame, entry in enumerate(manifest['files']):
            path = plain_path(Path(reference) / entry['name'])
            if verify.file_identity(path) != {k: entry[k] for k in ('sha256', 'nbytes')}:
                raise ValueError('reference changed after preflight')
            left = read_arrays(path, manifest['contract']['outputs'])
            right, timing = generation.step(frame, manifest['seed'])
            stats = verify.compare_outputs(left, right, None)
            if first is None:
                first = {n: dict(v) for n, v in stats.items()}
            for name, values in stats.items():
                values['max_abs_minus_first_frame'] = values['max_abs'] - first[name]['max_abs']
                values['mean_abs_minus_first_frame'] = values['mean_abs'] - first[name]['mean_abs']
                values['max_abs_delta_previous_frame'] = 0. if previous is None else values['max_abs'] - previous[name]['max_abs']
            rows.append({'frame': frame, 'tensors': stats, 'timing': timing})
            previous = stats
        aggregate = {name: {
            'maximum_max_abs': max(row['tensors'][name]['max_abs'] for row in rows),
            'mean_frame_mean_abs': float(np.mean([row['tensors'][name]['mean_abs'] for row in rows])),
            'last_max_abs_minus_first_frame': rows[-1]['tensors'][name]['max_abs_minus_first_frame'],
        } for name in contract['outputs']}
        return {'schema': 1, 'status': 'MEASURED_NO_ACCEPTANCE', 'exit_status': 3,
                'acceptance': 'UNDETERMINED: no established tolerance',
                'comparison': 'original-ORT-CPU-vs-BASE-TRT/independent-recurrent',
                'seed': manifest['seed'], 'frame_count': len(rows), 'frames': rows,
                'aggregate': aggregate, 'generation': generation.identity,
                'all_outputs_exact_contract_and_finite': True}
    finally:
        generation.close()


def export_ort(source, spec_path, output):
    from jetlink import cinque_v3 as v3
    from onnx_meta_light import check_meta_against_spec
    spec = json.loads(Path(spec_path).read_text())
    v3.validate_spec(spec)
    if verify.file_identity(Path(source)) != isolation.V3_IDENTITY:
        raise ValueError('original V3 ONNX full hash/size mismatch')
    check_meta_against_spec(source, spec)
    output = plain_path(output)
    if output.exists() or output.is_symlink():
        raise FileExistsError('reference output already exists')
    ort = importlib.import_module('onnxruntime')
    session = verify.ort_session(ort, source)
    contract = verify.ort_contract(session)
    verify.validate_contract(contract, verify.spec_contract(spec))
    names = list(contract['outputs'])
    return export_sequence(lambda feeds: dict(zip(names, session.run(names, feeds))), contract,
                           output, ort.__version__, session.get_providers())


def measure_trt(args):
    root = recurrent.guarded_root(args.development_root)
    isolation.validate_marker(root)
    engine, spec_path, reference, base_path = [isolation.inside(root, path) for path in (
        args.engine, args.spec, args.reference_dir, args.base_report)]
    spec = json.loads(spec_path.read_text())
    metadata = recurrent.validate_artifact(engine, spec)
    raw, physical = verify.spec_contract(spec), verify.spec_contract(spec, verify.V3_RETYPES)
    # Check the manifest and each file with the shared isolated path guard.
    isolation.inside(root, reference / 'manifest.json')
    for frame in range(FRAMES): isolation.inside(root, reference / f'frame-{frame:04d}.npz')
    manifest = validate_reference(reference, raw)
    validate_base_report(base_path, metadata['cinque_v3_record']['engine'], physical)
    output = recurrent.create_output(root, args.out_dir)
    recurrent.prepare_environment(output)
    def factory():
        isolation.validate_marker(root)
        return recurrent.CudaTrtSession(engine, physical, recurrent.validate_artifact(engine, spec))
    try:
        report = measure_sequence(factory, physical, reference, manifest)
        report.update(evidence='ORT_CPU_REFERENCE/TRT_REAL_SYNTHETIC', source=isolation.V3_IDENTITY,
                      engine=metadata['cinque_v3_record']['engine'],
                      base_report=verify.file_identity(base_path),
                      reference_manifest=verify.file_identity(reference / 'manifest.json'),
                      reference_runtime=manifest['runtime'], trt_version=metadata['trt_version'],
                      device=metadata['device'], optional_optimizations='OFF', installation='DO_NOT_INSTALL')
    except Exception as exc:
        report = {'schema': 1, 'status': 'FAIL', 'exit_status': 1, 'error_type': type(exc).__name__,
                  'error': str(exc), 'acceptance': 'UNDETERMINED', 'installation': 'DO_NOT_INSTALL'}
    with (output / 'report.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_subparsers(dest='mode', required=True)
    export = modes.add_parser('export-ort', help='PC CPU reference export; original ONNX required')
    export.add_argument('--onnx', type=Path, required=True)
    export.add_argument('--spec', type=Path, required=True)
    export.add_argument('--out-dir', type=Path, required=True)
    measure = modes.add_parser('measure-trt', help='isolated Jetson BASE comparison; no ORT import')
    for name in ('development-root', 'engine', 'spec', 'reference-dir', 'base-report', 'out-dir'):
        measure.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        report = export_ort(args.onnx, args.spec, args.out_dir) if args.mode == 'export-ort' else measure_trt(args)
        result = 0 if args.mode == 'export-ort' else report['exit_status']
    except Exception as exc:
        report = {'schema': 1, 'status': 'FAIL', 'error_type': type(exc).__name__, 'error': str(exc)}
        result = 1
    print(json.dumps(report, sort_keys=True), flush=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
