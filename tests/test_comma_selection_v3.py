"""Exercise the applied comma integration; no camera, devices or downloads."""
import copy
import importlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def comma(monkeypatch):
    root = Path(os.environ.get('CINQUE_COMMA_ROOT', REPO.parent/'development/openpilot-v3')).resolve()
    saved = {n:m for n,m in sys.modules.items() if n == 'openpilot' or n.startswith('openpilot.') or n == 'jetlink' or n.startswith('jetlink.')}
    for n in saved: del sys.modules[n]
    monkeypatch.syspath_prepend(str(root))
    monkeypatch.delenv('CARROT_JETLINK_V3', raising=False)
    try:
        mods = {n:importlib.import_module('openpilot.selfdrive.modeld.jetlink.'+n) for n in ('contracts','selection','link','mac')}
        yield NS(**mods, root=root)
    finally:
        for n in list(sys.modules):
            if n == 'openpilot' or n.startswith('openpilot.') or n == 'jetlink' or n.startswith('jetlink.'):
                del sys.modules[n]
        sys.modules.update(saved)


def v3dict():
    return json.loads((REPO/'artifacts/cinque_v3.json').read_text())


def peer(comma):
    from jetlink.v3_compat import CAPABILITY, capability
    return {'protocol':2, 'backend':'trt', 'device':'descriptive GPU', CAPABILITY:capability()}


def test_explicit_selection_preserves_v2_default_and_rejects_unknown_setting(comma, monkeypatch):
    assert not comma.selection.v3_enabled()
    monkeypatch.setenv('CARROT_JETLINK_V3','0')
    assert not comma.selection.v3_enabled()
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    assert comma.selection.v3_enabled()
    monkeypatch.setenv('CARROT_JETLINK_V3','yes')
    with pytest.raises(ValueError, match='CARROT_JETLINK_V3'):
        comma.selection.v3_enabled()


def test_canonical_full_contract_and_dtypes_are_pinned(comma):
    from jetlink.spec import ModelSpec
    canonical = v3dict()
    assert comma.contracts.V3_SPEC.to_dict() == canonical
    assert comma.contracts.validate_model_spec(ModelSpec.from_dict(canonical)).to_dict() == canonical
    for field, change in [('checkpoint','wrong'), ('nbytes',1), ('frame_skip',8),
                          ('input_dtypes',dict(canonical['input_dtypes'],new_img='float16')),
                          ('output_dtypes',dict(canonical['output_dtypes'],outputs='float16')),
                          ('output_slices',dict(canonical['output_slices'],action=[2062,2064]))]:
        bad = copy.deepcopy(canonical); bad[field] = change
        with pytest.raises(ValueError):
            comma.contracts.validate_model_spec(ModelSpec.from_dict(bad))
    assert comma.contracts.model_name(comma.contracts.V3_SPEC) == 'Cinque v3'


def test_v3_selection_requires_opt_in_protocol2_and_exact_current_capability(comma, monkeypatch):
    p = peer(comma)
    assert comma.selection.jetson_spec(p) == comma.link.SPEC
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    assert comma.selection.jetson_spec(p) == comma.contracts.V3_SPEC
    from jetlink.v3_compat import CAPABILITY
    for change in ({'protocol':3}, {CAPABILITY:True}, {CAPABILITY:dict(p[CAPABILITY],version=2)},
                   {CAPABILITY:dict(p[CAPABILITY],version=True)}, {CAPABILITY:dict(p[CAPABILITY],nbytes=float(p[CAPABILITY]['nbytes']))},
                   {CAPABILITY:None}):
        with pytest.raises(ValueError):
            comma.selection.jetson_spec(dict(p,**change))
    assert comma.selection.jetson_spec({'protocol':3,'backend':'ort','device':'ane-Apple_M4'}) is None


class ReadyClient:
    def __init__(self, spec):
        self.spec = None
        self.result = spec
        self.t = NS()
        self.calls=[]
        self.progress_cb=None
        self._should_stop=lambda:False
    def approve_v3(self,spec):
        self.calls.append(('approve',spec.to_dict()))
    def ensure_engine(self,*args,**kwargs):
        self.calls.append(('ensure',args,kwargs))
        self.spec=self.result
        return self.result


def test_v3_prepare_requests_only_pinned_preprovisioned_engine_and_remembers_approval(comma, monkeypatch, tmp_path):
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    client=ReadyClient(comma.contracts.V3_SPEC); original=client.t
    monkeypatch.setattr(comma.mac,'model_file',lambda *a,**kw:pytest.fail('V3 must not download'))
    result=comma.mac.prepare(client,peer(comma),lambda:True,lambda:True,lambda *a:None,tmp_path)
    assert result == comma.contracts.V3_SPEC and client.t is original
    assert client.calls[0][0]=='approve'
    request=client.calls[1]
    assert request[0]=='ensure' and request[1]==(result.sha256,result.nbytes)
    assert request[2]['frame_skip']==4 and 'onnx_path' not in request[2]
    assert request[2]['build_timeout']==900
    assert comma.selection.approved_spec(tmp_path/'jetson-v3') == result


@pytest.mark.parametrize('failure',['offroad','disconnected','missing','changed'])
def test_v3_prepare_failure_never_downloads_or_approves(comma, monkeypatch, tmp_path, failure):
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    client=ReadyClient(comma.contracts.V3_SPEC); original=client.t
    monkeypatch.setattr(comma.mac,'model_file',lambda *a,**kw:pytest.fail('V3 must not download'))
    if failure=='missing':
        from jetlink.client import EngineMissing
        def missing(*a,**kw): raise EngineMissing('absent')
        client.ensure_engine=missing
    elif failure=='changed':
        client.result=comma.link.SPEC
    with pytest.raises((comma.mac.PreparationDeferred,ValueError)):
        comma.mac.prepare(client,peer(comma),lambda:failure!='offroad',lambda:failure!='disconnected',lambda *a:None,tmp_path)
    assert client.t is original
    assert comma.selection.approved_spec(tmp_path/'jetson-v3') is None


def test_v3_preparation_pending_callbacks_recheck_ignition_and_restore_transport(comma, monkeypatch, tmp_path):
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    client=ReadyClient(comma.contracts.V3_SPEC); original=client.t
    def pending(*a,**kw):
        assert client.t is not original
        with pytest.raises(comma.mac.PreparationDeferred):
            kw['should_stop']()
        raise comma.mac.PreparationDeferred('ignition changed')
    client.ensure_engine=pending
    calls=iter([True,False])
    with pytest.raises(comma.mac.PreparationDeferred):
        comma.mac.prepare(client,peer(comma),lambda:next(calls),lambda:True,lambda *a:None,tmp_path)
    assert client.t is original


def test_local_handshake_admits_v3_only_with_opt_in_and_exact_peer(comma, monkeypatch):
    spec=comma.contracts.V3_SPEC; p=peer(comma)
    with pytest.raises(ValueError):
        comma.selection.validate_selected_spec(spec,p)
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    comma.selection.validate_selected_spec(spec,p)
    with pytest.raises(ValueError):
        comma.selection.validate_selected_spec(comma.link.SPEC,p)
    with pytest.raises(ValueError):
        comma.selection.validate_selected_spec(spec,dict(p,protocol=3))


def test_protocol3_app_dynamic_contract_remains_accepted(comma, monkeypatch):
    from jetlink.spec import ModelSpec
    app=ModelSpec.from_dict(dict(comma.link.SPEC.to_dict(),sha256='a'*64))
    p={'protocol':3,'backend':'ort','device':'ane-Apple_M4'}
    comma.selection.validate_selected_spec(app,p,'usb')
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    comma.selection.validate_selected_spec(app,p,'usb')
    with pytest.raises(ValueError):
        comma.selection.validate_selected_spec(app,dict(p,protocol=2),'usb')


def test_v3_parser_publishes_existing_shapes_without_hidden_feedback(comma):
    from openpilot.selfdrive.modeld.parse_model_outputs import Parser
    spec=comma.contracts.V3_SPEC
    assert spec.packed_nelem==12 and 'prev_feat' not in spec.packed_shapes
    out=comma.contracts.parse_outputs(Parser(),spec,np.zeros(spec.output_nelem,np.float32))
    assert out['plan'].shape==(1,33,15)
    assert out['lead'].shape==(1,3,6,4)
    assert out['action'].shape==(1,4)


def test_approved_preloaded_v3_can_resume_onroad_but_pending_work_cannot(comma, monkeypatch, tmp_path):
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    spec=comma.contracts.V3_SPEC
    comma.selection.remember_spec(tmp_path/'jetson-v3',spec)
    p=dict(peer(comma),loaded=spec.sha256)
    client=ReadyClient(spec)
    assert comma.mac.prepare(client,p,lambda:False,lambda:True,lambda *a:None,tmp_path)==spec
    assert client.calls[0][0]=='approve'
    with pytest.raises(comma.mac.PreparationDeferred):
        client.calls[1][2]['should_stop']()
    from jetlink.v3_compat import CAPABILITY
    with pytest.raises(ValueError):
        comma.mac.prepare(ReadyClient(spec),dict(p,**{CAPABILITY:None}),lambda:False,lambda:True,lambda *a:None,tmp_path)


def test_real_vendored_client_preparation_uses_current_hello_ready_and_cache(comma, monkeypatch, tmp_path):
    from test_v3_negotiation import Peer
    from jetlink import client, spec, v3_compat
    from jetlink import protocol as P
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    t=Peer(NS(client=client,spec=spec,v=v3_compat))
    t.hello.update(backend='trt',loaded=None)
    c=client.JetlinkClient(t); p=c.hello()
    monkeypatch.setattr(comma.mac,'model_file',lambda *a,**kw:pytest.fail('no fallback download'))
    assert comma.mac.prepare(c,p,lambda:True,lambda:True,lambda *a:None,tmp_path)==comma.contracts.V3_SPEC
    request=t.sent[-1][2]
    assert request[v3_compat.CAPABILITY]==v3_compat.capability()
    assert request['session_id']==t.hello['session_id']
    assert c._v3_generation==t.ready['generation']
    t.hello['loaded']=comma.contracts.V3_SPEC.sha256
    p=c.hello()
    assert c._v3_generation is None
    assert comma.mac.prepare(c,p,lambda:False,lambda:True,lambda *a:None,tmp_path)==comma.contracts.V3_SPEC
    assert t.sent[-1][0]==P.Msg.ENGINE_REQ
    assert c._v3_generation==t.ready['generation']


def test_local_client_applies_peer_and_transport_selection_before_accepting_spec(comma, monkeypatch):
    spec=comma.contracts.V3_SPEC
    closed=[]
    sock=NS(settimeout=lambda *a:None,connect=lambda *a:None,close=lambda:closed.append(True))
    monkeypatch.setattr(comma.link.socket,'AF_UNIX',1,raising=False)
    monkeypatch.setattr(comma.link.socket,'socket',lambda *a:sock)
    payload={'spec':spec.to_dict(),'peer':peer(comma),'mode':'usb'}
    monkeypatch.setattr(comma.link,'receive',lambda *a:json.dumps(payload).encode())
    with pytest.raises(ValueError):
        comma.link.Client()
    assert closed==[True]
    monkeypatch.setenv('CARROT_JETLINK_V3','1')
    assert comma.link.Client().spec==spec
    payload['mode']='ios'
    with pytest.raises(ValueError):
        comma.link.Client()


@pytest.mark.parametrize('failure',['stale','nonfinite','truncated','timeout','disconnect'])
def test_real_local_inference_failure_restores_internal_model_with_fault(comma, monkeypatch, tmp_path, failure):
    model=importlib.import_module('openpilot.selfdrive.modeld.jetlink.model')
    from openpilot.selfdrive.modeld.parse_model_outputs import Parser
    monkeypatch.setitem(sys.modules,'openpilot.common.swaglog',NS(cloudlog=NS(warning=lambda *a:None,exception=lambda *a:None)))
    monkeypatch.setattr(model,'FAULT',tmp_path/'fault')
    monkeypatch.setattr(comma.link,'send_parts',lambda *a,**kw:None)
    spec=comma.contracts.V3_SPEC
    output=np.zeros(spec.output_nelem,np.float32)
    calls=[]
    def receive(*args):
        calls.append(True)
        if len(calls)==1:
            return comma.link.REPLY.pack(1,0,0,0)+output.tobytes()
        if failure=='timeout': raise TimeoutError('IPC deadline')
        if failure=='disconnect': raise ConnectionError('IPC disconnected')
        if failure=='truncated': return b'bad'
        bad=output.copy()
        if failure=='nonfinite': bad[-1]=np.nan
        return comma.link.REPLY.pack(3 if failure=='stale' else 2,0,0,0)+bad.tobytes()
    client=comma.link.Client.__new__(comma.link.Client)
    closed=[]
    client.sock=NS(settimeout=lambda *a:None,close=lambda:closed.append(True))
    client.timeout=.15; client.spec=spec; client.reader=NS(receive=receive); client.timings=(0,0,0)
    class Camera:
        timings=(0.,0.,0.)
        def __call__(self,*a): return np.zeros(spec.warped_shape,np.uint8)
    small_calls=[]; small_resets=[]
    joined=model.JoiningModel.__new__(model.JoiningModel)
    joined.small=NS(run=lambda *a:small_calls.append(True) or {'internal':True},reset=lambda:small_resets.append(True))
    joined.warp=Camera(); joined.preparation=None; joined.connection=None; joined.client=client
    joined.ready=True; joined.join_allowed=True; joined.active=False; joined.small_runs=3; joined.next_join=0.
    joined.spec=spec; joined.parser=Parser(); joined.packed=np.zeros(12,np.float32)
    joined.views={name:a.reshape(shape) for (name,shape),a in zip(spec.packed_shapes.items(),np.split(joined.packed,[8,10]),strict=True)}
    joined.prev_desire=np.zeros(8,np.float32); joined.frame=0; joined.reset=True; joined.source_sof=0
    joined.last_slow_log=0.; joined.next_status=0.; joined.error=''
    inputs={'desire_pulse':np.zeros(8,np.float32),'traffic_convention':np.zeros((1,2),np.float32),'action_t':np.zeros((1,2),np.float32)}
    assert joined.run({}, {}, inputs,False)['plan'].shape==(1,33,15)
    assert joined.active and not joined.reset and not small_calls
    status=joined._status_record(1.)
    assert status['selected_model']=='Cinque v3' and status['active_model']=='Cinque v3'
    assert status['active_sha256']==spec.sha256 and status['fallback'] is False
    assert joined.run({}, {}, inputs,False)=={'internal':True}
    assert not joined.active and joined.client is None and small_calls==[True] and small_resets==[True]
    assert closed==[True] and model.FAULT.is_file()
    status=joined._status_record(2.)
    assert status['selected_model']=='Cinque v3' and status['active_model']=='Internal model'
    assert status['active_sha256'] is None and status['fallback'] is True and status['error']
