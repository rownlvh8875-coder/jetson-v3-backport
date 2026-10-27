"""Literal receipt contract tests are not producer authentication."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.openat2_payload_gate import OneShotReplyReceiver, ReceiptError, build_receiver


def literal():
    return {'schema': 3, 'profile': 'OPENAT2_ENDPOINT_CAPABILITY_V1',
        'status': 'ENDPOINT_CHECKS_PASS', 'reason_code': 'NONE',
        'failure_phase': 'COMPLETE', 'errno_code': 'NONE',
        'evidence_kind': 'NATIVE_LOCAL_PROCFS', 'inspect_attempts': 1,
        'endpoint_checks_pass': True, 'lease_closed': True, 'processes_created': 0,
        'journal_created': False, 'sampling_window_started': False, 'ticket_created': False,
        'device_validation': False, 'policy_acceptance': False,
        'negative_pid_witness_allowed': False, 'lifetime_acceptance': False,
        'temporal_visibility_proven': False, 'namespace_equality_proven': False,
        'full_host_visibility_proven': False, 'runtime_scope_confirmed': False,
        'full_ProcView_interface': False, 'legacy_fallback_allowed': False,
        'optimization_mode': 'DISABLED', 'bytecode_mode': 'SUPPRESSED',
        'isolation_mode': 'ISOLATED', 'source_bundle_sha256': 'b' * 64,
        'challenge': 'c' * 64}


def wire(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode() + b'\n'


def receiver():
    return OneShotReplyReceiver(expected_payload_sha='a' * 64, bundle_sha='b' * 64, challenge='c' * 64)


def test_exact_literal_contract_acceptance_has_no_authority_or_authentication():
    r = receiver()
    value = r.accept(wire(literal()), executed_sha='a' * 64)
    assert value == literal() and value['policy_acceptance'] is False
    with pytest.raises(ReceiptError, match='RECEIVER_USED'):
        r.accept(wire(literal()), executed_sha='a' * 64)


@pytest.mark.parametrize('field', ['journal_created', 'sampling_window_started', 'ticket_created',
    'device_validation', 'policy_acceptance', 'negative_pid_witness_allowed',
    'lifetime_acceptance', 'temporal_visibility_proven', 'namespace_equality_proven',
    'full_host_visibility_proven', 'runtime_scope_confirmed', 'full_ProcView_interface',
    'legacy_fallback_allowed'])
def test_no_true_authority_or_activity_flag_can_be_received(field):
    value = literal()
    value[field] = True
    with pytest.raises(ReceiptError):
        receiver().accept(wire(value), executed_sha='a' * 64)


@pytest.mark.parametrize('change', [
    {'schema': 2}, {'schema': True}, {'profile': 'OLD'}, {'status': 'OTHER'},
    {'source_bundle_sha256': 'd' * 64}, {'challenge': 'd' * 64},
    {'evidence_kind': 'INJECTED_FIXTURE'}, {'inspect_attempts': True},
    {'inspect_attempts': 2}, {'processes_created': 1}, {'processes_created': False},
    {'endpoint_checks_pass': 1}, {'lease_closed': False}, {'reason_code': 'READ_LIMIT'},
    {'errno_code': 'EXDEV'}, {'failure_phase': 'INSPECT'},
    {'optimization_mode': 'ENABLED'}, {'bytecode_mode': 'ENABLED'}, {'isolation_mode': 'NOT_ISOLATED'},
    {'extra': 'PRIVATE'},
])
def test_shape_source_runtime_and_relationship_tamper_rejected(change):
    with pytest.raises(ReceiptError):
        receiver().accept(wire({**literal(), **change}), executed_sha='a' * 64)


@pytest.mark.parametrize('raw', [b'', b'{}\n', b'x' * 8193, b'\xff\n',
    b'{"schema":3,"schema":3}\n', b'{"schema":NaN}\n'])
def test_invalid_raw_frame_seals_without_retry(raw):
    r = receiver()
    with pytest.raises(ReceiptError):
        r.accept(raw, executed_sha='a' * 64)
    with pytest.raises(ReceiptError, match='RECEIVER_USED'):
        r.accept(wire(literal()), executed_sha='a' * 64)


@pytest.mark.parametrize('transform', [lambda b: b[:-1], lambda b: b + b'\n',
    lambda b: b + b, lambda b: b.replace(b':', b': ', 1), lambda b: b'\xef\xbb\xbf' + b])
def test_noncanonical_multiple_or_truncated_frames_rejected(transform):
    with pytest.raises(ReceiptError):
        receiver().accept(transform(wire(literal())), executed_sha='a' * 64)


def test_unchecked_executed_digest_is_not_assumed_from_reply():
    with pytest.raises(ReceiptError, match='EXECUTION_PIN'):
        receiver().accept(wire(literal()), executed_sha='d' * 64)


@pytest.mark.parametrize('status,reason,phase,number,modes', [
    ('BLOCKED_NATIVE_CAPABILITY', 'NATIVE_OS_ERROR', 'INSPECT', 'ENOSYS', {}),
    ('BLOCKED_NATIVE_CAPABILITY', 'UNSUPPORTED_ABI', 'INSPECT', 'NONE', {}),
    ('BLOCKED_ENDPOINT_SCOPE', 'CLEANUP_FAILED', 'INSPECT', 'NONE', {}),
    ('BLOCKED_ENDPOINT_SCOPE', 'UNREVIEWED_SUBMOUNT', 'INSPECT', 'NONE', {}),
    ('BLOCKED_PAYLOAD_IDENTITY', 'PAYLOAD_IDENTITY', 'PAYLOAD', 'NONE', {}),
    ('BLOCKED_PAYLOAD_EXECUTION', 'PAYLOAD_EXECUTION', 'PAYLOAD', 'NONE', {}),
    ('BLOCKED_RUNTIME_FLAGS', 'OPTIMIZED_INTERPRETER', 'RUNTIME', 'NONE', {'optimization_mode': 'ENABLED'}),
    ('BLOCKED_RUNTIME_FLAGS', 'BYTECODE_ENABLED', 'RUNTIME', 'NONE', {'bytecode_mode': 'ENABLED'}),
    ('BLOCKED_RUNTIME_FLAGS', 'ISOLATION_REQUIRED', 'RUNTIME', 'NONE', {'isolation_mode': 'NOT_ISOLATED'}),
])
def test_valid_blocked_receipts_are_retained_as_failure_only(status, reason, phase, number, modes):
    value = {**literal(), **modes, 'status': status, 'reason_code': reason,
        'failure_phase': phase, 'errno_code': number, 'endpoint_checks_pass': False, 'lease_closed': False}
    if phase != 'INSPECT':
        value.update(inspect_attempts=0, evidence_kind='NO_ACQUISITION')
    received = receiver().accept(wire(value), executed_sha='a' * 64)
    assert received == value and received['endpoint_checks_pass'] is False


def script():
    source = (Path(__file__).resolve().parents[1] / 'tools/openat2_payload_gate.py').read_bytes()
    return build_receiver(source, hashlib.sha256(source).hexdigest(),
                          expected_payload_sha='a' * 64, bundle_sha='b' * 64, challenge='c' * 64)


def invoke(text, raw, flags=('-I', '-B')):
    return subprocess.run([sys.executable, *flags, '-c', text], input=raw,
                          capture_output=True, timeout=8)


def test_standalone_receiver_only_echoes_exact_validated_bytes():
    raw = wire(literal())
    out = invoke(script()['script'], raw)
    assert out.returncode == 0 and out.stdout == raw and out.stderr == b''


@pytest.mark.parametrize('flags', [('-O', '-I', '-B'), ('-OO', '-I', '-B'), ('-I',), ('-B',)])
def test_receiver_runtime_guards(flags):
    out = invoke(script()['script'], wire(literal()), flags)
    assert out.returncode == 78 and out.stdout == b''
    assert out.stderr.startswith(b'OPENAT2_REPLY_GATE:RUNTIME_')


def test_standalone_receiver_source_pin_and_frame_limits():
    release = script()
    altered = release['script'].replace(release['source_sha256'], '0' * 64, 1)
    bad = invoke(altered, wire(literal()))
    assert bad.returncode == 78 and bad.stdout == b''
    assert bad.stderr == b'OPENAT2_REPLY_GATE:RECEIVER_SOURCE\n'
    large = invoke(release['script'], b'x' * 8193)
    assert large.returncode == 78 and large.stdout == b''
