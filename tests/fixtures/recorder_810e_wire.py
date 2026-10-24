"""Separate server/comma CPU processes; real810e Session and daemon IPC.

GPU execution alone is deterministic CPU_FAKE. Native logging/Params/phase
reporting are inert. No USB device, ONNX model or vehicle service is accessed.
"""
import ast
import hashlib
import importlib.util
import json
import logging
import os
from pathlib import Path
import socket
import sys
import tempfile
import threading
import time
import types

import numpy as np


def sha(a):return hashlib.sha256(memoryview(a).cast('B')).hexdigest()
def emit(value):print(json.dumps(value),flush=True)


def server(root):
    from jetlink.server import session as S
    from jetlink.server.cache import EngineCache
    from jetlink.spec import ModelSpec
    from jetlink.transport.tcp import TcpTransport
    from jetlink.transport.base import LinkError
    spec=ModelSpec.from_dict(json.loads((root/'nav.json').read_text()))
    seen=[]
    class Engine:
        dtype_transforms={};last_gpu_us=0
        def __init__(self):
            self.inputs={n:types.SimpleNamespace(shape=s,dtype=np.dtype(np.uint8 if 'img' in n else np.float32)) for n,s in spec.input_shapes.items()}
            self.outputs={n:types.SimpleNamespace(shape=s,dtype=np.dtype(np.uint8 if 'img' in n else np.float32)) for n,s in spec.output_shapes.items()}
            self.buffers={n:np.zeros(v.shape,v.dtype) for n,v in self.inputs.items()}
        def host_input(self,n):return self.buffers[n]
        def warm(self):self.run();return 'CPU_FAKE'
        def run(self):
            seen.append({n:sha(self.buffers[n]) for n in ('new_img','desire','traffic_convention','action_t')})
            return {'outputs':np.zeros(spec.output_shapes['outputs'],np.float32),
                    **{out:self.buffers[n].copy() for n,out in spec.state_pairs.items()}}
        def close(self):pass
    backend=types.SimpleNamespace(name='CPU_FAKE',suffix='.fixture',tag=lambda:'CPU_FAKE',describe=lambda:{'backend':'trt','device':'CPU_FAKE','runtime_version':'CPU_FAKE','carrot_host':'jetson'})
    with tempfile.TemporaryDirectory() as cache:
        host=S.EngineHost(EngineCache(Path(cache),backend));engine=Engine();host.loaded=host._warm(engine,spec);seen.clear()
        listener=TcpTransport.listen('127.0.0.1',0)
        emit({'port':listener.getsockname()[1],'module':S.__file__})
        transport,_=TcpTransport.accept(listener)
        session=S.Session(transport,host)
        try:session.serve_forever()
        except LinkError:pass
        finally:session.close();transport.close();listener.close();host.close()
        emit({'engine_input_hashes':seen,'openpilot_loaded':any(n.startswith('openpilot.') for n in sys.modules),'protocol':transport.protocol_version})


def client(root,port,shared_on):
    from jetlink.client import JetlinkClient
    from jetlink.spec import ModelSpec
    from jetlink import output_projection as projection
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from recorder_810e_support import selected, blob, receive_frame, fake_namespace
    from test_recorder_810e_shared import modules, source_warp
    link,shared=modules()
    # Point canonical imports used inside unchanged _serve_local to the exact
    # modules already loaded. Only OS diagnostics/Params are inert boundaries.
    for name,value in {
        'openpilot.common.params':types.SimpleNamespace(Params=lambda:types.SimpleNamespace(get_bool=lambda k:k=='IsOffroad')),
        'openpilot.common.runtime_diagnostics':types.SimpleNamespace(RuntimeDiagnostics=lambda *a:types.SimpleNamespace(record=lambda **k:None)),
        'openpilot.common.swaglog':types.SimpleNamespace(cloudlog=types.SimpleNamespace(event=lambda *a,**k:None)),
        'openpilot.selfdrive.modeld.jetlink.shared_input':shared,
    }.items():sys.modules[name]=value
    for name in ('openpilot','openpilot.selfdrive','openpilot.selfdrive.modeld','openpilot.selfdrive.modeld.jetlink','openpilot.common'):
        module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module
    sys.modules['openpilot.selfdrive.modeld.jetlink'].shared_input=shared
    os.environ['JETLINK_RAM_INPUT']='1' if shared_on else '0';os.environ['SEND_RAW_PRED']='1'
    remote=JetlinkClient.open_tcp('127.0.0.1',port)
    peer=remote.hello();remote.spec=remote.ensure_engine(
        '01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a',814591107)
    assert peer['protocol']==2
    active=threading.Event();active.set()
    daemon=dict(json=json,time=time,np=np,PacketReader=link.PacketReader,REQUEST=link.REQUEST,REPLY=link.REPLY,
        send=link.send,send_parts=link.send_parts,host_attached=active.is_set,
        HUD_USB_CAPABILITY='unused',NAVI_CAPABILITY='unused',PUMP_CAPABILITY='unused',
        update_affinity=lambda:None,publish=lambda *a,**k:None,check_loaded=lambda *a:None,
        log=logging.getLogger('fixture'))
    selected('openpilot/selfdrive/modeld/jetlink/daemon.py',['_serve_local'],daemon)
    listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);path=str(root/'ipc.sock')
    listener.bind(path);listener.listen(1);listener.settimeout(.05)
    errors=[]
    def serve():
        try:daemon['_serve_local'](listener,remote,peer,None,types.SimpleNamespace(sent=lambda sof:None))
        except Exception as e:errors.append(repr(e))
    thread=threading.Thread(target=serve);thread.start()
    sys.path.insert(0,str(root))
    # Fixture package contains the exact generated five modules.
    import capture810.hook as hook
    import capture810.recorder as recorder
    import capture810.dataset as dataset
    ns=fake_namespace(remote.spec);ns['Client']=link.Client
    pixels=np.zeros((2,6,128,256),np.uint8)
    patcher=types.SimpleNamespace(setitem=lambda mapping,key,value:mapping.__setitem__(key,value))
    cls,warp,gpu=source_warp(patcher,pixels);ns['Warp']=cls
    outputs=root/'capture';value=dict(output=str(outputs),frames=3,depth=4,capture_id='a'*32,
        source_model_sha=remote.spec.sha256,source_spec_sha=projection.SPEC_SHA256)
    state=hook.install(ns,arm_path='fixture',ticket_loader=lambda _:value,
        source_verifier=lambda _:None,recorder_factory=recorder.Recorder)
    assert state is not None
    local=link.Client(path)
    deadline=time.monotonic()+8
    while not state.recorder.ready and time.monotonic()<deadline:
        state.recorder.poll();time.sleep(.005)
    assert state.recorder.ready
    submitted=[]
    for index in range(3):
        transforms=receive_frame(ns,index+1)
        pixels[:]=17+index
        packed=np.zeros(remote.spec.packed_nelem,np.float32);packed[:12]=np.arange(12,dtype=np.float32)+index
        packed[1]=-0.0
        buffer=local.image_buffer()
        image=warp({'img':types.SimpleNamespace(data=b'1234'),'big_img':types.SimpleNamespace(data=b'5678')},
                   transforms,output_buffer=buffer)
        assert image is (buffer if shared_on else pixels)
        submitted.append({n:sha(a) for n,a in zip(('new_img','desire','traffic_convention','action_t'),
                         (image,packed[:8],packed[8:10],packed[10:12]))})
        result=local.infer(image,packed,index+1)
        assert result.shape==(18580,)
        time.sleep(.02)
    local.close();active.clear();thread.join(2);listener.close();remote.close()
    state.recorder.close(timeout=10)
    assert not thread.is_alive() and not errors
    with dataset.Dataset(outputs) as saved:
        recorded=[{n:sha(a) for n,a in saved.ort_feeds(i).items()} for i in range(len(saved))]
        assert submitted==recorded
        emit({'recorded_hashes':recorded,'frames':len(saved),'dataset_digest':saved.manifest['dataset_digest'],
              'shared':shared_on,'daemon_source':'exact810e._serve_local','protocol':2,'module':JetlinkClient.__module__})


if __name__=='__main__':
    mode,root=sys.argv[1:3];root=Path(root)
    sys.path.insert(0,str(root/'third_party/jetlink'))
    # Keep existing optimization knobs OFF in this deterministic baseline test.
    for key in ('CARROT_TRT_DIRECT_MAP','CARROT_TRT_NATIVE_IMAGE','CARROT_TRT_DEVICE_STATE','CARROT_TRT_INPUT_FASTPATH','CARROT_JETLINK_AIO_WRITE'):
        os.environ[key]='0'
    if mode=='server':server(root)
    else:client(root,int(sys.argv[3]),sys.argv[4]=='1')
