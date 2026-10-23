"""CPU boundary tests for the standalone BASE probe; no hardware evidence."""
from __future__ import annotations

import copy
import ctypes
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_help_needs_no_cuda_trt_or_ort_packages():
    result = subprocess.run([sys.executable, str(ROOT / 'tools/jetson_m1_recurrent.py'), '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert '--development-root' in result.stdout


@pytest.fixture
def probe():
    path = ROOT / 'tools/jetson_m1_recurrent.py'
    assert path.is_file(), 'standalone BASE probe is not implemented'
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        spec = importlib.util.spec_from_file_location('m1_probe', path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        yield module
    finally:
        sys.path.pop(0)


@pytest.fixture
def contract():
    return {
        'inputs': {
            'new_img': {'shape': [2], 'dtype': 'float16'},
            'desire': {'shape': [8], 'dtype': 'float32'},
            'traffic_convention': {'shape': [1, 2], 'dtype': 'float32'},
            'action_t': {'shape': [1, 2], 'dtype': 'float32'},
            'state_img_q': {'shape': [2], 'dtype': 'float16'},
            'state_desire_q': {'shape': [2], 'dtype': 'float32'},
            'state_feat_q': {'shape': [2], 'dtype': 'float32'},
        },
        'outputs': {
            'outputs': {'shape': [2], 'dtype': 'float32'},
            'next_state_img_q': {'shape': [2], 'dtype': 'float16'},
            'next_state_desire_q': {'shape': [2], 'dtype': 'float32'},
            'next_state_feat_q': {'shape': [2], 'dtype': 'float32'},
        },
    }


class CpuBoundary:
    def __init__(self, contract, fault=None):
        self.contract, self.fault, self.closed = contract, fault, False
        self.last_timing = {'gpu_execute_ms': 1., 'completed_h2d_execute_d2h_ms': 2.}
        self.seen = []

    def run(self, feeds):
        self.seen.append({n: x.copy() for n, x in feeds.items()})
        result = {n: np.ones(v['shape'], v['dtype']) for n, v in self.contract['outputs'].items()}
        for n in ('state_img_q', 'state_desire_q', 'state_feat_q'):
            result['next_' + n] = feeds[n] + np.array(1, dtype=feeds[n].dtype)
        if self.fault is not None:
            self.fault(result)
        return result

    def close(self):
        self.closed = True


def test_recurrence_reset_replay_and_fresh_reload(probe, contract):
    sessions = []
    def factory():
        sessions.append(CpuBoundary(contract))
        return sessions[-1]
    report = probe.run_exercise(factory, contract, smoke_frames=10, stress_frames=1000)
    assert report['status'] == 'PASS'
    assert report['smoke']['frames'] == 10
    assert report['stress']['frames'] == 1000
    assert report['stress']['host_roundtrip_ms']['samples'] == 1000
    assert report['stress']['host_roundtrip_ms']['p99'] >= 0
    assert report['reset_first_frame_exact'] and report['reload_first_frame_exact']
    assert report['generations'][0] != report['generations'][1]
    assert all(s.closed for s in sessions)
    assert sessions[0].seen[9]['state_feat_q'].tolist() == [9., 9.]
    assert sessions[0].seen[10]['state_feat_q'].tolist() == [0., 0.]
    assert sessions[1].seen[0]['state_feat_q'].tolist() == [0., 0.]
    assert report['stress']['memory']['start']['process_rss_bytes'] > 0


@pytest.mark.parametrize('name,kind', [
    ('outputs', 'nan'), ('next_state_img_q', 'inf'),
    ('next_state_desire_q', 'shape'), ('next_state_feat_q', 'dtype'),
    ('next_state_feat_q', 'missing'),
])
def test_all_output_faults_invalidate_before_any_state_commit(probe, contract, name, kind):
    def fault(outputs):
        if kind == 'nan': outputs[name][0] = np.nan
        elif kind == 'inf': outputs[name][0] = np.inf
        elif kind == 'shape': outputs[name] = outputs[name].reshape(1, 2)
        elif kind == 'dtype': outputs[name] = outputs[name].astype(np.float16)
        else: outputs.pop(name)
    generation = probe.Generation(CpuBoundary(contract, fault), contract)
    before = {n: x.copy() for n, x in generation.states.items()}
    with pytest.raises(ValueError): generation.step(0, 73)
    assert generation.valid is False
    for name, value in before.items(): np.testing.assert_array_equal(generation.states[name], value)
    with pytest.raises(RuntimeError, match='invalid'): generation.step(1, 73)
    with pytest.raises(RuntimeError, match='invalid'): generation.reset()


def test_partial_commit_failure_cannot_reuse_generation(probe, contract, monkeypatch):
    generation = probe.Generation(CpuBoundary(contract), contract)
    def fail_copy(feeds, outputs):
        feeds['state_img_q'][:] = outputs['next_state_img_q']
        raise RuntimeError('injected copy failure')
    monkeypatch.setattr(probe.verify, 'advance_state', fail_copy)
    with pytest.raises(RuntimeError, match='copy failure'): generation.step(0, 73)
    assert generation.valid is False
    assert not np.any(generation.states['state_img_q'])
    with pytest.raises(RuntimeError, match='invalid'): generation.step(0, 73)


def test_failure_closes_session_and_deterministic_reset_is_checked(probe, contract):
    session = CpuBoundary(contract)
    runs = [0]
    def vary(outputs):
        runs[0] += 1
        outputs['outputs'].fill(runs[0])
    session.fault = vary
    with pytest.raises(ValueError, match='replay'):
        probe.run_exercise(lambda: session, contract, smoke_frames=2, stress_frames=2)
    assert session.closed


def test_cuda_binding_new_namespace_and_legacy_fallback(probe, monkeypatch):
    sentinel = object()
    calls = []
    def import_new(name):
        calls.append(name)
        return sentinel
    monkeypatch.setattr(probe.importlib, 'import_module', import_new)
    assert probe.load_cuda_runtime() is sentinel
    assert calls == ['cuda.bindings.runtime']
    calls.clear()
    def import_old(name):
        calls.append(name)
        if name == 'cuda.bindings.runtime': raise ImportError('old CUDA wheel')
        return sentinel
    monkeypatch.setattr(probe.importlib, 'import_module', import_old)
    assert probe.load_cuda_runtime() is sentinel
    assert calls == ['cuda.bindings.runtime', 'cuda.cudart']


def test_cuda_errors_are_never_ignored(probe):
    cuda = probe.CudaRuntime(NS(cudaError_t=NS(cudaSuccess=0)))
    assert cuda.check((0, 12)) == 12
    with pytest.raises(RuntimeError, match='CUDA'): cuda.check((7, 99))


def test_driver_and_temp_caches_stay_in_new_output(probe, tmp_path, monkeypatch):
    monkeypatch.setenv('CUDA_CACHE_PATH', '/must-not-write/global-cache')
    monkeypatch.setenv('TMPDIR', str(tmp_path))
    monkeypatch.setenv('XDG_CACHE_HOME', str(tmp_path))
    monkeypatch.setenv('PYTHONDONTWRITEBYTECODE', '1')
    monkeypatch.setenv('HOME', str(tmp_path))
    for flag in ('CARROT_TRT_DEVICE_STATE', 'CARROT_TRT_INPUT_FASTPATH', 'CARROT_JETLINK_AIO_WRITE'):
        monkeypatch.setenv(flag, '1')
    import tempfile
    monkeypatch.setattr(tempfile, 'tempdir', '/previously-cached-global-temp')
    probe.prepare_environment(tmp_path)
    import os
    assert Path(os.environ['CUDA_CACHE_PATH']).parent == tmp_path
    assert Path(os.environ['TMPDIR']).parent == tmp_path
    assert Path(os.environ['XDG_CACHE_HOME']).parent == tmp_path
    assert Path(os.environ['HOME']).parent == tmp_path
    assert tempfile.tempdir == os.environ['TMPDIR']
    assert all(os.environ[n] == '0' for n in (
        'CARROT_TRT_DEVICE_STATE', 'CARROT_TRT_INPUT_FASTPATH', 'CARROT_JETLINK_AIO_WRITE'))


def test_protected_runtime_root_is_refused(probe, monkeypatch):
    with pytest.raises(ValueError):
        probe.create_output(Path('/opt/carrot-jetlink'), Path('/opt/carrot-jetlink/probe'))


@pytest.mark.parametrize('root', ['/run/carrot-data/runtime', '/run/carrot-data', '/run', '/opt',
                                 '/mnt/data/jetlink', '/mnt/data'])
def test_operating_aliases_and_their_ancestors_are_refused_before_existence(probe, root):
    with pytest.raises(ValueError):
        probe.create_output(Path(root), Path(root) / 'probe')


def test_symlink_root_output_and_source_are_refused(probe, tmp_path):
    root = tmp_path / 'dev'
    root.mkdir()
    alias = tmp_path / 'alias'
    alias.symlink_to(root, target_is_directory=True)
    with pytest.raises(ValueError): probe.create_output(alias, alias / 'report')
    real = root / 'real'
    real.mkdir()
    linked = root / 'linked'
    linked.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError): probe.create_output(root, linked / 'report')
    source = root / 'source.onnx'
    source.write_bytes(b'fixture')
    source_alias = root / 'source-alias.onnx'
    source_alias.symlink_to(source)
    with pytest.raises(ValueError): probe.beneath(root, source_alias)


def test_cli_requires_exact_isolation_marker_before_gpu_or_artifact_load(probe, tmp_path, monkeypatch):
    def forbid_artifact(*args): pytest.fail('marker must be checked before artifact/GPU paths')
    monkeypatch.setattr(probe, 'validate_artifact', forbid_artifact)
    arguments = ['--development-root', str(tmp_path), '--engine', str(tmp_path / 'e.plan'),
                 '--onnx', str(tmp_path / 'source.onnx'), '--spec', str(tmp_path / 'spec.json'),
                 '--out-dir', str(tmp_path / 'out')]
    (tmp_path / 'spec.json').write_text('{}')
    tmp_path.chmod(0o700)
    for marker in (None, {}, {'identity': {}, 'do_not_install': True},
                   {'identity': {'sha256': '404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4',
                                 'nbytes': 766354845}, 'do_not_install': False},
                   {'schema': 1, 'development_root': str(tmp_path / 'another-root'),
                    'identity': {'sha256': '404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4',
                                 'nbytes': 766354845}, 'do_not_install': True}):
        if marker is not None:
            (tmp_path / '.m1-isolated.json').write_text(json.dumps(marker))
            (tmp_path / '.m1-isolated.json').chmod(0o600)
        assert probe.main(arguments) == 1
        assert not (tmp_path / 'out').exists()


def test_existing_or_escaped_output_is_refused_before_any_gpu_import(probe, tmp_path, monkeypatch):
    existing = tmp_path / 'existing'
    existing.mkdir()
    with pytest.raises((ValueError, FileExistsError)):
        probe.create_output(tmp_path, existing)
    outside = tmp_path.parent / 'outside'
    with pytest.raises(ValueError): probe.create_output(tmp_path, outside)
    nested = probe.create_output(tmp_path, tmp_path / 'fresh')
    assert nested.is_dir()
    assert 'tensorrt' not in sys.modules


def test_contract_and_record_fail_closed(probe, tmp_path):
    from jetlink import cinque_v3 as v3
    spec = copy.deepcopy(v3.CANONICAL_SPEC)
    engine = tmp_path / 'test.plan'
    engine.write_bytes(b'CPU fixture, not an engine')
    record = dict(source={k: spec[k] for k in ('sha256', 'nbytes')},
                  patched={'sha256': 'a' * 64, 'nbytes': 1},
                  engine=probe.verify.file_identity(engine), patch_id=v3.PATCH_ID,
                  semantic_spec=spec, dtype_transforms=v3.DTYPE_TRANSFORMS)
    metadata = {'backend': 'trt', 'trt_version': '10.3.0.30', 'device': 'Orin-sm87',
                'spec': spec, 'cinque_v3_record': record,
                'cinque_v3_record_sha256': v3.record_digest(record)}
    engine.with_suffix('.json').write_text(json.dumps(metadata))
    assert probe.validate_artifact(engine, spec)['cinque_v3_record']['engine']['nbytes'] == 26
    metadata['cinque_v3_record']['dtype_transforms'] = {}
    engine.with_suffix('.json').write_text(json.dumps(metadata))
    with pytest.raises(ValueError): probe.validate_artifact(engine, spec)


@pytest.mark.parametrize('smoke,stress', [(0, 1), (1, 0), (-1, 2)])
def test_bad_frame_counts_do_not_open_engine(probe, contract, smoke, stress):
    with pytest.raises(ValueError):
        probe.run_exercise(lambda: pytest.fail('must not open'), contract, smoke, stress)


def cuda_trt_boundary(probe, contract, monkeypatch, failure=None):
    """Only CUDA/TRT are replaced; real probe allocates/views/copies/cleans up."""
    allocations, events, addresses = {}, [], {}
    def allocate(size, kind):
        if failure == 'host-alloc' and kind == 'host': return (7, 0)
        data = ctypes.create_string_buffer(size)
        pointer = ctypes.addressof(data)
        allocations[pointer] = data
        events.append(kind + '-alloc')
        return (0, pointer)
    def free(pointer, kind):
        del allocations[pointer]
        events.append(kind + '-free')
        return (0,)
    def copy(dst, src, size, kind, stream):
        events.append('h2d' if kind == 1 else 'd2h')
        if failure == 'copy': return (7,)
        ctypes.memmove(dst, src, size)
        return (0,)
    def mark(name, *args):
        events.append(name)
        return (0,)
    rt = NS(cudaError_t=NS(cudaSuccess=0),
            cudaMemcpyKind=NS(cudaMemcpyHostToDevice=1, cudaMemcpyDeviceToHost=2),
            cudaSetDevice=lambda *a: mark('set-device'),
            cudaGetDeviceProperties=lambda *a: (0, NS(name=b'Orin', major=8, minor=7)),
            cudaStreamCreate=lambda: (0, 11),
            cudaStreamSynchronize=lambda *a: mark('sync'),
            cudaStreamDestroy=lambda *a: mark('stream-free'),
            cudaEventCreate=lambda: (0, 12),
            cudaEventRecord=lambda *a: mark('event'),
            cudaEventDestroy=lambda *a: mark('event-free'),
            cudaEventElapsedTime=lambda *a: (0, 1.25),
            cudaMalloc=lambda size: allocate(size, 'device'),
            cudaHostAlloc=lambda size, flags: allocate(size, 'host'),
            cudaFree=lambda pointer: free(pointer, 'device'),
            cudaFreeHost=lambda pointer: free(pointer, 'host'),
            cudaMemcpyAsync=copy)
    def set_address(name, pointer):
        addresses[name] = pointer
        return failure != 'address'
    def execute(stream):
        events.append('execute')
        for name, info in contract['outputs'].items():
            values = np.frombuffer(allocations[addresses[name]], dtype=info['dtype'])
            values.fill(np.nan if failure == 'nonfinite' and name == 'outputs' else 1)
        return failure != 'execute'
    context = NS(set_tensor_address=set_address, execute_async_v3=execute)
    names = [*contract['inputs'], *contract['outputs']]
    descriptors = contract['inputs'] | contract['outputs']
    def shape(name):
        if failure == 'contract' and name == 'new_img': return [1, 2]
        return descriptors[name]['shape']
    engine = NS(num_io_tensors=len(names), get_tensor_name=lambda i: names[i],
                get_tensor_mode=lambda n: 'in' if n in contract['inputs'] else 'out',
                get_tensor_shape=shape, get_tensor_dtype=lambda n: descriptors[n]['dtype'],
                create_execution_context=lambda: None if failure == 'context' else context)
    def deserialize(data):
        events.append('deserialize')
        return None if failure == 'deserialize' else engine
    class Logger:
        WARNING = 1
        def __init__(self, *args): pass
    trt = NS(__version__='10.3.0', Logger=Logger,
             Runtime=lambda *a: NS(deserialize_cuda_engine=deserialize),
             TensorIOMode=NS(INPUT='in', OUTPUT='out'),
             **{n: n for n in ['float32', 'float16', 'int32', 'int64', 'uint8', 'bool']})
    monkeypatch.setitem(sys.modules, 'tensorrt', trt)
    monkeypatch.setattr(probe, 'load_cuda_runtime', lambda: rt)
    return NS(allocations=allocations, events=events)


@pytest.mark.parametrize('failure', ['contract', 'deserialize', 'context', 'address', 'host-alloc'])
def test_cuda_constructor_failures_release_partial_allocations(probe, contract, tmp_path, monkeypatch, failure):
    boundary = cuda_trt_boundary(probe, contract, monkeypatch, failure)
    plan = tmp_path / 'e.plan'
    plan.write_bytes(b'CPU fixture')
    with pytest.raises((ValueError, RuntimeError)):
        probe.CudaTrtSession(plan, contract, {'trt_version': '10.3.0', 'device': 'Orin-sm87'})
    assert boundary.allocations == {}
    if failure in ('contract', 'deserialize', 'context'):
        assert not any(e.endswith('-alloc') for e in boundary.events)
    assert boundary.events.index('set-device') < boundary.events.index('deserialize')


@pytest.mark.parametrize('failure', [None, 'copy', 'execute', 'nonfinite'])
def test_cuda_roundtrip_and_failed_generation_cleanup(probe, contract, tmp_path, monkeypatch, failure):
    boundary = cuda_trt_boundary(probe, contract, monkeypatch, failure)
    plan = tmp_path / 'e.plan'
    plan.write_bytes(b'CPU fixture')
    session = probe.CudaTrtSession(plan, contract, {'trt_version': '10.3.0', 'device': 'Orin-sm87'})
    generation = probe.Generation(session, contract)
    try:
        if failure:
            with pytest.raises((ValueError, RuntimeError)): generation.step(0, 73)
            assert generation.valid is False
        else:
            outputs, timing = generation.step(1, 73)
            assert outputs['outputs'].tolist() == [1., 1.]
            assert timing['gpu_execute_ms'] == 1.25
            assert boundary.events.index('h2d') < boundary.events.index('execute') < boundary.events.index('d2h')
    finally:
        generation.close()
    assert boundary.allocations == {}
    assert boundary.events.index('sync') < boundary.events.index('host-free')
