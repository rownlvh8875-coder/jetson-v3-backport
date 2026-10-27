"""Offline source-bundle fixtures; synthetic source is never native evidence."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import errno

import pytest

from tools import proc_openat2_capability as cap

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('proc_view_scope_model', 'pinned_proc_view', 'proc_openat2_bootstrap',
         'proc_openat2_scope', 'proc_openat2_capability')
GOOD = ('DISABLED', 'SUPPRESSED', 'ISOLATED')


def scope_value():
    return {'kind': 'OPENAT2_ENDPOINT_SCOPE_V1',
            'acquisition_backend': 'INJECTED_OPENAT2_SCOPE_ONLY',
            'endpoint_checks_pass': True, 'lease_closed': True,
            'full_ProcView_interface': False,
            **{k: False for k in ('runtime_scope_confirmed', 'namespace_equality_proven',
                'full_host_visibility_proven', 'temporal_visibility_proven',
                'negative_pid_witness_allowed', 'policy_acceptance',
                'legacy_fallback_allowed', 'lifetime_acceptance')}}


def sources(stub='reject'):
    value = {n: (ROOT / 'tools' / (n + '.py')).read_bytes() for n in NAMES}
    if stub == 'reject':
        value['proc_openat2_scope'] = b'from tools.proc_openat2_bootstrap import BootstrapError\ndef inspect_protected_scope():raise BootstrapError("UNREVIEWED_SUBMOUNT")\n'
    elif stub == 'poison':
        value['proc_openat2_scope'] = b'raise RuntimeError("PRIVATE_MODULE_EXECUTED")\n'
    elif stub == 'success':
        result = scope_value()
        result['acquisition_backend'] = 'NATIVE_OPENAT2_SCOPE_ONLY'
        value['proc_openat2_scope'] = ('def inspect_protected_scope():return ' + repr(result) + '\n').encode()
    return value


def bundle(stub='reject'):
    raw = sources(stub)
    return cap.build_payload(raw, {n: hashlib.sha256(v).hexdigest() for n, v in raw.items()}, challenge='c' * 64)


def invoke(script, flags=('-I', '-B')):
    return subprocess.run([sys.executable, *flags, '-'], input=script.encode(), capture_output=True, timeout=8, check=True)


def test_projection_inspects_once_and_never_promotes_fixture(monkeypatch):
    monkeypatch.setattr(cap, '_modes', lambda: GOOD)
    calls = []
    def inspect_once():
        calls.append(1)
        return scope_value()
    value = cap.probe_endpoint(bundle_sha256='b' * 64, challenge='c' * 64, _inspector=inspect_once)
    assert calls == [1] and value['inspect_attempts'] == 1
    assert value['status'] == 'ENDPOINT_CHECKS_PASS'
    assert value['evidence_kind'] == 'INJECTED_FIXTURE'
    assert value['endpoint_checks_pass'] is True and value['lease_closed'] is True
    assert value['processes_created'] == 0
    assert value['policy_acceptance'] is value['device_validation'] is False


@pytest.mark.parametrize('change', [
    {'kind': 'OTHER'}, {'acquisition_backend': 'NATIVE_OPENAT2_SCOPE_ONLY'},
    {'lease_closed': False}, {'endpoint_checks_pass': 1},
    {'policy_acceptance': True}, {'full_ProcView_interface': True},
    {'temporal_visibility_proven': True}, {'namespace_equality_proven': True},
    {'device_validation': True}, {'ticket_created': True}, {'processes_created': 1},
])
def test_private_result_contract_cannot_be_upgraded(monkeypatch, change):
    monkeypatch.setattr(cap, '_modes', lambda: GOOD)
    value = cap.probe_endpoint(bundle_sha256='b' * 64, challenge='c' * 64,
                               _inspector=lambda: {**scope_value(), **change})
    assert value['status'] == 'BLOCKED_ENDPOINT_SCOPE'
    assert value['reason_code'] == 'RESULT_CONTRACT'
    assert value['endpoint_checks_pass'] is False and value['lease_closed'] is False


@pytest.mark.parametrize('number,code', [(errno.ENOSYS, 'ENOSYS'), (errno.EXDEV, 'EXDEV'),
    (errno.ELOOP, 'ELOOP'), (errno.EAGAIN, 'EAGAIN'), (99999, 'OTHER')])
def test_errno_projection_discards_private_text(monkeypatch, number, code):
    monkeypatch.setattr(cap, '_modes', lambda: GOOD)
    def failed():
        raise OSError(number, 'PRIVATE_PATH_AND_PROCESS')
    value = cap.probe_endpoint(bundle_sha256='b' * 64, challenge='c' * 64, _inspector=failed)
    assert value['status'] == 'BLOCKED_NATIVE_CAPABILITY'
    assert value['reason_code'] == 'NATIVE_OS_ERROR' and value['errno_code'] == code
    assert 'PRIVATE' not in json.dumps(value)


def test_unknown_exception_is_not_stringified(monkeypatch):
    monkeypatch.setattr(cap, '_modes', lambda: GOOD)
    class PrivateError(RuntimeError):
        def __str__(self):
            pytest.fail('private exception stringified')
    def failed():
        raise PrivateError('PRIVATE_ARGV')
    value = cap.probe_endpoint(bundle_sha256='b' * 64, challenge='c' * 64, _inspector=failed)
    assert value['reason_code'] == 'UNKNOWN_EXCEPTION'
    assert 'PRIVATE' not in json.dumps(value)


@pytest.mark.parametrize('stub,status', [('reject', 'BLOCKED_ENDPOINT_SCOPE'),
    ('success', 'ENDPOINT_CHECKS_PASS'), ('poison', 'BLOCKED_PAYLOAD_EXECUTION')])
def test_bundle_runs_only_pinned_in_memory_sources(stub, status):
    release = bundle(stub)
    out = invoke(release['script'])
    value = json.loads(out.stdout)
    assert out.stderr == b'' and value['schema'] == 3 and value['status'] == status
    assert value['source_bundle_sha256'] == release['source_bundle_sha256']
    assert value['challenge'] == 'c' * 64 and b'PRIVATE_MODULE_EXECUTED' not in out.stdout


@pytest.mark.parametrize('flags,reason', [
    (('-O', '-I', '-B'), 'OPTIMIZED_INTERPRETER'),
    (('-OO', '-I', '-B'), 'OPTIMIZED_INTERPRETER'),
    (('-I',), 'BYTECODE_ENABLED'), (('-B',), 'ISOLATION_REQUIRED'),
])
def test_runtime_rejection_precedes_bundled_execution(flags, reason):
    value = json.loads(invoke(bundle('poison')['script'], flags).stdout)
    assert value['status'] == 'BLOCKED_RUNTIME_FLAGS' and value['reason_code'] == reason
    assert value['inspect_attempts'] == 0 and value['evidence_kind'] == 'NO_ACQUISITION'


def test_changed_embedded_source_pin_is_rejected_before_execution():
    release = bundle('poison')
    pin = release['source_pins']['proc_openat2_scope']
    value = json.loads(invoke(release['script'].replace(pin, '0' * 64, 1)).stdout)
    assert value['status'] == 'BLOCKED_PAYLOAD_IDENTITY'
    assert value['inspect_attempts'] == 0


@pytest.mark.parametrize('stub', ['poison', 'success', 'reject'])
def test_aliases_and_startup_bytecode_flag_are_restored(stub):
    release = bundle(stub)
    names = ('tools',) + tuple('tools.' + n for n in NAMES)
    wrapper = '''import sys,types
names=NAMES
for name in names:sys.modules[name]=types.ModuleType(name)
before={n:sys.modules[n] for n in names};mode=sys.dont_write_bytecode
exec(SCRIPT)
if any(sys.modules.get(n) is not v for n,v in before.items()) or sys.dont_write_bytecode!=mode:raise RuntimeError('RESTORE_FAILED')
'''.replace('NAMES', repr(names)).replace('SCRIPT', repr(release['script']))
    assert json.loads(invoke(wrapper).stdout)['schema'] == 3


def test_cleanup_failure_is_fixed_and_dominates_private_primary_diagnostic(monkeypatch):
    monkeypatch.setattr(cap, '_modes', lambda: GOOD)
    def failed():
        error = OSError(errno.EXDEV, 'PRIVATE_PRIMARY')
        error.private_cleanup_errors = [{'path': 'PRIVATE_CLOSE', 'errno': errno.EIO}]
        raise error
    value = cap.probe_endpoint(bundle_sha256='b' * 64, challenge='c' * 64, _inspector=failed)
    assert value['reason_code'] == 'CLEANUP_FAILED' and value['lease_closed'] is False
    assert 'PRIVATE' not in json.dumps(value)


@pytest.mark.parametrize('tampered', [False, True])
def test_exact_source_gate_to_payload_to_native_only_receiver_pipeline(tampered):
    import base64
    import os
    import zlib
    from tools.readonly_payload_gate import build_decoder
    from tools.openat2_payload_gate import OneShotReplyReceiver
    release = bundle('reject')
    script = release['script'] + ('\n# unreviewed change\n' if tampered else '')
    encoded = base64.b64encode(zlib.compress(script.encode())).decode()
    gate = build_decoder(release['sha256'], mode='execute')
    out = subprocess.run([sys.executable, '-I', '-B', '-c', gate], capture_output=True,
                         env={**os.environ, 'M192_AUDIT_SRC': encoded}, timeout=8)
    if tampered:
        assert out.returncode == 78 and out.stdout == b''
        assert out.stderr == b'READONLY_PAYLOAD_GATE:SOURCE_PIN_MISMATCH\n'
    else:
        assert out.returncode == 0 and out.stderr == b''
        receiver = OneShotReplyReceiver(expected_payload_sha=release['sha256'],
            bundle_sha=release['source_bundle_sha256'], challenge=release['challenge'])
        value = receiver.accept(out.stdout, executed_sha=release['sha256'])
        assert value['status'] == 'BLOCKED_ENDPOINT_SCOPE'
        assert value['reason_code'] == 'UNREVIEWED_SUBMOUNT'


@pytest.mark.parametrize('bad', ['missing', 'pin', 'utf8', 'oversize', 'challenge'])
def test_builder_rejects_unreviewed_or_unbounded_input(bad):
    raw = sources()
    pins = {n: hashlib.sha256(v).hexdigest() for n, v in raw.items()}
    challenge = 'c' * 64
    if bad == 'missing':
        raw.pop(NAMES[0])
    elif bad == 'pin':
        pins[NAMES[0]] = '0' * 64
    elif bad == 'utf8':
        raw[NAMES[0]] = b'\xff'
        pins[NAMES[0]] = hashlib.sha256(raw[NAMES[0]]).hexdigest()
    elif bad == 'oversize':
        raw[NAMES[0]] = b'x' * 262145
        pins[NAMES[0]] = hashlib.sha256(raw[NAMES[0]]).hexdigest()
    else:
        challenge = '../private'
    with pytest.raises(ValueError):
        cap.build_payload(raw, pins, challenge=challenge)


@pytest.mark.parametrize('length', [60000, 220000])
def test_bundle_and_whole_payload_respect_existing_source_gate_limits(length):
    # Each source is below262144. The smaller case exceeds the frozen decoder's
    # whole-script limit after embedding; the larger exceeds the bundle budget.
    raw = {name: b'#' + b'x' * length for name in NAMES}
    pins = {name: hashlib.sha256(value).hexdigest() for name, value in raw.items()}
    with pytest.raises(ValueError):
        cap.build_payload(raw, pins, challenge='c' * 64)
