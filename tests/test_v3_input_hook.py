"""M18 CPU fixture and disposable actual366 candidate checks; no device access."""
from __future__ import annotations
import ast
import copy
import hashlib
import json
import marshal
import os
from pathlib import Path
import subprocess
import struct
import sys
import time
import types

import numpy as np
import pytest

from recording import hook


REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / '.reference/m15-carrot-nav-366d6eae'


class Spec:
    sha256 = '1' * 64
    stateful = False
    warped_shape = (2, 6, 128, 256)
    packed_shapes = {'desire': (8,), 'traffic_convention': (1, 2), 'action_t': (1, 2), 'prev_feat': (1, 16)}
    packed_nelem = 28
    input_shapes = {'img': (1, 12, 128, 256), 'big_img': (1, 12, 128, 256)}
    output_shapes = {'outputs': (1, 42)}
    output_slices = {'hidden_state': slice(0, 16)}
    nbytes = 100
    frame_skip = 4
    checkpoint = 'fixture'

    def to_dict(self):
        return {'sha256': self.sha256, 'input_shapes': self.input_shapes, 'frame_skip': self.frame_skip,
                'output_shapes': self.output_shapes, 'nbytes': self.nbytes,
                'output_slices': {k: [v.start, v.stop] for k, v in self.output_slices.items()},
                'checkpoint': self.checkpoint}


class Sink:
    def __init__(self, *args, **kwargs):
        self.records = []
        self.stops = []

    def observe(self, *args):
        image, desire, traffic, action, meta = args
        self.records.append((image.copy(), desire.copy(), traffic.copy(), action.copy(), copy.deepcopy(meta)))
        return True

    def stop(self, reason):
        self.stops.append(reason)

    def close(self, timeout=1):
        return None


def fake_namespace(spec=None):
    spec = spec or Spec()
    class CameraGapTrace:
        def receive(self, main, extra=None):
            return self.result
    class Warp:
        def __call__(self, bufs, transforms, *, prepare=None):
            self.transforms = {'tfm': np.asarray(transforms['img'], dtype=np.float32),
                               'big_tfm': np.asarray(transforms['big_img'], dtype=np.float32)}
            if prepare:
                prepare()
            return bufs
    class Client:
        def __init__(self):
            self.spec = spec
            self.calls = []
        def infer(self, image, packed, frame, reset=False, source_sof=0):
            self.calls.append((image, packed, frame, reset, source_sof))
            if getattr(self, 'failure', None):
                raise self.failure
            packed[:] = 99  # Observer must copy before the existing call.
            return self
    return {'CameraGapTrace': CameraGapTrace, 'Warp': Warp, 'Client': Client}


def ticket(tmp_path, spec=None):
    spec = spec or Spec()
    root = tmp_path / 'external-captures'
    root.mkdir(exist_ok=True)
    return {'schema': 1, 'capture_id': 'a' * 32, 'output_root': str(root), 'output': str(root / ('a' * 32)),
            'frames': 256, 'depth': 4, 'carrot_head': hook.BASE_SHA,
            'source_model_sha': spec.sha256,
            'source_spec_sha': hashlib.sha256(hook.canonical(spec.to_dict())).hexdigest()}


def enable(monkeypatch, tmp_path, *, spec=None, sink=None):
    ns = fake_namespace(spec)
    value = ticket(tmp_path, spec)
    sink = sink or Sink()
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE', '/fixture/arm.json')
    state = hook.install(ns, ticket_loader=lambda path: value, recorder_factory=lambda *a, **k: sink,
                         source_verifier=lambda ns: None)
    assert state is not None
    return ns, state, sink


def frame(ns, fid=17, extra=True):
    camera = ns['CameraGapTrace']()
    main = types.SimpleNamespace(frame_id=fid, timestamp_sof=1_000_000_000 + fid * 50_000_000,
                                 timestamp_eof=1_010_000_000 + fid * 50_000_000)
    second = types.SimpleNamespace(frame_id=fid + 2, timestamp_sof=main.timestamp_sof + 3_000_000,
                                   timestamp_eof=main.timestamp_eof + 3_000_000) if extra else main
    image = np.arange(393216, dtype=np.uint8).reshape(2, 6, 128, 256)
    camera.result = (object(), main, object(), second)
    result = camera.receive(object(), object() if extra else None)
    transforms = {'img': np.arange(9, dtype=np.float32).reshape(3, 3),
                  'big_img': np.eye(3, dtype=np.float32) * 2}
    warped = ns['Warp']()(image, transforms)
    assert result is camera.result and warped is image
    return image, transforms, main, second


def test_off_does_not_touch_methods_or_call_any_factory(monkeypatch):
    monkeypatch.delenv('CARROT_V3_INPUT_CAPTURE', raising=False)
    ns = fake_namespace()
    methods = [ns['Warp'].__call__, ns['Client'].__init__, ns['Client'].infer, ns['CameraGapTrace'].receive]
    def forbidden(*a, **k):
        pytest.fail('OFF performed enabled work')
    assert hook.install(ns, recorder_factory=forbidden, ticket_loader=forbidden, source_verifier=forbidden) is None
    assert methods == [ns['Warp'].__call__, ns['Client'].__init__, ns['Client'].infer, ns['CameraGapTrace'].receive]


def test_capture_is_exact_before_original_infer_and_keeps_borrowed_identity(monkeypatch, tmp_path):
    ns, state, sink = enable(monkeypatch, tmp_path)
    client = ns['Client']()
    image, transforms, main, extra = frame(ns)
    packed = np.arange(28, dtype=np.float32)
    packed[1] = -0.0
    before = packed.copy()
    assert client.infer(image, packed, 12, True, source_sof=main.timestamp_sof) is client
    assert len(client.calls) == 1 and client.calls[0][0] is image and client.calls[0][1] is packed
    recorded = sink.records[0]
    assert recorded[0].tobytes() == image.tobytes()
    for value, expected in zip(recorded[1:4], (before[:8], before[8:10].reshape(1, 2), before[10:12].reshape(1, 2))):
        assert value.tobytes() == expected.tobytes()
    meta = recorded[4]
    assert (meta['main_frame_id'], meta['extra_frame_id'], meta['flags']) == (17, 19, 1)
    assert (meta['model_timestamp_ns'], meta['main_sof_ns'], meta['extra_sof_ns']) == (main.timestamp_sof, main.timestamp_sof, extra.timestamp_sof)
    assert meta['selection'] == (0, 1)
    assert meta['monotonic_ns'] > 0
    assert all(np.array_equal(a, b) for a, b in zip(meta['transforms'], transforms.values()))


def test_no_extra_stream_keeps_main_role_twice(monkeypatch, tmp_path):
    ns, _, sink = enable(monkeypatch, tmp_path)
    client = ns['Client']()
    image, _, _, _ = frame(ns, extra=False)
    client.infer(image, np.zeros(28, np.float32), 1)
    assert sink.records[0][4]['selection'] == (0, 0)


def test_transforms_are_actual_float32_warp_inputs_not_float64_callers(monkeypatch, tmp_path):
    ns, _, sink = enable(monkeypatch, tmp_path)
    client = ns['Client']()
    image, _, _, _ = frame(ns)
    transforms = {'img': np.eye(3, dtype=np.float64) / 3, 'big_img': np.eye(3, dtype=np.float64) / 7}
    warp = ns['Warp']()
    warp(image, transforms)
    client.infer(image, np.zeros(28, np.float32), 1)
    actual = sink.records[0][4]['transforms']
    assert all(a.dtype == np.float32 for a in actual)
    assert actual[0].tobytes() == warp.transforms['tfm'].tobytes()
    assert actual[1].tobytes() == warp.transforms['big_tfm'].tobytes()


def test_existing_infer_exception_is_same_object_and_called_once(monkeypatch, tmp_path):
    ns, _, sink = enable(monkeypatch, tmp_path)
    client = ns['Client']()
    image, _, _, _ = frame(ns)
    client.failure = ValueError('existing failure')
    with pytest.raises(ValueError) as exc:
        client.infer(image, np.zeros(28, np.float32), 1)
    assert exc.value is client.failure and len(client.calls) == 1 and len(sink.records) == 1


@pytest.mark.parametrize('failure', ['missing_pair', 'different_image', 'shape', 'dtype', 'packed', 'identity', 'layout'])
def test_failed_capture_gate_only_stops_recorder_and_keeps_inference(monkeypatch, tmp_path, failure):
    ns, _, sink = enable(monkeypatch, tmp_path)
    client = ns['Client']()
    image, _, _, _ = frame(ns)
    packed = np.zeros(28, np.float32)
    if failure == 'missing_pair':
        camera = ns['CameraGapTrace'](); camera.result = None; camera.receive(object(), None)
    elif failure == 'different_image': image = image.copy()
    elif failure == 'shape': image = image.reshape(-1)
    elif failure == 'dtype': image = image.astype(np.float32)
    elif failure == 'packed': packed = packed.astype(np.float64)
    elif failure == 'identity': client.spec = Spec()
    elif failure == 'layout': client.spec.input_shapes = {'img': (2, 12, 128, 256)}
    assert client.infer(image, packed, 1) is client
    assert len(client.calls) == 1 and not sink.records and sink.stops


def test_observer_exception_is_contained(monkeypatch, tmp_path):
    class Broken(Sink):
        def observe(self, *args): raise OSError('writer failed')
        def stop(self, reason): raise RuntimeError('stop failed too')
    ns, _, sink = enable(monkeypatch, tmp_path, sink=Broken())
    client = ns['Client']()
    image, _, _, _ = frame(ns)
    assert client.infer(image, np.zeros(28, np.float32), 1) is client
    assert len(client.calls) == 1


def test_hot_observer_does_not_hash_scan_json_or_open_files(monkeypatch, tmp_path):
    ns, _, sink = enable(monkeypatch, tmp_path)
    client = ns['Client']()
    image, _, _, _ = frame(ns)
    packed = np.zeros(28, np.float32)
    def forbidden(*args, **kwargs):
        raise AssertionError('forbidden hot-path operation')
    monkeypatch.setattr(hook.hashlib, 'sha256', forbidden)
    monkeypatch.setattr(hook, 'canonical', forbidden)
    monkeypatch.setattr(hook.json, 'loads', forbidden)
    monkeypatch.setattr(hook.os, 'open', forbidden)
    monkeypatch.setattr(Path, 'open', forbidden)
    monkeypatch.setattr(hook.np, 'isfinite', forbidden)
    assert client.infer(image, packed, 1) is client
    assert len(sink.records) == 1 and not sink.stops


@pytest.mark.parametrize('change', ['sha', 'spec', 'stateful', 'scalar_order'])
def test_source_contract_mismatch_does_not_change_client_init(monkeypatch, tmp_path, change):
    ns, _, sink = enable(monkeypatch, tmp_path)
    # Ticket was pinned before the runtime handshake obtains this changed source.
    spec = Spec()
    # Install a fresh namespace retaining a separately pinned original ticket.
    value = ticket(tmp_path)
    if change == 'sha': spec.sha256 = '2' * 64
    elif change == 'spec': spec.frame_skip = 2
    elif change == 'stateful': spec.stateful = True
    else: spec.packed_shapes = {'traffic_convention': (1, 2), 'desire': (8,), 'action_t': (1, 2), 'prev_feat': (1, 16)}
    ns = fake_namespace(spec)
    hook.install(ns, ticket_loader=lambda p: value, recorder_factory=lambda *a, **k: sink, source_verifier=lambda ns: None)
    client = ns['Client']()
    assert client.spec is spec and sink.stops


def test_arm_ticket_consumes_once_and_rejects_boot_expiry_and_onroad(tmp_path):
    spec = Spec()
    path = tmp_path / 'arm.json'
    root = tmp_path / 'captures'; root.mkdir()
    kwargs = dict(output_root=root, source_model_sha=spec.sha256,
                  source_spec_sha=hashlib.sha256(hook.canonical(spec.to_dict())).hexdigest(), offroad=True,
                  boot_id='fixture-boot', monotonic_ns=1_000_000_000, expires_seconds=30)
    with pytest.raises(ValueError): hook.arm_ticket(path, **{**kwargs, 'offroad': False})
    value = hook.arm_ticket(path, **kwargs)
    assert not Path(value['output']).exists()
    assert hook.consume_ticket(path, boot_id='fixture-boot', monotonic_ns=2_000_000_000)['capture_id'] == value['capture_id']
    assert not path.exists()
    with pytest.raises((ValueError, OSError)): hook.consume_ticket(path, boot_id='fixture-boot', monotonic_ns=2_000_000_000)
    for suffix, boot, now in [('boot', 'other', 2_000_000_000), ('expired', 'fixture-boot', 32_000_000_000)]:
        other = tmp_path / (suffix + '.json')
        hook.arm_ticket(other, **kwargs)
        with pytest.raises(ValueError): hook.consume_ticket(other, boot_id=boot, monotonic_ns=now)


def test_ticket_rejects_realdata_and_existing_output_and_symlink(tmp_path):
    root = tmp_path / 'realdata'; root.mkdir()
    with pytest.raises(ValueError):
        hook.arm_ticket(tmp_path / 'arm.json', output_root=root, source_model_sha='1'*64, source_spec_sha='2'*64, offroad=True)
    root = tmp_path / 'captures'; root.mkdir()
    path = tmp_path / 'arm.json'
    hook.arm_ticket(path, output_root=root, source_model_sha='1'*64, source_spec_sha='2'*64, offroad=True,
                    boot_id='fixture', monotonic_ns=1)
    symlink = tmp_path / 'alias.json'; symlink.symlink_to(path)
    with pytest.raises((ValueError, OSError)): hook.consume_ticket(symlink, boot_id='fixture', monotonic_ns=2)
    value = json.loads(path.read_text()); Path(value['output']).mkdir()
    with pytest.raises(ValueError): hook.consume_ticket(path, boot_id='fixture', monotonic_ns=2)


def test_ticket_rejects_duplicate_json_keys_and_cannot_rearm_same_path(tmp_path):
    root = tmp_path / 'captures'; root.mkdir()
    path = tmp_path / 'arm.json'
    kwargs = dict(output_root=root, source_model_sha='1'*64, source_spec_sha='2'*64, offroad=True,
                  boot_id='fixture', monotonic_ns=1)
    hook.arm_ticket(path, **kwargs)
    original = path.read_bytes()
    path.write_bytes(original[:-1] + b',"offroad_armed":true}')
    with pytest.raises(ValueError): hook.consume_ticket(path, boot_id='fixture', monotonic_ns=2)
    assert path.with_name('arm.json.consumed').exists()
    # Even putting a fresh ticket at the old location cannot bypass its retained
    # consumed claim; a distinct explicit offroad action needs a distinct path.
    hook.arm_ticket(path, **kwargs)
    with pytest.raises(FileExistsError): hook.consume_ticket(path, boot_id='fixture', monotonic_ns=2)


def test_invalid_ticket_or_startup_failure_does_not_replace_methods(monkeypatch):
    ns = fake_namespace(); before = ns['Client'].infer
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE', '/invalid.json')
    def broken(path): raise ValueError('invalid ticket')
    assert hook.install(ns, ticket_loader=broken) is None
    assert ns['Client'].infer is before


def test_fifo_ticket_is_rejected_without_blocking_or_replacing_methods(tmp_path):
    fifo = tmp_path / 'arm-fifo'
    os.mkfifo(fifo)
    script = '''
import os, sys
from recording.hook import install
os.environ['CARROT_V3_INPUT_CAPTURE'] = sys.argv[1]
class Client:
    def infer(self): pass
before = Client.infer
assert install({'Client': Client}) is None
assert Client.infer is before
print('rejected')
'''
    result = subprocess.run([sys.executable, '-c', script, str(fifo)], capture_output=True, text=True, timeout=2)
    assert result.returncode == 0 and result.stdout.strip() == 'rejected'


@pytest.mark.parametrize('method', ['receive', 'warp', 'init'])
def test_original_setup_camera_warp_exceptions_keep_identity_and_cancel_only_recorder(monkeypatch, tmp_path, method):
    ns = fake_namespace()
    failure = RuntimeError('original ' + method)
    def fail(*args, **kwargs): raise failure
    if method == 'receive': ns['CameraGapTrace'].receive = fail
    elif method == 'warp': ns['Warp'].__call__ = fail
    else: ns['Client'].__init__ = fail
    sink = Sink(); value = ticket(tmp_path)
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE', '/fixture/arm.json')
    assert hook.install(ns, ticket_loader=lambda p: value, recorder_factory=lambda *a, **k: sink,
                        source_verifier=lambda ns: None) is not None
    with pytest.raises(RuntimeError) as exc:
        if method == 'receive': ns['CameraGapTrace']().receive(None, None)
        elif method == 'warp': ns['Warp']()(None, {})
        else: ns['Client']()
    assert exc.value is failure and sink.stops


def test_real_recorder_hook_reader_copies_bits_and_finishes_without_postcap_cancellation(monkeypatch, tmp_path):
    from recording.dataset import Dataset
    ns = fake_namespace()
    value = ticket(tmp_path); value['frames'] = 2
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE', '/fixture/arm.json')
    state = hook.install(ns, ticket_loader=lambda p: value, source_verifier=lambda ns: None)
    assert state is not None
    rec = state.recorder
    deadline = time.monotonic() + 10
    while not rec.ready and rec.reason is None and time.monotonic() < deadline:
        rec.poll(); time.sleep(.005)
    assert rec.ready
    client = ns['Client']()
    snapshots = []
    try:
        for index in range(2):
            image, _, _, _ = frame(ns, fid=17 + index)
            packed = np.arange(28, dtype=np.float32); packed[0] = -0.0
            snapshots.append((image.tobytes(), packed[:8].tobytes()))
            assert client.infer(image, packed, index, reset=index == 0) is client
        assert rec.count == 2 and state.disabled
        # A later source transition must not retroactively cancel the already
        # completed input sequence while its private writer finishes fsync.
        client.spec = Spec()
        client.infer(image, packed, 3)
    finally:
        rec.close(timeout=10)
    assert rec.reason is None
    with Dataset(value['output']) as dataset:
        assert len(dataset) == 2
        for index, expected in enumerate(snapshots):
            values = dataset.ort_feeds(index)
            assert values['new_img'].tobytes() == expected[0]
            assert values['desire'].tobytes() == expected[1]


def test_actual366_enabled_call_bodies_preserve_ipc_and_capture_exact_inputs(monkeypatch, tmp_path):
    """Run unmodified reviewed methods with fake camera/GPU/IPC boundaries."""
    def source(name):
        return subprocess.check_output(['git', '-C', str(REFERENCE), 'show', 'HEAD:' + name])
    def source_class(name, class_name, globals):
        tree = ast.parse(source(name))
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
        exec(compile(ast.Module(body=[cls], type_ignores=[]), name, 'exec'), globals)
        return globals[class_name]
    spec = Spec()
    spec.output_nelem = 42; spec.output_nbytes = 168
    traffic = []
    class Socket:
        def settimeout(self, timeout): pass
        def connect(self, path): pass
        def close(self): pass
    def send_parts(sock, request, image, packed, **kwargs):
        traffic.append((request, image, packed))
    class PacketReader:
        def __init__(self, size): pass
        def receive(self, sock, deadline):
            fid, flags, sof = struct.unpack('<IIQ', traffic[-1][0])
            return struct.pack('<I3I', fid, 0, 0, 0) + np.arange(42, dtype=np.float32).tobytes()
    globals = dict(np=np, time=time, os=os, json=json, SOCKET='/fixture.sock',
        socket=types.SimpleNamespace(socket=lambda *a: Socket(), AF_UNIX=1, SOCK_STREAM=1),
        receive=lambda *a: json.dumps({'spec': spec.to_dict()}),
        ModelSpec=types.SimpleNamespace(from_dict=lambda value: spec), validate_model_spec=lambda value: value,
        projection=types.SimpleNamespace(eligible=lambda spec: False, COUNT=42, IPC_FLAG=2),
        REQUEST=struct.Struct('<IIQ'), REPLY=struct.Struct('<I3I'), PacketReader=PacketReader, send_parts=send_parts)
    client_cls = source_class('openpilot/selfdrive/modeld/jetlink/link.py', 'Client', globals)
    warp_cls = source_class('openpilot/selfdrive/modeld/jetlink/model.py', 'Warp', {'np': np, 'time': time})
    sync_globals = {}; exec(compile(source('openpilot/selfdrive/modeld/camera_sync.py'), 'camera_sync.py', 'exec'), sync_globals)
    camera_cls = source_class('openpilot/selfdrive/modeld/camera_gap.py', 'CameraGapTrace',
                              {'time': time, 'receive_camera_pair': sync_globals['receive_camera_pair']})
    ns = {'Client': client_cls, 'Warp': warp_cls, 'CameraGapTrace': camera_cls}
    sink = Sink(); value = ticket(tmp_path, spec)
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE', '/fixture/arm.json')
    assert hook.install(ns, ticket_loader=lambda p: value, recorder_factory=lambda *a, **k: sink,
                        source_verifier=lambda ns: None) is not None
    tinygrad = types.ModuleType('tinygrad')
    tinygrad.Tensor = types.SimpleNamespace(from_blob=lambda *a, **k: object())
    monkeypatch.setitem(sys.modules, 'tinygrad', tinygrad)
    class Camera:
        frame_id = 101
        timestamp_sof = 2_000_000_000
        timestamp_eof = 2_010_000_000
        def recv(self): return types.SimpleNamespace(data=bytes(16))
    main = Camera(); extra = Camera(); extra.frame_id = 103; extra.timestamp_sof += 2_000_000
    pair = camera_cls(lambda *a, **k: None).receive(main, extra)
    image = np.arange(393216, dtype=np.uint8).reshape(2, 6, 128, 256)
    warp = object.__new__(warp_cls)
    warp.size = 16; warp.blobs = {}; warp.inputs = {}
    warp.transforms = {'tfm': np.eye(3, dtype=np.float32), 'big_tfm': np.eye(3, dtype=np.float32)}
    warp.run_warp = lambda **kwargs: types.SimpleNamespace(numpy=lambda: image)
    transforms = {'img': np.eye(3, dtype=np.float64) / 3, 'big_img': np.eye(3, dtype=np.float64) / 7}
    warped = warp({'img': pair[0], 'big_img': pair[2]}, transforms, prepare=lambda: None)
    packed = np.arange(28, dtype=np.float32); packed[0] = -0.0
    output = client_cls().infer(warped, packed, 7, True, source_sof=main.timestamp_sof)
    assert np.array_equal(output, np.arange(42, dtype=np.float32))
    assert len(traffic) == 1 and traffic[0][1] is image and traffic[0][2] is packed
    assert sink.records[0][1].tobytes() == packed[:8].tobytes()
    assert sink.records[0][4]['main_frame_id'] == 101 and sink.records[0][4]['extra_frame_id'] == 103


def test_actual366_candidate_preserves_all_original_code_and_reverse_applies(tmp_path, monkeypatch):
    from adapters.carrot.recorder import build_recorder_candidate, MODEL, FOOTER
    destination = tmp_path / 'candidate'
    manifest = build_recorder_candidate(REFERENCE, destination)
    original = subprocess.check_output(['git', '-C', str(REFERENCE), 'show', 'HEAD:' + MODEL])
    after = (destination / MODEL).read_bytes()
    assert after == original + FOOTER.encode()
    # A disposable copy intentionally has no Git metadata. Inject only the
    # read-only HEAD lookup while exercising real startup source-file hashing.
    with monkeypatch.context() as source_check:
        source_check.setattr(hook.subprocess, 'check_output', lambda *a, **k: (hook.BASE_SHA + '\n').encode())
        assert hook._verify_source({'__file__': str(destination / MODEL)}) is None
        camera_source = destination / 'openpilot/selfdrive/modeld/camera_sync.py'
        camera_bytes = camera_source.read_bytes()
        camera_source.write_bytes(camera_bytes + b'\n')
        with pytest.raises(ValueError, match='source hash changed'):
            hook._verify_source({'__file__': str(destination / MODEL)})
        camera_source.write_bytes(camera_bytes)
    original_ast = ast.parse(original)
    after_ast = ast.parse(after)
    assert ast.dump(ast.Module(body=after_ast.body[:-1], type_ignores=[])) == ast.dump(original_ast)
    def functions(raw):
        return {value.co_name: marshal.dumps(value) for value in compile(raw, 'same.py', 'exec').co_consts if isinstance(value, types.CodeType)}
    assert functions(original) == functions(after)
    monkeypatch.delenv('CARROT_V3_INPUT_CAPTURE', raising=False)
    # Execute the actual appended footer with an importer that rejects *every*
    # import: OFF must not even import the recording package.
    exec(compile(ast.Module(body=after_ast.body[-1:], type_ignores=[]), 'footer.py', 'exec'),
         {'os': os, '__builtins__': {'__import__': lambda *a, **k: pytest.fail('OFF import')}})
    patch = destination / '.jetlink-recorder/candidate.patch'
    subprocess.run(['git', 'apply', '--reverse', '--check', str(patch)], cwd=destination, check=True)
    subprocess.run(['git', 'apply', '--reverse', str(patch)], cwd=destination, check=True)
    assert (destination / MODEL).read_bytes() == original
    subprocess.run(['git', 'apply', '--check', str(patch)], cwd=destination, check=True)
    subprocess.run(['git', 'apply', str(patch)], cwd=destination, check=True)
    for entry in manifest['touched_files']:
        assert hashlib.sha256((destination / entry['path']).read_bytes()).hexdigest() == entry['after_sha256']
    assert manifest['installation'] == 'DO_NOT_INSTALL'
