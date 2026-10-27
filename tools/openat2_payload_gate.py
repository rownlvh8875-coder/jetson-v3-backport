"""Independent schema3 one-shot grammar gate, not producer authentication.

Expected IDs/executed SHA are trusted caller inputs from a separately reviewed
release and exact-source transport gate. A valid frame grants no policy rights.
"""
import json

_FALSE = ('journal_created', 'sampling_window_started', 'ticket_created',
    'device_validation', 'policy_acceptance', 'negative_pid_witness_allowed',
    'lifetime_acceptance', 'temporal_visibility_proven', 'namespace_equality_proven',
    'full_host_visibility_proven', 'runtime_scope_confirmed', 'full_ProcView_interface',
    'legacy_fallback_allowed')
_KEYS = frozenset(('schema', 'profile', 'status', 'reason_code', 'failure_phase',
    'errno_code', 'evidence_kind', 'inspect_attempts', 'endpoint_checks_pass',
    'lease_closed', 'processes_created', 'optimization_mode', 'bytecode_mode',
    'isolation_mode', 'source_bundle_sha256', 'challenge') + _FALSE)
_NATIVE = frozenset({'UNSUPPORTED_ABI', 'UNSUPPORTED_NATIVE', 'THREAD_PROFILE'})
_SCOPE = frozenset({'NOT_PROCFS', 'OWNER_MAPPING', 'FD_OWNERSHIP', 'FD_KIND', 'FD_FLAGS',
    'PROC_DEVICE', 'OWNER_CHANGED', 'FD_IDENTITY_CHANGED', 'OPEN_LIMIT', 'READ_CALL_LIMIT',
    'READ_LIMIT', 'OWNER_STATUS', 'FDINFO_FIELDS', 'FDINFO_POSITION', 'FDINFO_FLAGS',
    'FDINFO_INODE', 'MOUNT_ID_CHANGED', 'NAMED_ROOT_CHANGED', 'OWNER_GENERATION_CHANGED',
    'OWNER_STATUS_CHANGED', 'NAMESPACE_ENDPOINT_CHANGED', 'MOUNT_ENDPOINT_CHANGED',
    'BOOT_ENDPOINT_CHANGED', 'CLEANUP_FAILED', 'UNREVIEWED_SUBMOUNT', 'VISIBILITY',
    'MOUNT_IDENTITY', 'MOUNT_NOT_CURRENT', 'AMBIGUOUS_MOUNT', 'MOUNTINFO', 'FDINFO',
    'STAT_LAYOUT', 'READLINK_LIMIT', 'UNSUPPORTED_OPEN_HOW', 'RESULT_CONTRACT',
    'UNKNOWN_SCOPE', 'VALUE_ERROR', 'UNKNOWN_EXCEPTION'})
_ERRNOS = frozenset({'NONE', 'OTHER', 'ENOENT', 'EACCES', 'EPERM', 'ENOSYS', 'EINVAL',
    'EXDEV', 'EAGAIN', 'ELOOP', 'EIO', 'EBADF', 'EINTR', 'EOPNOTSUPP', 'ERANGE', 'EOVERFLOW'})


class ReceiptError(ValueError):
    pass


def _need(condition, reason):
    if not condition:
        raise ReceiptError(reason)


def _hex(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _pairs(items):
    value = {}
    for key, item in items:
        _need(key not in value, 'DUPLICATE_KEY')
        value[key] = item
    return value


def _constant(_value):
    raise ReceiptError('JSON_CONSTANT')


class OneShotReplyReceiver:
    """Single attempted accept seals this context, including malformed input.

    No persistence/global replay guarantee or proof of an honest peer. Fixtures
    can satisfy a grammar; the caller must establish exact-source execution.
    """
    def __init__(self, *, expected_payload_sha, bundle_sha, challenge):
        _need(all(_hex(v) for v in (expected_payload_sha, bundle_sha, challenge)), 'RELEASE_ID')
        self._payload, self._bundle, self._challenge = expected_payload_sha, bundle_sha, challenge
        self._used = False

    def accept(self, raw, *, executed_sha):
        _need(not self._used, 'RECEIVER_USED')
        self._used = True
        _need(_hex(executed_sha) and executed_sha == self._payload, 'EXECUTION_PIN')
        _need(type(raw) is bytes and 0 < len(raw) <= 8192, 'FRAME_SIZE')
        try:
            value = json.loads(raw.decode('ascii', 'strict'), object_pairs_hook=_pairs,
                               parse_constant=_constant)
        except ReceiptError:
            raise
        except (ValueError, UnicodeError, RecursionError):
            raise ReceiptError('FRAME_JSON') from None
        _need(type(value) is dict and set(value) == _KEYS, 'FRAME_KEYS')
        _need(type(value['schema']) is int and value['schema'] == 3 and
              value['profile'] == 'OPENAT2_ENDPOINT_CAPABILITY_V1', 'FRAME_PROFILE')
        _need(value['source_bundle_sha256'] == self._bundle and
              value['challenge'] == self._challenge, 'FRAME_CONTEXT')
        _need(type(value['processes_created']) is int and value['processes_created'] == 0,
              'FRAME_ACTIVITY')
        _need(all(value[k] is False for k in _FALSE), 'FRAME_AUTHORITY')
        _need(type(value['inspect_attempts']) is int and value['inspect_attempts'] in (0, 1) and
              type(value['endpoint_checks_pass']) is bool and type(value['lease_closed']) is bool,
              'FRAME_COUNTS')
        for key, options in (
            ('status', {'ENDPOINT_CHECKS_PASS', 'BLOCKED_NATIVE_CAPABILITY', 'BLOCKED_ENDPOINT_SCOPE',
                        'BLOCKED_RUNTIME_FLAGS', 'BLOCKED_PAYLOAD_IDENTITY', 'BLOCKED_PAYLOAD_EXECUTION'}),
            ('failure_phase', {'COMPLETE', 'INSPECT', 'RUNTIME', 'PAYLOAD'}),
            ('evidence_kind', {'NATIVE_LOCAL_PROCFS', 'NO_ACQUISITION'}),
            ('errno_code', _ERRNOS), ('optimization_mode', {'DISABLED', 'ENABLED'}),
            ('bytecode_mode', {'SUPPRESSED', 'ENABLED'}),
            ('isolation_mode', {'ISOLATED', 'NOT_ISOLATED'})):
            _need(type(value[key]) is str and value[key] in options, 'FRAME_ENUM')
        _need(type(value['reason_code']) is str, 'FRAME_REASON')
        good_modes = (value['optimization_mode'] == 'DISABLED' and
                      value['bytecode_mode'] == 'SUPPRESSED' and value['isolation_mode'] == 'ISOLATED')
        status, reason, phase, number = (value[k] for k in ('status', 'reason_code', 'failure_phase', 'errno_code'))
        attempted, passed = value['inspect_attempts'], status == 'ENDPOINT_CHECKS_PASS'
        _need(value['endpoint_checks_pass'] is passed and value['lease_closed'] is passed, 'FRAME_RELATION')
        if status == 'BLOCKED_RUNTIME_FLAGS':
            expected = ('OPTIMIZED_INTERPRETER' if value['optimization_mode'] == 'ENABLED' else
                        'BYTECODE_ENABLED' if value['bytecode_mode'] == 'ENABLED' else
                        'ISOLATION_REQUIRED' if value['isolation_mode'] == 'NOT_ISOLATED' else None)
            _need(expected is not None and reason == expected and phase == 'RUNTIME' and
                  number == 'NONE' and attempted == 0 and value['evidence_kind'] == 'NO_ACQUISITION',
                  'FRAME_RUNTIME')
        elif status in {'BLOCKED_PAYLOAD_IDENTITY', 'BLOCKED_PAYLOAD_EXECUTION'}:
            expected = 'PAYLOAD_IDENTITY' if status == 'BLOCKED_PAYLOAD_IDENTITY' else 'PAYLOAD_EXECUTION'
            _need(good_modes and reason == expected and phase == 'PAYLOAD' and number == 'NONE' and
                  attempted == 0 and value['evidence_kind'] == 'NO_ACQUISITION', 'FRAME_PAYLOAD')
        else:
            _need(good_modes and attempted == 1 and value['evidence_kind'] == 'NATIVE_LOCAL_PROCFS',
                  'FRAME_INSPECT')
            if passed:
                _need(reason == number == 'NONE' and phase == 'COMPLETE', 'FRAME_SUCCESS')
            elif status == 'BLOCKED_NATIVE_CAPABILITY':
                _need(phase == 'INSPECT' and ((reason == 'NATIVE_OS_ERROR' and number != 'NONE') or
                      (reason in _NATIVE and number == 'NONE')), 'FRAME_NATIVE')
            else:
                _need(phase == 'INSPECT' and reason in _SCOPE and number == 'NONE', 'FRAME_SCOPE')
        canonical = json.dumps(value, sort_keys=True, separators=(',', ':'),
                               ensure_ascii=True, allow_nan=False).encode('ascii') + b'\n'
        _need(raw == canonical, 'FRAME_CANONICAL')
        return value


def build_receiver(source, source_sha, *, expected_payload_sha, bundle_sha, challenge):
    """Build only; source SHA and expected execution IDs are independently trusted."""
    import base64
    import hashlib
    OneShotReplyReceiver(expected_payload_sha=expected_payload_sha, bundle_sha=bundle_sha, challenge=challenge)
    if (type(source) is not bytes or not 0 < len(source) <= 262144 or not _hex(source_sha) or
        hashlib.sha256(source).hexdigest() != source_sha):
        raise ValueError('RECEIVER_SOURCE_PIN')
    try:
        source.decode('utf-8', 'strict')
    except UnicodeError:
        raise ValueError('RECEIVER_ENCODING') from None
    template = '''import sys

def _fail(code):
    sys.stderr.write("OPENAT2_REPLY_GATE:"+code+"\\n")
    raise SystemExit(78)

if sys.flags.optimize!=0:_fail("RUNTIME_OPTIMIZED")
if not sys.dont_write_bytecode:_fail("RUNTIME_BYTECODE")
if sys.flags.isolated!=1:_fail("RUNTIME_ISOLATION")
import base64,hashlib
try:
    raw=base64.b64decode(@@SOURCE@@,validate=True)
    if not raw or len(raw)>262144 or hashlib.sha256(raw).hexdigest()!=@@SHA@@:raise ValueError()
    namespace={"__name__":"pinned_openat2_receiver"}
    exec(compile(raw,"<pinned:openat2_receiver>","exec"),namespace)
except Exception:
    _fail("RECEIVER_SOURCE")
try:
    receiver=namespace["OneShotReplyReceiver"](expected_payload_sha=@@PAYLOAD@@,bundle_sha=@@BUNDLE@@,challenge=@@CHALLENGE@@)
    frame=sys.stdin.buffer.read(8193)
    receiver.accept(frame,executed_sha=@@PAYLOAD@@)
except Exception:
    _fail("FRAME_REJECTED")
sys.stdout.buffer.write(frame)
'''
    script = (template.replace('@@SOURCE@@', repr(base64.b64encode(source).decode('ascii')))
        .replace('@@SHA@@', repr(source_sha)).replace('@@PAYLOAD@@', repr(expected_payload_sha))
        .replace('@@BUNDLE@@', repr(bundle_sha)).replace('@@CHALLENGE@@', repr(challenge)))
    return {'script': script, 'sha256': hashlib.sha256(script.encode()).hexdigest(),
            'payload_bytes': len(script.encode()), 'source_sha256': source_sha}
