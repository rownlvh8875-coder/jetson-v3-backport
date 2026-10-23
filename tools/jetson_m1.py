#!/usr/bin/env python3
"""Guarded, isolated development build using the existing current TRT builder.

Never starts a server or publishes to the operating cache. The caller must
provide the standard candidate jetlink on PYTHONPATH and an already-approved
new development directory. Physical hardware results remain DO_NOT_INSTALL.
"""
from __future__ import annotations

import argparse
import sys
sys.dont_write_bytecode = True
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import stat
import subprocess
import time

MIN_FREE = 6 << 30
PROTECTED = (Path('/opt/carrot-jetlink'), Path('/run/carrot-data/runtime'))
V3_IDENTITY = {'sha256': '404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4', 'nbytes': 766354845}


class GateError(ValueError):
    pass


def storage_gate(available: int, minimum: int = MIN_FREE) -> None:
    if available < minimum:
        raise GateError(f'BLOCKED_STORAGE: available={available}, required={minimum}')


def file_identity(path: Path) -> dict:
    digest, count = hashlib.sha256(), 0
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(4 << 20), b''):
            digest.update(block)
            count += len(block)
    return {'sha256': digest.hexdigest(), 'nbytes': count}


def identity_gate(path: Path, expected: dict) -> dict:
    actual = file_identity(path)
    if actual != expected:
        raise GateError(f'FAIL_IDENTITY: actual={actual}, expected={expected}')
    return actual


def validate_root(root: Path) -> Path:
    root = Path(root).absolute()
    resolved = root.resolve()
    if root != resolved:
        raise GateError('ISOLATION: development root contains a symlink')
    for protected in PROTECTED:
        p = protected.resolve()
        if resolved == p or resolved.is_relative_to(p) or p.is_relative_to(resolved):
            raise GateError('ISOLATION: development root overlaps operating runtime or bind alias')
    return resolved


def inside(root: Path, path: Path) -> Path:
    root = validate_root(root)
    path = Path(path).absolute()
    resolved = path.resolve()
    if path != resolved or resolved == root or not resolved.is_relative_to(root):
        raise GateError('ISOLATION: path escape or symlink')
    return resolved


def new_output(root: Path, path: Path) -> Path:
    path = inside(root, path)
    if path.exists() or path.is_symlink():
        raise GateError('COLLISION: preserve previous output')
    return path


def validate_marker(root: Path) -> None:
    root = validate_root(root)
    marker = root / '.m1-isolated.json'
    try:
        directory, entry = root.stat(), marker.lstat()
        if (directory.st_uid != os.getuid() or directory.st_mode & 0o077
                or not stat.S_ISREG(entry.st_mode) or entry.st_uid != os.getuid() or entry.st_mode & 0o077):
            raise ValueError('root/marker ownership or permissions')
        value = json.loads(marker.read_text())
        if (value.get('schema') != 1 or value.get('development_root') != str(root)
                or value.get('identity') != V3_IDENTITY or value.get('do_not_install') is not True):
            raise ValueError('marker belongs to another root/identity')
    except (OSError, ValueError, TypeError) as exc:
        raise GateError('ISOLATION: approved private root marker required') from exc


def classify_error(message: str, stage: str) -> str:
    text = message.lower()
    if 'out of memory' in text or 'out_of_memory' in text or 'bad_alloc' in text:
        return 'OUT_OF_MEMORY'
    if 'no space left' in text or 'disk' in text and 'full' in text:
        return 'STORAGE_ERROR'
    if 'cuda' in text:
        return 'CUDA_ERROR'
    if stage == 'patch':
        return 'ONNX_PATCH_ERROR'
    if 'parse' in text or 'unsupported operator' in text:
        return 'PARSER_UNSUPPORTED'
    if 'internal error' in text and ('trt' in text or 'tensorrt' in text):
        return 'TRT_INTERNAL_ERROR'
    return 'UNKNOWN'


def check_offroad_lease(path: Path, now=None, maximum_age=30) -> None:
    """Controller observation, refreshed from comma; never a fake True provider."""
    try:
        value = json.loads(Path(path).read_text())
        age = (time.monotonic() if now is None else now) - value['issued_monotonic']
        if value['IsOffroad'] != '1' or value['IsOnroad'] != '0' or not 0 <= age <= maximum_age:
            raise ValueError('unsafe, stale or future observation')
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise GateError('OFFROAD: fresh safe controller observation required') from exc


def run_guarded(command, authorize, sink, poll=1.0) -> int:
    """Monitor only our own child; terminate it on any lost authorization."""
    authorize()
    interrupted = []
    def on_signal(signum, _frame):
        # Defer raising until Popen has returned its owned handle, including
        # a signal delivered during process creation.
        interrupted.append(signum)
    signals = (signal.SIGTERM, signal.SIGHUP)
    previous = {sig: signal.signal(sig, on_signal) for sig in signals}
    child = None
    try:
        child = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=sink, stderr=subprocess.STDOUT,
                                 start_new_session=True)
        while True:
            if interrupted:
                raise GateError('OFFROAD: supervisor shutdown; retiring owned child')
            authorize()
            code = child.poll()
            if code is not None:
                return code
            time.sleep(poll)
    except BaseException:
        if child is not None and child.poll() is None:
            os.killpg(child.pid, signal.SIGTERM)
            try:
                child.wait(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
        raise
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def memory_snapshot() -> dict:
    result = {}
    for line in Path('/proc/meminfo').read_text().splitlines():
        key, value = line.split(':', 1)
        if key in ('MemTotal', 'MemAvailable', 'SwapTotal', 'SwapFree'):
            result[key] = int(value.strip().split()[0]) * 1024
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development-root', type=Path, required=True)
    parser.add_argument('--onnx', type=Path, required=True)
    parser.add_argument('--spec', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--offroad-lease', type=Path, required=True)
    parser.add_argument('--workspace-mib', type=int, default=1536)
    args = parser.parse_args(argv)
    if args.workspace_mib <= 0:
        parser.error('workspace must be positive')
    root = validate_root(args.development_root)
    lease = inside(root, args.offroad_lease)
    check_offroad_lease(lease)
    validate_marker(root)
    source, spec_path = inside(root, args.onnx), inside(root, args.spec)
    out = new_output(root, args.out)
    new_output(root, out.with_suffix('.json'))
    result_path = new_output(root, out.parent / 'm1-build-result.json')
    patched_path = new_output(root, out.parent / 'cinque-v3-patched.onnx')
    storage_gate(shutil.disk_usage(root).free)
    spec = json.loads(spec_path.read_text())
    if {k: spec.get(k) for k in V3_IDENTITY} != V3_IDENTITY:
        raise GateError('FAIL_IDENTITY: requested spec is not exact Cinque V3')
    identity_gate(source, V3_IDENTITY)
    out.parent.mkdir(parents=True, exist_ok=True)
    for name in ('tmp', 'home', 'cache', 'cuda-cache'):
        inside(root, root / name).mkdir(exist_ok=True)
    os.environ.update(PYTHONDONTWRITEBYTECODE='1', TMPDIR=str(root / 'tmp'), HOME=str(root / 'home'),
                      XDG_CACHE_HOME=str(root / 'cache'), CUDA_CACHE_PATH=str(root / 'cuda-cache'),
                      CARROT_TRT_DEVICE_STATE='0', CARROT_TRT_INPUT_FASTPATH='0', CARROT_JETLINK_AIO_WRITE='0')
    import tempfile
    tempfile.tempdir = str(root / 'tmp')
    result = {'schema': 1, 'evidence': ['TRT_REAL_PRECHECK', 'TRT_REAL', 'JETSON_REAL'],
              'status': 'TRT_BUILD_FAIL', 'installation': 'DO_NOT_INSTALL', 'source': V3_IDENTITY,
              'workspace_bytes': args.workspace_mib << 20, 'fp16': True, 'optimization_level': 3,
              'timing_cache': 'NONE: cold build; operating timing cache never opened',
              'optional_optimizations': 'OFF', 'memory_before': memory_snapshot()}
    stage, started = 'contract', time.monotonic()
    try:
        from jetlink import cinque_v3 as v3
        v3.validate_source(source, spec)
        result['semantic_contract'] = 'PASS: exact identity, names/shapes/dtypes/slices/checkpoint and3 state pairs'
        stage = 'patch'
        from jetlink.onnx_patch import patch_file
        patch_file(str(source), str(patched_path), spec=spec)
        v3.validate_graph_file(patched_path, spec, patched=True)
        result['patched'] = file_identity(patched_path)
        stage = 'precheck'
        check_offroad_lease(lease)
        import tensorrt as trt
        from jetlink.server.backends.trt import cudart, build
        if not trt.__version__.startswith('10.3.'):
            raise GateError('TensorRT version is not10.3; no upgrade allowed')
        cudart.set_device(0)
        name, major, minor = cudart.device_name(0)
        if (major, minor) != (8, 7):
            raise GateError('Unexpected GPU architecture; build refused')
        logger = trt.Logger(trt.Logger.WARNING)
        builder = trt.Builder(logger)
        network = builder.create_network(build.network_flags())
        onnx_parser = trt.OnnxParser(network, logger)
        result['precheck'] = {'status': 'PASS', 'evidence': 'TRT_REAL_PRECHECK', 'tensorrt': trt.__version__,
                              'gpu': name, 'compute_capability': [major, minor], 'parser_created': onnx_parser is not None}
        del onnx_parser, network, builder
        def authorize():
            # No daemon/provider is fabricated: this is the explicit offline M1
            # build, with live observations refreshed by its SSH controller.
            check_offroad_lease(lease)
            storage_gate(shutil.disk_usage(root).free)
            if out.exists() or out.with_suffix('.json').exists():
                raise GateError('COLLISION: output appeared during build')
        def progress(phase, fraction, detail):
            print(json.dumps({'phase': phase, 'fraction': fraction, 'detail': detail}), flush=True)
        stage = 'build'
        build.build_engine(source, out, report=progress, fp16=True, optimization_level=3,
                           workspace=args.workspace_mib << 20, meta_extra={'spec': spec},
                           timing_cache=None, authorize=authorize)
        sidecar = json.loads(out.with_suffix('.json').read_text())
        record = sidecar['cinque_v3_record']
        v3.validate_record(record, out, spec)
        if record['patched'] != result['patched']:
            raise GateError('ONNX_PATCH_ERROR: saved patch differs from parser-bound record')
        result.update(status='TRT_BUILD_PASS', engine=file_identity(out), builder_seconds=sidecar['build_seconds'],
                      trt_record_digest=sidecar['cinque_v3_record_sha256'], build_exit_status=0)
    except Exception as exc:
        result.update(failure_stage=stage, failure_class=classify_error(str(exc), stage),
                      error_type=type(exc).__name__, error=str(exc), build_exit_status=1)
    finally:
        result.update(elapsed_seconds=time.monotonic() - started, memory_after=memory_snapshot())
        with result_path.open('x', encoding='utf-8') as stream:
            json.dump(result, stream, indent=2)
        print(json.dumps(result), flush=True)
    return result['build_exit_status']


if __name__ == '__main__':
    raise SystemExit(main())
