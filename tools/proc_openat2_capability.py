"""Offline schema3 endpoint-only release builder and fixed privacy projection.

No dispatcher or native import at builder import time. Reviewed source pins and
runtime/transport identity are caller trust premises, never peer authentication.
"""
import errno
import sys

NAMES = ('proc_view_scope_model', 'pinned_proc_view', 'proc_openat2_bootstrap',
         'proc_openat2_scope', 'proc_openat2_capability')
_FALSE = ('journal_created', 'sampling_window_started', 'ticket_created',
          'device_validation', 'policy_acceptance', 'negative_pid_witness_allowed',
          'lifetime_acceptance', 'temporal_visibility_proven', 'namespace_equality_proven',
          'full_host_visibility_proven', 'runtime_scope_confirmed',
          'full_ProcView_interface', 'legacy_fallback_allowed')
_PRIVATE_FALSE = ('runtime_scope_confirmed', 'namespace_equality_proven',
    'full_host_visibility_proven', 'temporal_visibility_proven',
    'negative_pid_witness_allowed', 'policy_acceptance', 'legacy_fallback_allowed',
    'lifetime_acceptance', 'full_ProcView_interface')
_NATIVE = frozenset({'UNSUPPORTED_ABI', 'UNSUPPORTED_NATIVE', 'THREAD_PROFILE'})
_SCOPE = frozenset({'NOT_PROCFS', 'OWNER_MAPPING', 'FD_OWNERSHIP', 'FD_KIND', 'FD_FLAGS',
    'PROC_DEVICE', 'OWNER_CHANGED', 'FD_IDENTITY_CHANGED', 'OPEN_LIMIT', 'READ_CALL_LIMIT',
    'READ_LIMIT', 'OWNER_STATUS', 'FDINFO_FIELDS', 'FDINFO_POSITION', 'FDINFO_FLAGS',
    'FDINFO_INODE', 'MOUNT_ID_CHANGED', 'NAMED_ROOT_CHANGED', 'OWNER_GENERATION_CHANGED',
    'OWNER_STATUS_CHANGED', 'NAMESPACE_ENDPOINT_CHANGED', 'MOUNT_ENDPOINT_CHANGED',
    'BOOT_ENDPOINT_CHANGED', 'CLEANUP_FAILED', 'UNREVIEWED_SUBMOUNT', 'VISIBILITY',
    'MOUNT_IDENTITY', 'MOUNT_NOT_CURRENT', 'AMBIGUOUS_MOUNT', 'MOUNTINFO', 'FDINFO',
    'STAT_LAYOUT', 'READLINK_LIMIT', 'UNSUPPORTED_OPEN_HOW'})
_ERRNO = {getattr(errno, name): name for name in ('ENOENT', 'EACCES', 'EPERM', 'ENOSYS',
    'EINVAL', 'EXDEV', 'EAGAIN', 'ELOOP', 'EIO', 'EBADF', 'EINTR', 'EOPNOTSUPP',
    'ERANGE', 'EOVERFLOW')}


def _hex(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def _modes():
    return ('DISABLED' if sys.flags.optimize == 0 else 'ENABLED',
            'SUPPRESSED' if sys.dont_write_bytecode else 'ENABLED',
            'ISOLATED' if sys.flags.isolated == 1 else 'NOT_ISOLATED')


def _runtime_reason(modes):
    if modes[0] != 'DISABLED':
        return 'OPTIMIZED_INTERPRETER'
    if modes[1] != 'SUPPRESSED':
        return 'BYTECODE_ENABLED'
    if modes[2] != 'ISOLATED':
        return 'ISOLATION_REQUIRED'
    return None


def _receipt(bundle, challenge, modes, status, reason, phase, number='NONE', *, attempted=False,
             injected=False, passed=False):
    return {'schema': 3, 'profile': 'OPENAT2_ENDPOINT_CAPABILITY_V1', 'status': status,
            'reason_code': reason, 'failure_phase': phase, 'errno_code': number,
            'evidence_kind': ('INJECTED_FIXTURE' if injected else 'NATIVE_LOCAL_PROCFS')
                             if attempted else 'NO_ACQUISITION',
            'inspect_attempts': 1 if attempted else 0,
            'endpoint_checks_pass': passed, 'lease_closed': passed,
            'processes_created': 0, **{key: False for key in _FALSE},
            'optimization_mode': modes[0], 'bytecode_mode': modes[1], 'isolation_mode': modes[2],
            'source_bundle_sha256': bundle, 'challenge': challenge}


def _project(error):
    # Only this fixed fact about cleanup leaves the private error; never its
    # descriptor, path, exception text, cause, or diagnostic dictionary.
    cleanup = getattr(error, 'private_cleanup_errors', None)
    if type(cleanup) is list and cleanup:
        return 'BLOCKED_ENDPOINT_SCOPE', 'CLEANUP_FAILED', 'NONE'
    if isinstance(error, OSError):
        number = error.errno
        return 'BLOCKED_NATIVE_CAPABILITY', 'NATIVE_OS_ERROR', _ERRNO.get(number, 'OTHER') if type(number) is int else 'OTHER'
    classes = []
    for module, name in (('pinned_proc_view', 'AcquisitionError'),
                         ('proc_openat2_bootstrap', 'BootstrapError'),
                         ('proc_view_scope_model', '_Reject')):
        cls = getattr(sys.modules.get('tools.' + module), name, None)
        if isinstance(cls, type):
            classes.append(cls)
    if type(error) in classes:
        args = error.args
        reason = args[0] if len(args) == 1 and type(args[0]) is str else None
        if reason in _NATIVE:
            return 'BLOCKED_NATIVE_CAPABILITY', reason, 'NONE'
        return 'BLOCKED_ENDPOINT_SCOPE', reason if reason in _SCOPE else 'UNKNOWN_SCOPE', 'NONE'
    return 'BLOCKED_ENDPOINT_SCOPE', 'VALUE_ERROR' if type(error) is ValueError else 'UNKNOWN_EXCEPTION', 'NONE'


def probe_endpoint(*, bundle_sha256, challenge, _inspector=None):
    """Exactly one local endpoint inspection; no file/process/window/authority.

    Test injection remains INJECTED_FIXTURE and is rejected by native receivers.
    Actual invocation needs separately reviewed release/runtime/fresh OFF gates.
    """
    if not _hex(bundle_sha256) or not _hex(challenge):
        raise ValueError('RELEASE_ID')
    modes = _modes()
    runtime = _runtime_reason(modes)
    if runtime:
        return _receipt(bundle_sha256, challenge, modes, 'BLOCKED_RUNTIME_FLAGS', runtime, 'RUNTIME')
    injected = _inspector is not None
    try:
        if _inspector is None:
            from tools.proc_openat2_scope import inspect_protected_scope
            _inspector = inspect_protected_scope
        value = _inspector()
        backend = 'INJECTED_OPENAT2_SCOPE_ONLY' if injected else 'NATIVE_OPENAT2_SCOPE_ONLY'
        valid = (type(value) is dict and value.get('kind') == 'OPENAT2_ENDPOINT_SCOPE_V1' and
                 value.get('acquisition_backend') == backend and
                 value.get('endpoint_checks_pass') is True and value.get('lease_closed') is True and
                 all(value.get(key) is False for key in _PRIVATE_FALSE) and
                 all(value.get(key, False) is False for key in _FALSE) and
                 type(value.get('processes_created', 0)) is int and value.get('processes_created', 0) == 0)
        if not valid:
            return _receipt(bundle_sha256, challenge, modes, 'BLOCKED_ENDPOINT_SCOPE',
                            'RESULT_CONTRACT', 'INSPECT', attempted=True, injected=injected)
        return _receipt(bundle_sha256, challenge, modes, 'ENDPOINT_CHECKS_PASS', 'NONE',
                        'COMPLETE', attempted=True, injected=injected, passed=True)
    except Exception as error:
        status, reason, number = _project(error)
        return _receipt(bundle_sha256, challenge, modes, status, reason, 'INSPECT', number,
                        attempted=True, injected=injected)


def build_payload(sources, expected_hashes, *, challenge):
    """Build only. Pins/challenge must come from the independently reviewed release."""
    import base64
    import hashlib
    import json
    if (type(sources) is not dict or type(expected_hashes) is not dict or
        set(sources) != set(NAMES) or set(expected_hashes) != set(NAMES) or not _hex(challenge)):
        raise ValueError('BUNDLE_CONTRACT')
    for name in NAMES:
        raw, pin = sources[name], expected_hashes[name]
        if (type(raw) is not bytes or not raw or len(raw) > 262144 or not _hex(pin) or
            hashlib.sha256(raw).hexdigest() != pin):
            raise ValueError('SOURCE_PIN')
    try:
        body = json.dumps({n: sources[n].decode('utf-8') for n in NAMES}, sort_keys=True,
                          separators=(',', ':'), ensure_ascii=True).encode('ascii')
    except UnicodeError:
        raise ValueError('SOURCE_ENCODING') from None
    if len(body) > 1048576:
        raise ValueError('BUNDLE_SIZE')
    bundle_sha = hashlib.sha256(body).hexdigest()
    base = _receipt(bundle_sha, challenge, ('DISABLED', 'SUPPRESSED', 'ISOLATED'),
                    'BLOCKED_PAYLOAD_EXECUTION', 'PAYLOAD_EXECUTION', 'PAYLOAD')
    template = '''import sys
_startup=(sys.flags.optimize,sys.dont_write_bytecode,sys.flags.isolated)
_base=@@BASE@@

def _blocked(status,reason,phase="PAYLOAD"):
    value=dict(_base)
    value.update(status=status,reason_code=reason,failure_phase=phase,
        optimization_mode="DISABLED" if _startup[0]==0 else "ENABLED",
        bytecode_mode="SUPPRESSED" if _startup[1] else "ENABLED",
        isolation_mode="ISOLATED" if _startup[2]==1 else "NOT_ISOLATED")
    return value

def _entry():
    if _startup[0]!=0:return _blocked("BLOCKED_RUNTIME_FLAGS","OPTIMIZED_INTERPRETER","RUNTIME")
    if not _startup[1]:return _blocked("BLOCKED_RUNTIME_FLAGS","BYTECODE_ENABLED","RUNTIME")
    if _startup[2]!=1:return _blocked("BLOCKED_RUNTIME_FLAGS","ISOLATION_REQUIRED","RUNTIME")
    import base64,hashlib,types
    names=@@NAMES@@
    pins=@@PINS@@
    encoded=@@BLOB@@
    try:
        if len(encoded)>1398104:raise ValueError()
        raw=base64.b64decode(encoded,validate=True)
        if len(raw)>1048576 or base64.b64encode(raw).decode("ascii")!=encoded or hashlib.sha256(raw).hexdigest()!=@@BUNDLE@@:raise ValueError()
        data=json.loads(raw)
        if type(data) is not dict or set(data)!=set(names) or set(pins)!=set(names):raise ValueError()
        for name in names:
            text=data[name]
            if type(text) is not str or not text or len(text.encode("utf-8"))>262144 or hashlib.sha256(text.encode("utf-8")).hexdigest()!=pins[name]:raise ValueError()
    except Exception:
        return _blocked("BLOCKED_PAYLOAD_IDENTITY","PAYLOAD_IDENTITY")
    sentinel=object();aliases=("tools",)+tuple("tools."+n for n in names)
    saved={n:sys.modules.get(n,sentinel) for n in aliases};bytecode=sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode=True
        package=types.ModuleType("tools");package.__path__=[];sys.modules["tools"]=package
        for name in names:
            alias="tools."+name;module=types.ModuleType(alias);module.__package__="tools"
            sys.modules[alias]=module
            exec(compile(data[name],"<pinned:"+name+">","exec"),module.__dict__)
        return sys.modules["tools.proc_openat2_capability"].probe_endpoint(bundle_sha256=@@BUNDLE@@,challenge=@@CHALLENGE@@)
    except Exception:
        return _blocked("BLOCKED_PAYLOAD_EXECUTION","PAYLOAD_EXECUTION")
    finally:
        for alias,value in saved.items():
            if value is sentinel:sys.modules.pop(alias,None)
            else:sys.modules[alias]=value
        sys.dont_write_bytecode=bytecode

try:
    sys.dont_write_bytecode=True
    import json
    sys.stdout.buffer.write(json.dumps(_entry(),sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")+b"\\n")
finally:
    sys.dont_write_bytecode=_startup[1]
'''
    script = (template.replace('@@BASE@@', repr(base)).replace('@@NAMES@@', repr(NAMES))
        .replace('@@PINS@@', repr({n: expected_hashes[n] for n in NAMES}))
        .replace('@@BLOB@@', repr(base64.b64encode(body).decode('ascii')))
        .replace('@@BUNDLE@@', repr(bundle_sha)).replace('@@CHALLENGE@@', repr(challenge)))
    # The reused outer readonly decoder independently caps the whole source,
    # not just each embedded module. Never publish an unusable larger release.
    if len(script.encode()) > 262144:
        raise ValueError('PAYLOAD_SIZE')
    return {'script': script, 'sha256': hashlib.sha256(script.encode()).hexdigest(),
            'payload_bytes': len(script.encode()), 'source_pins': dict(expected_hashes),
            'source_bundle_sha256': bundle_sha, 'challenge': challenge}
