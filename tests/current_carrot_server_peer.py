"""Separate-process CURRENT Session/JetlinkClient fixture, fake GPU boundary only."""
from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import numpy as np

from jetlink import protocol as P
from jetlink.client import JetlinkClient
from jetlink.server.backends.base import IO
from jetlink.server.cache import EngineCache
from jetlink.server.session import EngineHost, Request, Session, _check_shapes
from jetlink.spec import ModelSpec
from jetlink.transport.base import LinkError
from jetlink.transport.tcp import TcpTransport


def fixture(model):
    if model == 'v2':
        ins = {'img': (1, 12, 1, 2), 'big_img': (1, 12, 1, 2),
               'features_buffer': (1, 2, 3), 'desire_pulse': (1, 2, 8),
               'traffic_convention': (1, 2), 'action_t': (1, 2)}
        return ModelSpec('2' * 64, 222, 4, ins, {'outputs': (1, 7)},
                         {'plan': slice(0, 4), 'hidden_state': slice(4, 7)}, 'FIXTURE-V2')
    ins = {'new_img': (2, 6, 1, 2), 'desire': (8,), 'traffic_convention': (1, 2),
           'action_t': (1, 2), 'state_img_q': (2, 2), 'state_desire_q': (2, 2),
           'state_feat_q': (2, 2)}
    outs = {f'next_{n}': shape for n, shape in ins.items() if n.startswith('state_')}
    outs['outputs'] = (1, 7)  # Deliberately LAST: the driving name matters.
    return ModelSpec.from_dict({'sha256': '3' * 64, 'nbytes': 333, 'frame_skip': 4,
        'input_shapes': ins, 'output_shapes': outs, 'output_slices': {'plan': [0, 7]},
        'checkpoint': 'FIXTURE-V3',
        'input_dtypes': {n: 'uint8' if n in ('new_img', 'state_img_q') else 'float32' for n in ins},
        'output_dtypes': {n: 'uint8' if n == 'next_state_img_q' else 'float32' for n in outs}})


class CpuEngine:
    def __init__(self, spec):
        self.spec, self.last_gpu_us, self.runs = spec, 0, 0
        self.dtype_transforms = {}
        self.inputs = {n: IO(n, shape, np.dtype(getattr(spec, 'input_dtypes', {}).get(n, 'float16')))
                       for n, shape in spec.input_shapes.items()}
        self.outputs = {n: IO(n, shape, np.dtype(getattr(spec, 'output_dtypes', {}).get(n, 'float32')))
                        for n, shape in spec.output_shapes.items()}
        self.values = {n: np.zeros(io.shape, io.dtype) for n, io in self.inputs.items()}
        self.fault = None
        self.closed = False

    def host_input(self, name):
        return self.values[name]

    def run(self):
        self.runs += 1
        assert not self.closed
        if self.spec.stateful:
            outputs = {b: (self.values[a] + 1).astype(self.values[a].dtype)
                       for a, b in self.spec.state_pairs.items()}
            value = float(self.values['state_feat_q'].flat[0]) + 1
            outputs['outputs'] = np.full((1, 7), value, np.float32)
        else:
            value = 1 + float(self.values['features_buffer'].flat[-1])
            outputs = {'outputs': np.full((1, 7), value, np.float32)}
        if self.fault:
            name, kind = self.fault
            if kind == 'missing':
                del outputs[name]
            elif kind == 'shape':
                outputs[name] = outputs[name].reshape(-1)
            elif kind == 'dtype':
                outputs[name] = outputs[name].astype(np.float64)
            elif kind in ('nonfinite', 'inf'):
                # UINT8 has no nonfinite values: use the declared float states.
                outputs[name] = outputs[name].astype(np.float32)
                outputs[name].flat[-1] = np.nan if kind == 'nonfinite' else np.inf
            elif kind == 'extra':
                outputs['surprise'] = np.zeros(1, np.float32)
            elif kind == 'run':
                raise RuntimeError('CPU_FAKE execution failure')
        return outputs

    def warm(self):
        self.run()
        return 'CPU_FAKE warm; no CUDA/TensorRT'

    def close(self):
        self.closed = True


class CpuBackend:
    name, suffix = 'trt', '.plan'

    def describe(self):
        return {'backend': 'trt', 'runtime_version': 'CPU_FAKE', 'device': 'CPU_FAKE'}

    def tag(self):
        return 'CPU_FAKE'


def new_host(root, model='v3'):
    host = EngineHost(EngineCache(root, CpuBackend()))
    spec = fixture(model)
    host.loaded = host._warm(CpuEngine(spec), spec)
    return host


def snapshot(host):
    loaded = host.loaded
    return {'valid': bool(loaded and getattr(loaded, 'valid', True)),
            'state': {n: v.tolist() for n, v in loaded.host_inputs.items() if n.startswith('state_')},
            'runs': loaded.engine.runs,
            'previous': None if getattr(loaded, 'prev_feat', None) is None else loaded.prev_feat.tolist()}


def serve(version, model, root):
    host = new_host(root / 'cache', model)
    host.telemetry = SimpleNamespace(read=lambda: snapshot(host), close=lambda: None)
    listener = TcpTransport.listen('127.0.0.1', 0)
    print(listener.getsockname()[1], flush=True)
    transport, _ = TcpTransport.accept(listener)
    transport.protocol_version = version
    session = Session(transport, host)
    command = root / 'command.json'
    try:
        while True:
            message = transport.recv(timeout=20)
            if command.exists():
                control = json.loads(command.read_text())
                command.unlink()
                if control.get('reload'):
                    host._unload()
                    spec = fixture(model)
                    host.loaded = host._warm(CpuEngine(spec), spec)
                if 'fault' in control:
                    host.loaded.engine.fault = control['fault']
                if control.get('partial'):
                    host.loaded.host_inputs['state_desire_q'].flags.writeable = False
                if control.get('mutate'):
                    # Same SHA, new wire semantic identity, old pinned buffers.
                    host.loaded.spec = replace(host.loaded.spec, checkpoint='MUTATED')
            session.handle(message)
    except LinkError:
        pass
    finally:
        session.close()
        host.close()
        transport.close()
        listener.close()


def connect(port, version):
    transport = TcpTransport.connect('127.0.0.1', port)
    transport.protocol_version = version
    return JetlinkClient(transport, deadline=3, name='CPU_FAKE-FIXTURE')


def inputs(client):
    return np.ones(client.spec.warped_shape, np.uint8), np.zeros(client.spec.packed_nelem, np.float32)


def control(root, client, command):
    (root / 'command.json').write_text(json.dumps(command))
    return client.state()


def expect_error(fn):
    try:
        fn()
    except (LinkError, ValueError, FloatingPointError):
        return
    raise AssertionError('expected failure')


def client_loopback(port, version, model, root):
    client = connect(port, version)
    hello = client.hello()
    assert hello['protocol'] == version
    if version == 3:
        assert hello['carrot_host'] == 'jetson'
        assert hello['carrot_model_selection_v1'] == {'version': 1, 'selection': 'host'}
    else:
        assert 'carrot_model_selection_v1' not in hello
    spec = fixture(model)
    loaded = client.ensure_engine(spec.sha256, spec.nbytes)
    assert loaded.to_dict() == spec.to_dict()
    if model == 'v2':
        assert 'input_dtypes' not in loaded.to_dict()
    warped, packed = inputs(client)
    first = client.infer(warped, packed, frame_id=11, reset=True, want_state=True)
    np.testing.assert_array_equal(first, np.ones(7, np.float32))
    assert client.last_state['loaded'] == spec.sha256
    second = client.infer(warped, packed, frame_id=12)
    np.testing.assert_array_equal(second, np.full(7, 2 if model == 'v3' else 1, np.float32))
    if model == 'v2' and version == 3:
        np.testing.assert_array_equal(client.state()['previous'], np.ones(3))
    reset = client.infer(warped, packed, frame_id=13, reset=True)
    np.testing.assert_array_equal(reset, first)
    # A replay must never run the engine/advance history twice.
    runs = client.state()['runs']
    client.t.send(P.Msg.INFER_REQ, client.seq - 2, (P.pack_infer_req(99), warped, packed))
    assert client.state()['runs'] == runs
    client.hello()
    if version == 3:
        fresh = client.state()
        assert all(not np.any(value) for value in fresh['state'].values()), 'new protocol3 session starts with zero state'
        assert fresh['previous'] is None or not np.any(fresh['previous'])
    expect_error(lambda: client.infer(warped, packed, frame_id=14))
    client.dead = False  # New logical owner on same transport, explicit HELLO.
    client.ensure_engine(spec.sha256, 0)
    resumed = client.infer(warped, packed, frame_id=15, reset=False)
    np.testing.assert_array_equal(resumed, first)
    client.close()
    return {'evidence': 'CPU_FAKE/FIXTURE', 'protocol': version, 'model': model, 'passed': True}


def client_faults(port, version, model, root):
    client = connect(port, version)
    spec = fixture(model)
    cases = 0
    for name in spec.output_shapes:
        kinds = ['missing', 'shape', 'dtype', 'nonfinite', 'inf']
        for kind in kinds:
            control(root, client, {'reload': True})
            client.dead = False
            client.hello()
            client.ensure_engine(spec.sha256, spec.nbytes)
            warped, packed = inputs(client)
            client.infer(warped, packed, frame_id=1)
            before = control(root, client, {'fault': [name, kind]})
            expect_error(lambda: client.infer(warped, packed, frame_id=2))
            after = client.state()
            assert after['state'] == before['state'], (name, kind)
            assert not after['valid']
            client.dead = False
            client.hello()
            expect_error(lambda: client.ensure_engine(spec.sha256, 0))
            client.spec = spec
            expect_error(lambda: client.infer(warped, packed, frame_id=3, reset=True))
            assert client.state()['state'] == before['state']
            cases += 1
    for kind in ('extra', 'run'):
        control(root, client, {'reload': True})
        client.dead = False
        client.hello()
        client.ensure_engine(spec.sha256, 0)
        warped, packed = inputs(client)
        control(root, client, {'fault': ['outputs', kind]})
        expect_error(lambda: client.infer(warped, packed))
        assert not client.state()['valid']
        cases += 1
    # Partial copy invalidates even though the first state was copied.
    control(root, client, {'reload': True})
    client.dead = False
    client.hello()
    client.ensure_engine(spec.sha256, 0)
    warped, packed = inputs(client)
    before = control(root, client, {'partial': True})
    expect_error(lambda: client.infer(warped, packed))
    after = client.state()
    assert not after['valid'] and after['state'] != before['state']
    client.dead = False
    client.hello()
    expect_error(lambda: client.ensure_engine(spec.sha256, 0))
    control(root, client, {'reload': True})
    client.hello()
    client.ensure_engine(spec.sha256, 0)
    state = client.state()
    assert all(not np.any(value) for value in state['state'].values())
    client.dead = False
    np.testing.assert_array_equal(client.infer(warped, packed), np.ones(7))
    client.close()
    return {'evidence': 'CPU_FAKE/FIXTURE', 'cases': cases + 1}


def client_identity(port, version, model, root):
    client = connect(port, version)
    spec = fixture(model)
    client.hello()
    expect_error(lambda: client.ensure_engine('4' * 64, 0))
    expect_error(lambda: client.ensure_engine(spec.sha256, spec.nbytes + 1))
    expect_error(lambda: client.ensure_engine(spec.sha256, 0, frame_skip=1))
    client.ensure_engine(spec.sha256, 0)
    warped, packed = inputs(client)
    # New generation requires a fresh HELLO even with same SHA/spec.
    control(root, client, {'reload': True})
    expect_error(lambda: client.infer(warped, packed))
    expect_error(lambda: client.ensure_engine(spec.sha256, 0))
    client.dead = False
    client.hello()
    client.ensure_engine(spec.sha256, 0)
    # Same object/SHA but changed semantic spec is also rejected.
    control(root, client, {'mutate': True})
    expect_error(lambda: client.infer(warped, packed))
    expect_error(lambda: client.ensure_engine(spec.sha256, 0))
    client.close()
    return {'evidence': 'CPU_FAKE/FIXTURE', 'passed': True}


def contracts():
    cases = 0
    with tempfile.TemporaryDirectory() as tmp:
        host = new_host(Path(tmp))
        spec = fixture('v3')
        assert isinstance(spec.state_pairs, dict), 'retain current public API'
        assert len(spec.validate_stateful()) == 3
        from jetlink.onnx_meta import OnnxMeta
        from jetlink.spec import spec_from_meta
        import base64
        import pickle
        legacy = fixture('v2')
        meta = OnnxMeta(inputs=legacy.input_shapes, outputs=legacy.output_shapes,
                        input_types={n: 'float16' for n in legacy.input_shapes},
                        output_types={'outputs': 'float32'}, props={
                            'model_checkpoint': legacy.checkpoint,
                            'output_slices': base64.b64encode(pickle.dumps(legacy.output_slices)).decode()})
        derived = spec_from_meta(meta, legacy.sha256, legacy.nbytes, legacy.frame_skip)
        assert derived.to_dict() == legacy.to_dict(), 'fresh V2 retains exact legacy wire identity'
        cases += 1
        from jetlink.server.session import _check_request_spec
        for mismatch in (replace(legacy, sha256='4' * 64), replace(legacy, nbytes=legacy.nbytes + 1),
                         replace(legacy, frame_skip=1)):
            expect_error(lambda: _check_request_spec(Request(legacy.sha256, legacy.nbytes, legacy.frame_skip), mismatch))
            cases += 1
        entry = host.cache.entry(legacy.sha256)
        entry.path.write_bytes(b'CPU_FAKE old cached plan')
        entry.write_meta({'spec': legacy.to_dict()})
        for req in (Request(legacy.sha256, legacy.nbytes + 1, 4), Request(legacy.sha256, 0, 1)):
            expect_error(lambda: host._spec_on_disk(entry, host.cache.model_path(legacy.sha256), req))
            cases += 1
        for location in ('inputs', 'outputs'):
            for kind in ('missing', 'extra', 'shape', 'dtype'):
                engine = CpuEngine(spec)
                values = getattr(engine, location)
                name = next(iter(values))
                if kind == 'missing': del values[name]
                elif kind == 'extra': values['extra'] = values[name]
                elif kind == 'shape': values[name] = replace(values[name], shape=(4,))
                elif kind == 'dtype': values[name] = replace(values[name], dtype=np.dtype('float64'))
                expect_error(lambda: _check_shapes(engine, spec))
                cases += 1
        for name in spec.output_shapes:
            engine = CpuEngine(spec)
            engine.fault = [name, 'nonfinite']
            expect_error(lambda: host._warm(engine, spec))
            cases += 1
        engine = CpuEngine(spec)
        engine.dtype_transforms = {'state_feat_q': 'float16'}
        expect_error(lambda: _check_shapes(engine, spec))
        cases += 1
        # Narrowing an otherwise finite packed scalar must not execute GPU.
        narrow = replace(spec, input_dtypes={**spec.input_dtypes, 'desire': 'float16'})
        loaded = host._warm(CpuEngine(narrow), narrow)
        packed = np.full(narrow.packed_nelem, np.finfo(np.float32).max, np.float32)
        loaded.queues.step_into(np.zeros(narrow.warped_shape, np.uint8), packed, loaded.host_inputs)
        from jetlink.server.session import _check_finite_inputs
        expect_error(lambda: _check_finite_inputs(loaded.host_inputs))
        cases += 1
        host.close()
    return {'evidence': 'CPU_FAKE/FIXTURE', 'cases': cases}


def offroad():
    from jetlink.server.control import ControlServer
    from jetlink.server.session import Job
    import pytest
    cases = 0
    with tempfile.TemporaryDirectory() as temporary:
        root = Path(temporary)
        host = new_host(root / 'cache')
        original = host.loaded
        provider = [None]
        host.managed_selection = True
        host.offroad = lambda: provider[0]
        resolved, downloaded, submitted = [], [], []
        spec = original.spec
        registry = SimpleNamespace(
            resolve=lambda ref: (resolved.append(ref) or SimpleNamespace(oid='4' * 64, size=10)),
            model_path=lambda sha: root / (sha + '.onnx'),
            fetch=lambda *args, **kwargs: downloaded.append(args))
        control = ControlServer('tcp://127.0.0.1:0', host, host.cache, registry=registry)
        control._downloads = SimpleNamespace(submit=lambda fn, *args: submitted.append((fn, args)))
        for value in (None, False, 'true', 1):
            provider[0] = value
            assert not host.can_provision()
            for command, data in ((control._cmd_download, {'ref': 'fixture'}),
                                  (control._cmd_prepare, {'sha256': spec.sha256}),
                                  (control._cmd_import, {'path': str(root / 'source.onnx')})):
                with pytest.raises(PermissionError):
                    command(None, data)
                assert not resolved and not downloaded and not submitted and not control._active
                assert host.job is None and host.loaded is original
                cases += 1
        provider[0] = True
        assert host.can_provision()
        # Command proceeds through real resolver and queues exactly one worker.
        result = control._cmd_download(None, {'ref': 'fixture'})
        assert result['sha256'] == '4' * 64 and len(submitted) == 1
        provider[0] = False
        fn, args = submitted[0]
        fn(*args)
        assert not downloaded and not control._active
        cases += 1
        # Unknown/false authorization before worker entry preserves resident.
        job = Job('4' * 64, load_only=True)
        host._run(job, Request('4' * 64, 10, 4), host.cache.entry('4' * 64), root / 'model.onnx', spec)
        assert job.state == 'failed' and host.loaded is original
        with pytest.raises(PermissionError):
            host._start(Job('4' * 64, True), Request('4' * 64, 10, 4),
                        host.cache.entry('4' * 64), root / 'model.onnx', spec)
        cases += 1
        provider[0] = True
        sent = []
        transport = SimpleNamespace(protocol_version=3,
            send=lambda mt, seq, parts=(), flags=0: sent.append((mt, seq, parts)))
        active = Session(transport, host)
        active.handle(SimpleNamespace(msg_type=P.Msg.HELLO_REQ, seq=1, payload=memoryview(b'{}')))
        assert host.managed_selection and not host.can_provision()
        active.close()
        assert host.can_provision()
        cases += 1
        host.offroad = lambda: (_ for _ in ()).throw(OSError('provider lost'))
        assert not host.can_provision()
        cases += 1
        # CURRENT worker must check authorization after an expensive warm.
        provider[0] = True
        host.offroad = lambda: provider[0]
        candidate = CpuEngine(spec)
        original_warm = candidate.warm
        def lose_during_warm():
            result = original_warm()
            provider[0] = False
            return result
        candidate.warm = lose_during_warm
        host.backend.load = lambda artifact, report=None: candidate
        job = Job(spec.sha256, load_only=True)
        host.job = job
        entry = host.cache.entry(spec.sha256)
        entry.path.write_bytes(b'CPU_FAKE current load')
        entry.write_meta({'spec': spec.to_dict()})
        host._run(job, Request(spec.sha256, spec.nbytes, spec.frame_skip), entry,
                  host.cache.model_path(spec.sha256), spec)
        assert job.state == 'failed', 'offroad authorization lost during warm cannot publish ready'
        assert host.loaded is None and candidate.closed
        assert host.snapshot()['state'] != 'ready'
        cases += 1
        host.managed_selection = False
        assert host.can_provision(), 'preserve legacy protocol2 process semantics'
        host.close()
        import jetlink.server.main as main
        with pytest.raises(SystemExit) as denied:
            main.main(['--managed-jetson', '--build', str(root / 'unknown.onnx')])
        assert denied.value.code == 2
        cases += 1
    return {'evidence': 'CPU_FAKE/FIXTURE', 'cases': cases}


def orchestrate(scenario, version=3, model='v3'):
    with tempfile.TemporaryDirectory() as tmp:
        server = subprocess.Popen([sys.executable, __file__, 'serve', str(version), model, tmp],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        try:
            line = server.stdout.readline()
            assert line, server.stderr.read()
            result = subprocess.run([sys.executable, __file__, 'client', scenario, line.strip(),
                                     str(version), model, tmp], capture_output=True, text=True, timeout=30)
            assert result.returncode == 0, result.stdout + result.stderr
            server.wait(timeout=5)
            assert server.returncode == 0, server.stderr.read()
            return json.loads(result.stdout.strip().splitlines()[-1])
        finally:
            if server.poll() is None:
                server.terminate()
                server.communicate(timeout=5)


def native_protocol3():
    import jetlink
    root = Path(jetlink.__file__).resolve().parents[3]
    spec = ModelSpec.from_dict(json.loads((root / 'openpilot/selfdrive/modeld/jetlink/jetson_model.json').read_text()))
    resets, sent = [], []
    with tempfile.TemporaryDirectory() as tmp:
        host = EngineHost(EngineCache(Path(tmp), CpuBackend()))
        host.loaded = SimpleNamespace(spec=spec, sha256=spec.sha256, valid=True, prev_feat=None,
                                      queues=SimpleNamespace(reset=lambda: resets.append(True)),
                                      engine=SimpleNamespace(close=lambda: None))
        transport = SimpleNamespace(protocol_version=3, send=lambda kind, seq, parts, flags=0: sent.append(json.loads(bytes(parts[0]))))
        session = Session(transport, host)
        try:
            session.on_hello(SimpleNamespace(seq=1))
            session.on_engine_req(SimpleNamespace(seq=2, payload=memoryview(json.dumps(
                {'sha256': spec.sha256, 'nbytes': spec.nbytes, 'frame_skip': spec.frame_skip}).encode())))
            assert sent[-1]['state'] == 'failed', 'unsupported P3 N16 must not become ready'
            assert not resets, 'P3 HELLO must not reset the resident native N16 generation'
            session.engine_update()
            assert sent[-1]['state'] == 'failed', 'late engine notification must not authorize unsupported N16'
            assert session._prepared_loaded is None
            assert not resets
            assert host.loaded.valid
        finally:
            host.close()
    return {'evidence': 'CPU_FAKE/FIXTURE', 'passed': True}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'serve':
        serve(int(sys.argv[2]), sys.argv[3], Path(sys.argv[4]))
    elif action == 'client':
        result = globals()['client_' + sys.argv[2]](int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], Path(sys.argv[6]))
        print(json.dumps(result))
    elif action == 'contracts':
        print(json.dumps(contracts()))
    elif action == 'trt':
        from current_carrot_server_trt import run
        print(json.dumps(run()))
    elif action == 'offroad':
        print(json.dumps(offroad()))
    elif action == 'native-protocol3':
        print(json.dumps(native_protocol3()))
    else:
        print(json.dumps(orchestrate(action, int(sys.argv[2]) if len(sys.argv) > 2 else 3,
                                     sys.argv[3] if len(sys.argv) > 3 else 'v3')))
