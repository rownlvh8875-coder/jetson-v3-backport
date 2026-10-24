"""Paired exact33-pinned offline local/remote/map/capture regression fixture.

No device, socket, memfd, ticket, runtime process, model, ORT or GPU is used.
"""
from __future__ import annotations

import ast
import builtins
import copy
import dataclasses
import functools
import hashlib
import json
import math
import struct
import sys
import types

import numpy as np

from adapters.carrot import recorder_5bb as recorder
from recorder_810e_support import REFERENCE

SHA = recorder.BASE_SHA
# Verify every exact33 pin before compiling or executing any source object.
RAW = recorder.sources(REFERENCE)
assert len(RAW) == len(recorder.SOURCE_PINS) == 33
assert set(RAW) == set(recorder.SOURCE_PINS)
assert all(hashlib.sha256(raw).hexdigest() == recorder.SOURCE_PINS[name]
           for name, raw in RAW.items())
HOOK = recorder.recorder_files(REFERENCE)[recorder.PACKAGE + '/hook.py']


def source(path):
    raw = RAW[path]
    assert hashlib.sha256(raw).hexdigest() == recorder.SOURCE_PINS[path]
    return raw


def load_nodes(nodes, ns):
    module = ast.fix_missing_locations(ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *copy.deepcopy(nodes)], type_ignores=[]))
    exec(compile(module, '<exact5bb-private-paired-source>', 'exec', dont_inherit=True), ns)


def pick(raw, kind, name, owner=None):
    tree = ast.parse(raw)
    scope = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == owner).body if owner else tree.body
    return next(n for n in scope if isinstance(n, kind) and n.name == name)


def fn(raw, name, ns, owner=None):
    load_nodes([pick(raw, ast.FunctionDef, name, owner)], ns)
    return ns[name]


def digest(value):
    return hashlib.sha256(memoryview(value).cast('B')).hexdigest()


P = types.ModuleType('_c04pair_protocol')
exec(compile(source('third_party/jetlink/jetlink/protocol.py'), '<exact5bb-protocol>', 'exec'), P.__dict__)
projection = types.ModuleType('_c04pair_projection')
exec(compile(source('third_party/jetlink/jetlink/output_projection.py'), '<exact5bb-output-projection>', 'exec'), projection.__dict__)
codec = types.ModuleType('_c04pair_codec')
exec(compile(source('third_party/jetlink/jetlink/packed_codec.py'), '<exact5bb-packed-codec>', 'exec'), codec.__dict__)
model_module = types.ModuleType('_c04pair_spec')
sys.modules[model_module.__name__] = model_module
model_module.__dict__.update(math=math, hashlib=hashlib, dataclass=dataclasses.dataclass)
spec_tree = ast.parse(source('third_party/jetlink/jetlink/spec.py'))
load_nodes([n for n in spec_tree.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in
    ('MODEL_RUN_FREQ', 'MODEL_CONTEXT_FREQ', 'DEFAULT_FRAME_SKIP', 'STATEFUL_FRAME') for t in n.targets)], model_module.__dict__)
load_nodes([pick(source('third_party/jetlink/jetlink/spec.py'), ast.ClassDef, 'ModelSpec')], model_module.__dict__)
SPEC = model_module.ModelSpec.from_dict(json.loads(source('openpilot/selfdrive/modeld/jetlink/jetson_model.json')))
assert projection.eligible(SPEC)
errors = {}
base_raw = source('third_party/jetlink/jetlink/transport/base.py')
load_nodes([pick(base_raw, ast.ClassDef, 'LinkError'), pick(base_raw, ast.ClassDef, 'LinkTimeout')], errors)
LinkError, LinkTimeout = errors['LinkError'], errors['LinkTimeout']
LOCAL = source('openpilot/selfdrive/modeld/jetlink/link.py')
REMOTE = source('third_party/jetlink/jetlink/client.py')
SHARED = source('openpilot/selfdrive/modeld/jetlink/shared_input.py')
REQUEST, REPLY = struct.Struct('<IIQ'), struct.Struct('<I3I')


def run(scenario, wrapped):
    clock = [1_000_000_000]
    fake_time = types.SimpleNamespace(monotonic=lambda: clock[0] / 1e9, monotonic_ns=lambda: clock[0])
    events, steps = [], []
    dm = types.ModuleType('_c04pair_deferred')
    def offline_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == 'time':
            return fake_time
        if name == 'jetlink':
            return types.SimpleNamespace(output_projection=projection, packed_codec=codec)
        if name == 'jetlink.deferred_map':
            return dm
        if name == 'jetlink.packed_codec':
            return codec
        return builtins.__import__(name, globals, locals, fromlist, level)
    private_builtins = dict(vars(builtins), __import__=offline_import)
    dm.__dict__['__builtins__'] = private_builtins
    exec(compile(source('third_party/jetlink/jetlink/deferred_map.py'), '<exact5bb-deferred-map>', 'exec'), dm.__dict__)
    receiver = dm.Receiver()
    ns = {'np': np, 'time': fake_time, 'P': P, 'projection': projection,
          'LinkError': LinkError, 'LinkTimeout': LinkTimeout, '__builtins__': private_builtins}
    fn(REMOTE, '_as_bytes', ns)
    ns['_name'] = fn(REMOTE, '_name', ns)
    begin = fn(REMOTE, 'infer_begin', ns, 'JetlinkClient')
    end = fn(REMOTE, 'infer_end', ns, 'JetlinkClient')
    flush = fn(REMOTE, 'flush_map', ns, 'JetlinkClient')
    state = {'frame': 0, 'fault': None, 'local_reply': None, 'response': None, 'clear_receiver': False}
    sequence = [0]
    def next_seq():
        sequence[0] += 1
        return sequence[0]
    remote = types.SimpleNamespace(spec=SPEC, dead=False, _protocol_version=lambda: 2, _stateful_v2=True,
        project_output=False, deferred_map_available=True, _nav_u8=True, _lz4=False,
        map_sender=None, _next_seq=next_seq, deadline=.15, last_state=None)

    def transport_send(message, seq, parts, timeout):
        joined = b''.join(bytes(memoryview(p).cast('B')) for p in parts)
        if message == P.Msg.INFER_REQ:
            frame, flags = P.unpack_infer_req(joined)
            image = joined[P.INFER_REQ_SIZE:P.INFER_REQ_SIZE + SPEC.warped_nbytes]
            packed = joined[P.INFER_REQ_SIZE + SPEC.warped_nbytes:]
            events.append({'event': 'infer_req', 'seq': seq, 'frame': frame, 'flags': flags,
                           'wire_sha256': digest(joined), 'bytes': len(joined), 'image_sha256': digest(image)})
            if state['fault'] == 'remote_infer':
                raise LinkError('private infer transport fault')
            if state['clear_receiver']:
                receiver.clear()
            try:
                if flags & dm.FLAG:
                    packed = receiver.expand(packed, SPEC)
                else:
                    receiver.clear()
                logical = codec.decode(packed, SPEC) if flags & codec.FLAG else packed
                context = np.frombuffer(logical, np.float32)
                events.append({'event': 'host_input', 'image_sha256': digest(image), 'first12_sha256': digest(context[:12]),
                               'map_sha256': digest(context[12:-47]), 'navigation_sha256': digest(context[-47:])})
                status = P.Status.OK
            except ValueError as exc:
                events.append({'event': 'host_reject', 'error': str(exc)})
                status = P.Status.BAD_SHAPE
                receiver.clear()
            output = np.full(SPEC.output_nelem, frame, dtype=np.float32)
            state['response'] = types.SimpleNamespace(payload=memoryview(P.pack_infer_resp(frame, status, 1, 2, 3) + output.tobytes()), flags=0)
        elif message == dm.MESSAGE:
            events.append({'event': 'map_update', 'seq': seq, 'wire_sha256': digest(joined), 'bytes': len(joined)})
            if state['fault'] == 'remote_stage':
                raise LinkError('private map transport fault')
            receiver.accept(seq, joined)
        else:
            raise AssertionError(message)

    def expect(message, seq, remaining):
        events.append({'event': 'infer_end', 'seq': seq})
        return state['response']
    remote.t = types.SimpleNamespace(send=transport_send, last_receive=None)
    remote._expect = expect
    remote.infer_begin, remote.infer_end, remote.flush_map = types.MethodType(begin, remote), types.MethodType(end, remote), types.MethodType(flush, remote)

    shared_ns = {'np': np, 'struct': struct, 'time': fake_time}
    for n in ast.parse(SHARED).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('TOKEN', 'MAGIC') for t in n.targets):
            load_nodes([n], shared_ns)
    load_nodes([pick(SHARED, ast.ClassDef, 'Mapping'), pick(SHARED, ast.ClassDef, 'Reader'), pick(SHARED, ast.ClassDef, 'Writer')], shared_ns)
    class FakeMapping(bytearray):
        def close(self):
            events.append({'event': 'shared_mapping_close'})
    shared, shared_reader = None, None
    if scenario.get('shared'):
        mapping = FakeMapping(SPEC.warped_nbytes + SPEC.packed_nbytes)
        shared = shared_ns['Writer'](mapping, SPEC, b'1' * 16)
        shared.busy = False
        shared_reader = shared_ns['Reader'](mapping, SPEC, b'1' * 16)

    def bridge(sock, *parts, deadline):
        events.append({'event': 'local_send', 'parts': len(parts)})
        if state['fault'] == 'local_send':
            raise ConnectionError('private local IPC send fault')
        if shared is not None:
            frame, flags, sof, images, packed = shared_reader.read(parts[0])
            meta_bytes = parts[1] if len(parts) == 2 else None
        else:
            frame, flags, sof = REQUEST.unpack(parts[0])
            images, packed = parts[1:3]
            meta_bytes = parts[3] if len(parts) == 4 else None
        meta = dm.META.unpack(meta_bytes) if meta_bytes is not None else None
        events.append({'event': 'ipc_parse', 'frame': frame, 'flags': flags, 'source_sof': sof, 'metadata': meta})
        seq = remote.infer_begin(images, packed, frame, reset=bool(flags & 1), want_state=False, **({'nav_metadata': meta} if meta is not None else {}))
        events.append({'event': 'phase_sent'})
        stage_bytes = remote.flush_map() if meta is not None else 0
        events.append({'event': 'flush_complete', 'bytes': stage_bytes})
        output = remote.infer_end(seq)
        state['local_reply'] = REPLY.pack(frame, *remote.last_timings) + output.tobytes()

    def local_read(sock, deadline):
        events.append({'event': 'local_reply'})
        if state['fault'] == 'local_reply':
            raise ConnectionError('private local IPC reply fault')
        return state['local_reply']
    local_ns = {'np': np, 'time': fake_time, 'projection': projection, 'deferred_map': dm,
                'REQUEST': REQUEST, 'REPLY': REPLY, 'send_parts': bridge}
    infer = fn(LOCAL, 'infer', local_ns, 'Client')
    inner = fn(LOCAL, '_infer', local_ns, 'Client')
    close = fn(LOCAL, 'close', local_ns, 'Client')
    client = types.SimpleNamespace(spec=SPEC, timeout=.15, project_output=False, deferred_nav=True, shared=shared,
        sock=types.SimpleNamespace(settimeout=lambda timeout: events.append({'event': 'local_timeout', 'seconds': timeout}),
                                   close=lambda: events.append({'event': 'local_close'})),
        reader=types.SimpleNamespace(receive=local_read))
    def traced_inner(*args):
        events.append({'event': 'original_local_infer'})
        return inner(client, *args)
    client._infer, client.close = traced_inner, types.MethodType(close, client)

    capture_ns = {'np': np, 'time': fake_time, 'hashlib': hashlib,
                  'canonical': lambda x: json.dumps(x, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()}
    for n in ast.parse(HOOK).body:
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id in ('SCALARS', 'NAV_MODEL_SHA', 'NAV_SPEC_SHA', 'EXPECTED_STATE_PAIRS') for t in n.targets):
            load_nodes([n], capture_ns)
    load_nodes([pick(HOOK, ast.FunctionDef, '_contract'), pick(HOOK, ast.FunctionDef, '_unchanged'), pick(HOOK, ast.ClassDef, '_Capture')], capture_ns)
    sink = types.SimpleNamespace(count=0, reason=None)
    def observe_sink(*args):
        events.append({'event': 'observer_sink'})
        if scenario.get('sink_failure'):
            raise ValueError('private real capture sink fault')
        sink.count += 1
    def stop_sink(reason):
        events.append({'event': 'observer_stop', 'reason': reason})
        sink.reason = reason
    sink.observe, sink.stop = observe_sink, stop_sink
    ticket = {'source_model_sha': projection.MODEL_SHA256, 'source_spec_sha': projection.SPEC_SHA256, 'frames': 1000}
    capture = capture_ns['_Capture'](sink, ticket)
    client._v3_capture_contract = capture_ns['_contract'](SPEC, ticket)
    def observe(*args):
        events.append({'event': 'observer_enter'})
        return capture.observe(*args)
    proxy = types.SimpleNamespace(observe=observe)
    install = pick(HOOK, ast.FunctionDef, 'install')
    node = next(n for n in ast.walk(install) if isinstance(n, ast.FunctionDef) and n.name == 'infer')
    wrapped_ns = {'functools': functools, 'original_infer': infer, 'capture': proxy}
    load_nodes([node], wrapped_ns)
    callable_infer = wrapped_ns['infer'] if wrapped else infer

    for i, config in enumerate(scenario['steps']):
        clock[0] = config.get('now', 1_000_000_000 + i * 20_000_000)
        state.update(frame=config.get('frame', i + 1), fault=config.get('fault'), clear_receiver=config.get('cache_miss', False))
        if shared is not None:
            events.append({'event': 'shared_begin'})
            image = shared.begin()
            image.fill(i + 10)
        else:
            image = np.full(SPEC.warped_shape, i + 10, dtype=np.uint8)
        packed = np.full(SPEC.packed_nelem, config.get('map', i + 11), dtype=np.float32)
        packed[:12] = np.arange(12, dtype=np.float32) + i
        packed[-47:] = np.arange(47, dtype=np.float32) + i * 10
        if config.get('noncanonical'):
            packed[12] = .5
        if config.get('nan'):
            packed[0] = np.nan
        if config.get('fault') == 'shared_owner':
            image = image.copy()
        if config.get('fault') == 'shared_stale':
            shared_reader.generation = 99
        if config.get('fault') == 'shared_complete':
            def fail_complete():
                events.append({'event': 'shared_complete_fault'})
                raise ConnectionError('private shared complete fault')
            shared.complete = fail_complete
        image_time = config.get('image_time', clock[0] - 20_000_000)
        nav = (config.get('route', 1), image_time, image_time + 500_000_000)
        if config.get('none'):
            nav = None
        elif config.get('invalid'):
            nav = ()
        capture.pair = (types.SimpleNamespace(frame_id=state['frame'], timestamp_sof=clock[0] - 1),
                        types.SimpleNamespace(frame_id=state['frame'], timestamp_sof=clock[0] - 1), (0, 1))
        capture.warped = image
        capture.transforms = (np.eye(3, dtype=np.float32), np.eye(3, dtype=np.float32))
        before = digest(image), digest(packed)
        start = len(events)
        try:
            output = callable_infer(client, image, packed, state['frame'], config.get('reset', i == 0), source_sof=123, nav_metadata=nav)
            outcome = {'return_sha256': digest(output)}
        except Exception as exc:
            outcome = {'error_type': type(exc).__name__, 'error': str(exc)}
        assert before == (digest(image), digest(packed)), 'source arrays mutated'
        sender = remote.map_sender
        pending = sender.pending if sender else None
        sender_state = None if sender is None else {'cached': sender.cached, 'previous_frame': sender.previous_frame, 'used': sender.used,
            'pending': None if pending is None else {'packed_sha256': digest(pending[0]), 'metadata': pending[1], 'encoded': pending[2]}}
        receiver_state = None if receiver.cached is None else {'key': receiver.cached[0], 'route': receiver.cached[1],
            'until': receiver.cached[2], 'pixels_sha256': digest(receiver.cached[3])}
        source_trace = [e for e in events[start:] if not e['event'].startswith('observer_')]
        steps.append({'frame': state['frame'], 'outcome': outcome, 'trace': source_trace, 'sender': sender_state,
            'receiver': receiver_state, 'seq': sequence[0], 'remote_dead': remote.dead,
            'source_image_sha256': before[0], 'source_first12_sha256': digest(packed[:12]), 'source_navigation_sha256': digest(packed[-47:]),
            'source_map_sha256': digest(packed[12:-47]),
            'shared': None if shared is None else {'busy': shared.busy, 'closed': shared.closed,
                'generation': shared.generation, 'reader_generation': shared_reader.generation}})
        if 'error' in outcome:
            break
    return {'steps': steps, 'observer_events': [e for e in events if e['event'].startswith('observer_')],
            'observer_disabled': capture.disabled, 'observer_sink_count': sink.count, 'observer_reason': sink.reason,
            'full_event_order': [e['event'] for e in events]}


BASE = [{}, {}]
SCENARIOS = [
 ('C04PAIR-001', 'inline_then_cache_hit_and_new_stage', {'steps': BASE}),
 ('C04PAIR-002', 'host_cache_miss_bad_shape', {'steps': [{}, {'cache_miss': True}]}),
 ('C04PAIR-003', 'expired_sender_inline', {'steps': [{}, {'now': 1_400_000_000}]}),
 ('C04PAIR-004', 'route_change_inline', {'steps': [{}, {'route': 2}]}),
 ('C04PAIR-005', 'reset_inline', {'steps': [{}, {'reset': True}]}),
 ('C04PAIR-006', 'frame_gap_inline', {'steps': [{}, {'frame': 3}]}),
 ('C04PAIR-007', 'frame_repeat_inline', {'steps': [{}, {'frame': 1}]}),
 ('C04PAIR-008', 'timestamp_rollback_inline', {'steps': [{}, {'image_time': 979_999_999}]}),
 ('C04PAIR-009', 'none_cancels_sender', {'steps': [{}, {'none': True}]}),
 ('C04PAIR-010', 'same_generation_no_stage_or_ttl_refresh', {'steps': [{}, {'image_time': 980_000_000, 'map': 11}]}),
 ('C04PAIR-011', 'first_none_inline_without_stage', {'steps': [{'none': True}]}),
 ('C04PAIR-012', 'first_missing_cache_inline_then_stage', {'steps': [{}]}),
 ('C04PAIR-013', 'invalid_metadata_source_rejection', {'steps': [{'invalid': True}]}),
 ('C04PAIR-014', 'finite_gate_before_metadata', {'steps': [{'invalid': True, 'nan': True}]}),
 ('C04PAIR-015', 'infer_transport_failure_source_close', {'steps': [{'fault': 'remote_infer'}]}),
 ('C04PAIR-016', 'stage_transport_failure_source_close', {'steps': [{'fault': 'remote_stage'}]}),
 ('C04PAIR-017', 'local_reply_failure_source_close', {'steps': [{'fault': 'local_reply'}]}),
 ('C04PAIR-018', 'shared_owner_rejection_source_close', {'shared': True, 'steps': [{'fault': 'shared_owner'}]}),
 ('C04PAIR-019', 'shared_stale_generation_source_close', {'shared': True, 'steps': [{'fault': 'shared_stale'}]}),
 ('C04PAIR-020', 'shared_complete_failure_source_close', {'shared': True, 'steps': [{'fault': 'shared_complete'}]}),
 ('C04PAIR-021', 'real_capture_sink_failure_isolated', {'steps': BASE, 'sink_failure': True}),
 ('C04PAIR-022', 'shared_cache_hit_and_new_stage', {'shared': True, 'steps': BASE}),
 ('C04PAIR-023', 'shared_none_inline', {'shared': True, 'steps': [{}, {'none': True}]}),
 ('C04PAIR-024', 'noncanonical_inline_preserved', {'steps': [{'noncanonical': True}]}),
 ('C04PAIR-025', 'local_send_failure_source_close', {'shared': True, 'steps': [{'fault': 'local_send'}]}),
]


def check_case(case_id, label, scenario):
    plain, wrapped = (run(scenario, False), run(scenario, True))
    assert plain['steps'] == wrapped['steps'], (case_id, 'source trace mismatch')
    assert len([e for e in wrapped['observer_events'] if e['event'] == 'observer_enter']) == len(wrapped['steps'])
    for step in wrapped['steps']:
        trace = step['trace']
        assert len([e for e in trace if e['event'] == 'original_local_infer']) == 1
        for event in trace:
            if event['event'] == 'host_input':
                assert event['image_sha256'] == step['source_image_sha256']
                assert event['first12_sha256'] == step['source_first12_sha256']
                assert event['navigation_sha256'] == step['source_navigation_sha256']
        names = [e['event'] for e in trace]
        if 'map_update' in names:
            assert names.index('infer_req') < names.index('phase_sent') < names.index('map_update')
            if 'infer_end' in names:
                assert names.index('map_update') < names.index('infer_end')
        if 'error' in step['outcome']:
            assert names.count('local_close') == 1
        elif step['shared'] is not None:
            assert not step['shared']['busy'] and (not step['shared']['closed'])
            assert step['shared']['generation'] == step['shared']['reader_generation']
    flags = [e['flags'] for s in wrapped['steps'] for e in s['trace'] if e['event'] == 'infer_req']
    staged = [e['bytes'] for s in wrapped['steps'] for e in s['trace'] if e['event'] == 'flush_complete']
    expected_flags = {'C04PAIR-001': [9, 72], 'C04PAIR-002': [9, 72], 'C04PAIR-003': [9, 8], 'C04PAIR-004': [9, 8], 'C04PAIR-005': [9, 9], 'C04PAIR-006': [9, 8], 'C04PAIR-007': [9, 8], 'C04PAIR-008': [9, 8], 'C04PAIR-009': [9, 8], 'C04PAIR-010': [9, 72], 'C04PAIR-011': [9], 'C04PAIR-012': [9], 'C04PAIR-013': [], 'C04PAIR-014': [], 'C04PAIR-015': [9], 'C04PAIR-016': [9], 'C04PAIR-017': [9], 'C04PAIR-018': [], 'C04PAIR-019': [], 'C04PAIR-020': [9], 'C04PAIR-021': [9, 72], 'C04PAIR-022': [9, 72], 'C04PAIR-023': [9, 8], 'C04PAIR-024': [1], 'C04PAIR-025': []}
    assert flags == expected_flags[case_id], (case_id, flags)
    errors_expected = {'C04PAIR-002': ('LinkError', 'BAD_SHAPE'), 'C04PAIR-013': ('ValueError', 'invalid map metadata'), 'C04PAIR-014': ('ValueError', 'invalid recurrent input'), 'C04PAIR-015': ('LinkError', 'private infer transport fault'), 'C04PAIR-016': ('LinkError', 'map staging failed; link abandoned'), 'C04PAIR-017': ('ConnectionError', 'private local IPC reply fault'), 'C04PAIR-018': ('ValueError', 'shared input does not own this frame'), 'C04PAIR-019': ('ValueError', 'stale or foreign shared input'), 'C04PAIR-020': ('ConnectionError', 'private shared complete fault'), 'C04PAIR-025': ('ConnectionError', 'private local IPC send fault')}
    if case_id in errors_expected:
        error = wrapped['steps'][-1]['outcome']
        error_type, substring = errors_expected[case_id]
        assert error['error_type'] == error_type and substring in error['error']
    else:
        assert all(('error' not in s['outcome'] for s in wrapped['steps']))
    if case_id in ('C04PAIR-001', 'C04PAIR-021', 'C04PAIR-022'):
        assert staged == [65560, 65560] and [s['seq'] for s in wrapped['steps']] == [2, 4]
        second_host = next((e for e in wrapped['steps'][1]['trace'] if e['event'] == 'host_input'))
        assert second_host['map_sha256'] == wrapped['steps'][0]['source_map_sha256']
        assert second_host['map_sha256'] != wrapped['steps'][1]['source_map_sha256']
    if case_id in ('C04PAIR-009', 'C04PAIR-023'):
        assert staged == [65560, 0] and [s['seq'] for s in wrapped['steps']] == [2, 3]
        assert wrapped['steps'][-1]['sender']['cached'] is None and wrapped['steps'][-1]['receiver'] is None
    if case_id == 'C04PAIR-010':
        assert staged == [65560, 0] and [s['seq'] for s in wrapped['steps']] == [2, 3]
        assert wrapped['steps'][0]['sender']['cached'] == wrapped['steps'][1]['sender']['cached']
    if case_id in ('C04PAIR-011', 'C04PAIR-024'):
        assert staged == [0] and wrapped['steps'][0]['sender']['pending'] is None
    order = wrapped['full_event_order']
    assert order.index('observer_enter') < order.index('original_local_infer')
    if scenario.get('sink_failure'):
        assert wrapped['observer_disabled'] and wrapped['observer_reason'] == 'exact input observation failed'
        assert len([e for e in wrapped['observer_events'] if e['event'] == 'observer_sink']) == 1
        assert len([e for e in wrapped['observer_events'] if e['event'] == 'observer_stop']) == 1
        assert all(('error' not in s['outcome'] for s in wrapped['steps']))
        assert order.index('observer_sink') < order.index('observer_stop') < order.index('original_local_infer')
    return {'id': case_id, 'label': label, 'status': 'PASS', 'source_traces_equal': True, 'trace': wrapped['steps'], 'observer_events': wrapped['observer_events'], 'observer_disabled': wrapped['observer_disabled'], 'observer_reason': wrapped['observer_reason'], 'full_event_order': order, 'source_commit': SHA, 'candidate_hook_sha256': digest(HOOK), 'source_pins': {name: digest(raw) for name, raw in sorted(RAW.items())}}
