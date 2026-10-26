from tools.proc_view_capability import probe_capability
from tools.pinned_proc_view import AcquisitionError
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import pytest
from tools.proc_view_capability import build_payload


class Fixture:
    calls=0
    def __init__(self,audit_sink):self.sink=audit_sink
    def __enter__(self):return self
    def __exit__(self,*_):pass
    def scope(self):
        Fixture.calls+=1
        self.sink({'event':'CALL_RESULT','details':{'private':'not public'}})
        return {'endpoint_checks_pass':True,'owner':{'pid':12345},'mount_namespace':'private-link'}


def test_one_capability_read_never_emits_raw_process_fields():
    Fixture.calls=0
    value=probe_capability(view_factory=Fixture)
    assert Fixture.calls==1 and value['status']=='CAPABILITY_PROFILE_SUPPORTED'
    assert value['evidence_kind']=='INJECTED_FIXTURE' and value['policy_acceptance'] is False
    assert '12345' not in str(value) and 'private-link' not in str(value) and 'not public' not in str(value)


def test_rejected_scope_is_not_success_or_retry():
    class Denied(Fixture):
        def scope(self):return {'endpoint_checks_pass':False,'errors':{'private':'not echoed'}}
    value=probe_capability(view_factory=Denied)
    assert value['status']=='BLOCKED_SCOPE_PROFILE' and value['processes_created']==0
    assert value['journal_created'] is False and value['sampling_window_started'] is False


def test_unavailable_native_query_is_a_blocked_no_write_receipt():
    def unsupported(**kwargs):raise AcquisitionError('private unsupported detail')
    value=probe_capability(view_factory=unsupported)
    assert value['status']=='BLOCKED_NATIVE_CAPABILITY' and 'private' not in str(value)
    assert value['ticket_created'] is False and value['device_validation'] is False


def source_bundle():
    root=Path(__file__).resolve().parents[1]
    names=('proc_view_scope_model','pinned_proc_view','proc_view_capability')
    sources={name:(root/'tools'/f'{name}.py').read_bytes() for name in names}
    return sources,{name:hashlib.sha256(raw).hexdigest() for name,raw in sources.items()}


def test_payload_build_is_deterministic_and_source_pinned():
    sources,pins=source_bundle();first=build_payload(sources,pins);second=build_payload(sources,pins)
    assert first==second and first['source_pins']==pins
    assert first['sha256']==hashlib.sha256(first['script'].encode()).hexdigest()
    assert 'C:/Users/' not in first['script'] and '/mnt/c/' not in first['script']


def test_source_drift_blocks_payload_construction():
    sources,pins=source_bundle();pins['pinned_proc_view']='0'*64
    with pytest.raises(ValueError):build_payload(sources,pins)


@pytest.mark.parametrize('extra,missing',[(True,False),(False,True)])
def test_payload_closed_module_manifest(extra,missing):
    sources,pins=source_bundle()
    if extra:sources['unreviewed_extra']=b'print("unreviewed")'
    if missing:sources.pop('pinned_proc_view')
    with pytest.raises(ValueError):build_payload(sources,pins)


def test_standalone_payload_runs_only_bounded_local_capability():
    sources,pins=source_bundle();payload=build_payload(sources,pins)
    run=subprocess.run([sys.executable,'-B','-c',payload['script']],capture_output=True,timeout=5,check=True)
    assert run.stderr==b'' and len(run.stdout.splitlines())==1
    value=json.loads(run.stdout)
    assert value['status'] in {'CAPABILITY_PROFILE_SUPPORTED','BLOCKED_SCOPE_PROFILE','BLOCKED_NATIVE_CAPABILITY'}
    assert value['processes_created']==0 and value['journal_created'] is False
    assert value['sampling_window_started'] is False and value['device_validation'] is False
    assert not ({'pid','cmdline','mount_namespace','private'}&set(value))


def test_payload_pin_tamper_never_executes_module_sources():
    sources,pins=source_bundle();payload=build_payload(sources,pins)
    changed=payload['script'].replace(pins['pinned_proc_view'],'0'*64,1)
    assert changed!=payload['script']
    run=subprocess.run([sys.executable,'-B','-c',changed],capture_output=True,timeout=5,check=True)
    value=json.loads(run.stdout)
    assert value['status']=='BLOCKED_PAYLOAD_IDENTITY' and value['policy_acceptance'] is False
