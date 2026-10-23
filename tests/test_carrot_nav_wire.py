"""Real baseline/candidate client and TCP framing; named CPU fixture outputs."""
import json
import os
from pathlib import Path
import subprocess
import sys
import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=r'''
import hashlib,json,os,socket,threading
import numpy as np
from jetlink.client import JetlinkClient
from jetlink import protocol as P,output_projection as projection
from jetlink.packed_codec import CAPABILITY
from jetlink.transport.tcp import TcpTransport
from openpilot.selfdrive.modeld.jetlink.contracts import DEFAULT_SPEC,JETSON_SPEC
version=int(os.environ['WIRE_VERSION']);compact=os.environ['WIRE_COMPACT']=='1'
spec=JETSON_SPEC if os.environ['WIRE_MODEL']=='Nav' else DEFAULT_SPEC
a,b=socket.socketpair();ours,peer=TcpTransport(a),TcpTransport(b)
ours.protocol_version=peer.protocol_version=version
record={};errors=[]
def serve():
 try:
  msg=peer.recv(timeout=3)
  peer.send_json(P.Msg.HELLO_RESP,msg.seq,{'protocol':version,'stateful_v2':True,projection.CAPABILITY:projection.descriptor(),CAPABILITY:True})
  msg=peer.recv(timeout=3)
  peer.send_json(P.Msg.ENGINE_RESP,msg.seq,{'state':'ready','sha256':spec.sha256,'spec':spec.to_dict()})
  msg=peer.recv(timeout=3)
  payload=bytes(msg.payload);fid,flags=P.unpack_infer_req(msg.payload)
  count=projection.COUNT if compact else spec.output_nelem
  values=np.arange(count,dtype=np.float32)%100
  header=P.pack_infer_resp(fid,P.Status.OK,1,2,3)
  peer.send(P.Msg.INFER_RESP,msg.seq,(header,values),flags=projection.FLAG if compact else 0)
  record.update(request_sha256=hashlib.sha256(payload).hexdigest(),request_bytes=len(payload),flags=int(flags),seq=msg.seq,reply_bytes=len(header)+values.nbytes)
 except BaseException as e:errors.append(repr(e))
t=threading.Thread(target=serve);t.start()
client=JetlinkClient(ours,allow_output_projection=True)
try:
 client.hello();client.ensure_engine(spec.sha256,spec.nbytes)
 client.project_output=compact
 result=client.infer(np.arange(spec.warped_nbytes,dtype=np.uint8).reshape(spec.warped_shape),np.arange(spec.packed_nelem,dtype=np.float32)%256,frame_id=123,reset=True)
 assert np.array_equal(result,np.arange(result.size,dtype=np.float32)%100)
 record.update(result_sha256=hashlib.sha256(result.tobytes()).hexdigest(),spec=spec.to_dict(),protocol=version,prev_feat_present='prev_feat' in spec.packed_shapes,state_pairs=len(spec.state_pairs))
finally:client.close();t.join(timeout=5);peer.close()
assert not errors and not t.is_alive(),errors
print(json.dumps(record,sort_keys=True))
'''


@pytest.mark.parametrize('model,version,compact',[('V2',2,False),('V2',3,False),('Nav',2,False),('Nav',2,True),('Nav',3,False)])
def test_exact_source_wire_snapshot_matches_before_after(model,version,compact):
    reference=Path(os.environ.get('CARROT_NAV_REFERENCE_ROOT',ROOT/'.reference/m15-carrot-nav-366d6eae')).resolve()
    candidate=Path(os.environ['CARROT_NAV_CANDIDATE_ROOT']).resolve()
    values=[]
    for tree in (reference,candidate):
        env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(tree/'third_party/jetlink'),str(tree))),WIRE_MODEL=model,WIRE_VERSION=str(version),WIRE_COMPACT=str(int(compact)))
        result=subprocess.run([sys.executable,'-c',SCRIPT],cwd=tree,env=env,capture_output=True,text=True,timeout=15)
        assert result.returncode==0,result.stdout+result.stderr
        values.append(json.loads(result.stdout.strip().splitlines()[-1]))
    assert values[0]==values[1]
    assert values[1]['prev_feat_present'] is (model=='V2')
    assert values[1]['state_pairs']==(5 if model=='Nav' else 0)
    if model=='V2' and version==3:assert values[1]['request_bytes']==393272
    print('NAV_WIRE_BYTE_REGRESSION',json.dumps({'model':model,'protocol':version,'compact':compact,**values[1]},sort_keys=True))
