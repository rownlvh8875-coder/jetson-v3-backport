"""Exact protocol2 V3 exception; no GPU or model execution."""
import copy
import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS
import numpy as np
import pytest

@pytest.fixture
def comma(monkeypatch):
    root=Path(os.environ['CINQUE_COMMA_ROOT']).resolve()/"third_party/jetlink"
    saved={n:m for n,m in sys.modules.items() if n=='jetlink' or n.startswith('jetlink.')}
    for n in saved: del sys.modules[n]
    monkeypatch.syspath_prepend(str(root))
    try:
        c=importlib.import_module('jetlink.client')
        s=importlib.import_module('jetlink.spec')
        v=importlib.import_module('jetlink.v3_compat')
        assert Path(c.__file__).resolve().is_relative_to(root)
        print('COMMA_MODULE',c.__file__)
        yield NS(client=c,spec=s,v=v)
    finally:
        for n in list(sys.modules):
            if n=='jetlink' or n.startswith('jetlink.'): del sys.modules[n]
        sys.modules.update(saved)

class Peer:
    protocol_version=2
    def __init__(self,c):
        self.c=c; self.sent=[]; self.queue=[]
        self.hello={'protocol':2,'session_id':'a'*32,c.v.CAPABILITY:c.v.capability()}
        self.ready={'state':'ready','sha256':c.v.CANONICAL_SPEC['sha256'],
                    'spec':copy.deepcopy(c.v.CANONICAL_SPEC),'session_id':'a'*32,'generation':'b'*32}
    def send_json(self,mt,seq,data):
        from jetlink import protocol as P
        self.sent.append((mt,seq,data))
        reply=self.hello if mt==P.Msg.HELLO_REQ else self.ready
        self.queue.append(NS(msg_type=P.Msg.HELLO_RESP if mt==P.Msg.HELLO_REQ else P.Msg.ENGINE_RESP,
                             seq=seq,payload=memoryview(json.dumps(reply).encode())))
    def send(self,*a,**k): self.sent.append(a)
    def recv(self,timeout=None): return self.queue.pop(0)
    def close(self): pass

def ready(comma):
    t=Peer(comma); c=comma.client.JetlinkClient(t)
    c.hello(); spec=comma.spec.ModelSpec.from_dict(comma.v.CANONICAL_SPEC)
    c.approve_v3(spec)
    c.ensure_engine(spec.sha256,spec.nbytes,frame_skip=spec.frame_skip)
    return c,t,spec

def test_exact_spec_dtype_round_trip(comma):
    d=comma.v.CANONICAL_SPEC
    assert comma.spec.ModelSpec.from_dict(d).to_dict()==d

def test_v3_explicit_approval_and_ready_permit_protocol2(comma):
    c,t,s=ready(comma)
    c.infer_begin(np.zeros(s.warped_shape,np.uint8),np.ones(s.packed_nelem,np.float32),4)
    assert t.sent[-2][2]['session_id']=='a'*32
    assert t.sent[-2][2][comma.v.CAPABILITY]==comma.v.capability()

@pytest.mark.parametrize('fault',['missing','version','bool_version','size','digest','session'])
def test_bad_capability_rejected_before_engine_request(comma,fault):
    t=Peer(comma)
    if fault=='missing': del t.hello[comma.v.CAPABILITY]
    elif fault=='session': t.hello['session_id']=None
    else:
        key,value={'version':('version',2),'bool_version':('version',True),'size':('nbytes',1),'digest':('spec_sha256','0'*64)}[fault]
        t.hello[comma.v.CAPABILITY][key]=value
    c=comma.client.JetlinkClient(t); c.hello()
    with pytest.raises(comma.client.LinkError): c.approve_v3(comma.spec.ModelSpec.from_dict(comma.v.CANONICAL_SPEC))
    assert len(t.sent)==1

@pytest.mark.parametrize('fault',['spec','size','sha','generation','session'])
def test_bad_ready_rejected(comma,fault):
    t=Peer(comma); c=comma.client.JetlinkClient(t); c.hello()
    s=comma.spec.ModelSpec.from_dict(comma.v.CANONICAL_SPEC); c.approve_v3(s)
    if fault=='spec': t.ready['spec']['input_dtypes']['new_img']='float16'
    elif fault=='size': t.ready['spec']['nbytes']+=1
    elif fault=='sha': t.ready['sha256']='0'*64
    else: t.ready['session_id' if fault=='session' else fault]=None
    with pytest.raises(comma.client.LinkError): c.ensure_engine(s.sha256,s.nbytes)
    assert c.spec is None

def test_hello_discards_v3_approval_pending_and_telemetry(comma):
    c,t,s=ready(comma); c.last_state={'loaded':s.sha256}
    c.infer_begin(np.zeros(s.warped_shape,np.uint8),np.ones(s.packed_nelem,np.float32),4)
    c.hello()
    assert c.spec is None and c.last_state is None and c._infer_frame_id is None
    with pytest.raises(comma.client.LinkError): c.infer_end(1)
    with pytest.raises(comma.client.LinkError): c.ensure_engine(s.sha256,s.nbytes)

def test_opt_in_absent_keeps_generic_stateful_protocol2_blocked(comma):
    t=Peer(comma); c=comma.client.JetlinkClient(t); c.hello()
    s=comma.spec.ModelSpec.from_dict(comma.v.CANONICAL_SPEC)
    with pytest.raises(comma.client.LinkError): c.ensure_engine(s.sha256,s.nbytes)
    c.spec=s
    with pytest.raises(comma.client.LinkError): c.infer_begin(np.zeros(s.warped_shape,np.uint8),np.ones(s.packed_nelem,np.float32))

@pytest.mark.parametrize('change',[{'frame_skip':True},{'nbytes':766354845.0},{'checkpoint':'other'}])
def test_same_sha_altered_spec_or_types_rejected(comma,change):
    d=copy.deepcopy(comma.v.CANONICAL_SPEC); d.update(change)
    with pytest.raises(ValueError): comma.v.validate_spec(d)

def test_unsolicited_engine_generation_change_revokes_approval(comma):
    c,t,s=ready(comma)
    from jetlink import protocol as P
    d=dict(t.ready,generation='c'*32)
    with pytest.raises(comma.client.LinkError): c._dispatch(NS(msg_type=P.Msg.ENGINE_RESP,payload=memoryview(json.dumps(d).encode())))
    with pytest.raises(comma.client.LinkError): c.infer_begin(np.zeros(s.warped_shape,np.uint8),np.ones(s.packed_nelem,np.float32))

# Test real production Session with a bounded synthetic canonical fixture.
from test_production_v3 import prod, live

def test_server_requires_current_capability_before_v3_infer(live,monkeypatch):
    from jetlink import protocol as P
    from jetlink import v3_compat as v
    monkeypatch.setattr(v,'CANONICAL_SPEC',live.loaded.spec.to_dict())
    session=live.session
    assert session._v3_generation is None
    request={'sha256':live.loaded.sha256,'nbytes':live.loaded.spec.nbytes,'frame_skip':4}
    with pytest.raises(ValueError):
        session.on_engine_req(NS(seq=2,payload=memoryview(json.dumps(request).encode())))
    request.update({v.CAPABILITY:v.capability(),'session_id':session.session_id})
    session.on_engine_req(NS(seq=3,payload=memoryview(json.dumps(request).encode())))
    ready=json.loads(live.sent[-1][2])
    assert ready['generation']==live.loaded.generation
    assert ready['session_id']==session.session_id
    assert session._v3_generation==live.loaded.generation
    session._reset(4)
    assert session._v3_generation is None and session.request is None


def test_server_ready_only_never_starts_a_worker_for_stale_preloaded_hello(live,monkeypatch):
    from jetlink import v3_compat as v
    monkeypatch.setattr(v,'CANONICAL_SPEC',live.loaded.spec.to_dict())
    request={'sha256':live.loaded.sha256,'nbytes':live.loaded.spec.nbytes,'frame_skip':4,
             v.CAPABILITY:v.capability(),'session_id':live.session.session_id,'ready_only':True}
    def forbidden(*a): raise AssertionError('ready-only must not start preparation')
    monkeypatch.setattr(live.host,'request',forbidden)
    live.session.on_engine_req(NS(seq=2,payload=memoryview(json.dumps(request).encode())))
    assert json.loads(live.sent[-1][2])['state']=='ready'
    live.loaded.valid=False
    live.session.on_engine_req(NS(seq=3,payload=memoryview(json.dumps(request).encode())))
    assert json.loads(live.sent[-1][2])['state']=='failed'
    assert live.session._v3_generation is None

def test_prior_hello_engine_update_cannot_authorize_new_selection(comma):
    c,t,s=ready(comma)
    old=dict(t.ready)
    c.hello(); t.hello['session_id']='d'*32
    c._peer['session_id']='d'*32
    c.approve_v3(s)
    from jetlink import protocol as P
    with pytest.raises(comma.client.LinkError):
        c._dispatch(NS(msg_type=P.Msg.ENGINE_RESP,seq=0,payload=memoryview(json.dumps(old).encode())))
    assert c._v3_generation is None


def test_pinned_v3_decoder_does_not_discard_unknown_contract_fields(comma):
    d=copy.deepcopy(comma.v.CANONICAL_SPEC);d['unexpected_contract']='changed'
    with pytest.raises(ValueError):comma.spec.ModelSpec.from_dict(d)
