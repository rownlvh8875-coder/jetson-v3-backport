#!/usr/bin/env python3
"""Standalone Cinque V3 BASE recurrence probe, with no daemon/USB/graph paths.

Consumes a STANDARD current-candidate build.py plan and its bound .json sidecar.
No model download, build, service action, ORT or PyCUDA is performed. CUDA/TRT
imports are lazy, after source/spec/path gates. All reports go into a fresh
directory beneath the explicit isolated development root. A successful probe
is synthetic TRT recurrence evidence, not ORT parity, USB or vehicle evidence.
"""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import ctypes
import importlib
import json
import os
from pathlib import Path
import re
import time
import uuid

import numpy as np

import build_trt_v3 as verify
import jetson_m1 as isolation


def load_cuda_runtime():
    try:
        return importlib.import_module('cuda.bindings.runtime')
    except ImportError:
        return importlib.import_module('cuda.cudart')


class CudaRuntime:
    def __init__(self, module=None):
        self.rt = module if module is not None else load_cuda_runtime()

    def check(self, result):
        error, *values = result if isinstance(result, tuple) else (result,)
        if error != self.rt.cudaError_t.cudaSuccess:
            raise RuntimeError(f'CUDA runtime error: {error}')
        return None if not values else values[0] if len(values) == 1 else tuple(values)

    def call(self, name, *args):
        return self.check(getattr(self.rt, name)(*args))


def validate_artifact(engine_path, spec):
    """CPU-only checks; also called immediately before each fresh load."""
    from jetlink import cinque_v3 as v3
    v3.validate_spec(spec)
    metadata = json.loads(Path(engine_path).with_suffix('.json').read_text())
    if not isinstance(metadata, dict) or metadata.get('backend') != 'trt' or metadata.get('spec') != spec:
        raise ValueError('missing or mismatched candidate artifact metadata/spec')
    if not metadata.get('trt_version') or not metadata.get('device'):
        raise ValueError('artifact runtime/device identity absent')
    record = metadata.get('cinque_v3_record')
    if (not isinstance(record, dict)
            or metadata.get('cinque_v3_record_sha256') != v3.record_digest(record)):
        raise ValueError('artifact build record digest mismatch')
    v3.validate_record(record, engine_path, spec)
    return metadata


class CudaTrtSession:
    """Plain execute_async_v3 with all-state pinned H2D/D2H, no graph capture."""
    def __init__(self, engine_path, contract, metadata):
        self.buffers, self.stream, self.events = {}, None, []
        self.context = self.engine = self.runtime = None
        self.closed = False
        self.last_timing = {}
        import tensorrt as trt
        if trt.__version__ != metadata['trt_version']:
            raise ValueError('TensorRT runtime differs from build sidecar')
        self.cuda = CudaRuntime()
        c = self.cuda
        # CUDA 12 initializes the selected primary context here, before TRT load.
        c.call('cudaSetDevice', 0)
        props = c.call('cudaGetDeviceProperties', 0)
        name = props.name.decode() if isinstance(props.name, bytes) else str(props.name)
        device = re.sub(r'[^A-Za-z0-9._-]', '_', f'{name}-sm{props.major}{props.minor}')
        if metadata['device'] != device:
            raise ValueError(f'GPU identity differs from build sidecar: {device}')
        self.logger = trt.Logger(trt.Logger.WARNING)
        try:
            plugins = getattr(trt, 'init_libnvinfer_plugins', None)
            if plugins is not None:
                plugins(self.logger, '')
            self.runtime = trt.Runtime(self.logger)
            self.engine = self.runtime.deserialize_cuda_engine(Path(engine_path).read_bytes())
            if self.engine is None:
                raise RuntimeError('engine deserialize failed')
            verify.validate_contract(verify.engine_contract(self.engine, trt), contract)
            self.contract = contract
            self.context = self.engine.create_execution_context()
            if self.context is None:
                raise RuntimeError('execution context creation failed')
            self.stream = c.call('cudaStreamCreate')
            for _ in range(2):
                self.events.append(c.call('cudaEventCreate'))
            for kind in ('inputs', 'outputs'):
                for name, info in contract[kind].items():
                    dtype, shape = np.dtype(info['dtype']), tuple(info['shape'])
                    size = int(np.prod(shape)) * dtype.itemsize
                    allocation = self.buffers[name] = {'dev': None, 'host_ptr': None, 'host': None}
                    allocation['dev'] = c.call('cudaMalloc', size)
                    allocation['host_ptr'] = c.call('cudaHostAlloc', size, 0)
                    buf = (ctypes.c_ubyte * size).from_address(int(allocation['host_ptr']))
                    allocation['host'] = np.frombuffer(buf, dtype=dtype).reshape(shape)
                    if not self.context.set_tensor_address(name, int(allocation['dev'])):
                        raise RuntimeError(f'set_tensor_address failed: {name}')
        except BaseException:
            self.close()
            raise

    def run(self, feeds):
        if self.closed:
            raise RuntimeError('closed CUDA session')
        verify.validate_outputs(feeds, self.contract['inputs'])
        c, rt = self.cuda, self.cuda.rt
        start = time.perf_counter()
        for name in self.contract['inputs']:
            b = self.buffers[name]
            np.copyto(b['host'], feeds[name], casting='no')
            c.call('cudaMemcpyAsync', b['dev'], b['host_ptr'], b['host'].nbytes,
                   rt.cudaMemcpyKind.cudaMemcpyHostToDevice, self.stream)
        c.call('cudaEventRecord', self.events[0], self.stream)
        enqueue_start = time.perf_counter()
        if not self.context.execute_async_v3(int(self.stream)):
            raise RuntimeError('execute_async_v3 failed')
        enqueue_ms = (time.perf_counter() - enqueue_start) * 1000
        c.call('cudaEventRecord', self.events[1], self.stream)
        for name in self.contract['outputs']:
            b = self.buffers[name]
            c.call('cudaMemcpyAsync', b['host_ptr'], b['dev'], b['host'].nbytes,
                   rt.cudaMemcpyKind.cudaMemcpyDeviceToHost, self.stream)
        c.call('cudaStreamSynchronize', self.stream)
        completed_ms = (time.perf_counter() - start) * 1000
        gpu_ms = float(c.call('cudaEventElapsedTime', *self.events))
        self.last_timing = {'enqueue_ms': enqueue_ms, 'gpu_execute_ms': gpu_ms,
                            'completed_h2d_execute_d2h_ms': completed_ms}
        return {name: self.buffers[name]['host'].copy() for name in self.contract['outputs']}

    def close(self):
        if self.closed:
            return
        self.closed = True
        error = None
        c = self.cuda
        # A failed enqueue/copy may leave pending work: synchronize before free.
        if self.stream is not None:
            try: c.call('cudaStreamSynchronize', self.stream)
            except BaseException as exc: error = exc
        self.context = None
        for b in self.buffers.values():
            b['host'] = None
            for field, free in (('dev', 'cudaFree'), ('host_ptr', 'cudaFreeHost')):
                if b[field] is not None:
                    try: c.call(free, b[field])
                    except BaseException as exc: error = error or exc
        self.buffers.clear()
        for event in self.events:
            try: c.call('cudaEventDestroy', event)
            except BaseException as exc: error = error or exc
        self.events.clear()
        if self.stream is not None:
            try: c.call('cudaStreamDestroy', self.stream)
            except BaseException as exc: error = error or exc
        self.stream = self.engine = self.runtime = None
        if error is not None:
            raise error


class Generation:
    def __init__(self, session, contract):
        self.session, self.contract = session, contract
        self.identity, self.valid = uuid.uuid4().hex, True
        self.states = {n: np.zeros(v['shape'], v['dtype']) for n, v in contract['inputs'].items()
                       if n.startswith('state_')}

    def require_valid(self):
        if not self.valid:
            raise RuntimeError('invalid generation; close and reload required')

    def reset(self):
        self.require_valid()
        try:
            for state in self.states.values(): state.fill(0)
            if any(np.any(state) for state in self.states.values()):
                raise ValueError('state reset did not produce all zeros')
        except BaseException:
            self.valid = False
            raise

    def step(self, frame, seed):
        self.require_valid()
        start = time.perf_counter()
        try:
            feeds = verify.frame_inputs(self.contract['inputs'], frame, seed)
            for name, state in self.states.items(): np.copyto(feeds[name], state, casting='no')
            outputs = self.session.run(feeds)
            verify.validate_outputs(outputs, self.contract['outputs'])
            # advance_state validates every pair before copying. Publish only
            # the complete new state dictionary, and retire on any copy failure.
            verify.advance_state(feeds, outputs)
            pending = {n: feeds[n] for n in self.states}
            self.states = pending
            timing = dict(self.session.last_timing)
            timing['host_roundtrip_ms'] = (time.perf_counter() - start) * 1000
            return outputs, timing
        except BaseException:
            self.valid = False
            raise

    def close(self):
        self.valid = False
        self.session.close()


def memory_snapshot():
    result = {'process_rss_bytes': None, 'process_high_water_bytes': None,
              'system_available_bytes': None}
    for filename, fields in (
        ('/proc/self/status', {'VmRSS:': 'process_rss_bytes', 'VmHWM:': 'process_high_water_bytes'}),
        ('/proc/meminfo', {'MemAvailable:': 'system_available_bytes'}),
    ):
        try:
            for line in Path(filename).read_text().splitlines():
                words = line.split()
                if words and words[0] in fields:
                    result[fields[words[0]]] = int(words[1]) * 1024
        except OSError:
            pass
    return result


def aggregate(rows):
    result = {'frames': len(rows)}
    for key in sorted({k for row in rows for k in row}):
        values = np.array([row[key] for row in rows if key in row], dtype=np.float64)
        if not np.all(np.isfinite(values)) or np.any(values < 0):
            raise ValueError('invalid latency measurement')
        result[key] = dict(samples=len(values), p50=float(np.percentile(values, 50)),
                           p95=float(np.percentile(values, 95)), p99=float(np.percentile(values, 99)),
                           maximum=float(values.max()), mean=float(values.mean()))
    result['frames_over_50ms'] = sum(row['host_roundtrip_ms'] > 50 for row in rows)
    return result


def require_replay(reference, outputs):
    if set(reference) != set(outputs) or any(not np.array_equal(reference[n], outputs[n]) for n in reference):
        raise ValueError('deterministic first-frame replay differs after reset/reload')


def run_exercise(factory, contract, smoke_frames=10, stress_frames=1000, seed=73, per_frame=None):
    verify.validate_arguments(smoke_frames, None)
    verify.validate_arguments(stress_frames, None)
    generations, first = [], None
    report = {'schema': 1, 'status': 'FAIL', 'seed': seed, 'generations': generations,
              'mode': 'BASE/all-state-host-roundtrip/no-CUDA-graph',
              'parity': 'SKIP: no ORT reference comparison',
              'latency_acceptance': 'SKIP: measurements only; no end-to-end/USB claim'}
    generation = None
    try:
        generation = Generation(factory(), contract)
        generations.append(generation.identity)
        for phase, count in (('smoke', smoke_frames), ('stress', stress_frames)):
            if phase == 'stress':
                generation.reset()
                replay, _ = generation.step(0, seed)
                require_replay(first, replay)
                report['reset_first_frame_exact'] = True
                generation.reset()
            rows, memory = [], [memory_snapshot()]
            for frame in range(count):
                outputs, timing = generation.step(frame, seed)
                if phase == 'smoke' and frame == 0:
                    first = {n: x.copy() for n, x in outputs.items()}
                rows.append(timing)
                if per_frame is not None:
                    per_frame({'phase': phase, 'frame': frame, 'generation': generation.identity, **timing})
                if frame % 50 == 49: memory.append(memory_snapshot())
            memory.append(memory_snapshot())
            report[phase] = aggregate(rows)
            report[phase]['memory'] = {
                'start': memory[0], 'end': memory[-1],
                'max_sampled_process_rss_bytes': max((m['process_rss_bytes'] or 0) for m in memory),
                'minimum_sampled_system_available_bytes': min(
                    (m['system_available_bytes'] for m in memory if m['system_available_bytes'] is not None),
                    default=None),
                'samples': len(memory),
            }
        generation.close()
        generation = None
        generation = Generation(factory(), contract)
        generations.append(generation.identity)
        generation.reset()
        replay, _ = generation.step(0, seed)
        require_replay(first, replay)
        report.update(reload_first_frame_exact=True, all_outputs_exact_contract_and_finite=True)
        generation.close()
        generation = None
        report['status'] = 'PASS'
        return report
    finally:
        if generation is not None: generation.close()


def guarded_root(root):
    root = isolation.validate_root(root)
    legacy_cache = Path('/mnt/data/jetlink')
    if root == legacy_cache or legacy_cache in root.parents or root in legacy_cache.parents:
        raise ValueError('protected runtime/cache overlaps development root')
    return root.resolve(strict=True)


def beneath(root, path):
    return isolation.inside(guarded_root(root), path)


def create_output(development_root, output):
    root = guarded_root(development_root)
    if not root.is_dir() or root == Path(root.anchor):
        raise ValueError('development root must be a dedicated existing directory')
    output = beneath(root, output)
    if not output.parent.is_dir():
        raise ValueError('output parent must already exist inside development root')
    output.mkdir(exist_ok=False)
    return output


def prepare_environment(output):
    """Keep implicit CUDA/library caches and temporary files inside the report."""
    for variable, name in (('CUDA_CACHE_PATH', 'cuda-cache'), ('TMPDIR', 'tmp'),
                           ('XDG_CACHE_HOME', 'cache'), ('HOME', 'home')):
        path = Path(output) / name
        path.mkdir(exist_ok=False)
        os.environ[variable] = str(path)
    os.environ['PYTHONDONTWRITEBYTECODE'] = '1'
    for flag in ('CARROT_TRT_DEVICE_STATE', 'CARROT_TRT_INPUT_FASTPATH', 'CARROT_JETLINK_AIO_WRITE'):
        os.environ[flag] = '0'
    import tempfile
    tempfile.tempdir = os.environ['TMPDIR']


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--development-root', required=True, type=Path)
    parser.add_argument('--engine', required=True, type=Path)
    parser.add_argument('--onnx', required=True, type=Path)
    parser.add_argument('--spec', required=True, type=Path)
    parser.add_argument('--out-dir', required=True, type=Path)
    parser.add_argument('--smoke-frames', type=int, default=10)
    parser.add_argument('--stress-frames', type=int, default=1000)
    parser.add_argument('--seed', type=int, default=73)
    parser.add_argument('--per-frame', action='store_true')
    args = parser.parse_args(argv)
    output, frame_file = None, None
    try:
        verify.validate_arguments(args.smoke_frames, None)
        verify.validate_arguments(args.stress_frames, None)
        args.development_root = guarded_root(args.development_root)
        isolation.validate_marker(args.development_root)
        for name in ('engine', 'onnx', 'spec'):
            setattr(args, name, beneath(args.development_root, getattr(args, name)))
        spec = json.loads(args.spec.read_text())
        metadata = validate_artifact(args.engine, spec)
        if verify.file_identity(args.onnx) != {k: spec[k] for k in ('sha256', 'nbytes')}:
            raise ValueError('original ONNX hash/size mismatch')
        from onnx_meta_light import check_meta_against_spec
        check_meta_against_spec(args.onnx, spec)
        contract = verify.spec_contract(spec, verify.V3_RETYPES)
        output = create_output(args.development_root, args.out_dir)
        prepare_environment(output)
        if args.per_frame:
            frame_file = (output / 'frames.jsonl').open('x', encoding='utf-8')
        def factory():
            return CudaTrtSession(args.engine, contract, validate_artifact(args.engine, spec))
        def emit(row):
            if frame_file is not None:
                frame_file.write(json.dumps(row, sort_keys=True) + '\n')
                frame_file.flush()
        report = run_exercise(factory, contract, args.smoke_frames, args.stress_frames, args.seed, emit)
        report.update(evidence='TRT_REAL/SYNTHETIC', source=metadata['cinque_v3_record']['source'],
                      engine=metadata['cinque_v3_record']['engine'], contract=contract,
                      runtime_version=metadata['trt_version'], device=metadata['device'],
                      command=sys.argv if argv is None else argv,
                      probe=verify.file_identity(Path(__file__)))
        result = 0
    except Exception as exc:
        report = {'schema': 1, 'status': 'FAIL', 'error_type': type(exc).__name__, 'error': str(exc),
                  'parity': 'SKIP', 'vehicle_usb_validation': 'SKIP'}
        result = 1
    finally:
        if frame_file is not None: frame_file.close()
    if output is not None:
        with (output / 'report.json').open('x', encoding='utf-8') as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write('\n')
    print(json.dumps(report, sort_keys=True), flush=True)
    return result


if __name__ == '__main__':
    raise SystemExit(main())
