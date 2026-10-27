"""Single read-only capability check. No device dispatcher or sampling window."""
import errno
import sys

from tools.pinned_proc_view import AcquisitionError,ProcView

_REASONS=frozenset({'UNSUPPORTED_ABI','UNSUPPORTED_NATIVE','UNSUPPORTED_MOUNT_ID',
    'THREAD_PROFILE','NOT_PROCFS','SELF_MAPPING_UNSUPPORTED','FD_IDENTITY_CHANGED',
    'CLEANUP_FAILED','OWNER_CHANGED','OWNER_GENERATION_CHANGED','OWNER_STATUS_CHANGED',
    'NAMED_ROOT_CHANGED','NAMESPACE_ENDPOINT_CHANGED','MOUNT_ENDPOINT_CHANGED',
    'BOOT_ENDPOINT_CHANGED','UNREVIEWED_SUBMOUNT','STREAM_FAILED','READ_LIMIT',
    'READLINK_LIMIT','MOUNT_ID','FILE_KIND','CROSS_MOUNT','LINK_CROSS_MOUNT'})
_ERRNOS={getattr(errno,name):name for name in ('ENOENT','EACCES','EPERM','ENOSYS',
    'EINVAL','EIO','EBADF','EOPNOTSUPP','ERANGE','EOVERFLOW')}


def _project_record(record):
    if type(record) is not dict:return 'SCOPE_REJECTED','NONE'
    kind=record.get('type');reason=record.get('reason');number=record.get('errno')
    code=reason if kind in ('AcquisitionError','_Reject') and type(reason) is str and reason in _REASONS else 'SCOPE_REJECTED'
    if kind in ('OSError','PermissionError','FileNotFoundError') and code=='SCOPE_REJECTED':code='NATIVE_OS_ERROR'
    return code,_ERRNOS.get(number,'OTHER') if type(number) is int else 'NONE'


def _project_exception(error):
    if type(error) is AcquisitionError:
        args=error.args;reason=args[0] if len(args)==1 and type(args[0]) is str else None
        return (reason if reason in _REASONS else 'UNKNOWN_ACQUISITION'),'NONE'
    if isinstance(error,OSError):
        number=error.errno
        return 'NATIVE_OS_ERROR',_ERRNOS.get(number,'OTHER') if type(number) is int else 'NONE'
    return ('VALUE_ERROR' if type(error) is ValueError else 'UNEXPECTED_EXCEPTION'),'NONE'


def _result(status,events,injected,reason,phase,number):
    return {'schema':2,'status':status,'events':events,
        'evidence_kind':'INJECTED_FIXTURE' if injected else 'NATIVE_LOCAL_PROCFS',
        'processes_created':0,'journal_created':False,'sampling_window_started':False,'ticket_created':False,
        'device_validation':False,'policy_acceptance':False,'negative_pid_witness_allowed':False,
        'lifetime_acceptance':False,'temporal_visibility_proven':False,
        'reason_code':reason,'failure_phase':phase,'errno_code':number,
        'optimization_mode':'DISABLED' if sys.flags.optimize==0 else 'ENABLED',
        'bytecode_mode':'SUPPRESSED' if sys.dont_write_bytecode else 'ENABLED'}


def probe_capability(*,view_factory=None):
    """Caller must separately establish fresh actual OFF/source gates before use.

    Sink discards raw fields; only fixed enums, counts and false authority flags
    leave this function. No file journal, observer child, retry, or fast loop.
    """
    injected=view_factory is not None;factory=view_factory or ProcView;events=0
    def sink(event):
        nonlocal events
        events+=1
    if sys.flags.optimize!=0:return _result('BLOCKED_RUNTIME_FLAGS',0,injected,'OPTIMIZED_INTERPRETER','RUNTIME','NONE')
    phase='CONSTRUCT'
    try:
        view=factory(audit_sink=sink);phase='ENTER'
        with view as active:
            phase='SCOPE';value=active.scope();okay=value.get('endpoint_checks_pass') is True
            reason,number=_project_record(value.get('errors',{}).get('scope')) if not okay else ('NONE','NONE')
            phase='CLOSE'
        if okay:return _result('CAPABILITY_PROFILE_SUPPORTED',events,injected,'NONE','COMPLETE','NONE')
        return _result('BLOCKED_SCOPE_PROFILE',events,injected,reason,'SCOPE',number)
    except Exception as error:
        reason,number=_project_exception(error)
        return _result('BLOCKED_NATIVE_CAPABILITY',events,injected,reason,phase,number)


def build_payload(sources,expected_hashes):
    """Build, never execute, three exact-source modules for a future stdin check.

    expected_hashes must come from the reviewed release artifact. The payload's
    whole SHA must also be checked externally before any target invocation.
    """
    import base64
    import hashlib
    import json
    names=('proc_view_scope_model','pinned_proc_view','proc_view_capability')
    if type(sources) is not dict or type(expected_hashes) is not dict or set(sources)!=set(names) or set(expected_hashes)!=set(names):
        raise ValueError('PAYLOAD_MODULES')
    for name in names:
        raw,pin=sources[name],expected_hashes[name]
        if (type(raw) is not bytes or len(raw)>262144 or type(pin) is not str or len(pin)!=64 or
            any(c not in '0123456789abcdef' for c in pin) or hashlib.sha256(raw).hexdigest()!=pin):
            raise ValueError('PAYLOAD_SOURCE_PIN')
    try:body=json.dumps({n:sources[n].decode('utf-8') for n in names},sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
    except UnicodeError as error:raise ValueError('PAYLOAD_ENCODING') from error
    if len(body)>1024*1024:raise ValueError('PAYLOAD_SIZE')
    blob=base64.b64encode(body).decode('ascii')
    template='''import sys
_startup_bytecode=sys.dont_write_bytecode
_startup_optimize=sys.flags.optimize

def _blocked(status,reason=None,phase="PAYLOAD"):
    if reason is None:
        reason="PAYLOAD_IDENTITY" if status=="BLOCKED_PAYLOAD_IDENTITY" else "PAYLOAD_EXECUTION"
    return {"schema":2,"status":status,"events":0,"evidence_kind":"NO_ACQUISITION",
        "processes_created":0,"journal_created":False,"sampling_window_started":False,
        "ticket_created":False,"device_validation":False,"policy_acceptance":False,
        "negative_pid_witness_allowed":False,"lifetime_acceptance":False,"temporal_visibility_proven":False,
        "reason_code":reason,"failure_phase":phase,"errno_code":"NONE",
        "optimization_mode":"DISABLED" if _startup_optimize==0 else "ENABLED",
        "bytecode_mode":"SUPPRESSED" if _startup_bytecode else "ENABLED"}

def _entry():
    if _startup_optimize!=0:return _blocked("BLOCKED_RUNTIME_FLAGS","OPTIMIZED_INTERPRETER","RUNTIME")
    if not _startup_bytecode:return _blocked("BLOCKED_RUNTIME_FLAGS","BYTECODE_ENABLED","RUNTIME")
    import base64,hashlib,types
    pins=@@PINS@@
    names=("proc_view_scope_model","pinned_proc_view","proc_view_capability")
    encoded=@@BLOB@@
    try:
        if len(encoded)>1398104:return _blocked("BLOCKED_PAYLOAD_IDENTITY")
        raw=base64.b64decode(encoded,validate=True)
        if len(raw)>1048576 or hashlib.sha256(raw).hexdigest()!=@@BLOB_SHA@@:
            return _blocked("BLOCKED_PAYLOAD_IDENTITY")
        data=json.loads(raw)
        if type(data) is not dict or set(data)!=set(names) or set(pins)!=set(names):
            return _blocked("BLOCKED_PAYLOAD_IDENTITY")
        for name in names:
            text=data[name]
            if type(text) is not str or len(text.encode("utf-8"))>262144 or hashlib.sha256(text.encode("utf-8")).hexdigest()!=pins[name]:
                return _blocked("BLOCKED_PAYLOAD_IDENTITY")
    except Exception:
        return _blocked("BLOCKED_PAYLOAD_IDENTITY")
    sentinel=object();aliases=("tools",)+tuple("tools."+n for n in names)
    saved={n:sys.modules.get(n,sentinel) for n in aliases}
    bytecode=sys.dont_write_bytecode
    try:
        sys.dont_write_bytecode=True
        package=types.ModuleType("tools");package.__path__=[];sys.modules["tools"]=package
        for name in names:
            alias="tools."+name;module=types.ModuleType(alias);module.__package__="tools"
            sys.modules[alias]=module
            exec(compile(data[name],"<pinned:"+name+">","exec"),module.__dict__)
        return sys.modules["tools.proc_view_capability"].probe_capability()
    except Exception:
        return _blocked("BLOCKED_PAYLOAD_EXECUTION")
    finally:
        for alias,value in saved.items():
            if value is sentinel:sys.modules.pop(alias,None)
            else:sys.modules[alias]=value
        sys.dont_write_bytecode=bytecode

try:
    # JSON formatting after rejection must not write payload-import bytecode.
    # This cannot retroactively suppress interpreter startup writes without -B.
    sys.dont_write_bytecode=True
    import json
    print(json.dumps(_entry(),sort_keys=True,separators=(",",":"),allow_nan=False))
finally:
    sys.dont_write_bytecode=_startup_bytecode
'''
    script=(template.replace('@@PINS@@',repr({n:expected_hashes[n] for n in names}))
        .replace('@@BLOB@@',repr(blob)).replace('@@BLOB_SHA@@',repr(hashlib.sha256(body).hexdigest())))
    return {'script':script,'sha256':hashlib.sha256(script.encode('utf-8')).hexdigest(),
            'source_pins':dict(expected_hashes),'payload_bytes':len(script.encode('utf-8'))}
