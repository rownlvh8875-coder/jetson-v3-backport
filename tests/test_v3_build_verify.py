"""CPU contracts; TensorRT/CUDA doubles do not demonstrate GPU execution."""
import copy
import json
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import onnx
import pytest
from onnx import TensorProto as T, helper as H

ROOT = Path(__file__).resolve().parents[1]
_before_path = sys.path[:]
try:
    sys.path.insert(0, str(ROOT / 'tools'))
    import build_trt_v3 as b
    import patch_v3_uint8 as p
    from onnx_meta_light import decode_output_slices
finally:
    sys.path[:] = _before_path


@pytest.fixture
def spec():
    ins = {'new_img': 'uint8', 'desire': 'float32', 'traffic_convention': 'float32',
           'action_t': 'float32', 'state_img_q': 'uint8',
           'state_desire_q': 'float32', 'state_feat_q': 'float32'}
    outs = {'outputs': 'float32', 'next_state_img_q': 'uint8',
            'next_state_desire_q': 'float32', 'next_state_feat_q': 'float32'}
    return dict(input_shapes={n: [2] for n in ins}, input_dtypes=ins,
                output_shapes={n: [2] for n in outs}, output_dtypes=outs)


def tiny_model(path):
    inputs = [H.make_tensor_value_info(n, T.UINT8, [2]) for n in p.V3_IMG_INPUTS]
    nodes = [H.make_node('Cast', ['new_img'], ['vision'], to=T.FLOAT16),
             H.make_node('Reshape', ['state_img_q', 'shape'], ['next_state_img_q'])]
    graph = H.make_graph(nodes, 'queue', inputs,
                        [H.make_tensor_value_info('vision', T.FLOAT16, [2]),
                         H.make_tensor_value_info('next_state_img_q', T.UINT8, [2])],
                        [H.make_tensor('shape', T.INT64, [1], [2])])
    onnx.save(H.make_model(graph, opset_imports=[H.make_opsetid('', 17)], ir_version=9), path)


def fake_builder(monkeypatch, serialized=b'engine'):
    inp = NS(name='new_img', shape=(2,), dtype='half')
    class Network:
        num_inputs = 1
        def get_input(self, i):
            assert i == 0
            return inp
        def __iter__(self):
            return iter([NS(name='layer-without-shape')])
    cfg = NS(set_memory_pool_limit=lambda *a: None, set_flag=lambda *a: None)
    builder = NS(platform_has_fast_fp16=True, create_network=lambda *a: Network(),
                 create_builder_config=lambda: cfg,
                 build_serialized_network=lambda *a: serialized)
    class Logger:
        INFO = 1
        def __init__(self, *a): pass
    monkeypatch.setitem(sys.modules, 'tensorrt', NS(Logger=Logger, Builder=lambda *a: builder,
        NetworkDefinitionCreationFlag=NS(EXPLICIT_BATCH=0),
        BuilderFlag=NS(FP16=1), MemoryPoolType=NS(WORKSPACE=1),
        OnnxParser=lambda *a: NS(parse_from_file=lambda path: True, num_errors=0)))


def test_builder_enumerates_inputs_returns_bound_retypes_and_preserves_original(tmp_path, monkeypatch, capsys):
    src, dst = tmp_path/'raw.onnx', tmp_path/'v3.engine'
    tiny_model(src)
    original = src.read_bytes()
    fake_builder(monkeypatch)
    record = b.build_engine(src, dst, 1)
    assert "new_img" in capsys.readouterr().out
    assert record.is_file()
    data = json.loads(record.read_text())
    assert data['dtype_transforms'] == {'new_img': 'float16', 'state_img_q': 'float16',
                                       'next_state_img_q': 'float16'}
    assert data['original_io']['inputs']['new_img']['dtype'] == 'uint8'
    assert data['engine']['sha256'] == b.file_identity(dst)['sha256']
    assert data['source'] == b.file_identity(src)
    assert data['patched'] == b.file_identity(Path(data['patched_path']))
    assert src.read_bytes() == original
    assert b.load_build_record(dst, data['source']) == data
    dst.write_bytes(b'other engine')
    with pytest.raises((ValueError, FileNotFoundError)):
        b.load_build_record(dst, data['source'])


def test_failed_build_keeps_previous_engine(tmp_path, monkeypatch):
    src, dst = tmp_path/'raw.onnx', tmp_path/'v3.engine'
    tiny_model(src)
    dst.write_bytes(b'known-good')
    fake_builder(monkeypatch, None)
    with pytest.raises(RuntimeError, match='returned None'):
        b.build_engine(src, dst, 1)
    assert dst.read_bytes() == b'known-good'
    assert not list(tmp_path.glob('*.retypes.json'))


@pytest.mark.parametrize('frames,threshold', [(0, None), (-1, 0), (1, -1), (1, np.nan), (1, np.inf)])
def test_invalid_arguments_fail_before_gpu_import(frames, threshold):
    with pytest.raises(ValueError):
        b.verify_engine(Path('absent'), {}, None, frames, threshold)


def test_missing_ort_or_comparison_cannot_succeed(monkeypatch):
    with pytest.raises(b.VerificationIncomplete):
        b.verify_engine(Path('absent'), {}, None, 1, 0)
    monkeypatch.setitem(sys.modules, 'onnxruntime', None)
    with pytest.raises(b.VerificationIncomplete):
        b.verify_engine(Path('absent'), {}, Path('raw'), 1, 0)


def test_backend_inputs_keep_original_uint8_and_only_declared_fp16(spec):
    raw = b.spec_contract(spec)
    patched = b.spec_contract(spec, b.V3_RETYPES)
    left = b.frame_inputs(raw['inputs'], 1, 73)
    right = b.frame_inputs(patched['inputs'], 1, 73)
    assert left['new_img'].dtype == np.uint8
    assert right['new_img'].dtype == np.float16
    np.testing.assert_array_equal(left['new_img'], right['new_img'])
    assert left['new_img'][0] == 0 and left['new_img'][1] == 255
    assert right['state_feat_q'].dtype == np.float32


@pytest.mark.parametrize('value', [np.nan, np.inf, -np.inf])
def test_ort_nonfinite_is_failure(spec, value):
    c = b.spec_contract(spec)
    outputs = {n: np.zeros(v['shape'], v['dtype']) for n, v in c['outputs'].items()}
    outputs['outputs'][0] = value
    with pytest.raises(ValueError, match='non-finite'):
        b.validate_outputs(outputs, c['outputs'])


def test_error_overflow_and_threshold_exceedance_fail():
    with pytest.raises(ValueError, match='non-finite'):
        b.compare_outputs({'outputs': np.array([1e308])}, {'outputs': np.array([-1e308])}, 0)
    with pytest.raises(ValueError, match='threshold'):
        b.compare_outputs({'outputs': np.array([1.])}, {'outputs': np.array([0.])}, 0)
    assert b.compare_outputs({'outputs': np.array([1.])}, {'outputs': np.array([1.])}, 0)['outputs']['max_abs'] == 0


def test_engine_contract_rejects_mismatch_before_allocation(spec):
    actual = b.spec_contract(spec, b.V3_RETYPES)
    for change in ('shape', 'dtype', 'name'):
        bad = copy.deepcopy(actual)
        if change == 'shape': bad['inputs']['new_img']['shape'] = [1, 2]
        elif change == 'dtype': bad['inputs']['desire']['dtype'] = 'float16'
        else: bad['inputs']['extra'] = bad['inputs'].pop('new_img')
        with pytest.raises(ValueError):
            b.validate_contract(bad, b.spec_contract(spec, b.V3_RETYPES))


def test_feedback_uses_own_state_without_cast_or_reshape(spec):
    c = b.spec_contract(spec)
    a, z = b.frame_inputs(c['inputs'], 0, 7), b.frame_inputs(c['inputs'], 0, 7)
    outs = {n: np.ones(v['shape'], v['dtype']) for n, v in c['outputs'].items()}
    b.advance_state(a, outs)
    outs['next_state_feat_q'] *= 2
    b.advance_state(z, outs)
    np.testing.assert_array_equal(a['state_feat_q'], [1, 1])
    np.testing.assert_array_equal(z['state_feat_q'], [2, 2])
    outs['next_state_feat_q'] = outs['next_state_feat_q'].reshape(1, 2)
    with pytest.raises(ValueError): b.advance_state(a, outs)


def test_patch_refuses_overwrite_source_and_non_fp16_cast(tmp_path):
    src = tmp_path/'raw.onnx'
    tiny_model(src)
    raw = src.read_bytes()
    with pytest.raises(ValueError): p.patch_file_v3(src, src)
    assert src.read_bytes() == raw
    m = onnx.load(src)
    m.graph.node[0].attribute[0].i = T.FLOAT
    with pytest.raises(ValueError, match='Cast'):
        p.patch_v3_uint8_inputs(m)


def test_v2_auto_build_keeps_io_and_no_v3_retypes(tmp_path, monkeypatch):
    src, dst = tmp_path/'v2.onnx', tmp_path/'v2.engine'
    vi = H.make_tensor_value_info('img', T.UINT8, [2])
    vo = H.make_tensor_value_info('outputs', T.FLOAT, [2])
    onnx.save(H.make_model(H.make_graph([H.make_node('Cast', ['img'], ['outputs'], to=T.FLOAT)],
                                      'v2', [vi], [vo]), ir_version=9), src)
    fake_builder(monkeypatch)
    assert b.build_engine(src, dst, 1) is None
    record = b.load_build_record(dst, b.file_identity(src))
    assert record['dtype_transforms'] == {}
    assert record['original_io']['inputs']['img']['dtype'] == 'uint8'


def test_slice_metadata_is_decoded_without_executing_pickle():
    import base64
    import pickle
    encoded = base64.b64encode(pickle.dumps({'plan': slice(917, 1907)})).decode()
    assert decode_output_slices(encoded) == {'plan': [917, 1907]}
    # Even a builtin other than slice is forbidden; no arbitrary REDUCE call.
    with pytest.raises(ValueError):
        decode_output_slices(base64.b64encode(pickle.dumps(eval)).decode())


def fake_gpu(monkeypatch, contract, failure=None):
    events, pinned, devices = [], [], []
    class Host(np.ndarray):
        @property
        def base(self): return NS(free=lambda: events.append('host-free'))
    def host(shape, dtype):
        x = np.zeros(shape, dtype).view(Host); pinned.append(x); events.append('pin'); return x
    class DeviceBuffer:
        def __init__(self, size): self.size = size; devices.append(self)
        def __int__(self): return id(self)
        def free(self): events.append('device-free')
    primary = NS(push=lambda: events.append('push'), pop=lambda: events.append('pop'),
                 detach=lambda: events.append('detach'))
    cuda = NS(init=lambda: events.append('init'), Device=lambda i: NS(retain_primary_context=lambda: primary),
              pagelocked_empty=host, mem_alloc=DeviceBuffer)
    cuda.Stream = lambda: NS(handle=99, synchronize=lambda: events.append('sync'))
    cuda.Event = lambda: NS(record=lambda s: events.append('event'), time_till=lambda e: 1.)
    def h2d(dev, x, stream):
        assert any(x is v for v in pinned) and x.nbytes == dev.size
        events.append('h2d')
    def d2h(x, dev, stream):
        assert any(x is v for v in pinned) and x.nbytes == dev.size
        events.append('d2h'); x.fill(0)
    cuda.memcpy_htod_async, cuda.memcpy_dtoh_async = h2d, d2h
    names = [*contract['inputs'], *contract['outputs']]
    all_io = contract['inputs'] | contract['outputs']
    def execute(handle): events.append('execute'); return failure != 'execute'
    context = NS(set_tensor_address=lambda *a: failure != 'address', execute_async_v3=execute)
    engine = NS(num_io_tensors=len(names), get_tensor_name=lambda i: names[i],
                get_tensor_mode=lambda n: 'input' if n in contract['inputs'] else 'output',
                get_tensor_shape=lambda n: all_io[n]['shape'], get_tensor_dtype=lambda n: all_io[n]['dtype'],
                create_execution_context=lambda: None if failure == 'context' else context)
    def deserialize(data):
        assert events[-1] == 'push'
        events.append('deserialize'); return None if failure == 'deserialize' else engine
    class Logger:
        WARNING = 1
        def __init__(self, *a): pass
    trt = NS(Logger=Logger, Runtime=lambda l: NS(deserialize_cuda_engine=deserialize),
             TensorIOMode=NS(INPUT='input', OUTPUT='output'),
             **{n: n for n in ['float32', 'float16', 'int32', 'int64', 'uint8', 'bool']})
    monkeypatch.setitem(sys.modules, 'tensorrt', trt)
    monkeypatch.setitem(sys.modules, 'pycuda', NS(driver=cuda))
    monkeypatch.setitem(sys.modules, 'pycuda.driver', cuda)
    return events, pinned, devices


@pytest.mark.parametrize('failure', ['deserialize', 'context', 'address', 'execute', None])
def test_gpu_pinned_lifetime_primary_context_and_failures(tmp_path, monkeypatch, spec, failure):
    engine = tmp_path/'e.engine'; engine.write_bytes(b'engine')
    contract = b.spec_contract(spec, b.V3_RETYPES)
    events, pinned, devices = fake_gpu(monkeypatch, contract, failure)
    def run():
        with b.trt_runner(engine, contract) as infer:
            outs = infer(b.frame_inputs(contract['inputs'], 1, 73))
            b.validate_outputs(outs, contract['outputs'])
    if failure:
        with pytest.raises(RuntimeError): run()
    else:
        run()
        assert events.index('h2d') < events.index('execute') < events.index('d2h') < events.index('sync')
    assert events[-2:] == ['pop', 'detach']
    assert events.count('device-free') == len(devices)
    assert events.count('host-free') == len(pinned)
    if pinned: assert events.index('sync') < events.index('host-free')


def test_wrong_engine_io_allocates_nothing(tmp_path, monkeypatch, spec):
    engine = tmp_path/'e'; engine.write_bytes(b'engine')
    contract = b.spec_contract(spec, b.V3_RETYPES)
    actual = copy.deepcopy(contract)
    actual['inputs']['new_img']['shape'] = [1, 2]
    events, pinned, devices = fake_gpu(monkeypatch, actual)
    with pytest.raises(ValueError, match='contract'):
        with b.trt_runner(engine, contract): pytest.fail('must not yield')
    assert not pinned and not devices
    assert events[-2:] == ['pop', 'detach']


@pytest.mark.parametrize('mode,want_left,want_right', [('recurrent', [0, 1, 2], [0, 2, 4]),
                                                      ('same-state', [0, 0, 0], [0, 0, 0])])
@pytest.mark.parametrize('bad_backend,bad_value', [(None, None), (0, np.nan), (0, np.inf), (1, np.nan), (1, np.inf)])
def test_verifier_separates_feeds_and_recurrence(tmp_path, monkeypatch, spec, mode, want_left, want_right,
                                               bad_backend, bad_value):
    from contextlib import contextmanager
    raw_path, engine_path = tmp_path/'raw.bytes', tmp_path/'engine'
    raw_path.write_bytes(b'identity fixture, no graph')
    spec.update(b.file_identity(raw_path))
    raw, physical = b.spec_contract(spec), b.spec_contract(spec, b.V3_RETYPES)
    calls = [[], []]
    def run(feeds, index, contract):
        assert feeds['new_img'].dtype == (np.uint8 if index == 0 else np.float16)
        calls[index].append(float(feeds['state_feat_q'][0]))
        outs = {n: np.zeros(v['shape'], v['dtype']) for n, v in contract['outputs'].items()}
        for n in ('state_img_q', 'state_desire_q', 'state_feat_q'):
            outs['next_'+n] = feeds[n] + np.array(index+1, dtype=feeds[n].dtype)
        if index == bad_backend: outs['next_state_feat_q'][0] = bad_value
        return outs
    session = NS(get_inputs=lambda: [NS(name=n, shape=v['shape'], type='tensor(uint8)' if v['dtype']=='uint8' else 'tensor(float)') for n,v in raw['inputs'].items()],
                 get_outputs=lambda: [NS(name=n, shape=v['shape'], type='tensor(uint8)' if v['dtype']=='uint8' else 'tensor(float)') for n,v in raw['outputs'].items()],
                 run=lambda names, feeds: list(run(feeds, 0, raw).values()))
    monkeypatch.setattr(b, 'ort_session', lambda *a: session)
    monkeypatch.setattr(b, 'load_build_record', lambda *a: dict(original_io=raw, dtype_transforms=b.V3_RETYPES))
    @contextmanager
    def runner(*a): yield lambda feeds: run(feeds, 1, physical)
    monkeypatch.setattr(b, 'trt_runner', runner)
    error, message = (b.VerificationIncomplete, 'MEASURED') if bad_backend is None else (ValueError, 'non-finite')
    with pytest.raises(error, match=message):
        b.verify_engine(engine_path, spec, raw_path, 3, None, mode)
    assert calls == ([want_left, want_right] if bad_backend is None else [[0], [0]])


@pytest.mark.parametrize('name,change', [('outputs', 'shape'), ('next_state_feat_q', 'dtype'),
                                      ('next_state_img_q', 'missing')])
def test_output_contract_errors_are_not_cast_or_reshaped(spec, name, change):
    contract = b.spec_contract(spec)['outputs']
    outs = {n: np.zeros(v['shape'], v['dtype']) for n,v in contract.items()}
    if change == 'shape': outs[name] = outs[name].reshape(1, 2)
    elif change == 'dtype': outs[name] = outs[name].astype(np.float16)
    else: del outs[name]
    with pytest.raises(ValueError): b.validate_outputs(outs, contract)


def test_safety_script_finishes_with_onnx_packages_but_no_model(tmp_path):
    import shutil
    import subprocess
    # A small isolated checkout of the existing script and its dependencies.
    for directory in ('jetlink', 'patches', 'tools', 'tests'):
        shutil.copytree(ROOT/directory, tmp_path/directory,
                        ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (tmp_path/'artifacts').mkdir()
    shutil.copy(ROOT/'artifacts/cinque_v3.json', tmp_path/'artifacts/cinque_v3.json')
    result = subprocess.run([sys.executable, str(tmp_path/'tests/test_stateful_safety.py')],
                            capture_output=True, text=True, encoding='utf-8',
                            env={**__import__('os').environ, 'PYTHONIOENCODING': 'utf-8'})
    assert result.returncode == 0, result.stdout + result.stderr
    assert '40 passed, 0 failed' in result.stdout
    assert 'SKIP' in result.stdout


def test_engine_publish_failure_preserves_previous_build(tmp_path, monkeypatch):
    import os
    src, dst = tmp_path/'raw.onnx', tmp_path/'v3.engine'
    tiny_model(src)
    fake_builder(monkeypatch, b'old-good-engine')
    previous_record = b.build_engine(src, dst, 1)
    previous_bytes = previous_record.read_bytes()
    fake_builder(monkeypatch, b'new-engine')
    replace = os.replace
    def fail_publish(source, target):
        if Path(target) == dst: raise OSError('simulated engine publication failure')
        return replace(source, target)
    monkeypatch.setattr(os, 'replace', fail_publish)
    with pytest.raises(OSError, match='publication'):
        b.build_engine(src, dst, 1)
    assert dst.read_bytes() == b'old-good-engine'
    assert previous_record.read_bytes() == previous_bytes
    assert b.load_build_record(dst, b.file_identity(src))['engine']['nbytes'] == 15


def test_requested_parity_gate_cannot_be_ignored_by_build_only(tmp_path, monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['build_trt_v3.py', '--onnx', 'missing', '--spec', 'missing',
                                    '--out', str(tmp_path/'engine'), '--require-max-abs-err', '0'])
    with pytest.raises(SystemExit) as exc: b.main()
    assert exc.value.code == 2


def test_cleanup_failure_still_releases_primary_context(tmp_path, monkeypatch, spec):
    engine = tmp_path/'e'; engine.write_bytes(b'engine')
    contract = b.spec_contract(spec, b.V3_RETYPES)
    events, _, devices = fake_gpu(monkeypatch, contract)
    with pytest.raises(RuntimeError, match='free failure'):
        with b.trt_runner(engine, contract):
            def broken_free(): raise RuntimeError('free failure')
            devices[0].free = broken_free
    assert events[-2:] == ['pop', 'detach']
