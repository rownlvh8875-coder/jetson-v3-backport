"""Single read-only capability check. No device dispatcher or sampling window."""
from tools.pinned_proc_view import AcquisitionError,ProcView


def probe_capability(*,view_factory=None):
    """Caller must separately establish fresh actual OFF/source gates before use.

    Sink discards raw fields; only fixed enums, counts and false authority flags
    leave this function. No file journal, observer child, retry, or fast loop.
    """
    injected=view_factory is not None;factory=view_factory or ProcView;events=0
    def sink(event):
        nonlocal events
        events+=1
    status='BLOCKED_NATIVE_CAPABILITY'
    try:
        with factory(audit_sink=sink) as view:
            okay=view.scope().get('endpoint_checks_pass') is True
        status='CAPABILITY_PROFILE_SUPPORTED' if okay else 'BLOCKED_SCOPE_PROFILE'
    except (AcquisitionError,OSError,ValueError):pass
    return {'schema':1,'status':status,'events':events,
        'evidence_kind':'INJECTED_FIXTURE' if injected else 'NATIVE_LOCAL_PROCFS',
        'processes_created':0,'journal_created':False,'sampling_window_started':False,'ticket_created':False,
        'device_validation':False,'policy_acceptance':False,'negative_pid_witness_allowed':False,
        'lifetime_acceptance':False,'temporal_visibility_proven':False}


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
    template='''import base64, hashlib, json, sys, types

def _blocked(status):
    return {"schema":1,"status":status,"events":0,"evidence_kind":"NATIVE_LOCAL_PROCFS",
        "processes_created":0,"journal_created":False,"sampling_window_started":False,
        "ticket_created":False,"device_validation":False,"policy_acceptance":False,
        "negative_pid_witness_allowed":False,"lifetime_acceptance":False,"temporal_visibility_proven":False}

def _entry():
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

print(json.dumps(_entry(),sort_keys=True,separators=(",",":"),allow_nan=False))
'''
    script=(template.replace('@@PINS@@',repr({n:expected_hashes[n] for n in names}))
        .replace('@@BLOB@@',repr(blob)).replace('@@BLOB_SHA@@',repr(hashlib.sha256(body).hexdigest())))
    return {'script':script,'sha256':hashlib.sha256(script.encode('utf-8')).hexdigest(),
            'source_pins':dict(expected_hashes),'payload_bytes':len(script.encode('utf-8'))}
