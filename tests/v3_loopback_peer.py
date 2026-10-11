"""Subprocess-only offline loopback peer; never import both jetlink packages.

CpuEngine substitutes hardware inference. Real Session, EngineHost._warm,
EngineHost request/ready, queues/state validation and framed TCP transports run.
Faults are introduced exclusively at the server's outgoing transport boundary,
apart from invalid_state, which corrupts the fake hardware's next-state tensor.
"""
import copy
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
from types import SimpleNamespace as NS

import numpy as np


CAP = 'cinque_v3_stateful_v2'
ARTIFACT = Path(__file__).resolve().parents[1] / 'artifacts/cinque_v3.json'
CANONICAL = json.loads(ARTIFACT.read_text())
STATE_NAMES = ('state_img_q', 'state_desire_q', 'state_feat_q')


def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)


class CpuEngine:
    """Full-size semantic inputs with the applied TRT dtype transformation.

    The arithmetic is a deterministic recurrence oracle, not a V3 ONNX model.
    Arrays are ordinary CPU memory, never CUDA or page-locked allocations.
    """
    def __init__(self, spec):
        self.dtype_transforms = dict.fromkeys(
            ('new_img', 'state_img_q', 'next_state_img_q'), 'float16')
        self.inputs = {n: NS(shape=s, dtype=np.dtype(self.dtype_transforms.get(n, spec.input_dtypes[n])))
                       for n, s in spec.input_shapes.items()}
        self.outputs = {n: NS(shape=s, dtype=np.dtype(self.dtype_transforms.get(n, spec.output_dtypes[n])))
                        for n, s in spec.output_shapes.items()}
        self.buffers = {n: np.full(v.shape, 7, v.dtype) for n, v in self.inputs.items()}
        self.last_gpu_us = 1
        self.state_seen = []
        self.images = []
        self.fault = False
        self.before_fault = None
        self.output_scale = np.float32(1)

    def host_input(self, name):
        return self.buffers[name]

    def warm(self):
        self.run()
        return 'full-size CPU hardware substitute; no ONNX/CUDA'

    def run(self):
        state = [float(self.buffers[n].flat[0]) for n in STATE_NAMES]
        # Check the whole state arrays, not just the value used by the oracle.
        for n, value in zip(STATE_NAMES, state, strict=True):
            assert np.all(self.buffers[n] == value), n
        image = int(self.buffers['new_img'].flat[0])
        self.state_seen.append(state)
        self.images.append(image)
        delta = np.float32(1 + image % 7)
        scalar = np.float32(sum(float(self.buffers[n].sum())
                                for n in ('desire', 'traffic_convention', 'action_t')))
        value = np.float32(sum(state) + image + scalar) * self.output_scale
        out = {'outputs': np.full(self.outputs['outputs'].shape, value, np.float32)}
        for n in STATE_NAMES:
            out['next_' + n] = self.buffers[n] + np.array(delta, dtype=self.buffers[n].dtype)
        if self.fault and state[0] > 0:
            self.before_fault = {n: self.buffers[n].copy() for n in STATE_NAMES}
            out['next_state_feat_q'].flat[-1] = np.nan
        return out

    def close(self):
        pass


def serve(scenario):
    from jetlink import protocol as P
    from jetlink.server import session as S
    from jetlink.spec import ModelSpec
    from jetlink.transport.base import LinkError, Transport
    from jetlink.transport.tcp import TcpTransport

    spec = ModelSpec.from_dict(CANONICAL)
    backend = NS(name='cpu-loopback', suffix='.plan', tag=lambda: 'cpu-loopback',
                 describe=lambda: {'backend': 'cpu-loopback',
                                   'runtime_version': 'synthetic', 'device': 'CPU'})
    if scenario.startswith('daemon_'):
        # Exercise the actual C selection allowlist using a synthetic TRT
        # description. This fixture still runs CpuEngine; there is NO GPU/TRT.
        backend.describe = lambda: {'backend': 'trt', 'runtime_version': 'CPU_FAKE_NO_TRT',
                                    'device': 'CPU_FAKE_NO_GPU', 'carrot_host': 'jetson'}
    hardware_loads = []

    def load_cpu_artifact(path, report=None):
        assert path.read_bytes() == b'CPU hardware substitute, no TensorRT plan'
        loaded_engine = CpuEngine(spec)
        hardware_loads.append(loaded_engine)
        return loaded_engine

    backend.load = load_cpu_artifact
    with tempfile.TemporaryDirectory(prefix='cinque-v3-loopback-') as cache:
        host = S.EngineHost(S.EngineCache(Path(cache), backend))
        engine = CpuEngine(spec)
        if scenario.startswith('daemon_'):
            # Keep the real parser's exp(std) finite for this arithmetic oracle.
            engine.output_scale = np.float32(.001)
        host.loaded = host._warm(engine, spec)
        assert all(not np.any(engine.buffers[n]) for n in STATE_NAMES)
        engine.state_seen.clear()
        engine.images.clear()
        engine.fault = scenario in ('invalid_state', 'invalid_state_reload', 'daemon_fallback')
        if scenario == 'invalid_state_reload':
            # A hardware-fixture cache drives the REAL host request/load worker.
            # It cannot be consumed by a TRT backend and is confined to tempdir.
            entry = host.cache.entry(spec.sha256)
            entry.path.write_bytes(b'CPU hardware substitute, no TensorRT plan')
            entry.write_meta({'spec': spec.to_dict()})
        report = {'infer_request_sizes': [], 'infer_response_sizes': [],
                  'engine_requests': [], 'hello_sessions': [],
                  'hello_capabilities': [], 'ready_generations': []}
        previous = None
        before = {n: engine.buffers[n].copy() for n in STATE_NAMES}

        class FaultWire(Transport):
            def __init__(self, inner, index):
                self.inner, self.index = inner, index

            def recv(self, timeout=None):
                msg = self.inner.recv(timeout)
                if msg.msg_type == P.Msg.INFER_REQ:
                    report['infer_request_sizes'].append(msg.payload.nbytes)
                elif msg.msg_type == P.Msg.ENGINE_REQ:
                    report['engine_requests'].append(json.loads(bytes(msg.payload)))
                return msg

            def send(self, mt, seq, parts=(), flags=0, timeout=None):
                nonlocal previous
                payload = b''.join(memoryview(p).cast('B') for p in parts)
                if mt == P.Msg.HELLO_RESP:
                    obj = json.loads(payload)
                    report['hello_sessions'].append(obj.get('session_id'))
                    report['hello_capabilities'].append(obj.get(CAP))
                    if scenario == 'missing_capability':
                        obj.pop(CAP, None)
                    elif scenario in ('unsupported_capability', 'wrong_capability_spec'):
                        cap = obj.setdefault(CAP, {})
                        cap['version' if scenario == 'unsupported_capability' else 'spec_sha256'] = (
                            999 if scenario == 'unsupported_capability' else '0' * 64)
                    payload = json.dumps(obj).encode()
                elif mt == P.Msg.ENGINE_RESP:
                    obj = json.loads(payload)
                    if obj.get('state') == 'ready':
                        report['ready_generations'].append(obj.get('generation'))
                    if scenario == 'wrong_spec' and 'spec' in obj:
                        obj['spec']['output_slices']['plan'][0] += 1
                    elif scenario == 'wrong_dtype' and 'spec' in obj:
                        obj['spec']['input_dtypes']['new_img'] = 'float16'
                    elif scenario == 'wrong_model_size' and 'spec' in obj:
                        obj['spec']['nbytes'] += 1
                    elif scenario == 'wrong_model_sha' and 'spec' in obj:
                        obj['spec']['sha256'] = '0' * 64
                    elif scenario == 'not_ready':
                        obj['state'] = 'failed'
                        obj['detail'] = 'injected response-boundary failure'
                    elif scenario == 'missing_generation':
                        obj.pop('generation', None)
                    elif scenario == 'invalid_generation':
                        obj['generation'] = 'invalid'
                    elif scenario == 'wrong_session':
                        obj['session_id'] = 'f' * 32
                    payload = json.dumps(obj).encode()
                elif mt == P.Msg.INFER_RESP:
                    report['infer_response_sizes'].append(len(payload))
                    if scenario == 'previous_connection':
                        if self.index == 0:
                            previous = (seq, payload)
                        else:
                            # Simulate an old USB result delivered after rebind.
                            # No new reply is sent, so only rejection can pass.
                            self.inner.send(mt, previous[0], (previous[1],), flags, timeout)
                            return
                    if scenario == 'missing_header':
                        payload = payload[:3]
                    elif scenario == 'truncated':
                        payload = payload[:-4]
                    elif scenario == 'excess':
                        payload += b'junk'
                    elif scenario in ('nan', 'inf'):
                        payload = bytearray(payload)
                        np.frombuffer(payload, np.float32, offset=P.INFER_RESP_SIZE)[0] = (
                            np.nan if scenario == 'nan' else np.inf)
                    elif scenario == 'wrong_frame_id':
                        h = P.unpack_infer_resp(memoryview(payload))
                        payload = P.pack_infer_resp(h[0] + 1, *h[1:]) + payload[P.INFER_RESP_SIZE:]
                    elif scenario == 'stale_sequence':
                        seq = (seq - 1) & 0xffffffff
                    elif scenario == 'deadline':
                        time.sleep(.4)
                        return
                    elif scenario == 'disconnect':
                        self.inner.close()
                        return
                self.inner.send(mt, seq, (payload,), flags, timeout)

            def close(self):
                self.inner.close()

        listener = TcpTransport.listen('127.0.0.1', 0)
        listener.settimeout(10)
        emit({'host': '127.0.0.1', 'port': listener.getsockname()[1], 'module': S.__file__})
        try:
            for index in range(2 if scenario == 'previous_connection' else 1):
                inner, _ = TcpTransport.accept(listener)
                wire = FaultWire(inner, index)
                session = S.Session(wire, host)
                try:
                    session.serve_forever()
                except LinkError:
                    pass
                finally:
                    session.close()
                    wire.close()
            preserved = engine.before_fault if engine.before_fault is not None else before
            report.update(valid=host.loaded.valid, images=engine.images,
                          state_seen=engine.state_seen,
                          state_preserved=all(np.array_equal(preserved[n], engine.buffers[n])
                                              for n in STATE_NAMES))
            report['hardware_loads'] = len(hardware_loads)
            if hardware_loads:
                # warm() runs once with cleared queues; final entry is infer().
                report['reload_first_state'] = hardware_loads[-1].state_seen[-1]
            emit(report)
        finally:
            listener.close()
            host.close()


def drive(scenario, port):
    from jetlink import client as C
    from jetlink import protocol as P
    from jetlink.spec import ModelSpec
    from jetlink.transport.base import LinkError

    report = {'module': C.__file__, 'seed': 73}
    rng = np.random.default_rng(73)

    def connect():
        client = C.JetlinkClient.open_tcp('127.0.0.1', port, deadline=.25)
        hello = client.hello(timeout=2)
        assert hello['protocol'] == 2
        return client, hello

    def approve(client):
        client.approve_v3(ModelSpec.from_dict(copy.deepcopy(CANONICAL)))
        return client.ensure_engine(CANONICAL['sha256'], CANONICAL['nbytes'],
                                    frame_skip=CANONICAL['frame_skip'], build_timeout=2)

    def inputs(spec):
        image = int(rng.integers(1, 255))
        return (np.full(spec.warped_shape, image, np.uint8),
                rng.uniform(.1, .9, spec.packed_nelem).astype(np.float32))

    client, hello = connect()
    try:
        if scenario.startswith('daemon_'):
            drive_daemon(client, hello, scenario, report)
        elif scenario in ('missing_capability', 'unsupported_capability', 'wrong_capability_spec',
                        'wrong_spec', 'wrong_dtype', 'wrong_model_size', 'wrong_model_sha',
                        'not_ready', 'missing_generation', 'invalid_generation', 'wrong_session'):
            try:
                approve(client)
            except LinkError:
                report['rejected'] = True
            else:
                raise AssertionError('V3 was approved from an incompatible response')
        elif scenario == 'generic_stateful':
            raw = copy.deepcopy(CANONICAL)
            raw['sha256'] = '1' * 64
            try:
                client.approve_v3(ModelSpec.from_dict(raw))
            except LinkError:
                report['rejected'] = True
            else:
                raise AssertionError('generic stateful model obtained fixed V3 approval')
        elif scenario == 'no_approval':
            try:
                client.ensure_engine(CANONICAL['sha256'], CANONICAL['nbytes'],
                                     frame_skip=4, build_timeout=.2)
            except LinkError:
                report['rejected'] = True
            else:
                raise AssertionError('fixed V3 became ready without explicit approval')
        else:
            spec = approve(client)
            assert spec.to_dict() == CANONICAL
            assert 'prev_feat' not in spec.packed_shapes
            warped, packed = inputs(spec)
            if scenario == 'continuous':
                state = np.float32(0)
                for fid in range(1, 7):
                    warped, packed = inputs(spec)
                    image = int(warped.flat[0])
                    scalar = np.float32(sum(float(v.sum()) for v in (
                        packed[:8], packed[8:10], packed[10:12])))
                    expected = np.float32(3 * float(state) + image + scalar)
                    out = client.infer(warped, packed, frame_id=fid)
                    np.testing.assert_array_equal(out, np.full(spec.output_nelem, expected, np.float32))
                    state += np.float32(1 + image % 7)
                report.update(frames=6, output_nbytes=out.nbytes)
            elif scenario == 'hello_again':
                client.infer(warped, packed, frame_id=1)
                second = client.hello(timeout=2)
                report['fresh_session'] = hello['session_id'] != second['session_id']
                try:
                    client.ensure_engine(CANONICAL['sha256'], CANONICAL['nbytes'], frame_skip=4,
                                         build_timeout=.2)
                except LinkError:
                    report['approval_revoked'] = True
                else:
                    raise AssertionError('HELLO retained old explicit V3 approval')
                spec = approve(client)
                client.infer(warped, packed, frame_id=2)
            else:
                if scenario == 'previous_connection':
                    report['prior_seq'] = client.infer_begin(warped, packed, frame_id=7)
                    client.infer_end(report['prior_seq'])
                    client.close()
                    client, _ = connect()
                    spec = approve(client)
                elif scenario in ('invalid_state', 'invalid_state_reload'):
                    client.infer(warped, packed, frame_id=1)
                initial_generation = client._engine_state.get('generation')
                started = time.monotonic()
                try:
                    seq = client.infer_begin(warped, packed, frame_id=7)
                    report['fresh_seq'] = seq
                    client.infer_end(seq)
                except LinkError:
                    report.update(rejected=True, dead=client.dead,
                                  failure_seconds=time.monotonic() - started)
                else:
                    raise AssertionError('invalid response was accepted')
                try:
                    client.infer(warped, packed, frame_id=8)
                except LinkError:
                    report['resume_rejected'] = True
                else:
                    raise AssertionError('failed client resumed inference')
                if scenario in ('invalid_state', 'invalid_state_reload'):
                    # A transport probe after the real client fails proves the
                    # real server generation is invalid, even if caller retries.
                    client.t.send(P.Msg.INFER_REQ, client._next_seq(), (
                        P.pack_infer_req(8, 0), warped, packed))
                    probe = client.t.recv(timeout=2)
                    assert probe.msg_type == P.Msg.INFER_RESP and probe.payload.nbytes == 20
                    report['probe_status'] = int(P.unpack_infer_resp(probe.payload)[1])
                    if scenario == 'invalid_state_reload':
                        # A fresh real client owns the same transport after the
                        # old one is dead. HELLO/approve/request load a new CPU
                        # engine through the real worker rather than reviving it.
                        client = C.JetlinkClient(client.t, deadline=.5)
                        client.hello(timeout=2)
                        spec = approve(client)
                        report['fresh_generation'] = initial_generation != client._engine_state['generation']
                        output = client.infer(warped, packed, frame_id=9)
                        report['recovered'] = output.nbytes == 73808 and bool(np.all(np.isfinite(output)))
    finally:
        client.close()
    emit(report)


def drive_daemon(remote, peer, scenario, report):
    """Actual C preparation → daemon → Unix IPC → parser/JoiningModel.

    Substitutes Params, logging/diagnostics, status/phase publishers, affinity,
    attached lifetime, native camera warp and the internal model's hardware.
    No prepare, daemon serve function, IPC, client, parser or JoiningModel.run
    function is replaced. The __new__ setup avoids QCOM/tinygrad construction.
    """
    from openpilot.selfdrive.modeld.jetlink import daemon, link, mac, model, selection
    from openpilot.selfdrive.modeld.parse_model_outputs import Parser
    from jetlink.transport.base import LinkError

    os.environ['CARROT_JETLINK_V3'] = '1'
    diagnostics, statuses, phases = [], [], []
    sys.modules['openpilot.common.params'] = NS(Params=lambda: NS(
        get_bool=lambda key: key == 'IsOffroad', put_bool_nonblocking=lambda *a: None))
    sys.modules['openpilot.common.runtime_diagnostics'] = NS(RuntimeDiagnostics=lambda *a: NS(
        record=lambda **kw: diagnostics.append(kw)))
    sys.modules['openpilot.common.swaglog'] = NS(cloudlog=NS(
        event=lambda *a, **kw: None, warning=lambda *a, **kw: None,
        exception=lambda *a, **kw: None))
    attached = threading.Event()
    attached.set()
    daemon.host_attached = attached.is_set
    daemon.update_affinity = lambda: None
    daemon.publish = lambda status, **kw: statuses.append(status)
    daemon.TRANSPORT_MODE = daemon.SESSION_MODE = 'usb'
    failure = []

    with tempfile.TemporaryDirectory(prefix='cinque-comma-ipc-') as directory:
        cache = Path(directory)
        spec = mac.prepare(remote, peer, lambda: True, attached.is_set,
                           lambda *a: None, cache, mode='usb')
        assert spec.to_dict() == CANONICAL
        report['prepared'] = True
        report['approval_recorded'] = selection.approved_spec(cache / 'jetson-v3') == spec
        listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        address = str(cache / 'local.sock')
        listener.bind(address)
        listener.listen(1)
        listener.settimeout(.05)

        def owner():
            try:
                daemon._serve_local(listener, remote, peer, None,
                                    NS(sent=lambda source: phases.append(source)))
            except LinkError as exc:
                failure.append(str(exc))
            finally:
                attached.clear()

        thread = threading.Thread(target=owner, daemon=True, name='actual-jetlink-daemon')
        thread.start()
        local = None
        try:
            local = link.Client(path=address, timeout=.75)
            assert local.spec == spec
            if scenario == 'daemon_continuous':
                parser = Parser()
                outputs = []
                state = 0.
                for fid, image in enumerate((42, 133), start=1):
                    warped = np.full(spec.warped_shape, image, np.uint8)
                    packed = np.linspace(.1 * fid, .2 * fid, 12, dtype=np.float32)
                    output = local.infer(warped, packed, fid, source_sof=time.monotonic_ns())
                    assert output.nbytes == 73808 and np.all(np.isfinite(output))
                    scalar = np.float32(sum(float(v.sum()) for v in (
                        packed[:8], packed[8:10], packed[10:12])))
                    expected = np.float32(3 * state + image + scalar) * np.float32(.001)
                    np.testing.assert_array_equal(output, np.full(spec.output_nelem, expected, np.float32))
                    state += 1 + image % 7
                    outputs.append(output)
                    parsed = model.parse_outputs(parser, spec, output)
                    assert all(np.all(np.isfinite(v)) for v in parsed.values() if isinstance(v, np.ndarray))
                report.update(ipc_frames=2, finite_parsed=True,
                              changing_outputs=not np.array_equal(*outputs),
                              parsed_shapes={n: list(parsed[n].shape) for n in ('plan', 'lead', 'action')})
            else:
                small_runs, small_resets = [], []

                class Camera:
                    timings = (0., 0., 0.)
                    def __init__(self):
                        self.images = iter((42, 133))
                    def __call__(self, *a):
                        return np.full(spec.warped_shape, next(self.images), np.uint8)

                joined = model.JoiningModel.__new__(model.JoiningModel)
                joined.small = NS(run=lambda *a: small_runs.append(True) or {'internal': np.ones(4, np.float32)},
                                  reset=lambda: small_resets.append(True))
                joined.warp = Camera()
                joined.preparation = joined.connection = None
                joined.client = local
                joined.ready = joined.join_allowed = True
                joined.active = False
                joined.small_runs = 3
                joined.next_join = 0.
                joined.spec = spec
                joined.parser = Parser()
                joined.packed = np.zeros(12, np.float32)
                joined.views = {n: a.reshape(shape) for (n, shape), a in zip(
                    spec.packed_shapes.items(), np.split(joined.packed, [8, 10]), strict=True)}
                joined.prev_desire = np.zeros(8, np.float32)
                joined.frame = joined.source_sof = 0
                joined.reset = True
                joined.last_slow_log = joined.next_status = 0.
                joined.error = ''
                model.FAULT = cache / 'fault'
                inputs = {'desire_pulse': np.zeros(8, np.float32),
                          'traffic_convention': np.array([[1., 0.]], np.float32),
                          'action_t': np.array([[.2, .3]], np.float32)}
                first = joined.run({}, {}, inputs, False)
                report.update(initial_remote_active=joined.active,
                              remote_plan_shape=list(first['plan'].shape))
                second = joined.run({}, {}, inputs, False)
                report['fallback_returned'] = 'internal' in second and not joined.active and joined.client is None
                third = joined.run({}, {}, inputs, False)
                report['next_internal_frame_finite'] = bool(np.all(np.isfinite(third['internal'])))
                status = joined._status_record(time.monotonic())
                report.update(fault_written=model.FAULT.is_file(), small_resets=len(small_resets),
                              small_runs=len(small_runs), active_model_after_failure=status['active_model'],
                              selected_model_after_failure=status['selected_model'])
        finally:
            attached.clear()
            if local is not None:
                local.close()
            thread.join(timeout=3)
            listener.close()
            assert not thread.is_alive(), 'real daemon did not stop after simulated detach'
        report.update(diagnostic_frames=len(diagnostics), phase_frames=len(phases),
                      daemon_link_failed=bool(failure),
                      fake_backend_description='trt allowlist exercised; CpuEngine, no GPU/TRT',
                      glue_modules={n: module.__file__ for n, module in (
                          ('daemon', daemon), ('link', link), ('mac', mac), ('model', model))})


if __name__ == '__main__':
    if sys.argv[1] == 'server':
        serve(sys.argv[2])
    else:
        drive(sys.argv[2], int(sys.argv[3]))
