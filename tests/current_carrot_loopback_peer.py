"""Current-source protocol-3 integration peer, in one namespace per process.

The full-size CPU recurrence substitutes the inference hardware.  The current
Session, EngineHost._warm, TCP framing, client, mac.prepare, daemon IPC, parser
and JoiningModel methods execute unchanged.  FaultWire corrupts only response
bytes, except invalid_state which corrupts one CPU hardware output.
"""
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


CANONICAL = json.loads((Path(__file__).resolve().parents[1] / 'artifacts/cinque_v3.json').read_text())
STATE_NAMES = ('state_img_q', 'state_desire_q', 'state_feat_q')
CAPABILITY = 'carrot_model_selection_v1'


def emit(value):
    print(json.dumps(value, sort_keys=True), flush=True)


class CpuEngine:
    """A deterministic recurrence over real V3 shapes; no ONNX, CUDA or TRT."""
    dtype_transforms = {}

    def __init__(self, spec):
        self.inputs = {n: NS(shape=s, dtype=np.dtype(spec.input_dtypes[n]))
                       for n, s in spec.input_shapes.items()}
        self.outputs = {n: NS(shape=s, dtype=np.dtype(spec.output_dtypes[n]))
                        for n, s in spec.output_shapes.items()}
        self.buffers = {n: np.full(io.shape, 7, io.dtype) for n, io in self.inputs.items()}
        self.last_gpu_us = 0
        self.state_seen, self.images = [], []
        self.fault = False
        self.before_fault = None

    def host_input(self, name):
        return self.buffers[name]

    def warm(self):
        self.run()
        return 'CPU_FAKE: full-size synthetic recurrence, no ONNX/CUDA/TensorRT'

    def run(self):
        state = [float(self.buffers[n].flat[0]) for n in STATE_NAMES]
        for name, value in zip(STATE_NAMES, state, strict=True):
            assert np.all(self.buffers[name] == value), name
        image = int(self.buffers['new_img'].flat[0])
        self.state_seen.append(state)
        self.images.append(image)
        scalar = np.float32(sum(float(self.buffers[n].sum())
                                for n in ('desire', 'traffic_convention', 'action_t')))
        value = np.float32(sum(state) + image + scalar) * np.float32(.001)
        outputs = {'outputs': np.full(self.outputs['outputs'].shape, value, np.float32)}
        for name in STATE_NAMES:
            outputs['next_' + name] = self.buffers[name] + np.array(1 + image % 7, self.buffers[name].dtype)
        if self.fault and state[0] > 0:
            self.before_fault = {n: self.buffers[n].copy() for n in STATE_NAMES}
            outputs['next_state_feat_q'].flat[-1] = np.nan
        return outputs

    def close(self):
        pass


def serve(scenario):
    from jetlink import protocol as P
    from jetlink.server import session as S
    from jetlink.spec import ModelSpec
    from jetlink.transport.base import LinkError, Transport
    from jetlink.transport.tcp import TcpTransport

    spec = ModelSpec.from_dict(CANONICAL)
    assert spec.to_dict() == CANONICAL
    backend = NS(name='CPU_FAKE', suffix='.cpu-fixture', tag=lambda: 'CPU_FAKE',
                 describe=lambda: {'backend': 'trt', 'runtime_version': 'CPU_FAKE',
                                   'device': 'CPU_FAKE', 'carrot_host': 'jetson'})
    with tempfile.TemporaryDirectory(prefix='current-carrot-server-') as directory:
        host = S.EngineHost(S.EngineCache(Path(directory), backend))
        engine = CpuEngine(spec)
        host.loaded = host._warm(engine, spec)
        assert all(not np.any(engine.buffers[n]) for n in STATE_NAMES)
        engine.state_seen.clear()
        engine.images.clear()
        engine.fault = scenario == 'daemon_invalid_state'
        report = {'evidence': 'CPU_FAKE', 'protocol': 3, 'infer_request_sizes': [],
                  'infer_response_sizes': [], 'infer_response_statuses': [],
                  'engine_requests': [], 'hellos': [], 'telemetry_identity_changed': False}
        previous = None

        class FaultWire(Transport):
            def __init__(self, inner, index):
                self.inner, self.index = inner, index
                self.protocol_version = 3

            def recv(self, timeout=None):
                message = self.inner.recv(timeout)
                if message.msg_type == P.Msg.INFER_REQ:
                    report['infer_request_sizes'].append(message.payload.nbytes)
                elif message.msg_type == P.Msg.ENGINE_REQ:
                    report['engine_requests'].append(json.loads(bytes(message.payload)))
                return message

            def send(self, kind, seq, parts=(), flags=0, timeout=None):
                nonlocal previous
                payload = b''.join(memoryview(part).cast('B') for part in parts)
                if kind == P.Msg.HELLO_RESP:
                    report['hellos'].append(json.loads(payload))
                elif kind == P.Msg.ENGINE_RESP:
                    obj = json.loads(payload)
                    if scenario == 'prepare_wrong_sha' and 'spec' in obj:
                        obj['spec']['sha256'] = '0' * 64
                    elif scenario == 'prepare_wrong_size' and 'spec' in obj:
                        obj['spec']['nbytes'] += 1
                    elif scenario == 'prepare_changed_spec' and 'spec' in obj and self.index == 1:
                        obj['spec']['checkpoint'] = 'changed-after-offroad-approval'
                    payload = json.dumps(obj).encode()
                elif kind == P.Msg.INFER_RESP:
                    report['infer_response_sizes'].append(len(payload))
                    report['infer_response_statuses'].append(int(P.unpack_infer_resp(memoryview(payload))[1]))
                    if scenario == 'previous_connection':
                        if self.index == 0:
                            previous = (seq, payload)
                        else:
                            assert previous is not None
                            self.inner.send(kind, previous[0], (previous[1],), flags, timeout)
                            return
                    elif scenario == 'daemon_timeout':
                        # Withhold a response beyond the unchanged 3 s client
                        # deadline and the unchanged 150 ms local IPC deadline.
                        time.sleep(3.3)
                        return
                    elif scenario == 'daemon_disconnect':
                        self.inner.close()
                        return
                    elif scenario == 'daemon_wrong_frame':
                        fid, *header = P.unpack_infer_resp(memoryview(payload))
                        payload = P.pack_infer_resp(fid + 1, *header) + payload[P.INFER_RESP_SIZE:]
                    elif scenario == 'daemon_stale_sequence':
                        seq -= 1
                    elif scenario == 'daemon_nonfinite':
                        payload = bytearray(payload)
                        np.frombuffer(payload, np.float32, offset=P.INFER_RESP_SIZE)[0] = np.nan
                    elif scenario == 'daemon_truncated':
                        payload = payload[:-4]
                    elif scenario == 'daemon_identity_change':
                        # Frame 20 requests real protocol telemetry; the current
                        # daemon's check_loaded must reject it before IPC reply.
                        fid, _, _, _, _ = P.unpack_infer_resp(memoryview(payload))
                        if fid == 20:
                            end = P.INFER_RESP_SIZE + spec.output_nbytes
                            telemetry = json.loads(payload[end:])
                            telemetry['loaded'] = '0' * 64
                            payload = payload[:end] + json.dumps(telemetry).encode()
                            report['telemetry_identity_changed'] = True
                # Preserve empty PONG parts: an added zero-length buffer would
                # be a fixture transport mutation after the header is sent.
                self.inner.send(kind, seq, (payload,) if payload else (), flags, timeout)

            def close(self):
                self.inner.close()

        listener = TcpTransport.listen('127.0.0.1', 0)
        listener.settimeout(15)
        emit({'host': '127.0.0.1', 'port': listener.getsockname()[1], 'module': S.__file__})
        try:
            count = 2 if scenario in ('previous_connection', 'prepare_changed_spec') else 1
            for index in range(count):
                inner, _ = TcpTransport.accept(listener)
                inner.protocol_version = 3
                wire = FaultWire(inner, index)
                session = S.Session(wire, host)
                try:
                    session.serve_forever()
                except LinkError:
                    pass
                finally:
                    session.close()
                    wire.close()
            report.update(valid=host.loaded.valid, images=engine.images, state_seen=engine.state_seen,
                          state_preserved=engine.before_fault is not None and all(
                              np.array_equal(engine.before_fault[n], engine.buffers[n]) for n in STATE_NAMES),
                          has_openpilot_imports=any(n.startswith('openpilot.') for n in sys.modules))
            emit(report)
        finally:
            listener.close()
            host.close()


def connect(port):
    from jetlink.client import JetlinkClient
    remote = JetlinkClient.open_tcp('127.0.0.1', port)
    remote.t.protocol_version = 3
    peer = remote.hello(timeout=2)
    assert peer['protocol'] == 3
    assert peer['carrot_host'] == 'jetson'
    assert peer['device'] == peer['runtime_version'] == 'CPU_FAKE'
    assert peer[CAPABILITY] == {'version': 1, 'selection': 'host'}
    return remote, peer


def hardware_boundaries():
    """Only native Params/logging/diagnostics are replaced before method calls."""
    diagnostics = []
    sys.modules['openpilot.common.params'] = NS(Params=lambda: NS(
        get_bool=lambda key: key == 'IsOffroad', put_bool_nonblocking=lambda *args: None))
    sys.modules['openpilot.common.runtime_diagnostics'] = NS(RuntimeDiagnostics=lambda *args: NS(
        record=lambda **kwargs: diagnostics.append(kwargs)))
    sys.modules['openpilot.common.swaglog'] = NS(cloudlog=NS(
        event=lambda *args, **kwargs: None, warning=lambda *args, **kwargs: None,
        exception=lambda *args, **kwargs: None))
    return diagnostics


def drive(scenario, port):
    from jetlink import client as C
    from jetlink.transport.base import LinkError
    from openpilot.selfdrive.modeld.jetlink import mac, selection

    diagnostics = hardware_boundaries()
    report = {'module': C.__file__, 'evidence': 'CPU_FAKE', 'protocol': 3,
              'frame_timeout': C.FRAME_TIMEOUT,
              'glue_modules': {'mac': mac.__file__, 'selection': selection.__file__}}
    remote, peer = connect(port)
    try:
        with tempfile.TemporaryDirectory(prefix='current-carrot-comma-') as directory:
            cache = Path(directory)

            def prepare(offroad=True):
                return mac.prepare(remote, peer, lambda: offroad, lambda: True,
                                   lambda *args: None, cache, mode='usb')

            if scenario in ('prepare_wrong_sha', 'prepare_wrong_size'):
                try:
                    prepare()
                except (LinkError, ValueError, mac.PreparationDeferred) as exc:
                    report.update(preparation_rejected=True, error=str(exc))
                else:
                    raise AssertionError('invalid ready identity was approved')
            else:
                spec = prepare()
                assert spec.to_dict() == CANONICAL
                report['prepared'] = True
                approved = list(cache.rglob('selected.json'))
                assert len(approved) == 1, approved
                assert selection.approved_spec(approved[0].parent).to_dict() == CANONICAL
                report['approval_recorded'] = True
                if scenario == 'prepare_changed_spec':
                    remote.close()
                    remote, peer = connect(port)
                    try:
                        prepare(offroad=False)
                    except ValueError as exc:
                        report.update(preparation_rejected=True, error=str(exc),
                                      approval_preserved=selection.approved_spec(approved[0].parent).to_dict() == CANONICAL)
                    else:
                        raise AssertionError('previously approved spec changed onroad')
                elif scenario == 'previous_connection':
                    remote.ping()
                    remote.ping()
                    warped = np.full(spec.warped_shape, 42, np.uint8)
                    packed = np.zeros(spec.packed_nelem, np.float32)
                    prior = remote.infer_begin(warped, packed, frame_id=7)
                    remote.infer_end(prior)
                    remote.close()
                    remote, peer = connect(port)
                    prepare(offroad=False)
                    started = time.monotonic()
                    fresh = remote.infer_begin(warped, packed, frame_id=8)
                    try:
                        remote.infer_end(fresh)
                    except LinkError:
                        report.update(rejected=True, dead=remote.dead, prior_seq=prior,
                                      fresh_seq=fresh, failure_seconds=time.monotonic() - started)
                    else:
                        raise AssertionError('old connection response satisfied the new frame')
                else:
                    drive_daemon(remote, peer, scenario, spec, cache, diagnostics, report)
    finally:
        remote.close()
    emit(report)


def drive_daemon(remote, peer, scenario, spec, cache, diagnostics, report):
    from openpilot.selfdrive.modeld.jetlink import daemon, link, model
    from openpilot.selfdrive.modeld.parse_model_outputs import Parser
    from jetlink.transport.base import LinkError

    attached = threading.Event()
    attached.set()
    phases, statuses, failure = [], [], []
    daemon.host_attached = attached.is_set
    daemon.update_affinity = lambda: None
    daemon.publish = lambda status, **kwargs: statuses.append(status)
    daemon.TRANSPORT_MODE = daemon.SESSION_MODE = 'usb'
    listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    address = str(cache / 'local.sock')
    listener.bind(address)
    listener.listen(1)
    listener.settimeout(.05)

    def owner():
        try:
            daemon._serve_local(listener, remote, peer, None, NS(sent=lambda source: phases.append(source)))
        except (LinkError, RuntimeError) as exc:
            failure.append(str(exc))
        finally:
            attached.clear()

    thread = threading.Thread(target=owner, daemon=True, name='current-carrot-real-daemon')
    thread.start()
    local = None
    try:
        # Use link.Client's production 150 ms IPC and remote's 3 s deadlines.
        local = link.Client(path=address)
        assert local.spec.to_dict() == CANONICAL
        report['ipc_timeout'] = local.timeout
        if scenario == 'daemon_continuous':
            outputs, state = [], 0.
            for fid, image in enumerate((42, 133), start=1):
                warped = np.full(spec.warped_shape, image, np.uint8)
                packed = np.linspace(.1 * fid, .2 * fid, spec.packed_nelem, dtype=np.float32)
                output = local.infer(warped, packed, fid, source_sof=time.monotonic_ns())
                scalar = np.float32(sum(float(value.sum()) for value in (packed[:8], packed[8:10], packed[10:12])))
                expected = np.float32(3 * state + image + scalar) * np.float32(.001)
                np.testing.assert_array_equal(output, np.full(spec.output_nelem, expected, np.float32))
                state += 1 + image % 7
                outputs.append(output.copy())
                parsed = model.parse_outputs(Parser(), spec, output)
                assert all(np.all(np.isfinite(value)) for value in parsed.values() if isinstance(value, np.ndarray))
            report.update(ipc_frames=2, output_nbytes=outputs[-1].nbytes, finite_parsed=True,
                          changing_outputs=not np.array_equal(*outputs),
                          parsed_shapes={name: list(parsed[name].shape) for name in ('plan', 'lead', 'action')})
        else:
            small_runs, small_resets = [], []

            class Camera:
                timings = (0., 0., 0.)

                def __init__(self):
                    self.images = iter((42, 133))

                def __call__(self, *args):
                    return np.full(spec.warped_shape, next(self.images), np.uint8)

            # QCOM constructor is the hardware seam; run() is the current method.
            joined = model.JoiningModel.__new__(model.JoiningModel)
            joined.small = NS(run=lambda *args: small_runs.append(True) or {'internal': np.ones(4, np.float32)},
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
            joined.packed = np.zeros(spec.packed_nelem, np.float32)
            joined.views = {name: value.reshape(shape) for (name, shape), value in zip(
                spec.packed_shapes.items(), np.split(joined.packed, np.cumsum(spec.packed_sizes[:-1])), strict=True)}
            joined.prev_desire = np.zeros(8, np.float32)
            joined.frame = 18 if scenario == 'daemon_identity_change' else 0
            joined.source_sof = 0
            joined.reset = True
            joined.last_slow_log = joined.next_status = 0.
            joined.error = ''
            model.FAULT = cache / 'fault'
            inputs = {'desire_pulse': np.zeros(8, np.float32),
                      'traffic_convention': np.array([[1., 0.]], np.float32),
                      'action_t': np.array([[.2, .3]], np.float32)}
            if scenario in ('daemon_invalid_state', 'daemon_identity_change'):
                first = joined.run({}, {}, inputs, False)
                report.update(initial_remote_active=joined.active, remote_plan_shape=list(first['plan'].shape))
            else:
                # These wire faults act on the first response, exercising a
                # failure before adoption: the local fallback must still run.
                report['initial_remote_active'] = False
            started = time.monotonic()
            fallback = joined.run({}, {}, inputs, False)
            elapsed = time.monotonic() - started
            report['fallback_returned'] = 'internal' in fallback and not joined.active and joined.client is None
            next_output = joined.run({}, {}, inputs, False)
            report.update(next_internal_frame_finite=bool(np.all(np.isfinite(next_output['internal']))),
                          fault_written=model.FAULT.is_file(), small_resets=len(small_resets),
                          small_runs=len(small_runs), error=joined.error, fallback_seconds=elapsed)
            # A dead remote link must not leave a usable IPC session. The exact
            # default remote timeout can outlast modeld's local timeout.
            if scenario in ('daemon_timeout', 'daemon_stale_sequence'):
                thread.join(timeout=4)
            else:
                thread.join(timeout=1)
            report['ipc_closed_by_daemon'] = not thread.is_alive() and bool(failure)
    finally:
        attached.clear()
        if local is not None:
            local.close()
        thread.join(timeout=4)
        listener.close()
        assert not thread.is_alive(), 'current daemon failed to stop'
    report.update(diagnostic_frames=len(diagnostics), phase_frames=len(phases),
                  daemon_link_failed=bool(failure), daemon_error=failure,
                  fake_backend_description='trt identity allowlist only; CPU_FAKE hardware',
                  glue_modules={**report['glue_modules'], **{name: module.__file__ for name, module in (
                      ('daemon', daemon), ('link', link), ('model', model))}})


if __name__ == '__main__':
    if sys.argv[1] == 'server':
        serve(sys.argv[2])
    else:
        drive(sys.argv[2], int(sys.argv[3]))
