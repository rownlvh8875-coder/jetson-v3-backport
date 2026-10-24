"""Separate namespaces, exact060 sources, POSIX sockets and native file AIO.

Actual FfsTransport framing/bounded-send executes on socket-backed physical I/O;
native Writer executes on a private regular file before byte-exact socket relay.
Actual ReadAheadTransport, CarrotSession.handle, Session and EngineHost execute.
QCOM Warp execution and GPU engine are deterministic CPU_FAKE. No USB/device.
"""
import ast
import hashlib
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


def selected(root,name,names,ns):
    tree=ast.parse((root/name).read_bytes())
    nodes=[n for n in tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree),name,'exec'),ns)
    return ns


def load_modules(root,spec):
    shared=types.ModuleType('exact060_shared')
    exec(compile((root/'openpilot/selfdrive/modeld/jetlink/shared_input.py').read_bytes(),'shared_input.py','exec'),shared.__dict__)
    from jetlink import output_projection as projection
    contracts=dict(ModelSpec=type(spec),DEFAULT_SPEC=spec,JETSON_SPEC=spec,re=__import__('re'),math=__import__('math'),
        OUTPUT_WIDTHS={'lane_lines':(528,),'lane_lines_prob':(8,),'road_edges':(264,),'meta':(55,),
                      'desire_pred':(32,),'pose':(12,),'wide_from_device_euler':(6,),
                      'road_transform':(12,),'plan':(990,4955),'lead':(144,102),'lead_prob':(3,),'desire_state':(8,)})
    selected(root,'openpilot/selfdrive/modeld/jetlink/contracts.py',['slice_range','validate_model_spec'],contracts)
    link=types.ModuleType('exact060_link')
    link.__dict__.update(shared_input=shared,ModelSpec=type(spec),projection=projection,
        DEFAULT_SPEC=spec,validate_model_spec=contracts['validate_model_spec'])
    tree=ast.parse((root/'openpilot/selfdrive/modeld/jetlink/link.py').read_bytes())
    tree.body=[n for n in tree.body if not(isinstance(n,ast.ImportFrom) and n.module.startswith(('openpilot.','jetlink')))]
    exec(compile(tree,'exact060-link.py','exec'),link.__dict__)
    return link,shared


def source_warp(root,pixels):
    class Result:
        shape=pixels.shape
        def numpy(self):return pixels
        def _buffer(self):return self
        def copyout(self,dest):dest[:]=memoryview(pixels).cast('B')
    sys.modules['tinygrad']=types.SimpleNamespace(Tensor=types.SimpleNamespace(from_blob=lambda *a,**k:object()))
    ns=selected(root,'openpilot/selfdrive/modeld/jetlink/model.py',['Warp'],dict(np=np,time=time))
    cls=ns['Warp'];warp=object.__new__(cls)
    warp.size=4;warp.blobs={};warp.inputs={};warp.transforms={k:np.eye(3,dtype=np.float32) for k in ('tfm','big_tfm')}
    warp.run_warp=lambda **kw:Result()
    return cls,warp


def server(root):
    from jetlink.server import session as S
    from jetlink.server.cache import EngineCache
    from jetlink.spec import ModelSpec
    from jetlink.transport.tcp import TcpTransport
    from jetlink.transport.base import LinkError
    from jetlink import protocol as P,request_chunks as C
    from host_reader import ReadAheadTransport
    # Values from exact060 hud_wifi/hud_protocol/hud_navi/wifi_protocol. Those
    # non-inference handlers stay inactive; their OS/network workers never start.
    ns=selected(root,'tools/jetlink/server.py',['CarrotSession'],dict(Session=S.Session,P=P,request_chunks=C,
        HUD_WIFI_REQUEST=0x4020,HUD_MESSAGE=0x4000,NAVI_MESSAGE=0x4001,WIFI_MESSAGE=0x4002))
    seen=[];packed=[];requests=[]
    spec=ModelSpec.from_dict(json.loads((root/'openpilot/selfdrive/modeld/jetlink/jetson_model.json').read_bytes()))
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
            packed.append(sha(np.concatenate([self.buffers[n].reshape(-1) for n in spec.packed_shapes])))
            return {'outputs':np.zeros(spec.output_shapes['outputs'],np.float32),
                    **{out:self.buffers[n].copy() for n,out in spec.state_pairs.items()}}
        def close(self):pass
    class Session(ns['CarrotSession']):
        def __init__(self,t,host):
            S.Session.__init__(self,t,host)
            self.request_chunks=C.Receiver();self.telemetry.health=None
        def _send_json(self,kind,seq,obj,flags=0):
            # Metadata/native host identity boundary only; no client/receiver/
            # inference function is replaced. Actual capability descriptor.
            if kind==P.Msg.HELLO_RESP:obj={**obj,'carrot_host':'jetson',C.CAPABILITY:C.descriptor()}
            return S.Session._send_json(self,kind,seq,obj,flags)
        def _infer(self,loaded,msg):
            requests.append(sha(msg.payload));return super()._infer(loaded,msg)
        def close(self):S.Session.close(self)
    backend=types.SimpleNamespace(name='CPU_FAKE',suffix='.fixture',tag=lambda:'CPU_FAKE',describe=lambda:{'backend':'trt','device':'CPU_FAKE','runtime_version':'CPU_FAKE','carrot_host':'jetson'})
    with tempfile.TemporaryDirectory() as cache:
        host=S.EngineHost(EngineCache(Path(cache),backend));host.loaded=host._warm(Engine(),spec);seen.clear();packed.clear()
        listener=TcpTransport.listen('127.0.0.1',0)
        emit({'port':listener.getsockname()[1],'session_module':S.__file__})
        t,_=TcpTransport.accept(listener);t.rx_align=P.GADGET_TX_ALIGN
        reader=ReadAheadTransport(t);session=Session(reader,host)
        try:session.serve_forever()
        except LinkError:pass
        finally:session.close();reader.close();t.close();listener.close();host.close()
        emit({'engine_hashes':seen,'engine_packed_hashes':packed,'session_request_hashes':requests,
              'executions':len(seen),'protocol':t.protocol_version,'openpilot_loaded':any(n.startswith('openpilot.') for n in sys.modules)})


def client(root,port,shared_on,chunks,compact):
    from jetlink.client import JetlinkClient
    from jetlink import protocol as P,request_chunks as C,output_projection as projection
    from jetlink.transport.base import StreamTransport,LinkError,LinkTimeout
    from jetlink.transport.ffs import FfsTransport
    from jetlink.transport.request_writer import Writer,library
    class SocketFfs(FfsTransport):
        def __init__(self):
            StreamTransport.__init__(self)
            self.sock=socket.create_connection(('127.0.0.1',port))
            self._write_guard=types.SimpleNamespace(arm=lambda budget:True,disarm=lambda:True)
            self._request_writer=None;self.logical=[];self.chunked=0;self.native_writes=0;self.compact=0
            self.current_wire=None
        def _prepare_bounded_requests(self):
            self.file=tempfile.TemporaryFile();self.native=Writer(self.file.fileno(),library(),regular=True);self.offset=0
            def relay(packets,budget):
                self.native.send(packets,budget)
                length=sum(map(len,packets));data=os.pread(self.file.fileno(),length,self.offset);self.offset+=length
                assert data==b''.join(packets)
                assert self.current_wire is not None
                self.current_wire.append(data)
                self.native_writes+=1;self.chunked+=1
                # Repeat each complete physical frame. Actual host reassembly
                # must still yield exactly one EngineHost invocation per attempt.
                pos=0
                for packet in packets:
                    part=data[pos:pos+len(packet)];pos+=len(packet)
                    self.sock.sendall(part+part)
            self._request_writer=types.SimpleNamespace(send=relay)
            return True
        def send(self,kind,seq,parts=(),flags=0,timeout=None):
            parts=tuple(parts)
            if kind==P.Msg.INFER_REQ:
                self.logical.append(sha(b''.join(parts)))
                self.compact+=int(bool(P.unpack_infer_req(b''.join(parts))[1] & (1<<3)))
                self.current_wire=[]
            try:return super().send(kind,seq,parts,flags,timeout)
            finally:
                if kind==P.Msg.INFER_REQ:
                    self.last_request_wire=b''.join(self.current_wire);self.current_wire=None
        def _write(self,bufs):
            raw=b''.join(bufs)
            if self.current_wire is not None:self.current_wire.append(raw)
            self.sock.sendall(raw);return len(raw)
        def _read_into(self,dest,timeout):
            self.sock.settimeout(timeout)
            try:n=self.sock.recv_into(dest)
            except socket.timeout as e:raise LinkTimeout('socket fixture deadline') from e
            if not n:raise LinkError('fixture socket closed')
            return n
        def close(self):
            if hasattr(self,'native'):self.native.close();self.file.close()
            self.sock.close()
    t=SocketFfs();remote=JetlinkClient(t,allow_request_chunks=chunks)
    hello=remote.hello();remote.spec=remote.ensure_engine(projection.MODEL_SHA256,814591107)
    assert hello['protocol']==2 and hello['carrot_request_chunks_active'] is chunks
    link,shared=load_modules(root,remote.spec)
    for name in ('openpilot','openpilot.selfdrive','openpilot.selfdrive.modeld','openpilot.selfdrive.modeld.jetlink','openpilot.common'):
        module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module
    for name,value in {
        'openpilot.common.params':types.SimpleNamespace(Params=lambda:types.SimpleNamespace(get_bool=lambda k:k=='IsOffroad')),
        'openpilot.common.runtime_diagnostics':types.SimpleNamespace(RuntimeDiagnostics=lambda *a:types.SimpleNamespace(record=lambda **k:None)),
        'openpilot.common.swaglog':types.SimpleNamespace(cloudlog=types.SimpleNamespace(event=lambda *a,**k:None)),
        'openpilot.selfdrive.modeld.jetlink.shared_input':shared}.items():sys.modules[name]=value
    sys.modules['openpilot.selfdrive.modeld.jetlink'].shared_input=shared
    os.environ['JETLINK_RAM_INPUT']='1' if shared_on else '0';os.environ['SEND_RAW_PRED']='1'
    active=threading.Event();active.set()
    daemon=dict(json=json,time=time,np=np,PacketReader=link.PacketReader,REQUEST=link.REQUEST,REPLY=link.REPLY,
        send=link.send,send_parts=link.send_parts,host_attached=active.is_set,
        HUD_USB_CAPABILITY='unused',NAVI_CAPABILITY='unused',PUMP_CAPABILITY='unused',
        update_affinity=lambda:None,publish=lambda *a,**k:None,check_loaded=lambda *a:None,log=logging.getLogger('fixture'))
    selected(root,'openpilot/selfdrive/modeld/jetlink/daemon.py',['_serve_local'],daemon)
    listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);path=str(root/'ipc.sock')
    listener.bind(path);listener.listen(1);listener.settimeout(.05);errors=[]
    def serve():
        try:daemon['_serve_local'](listener,remote,hello,None,types.SimpleNamespace(sent=lambda sof:None))
        except Exception as e:errors.append(repr(e))
    thread=threading.Thread(target=serve);thread.start()
    sys.path.insert(0,str(root));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from recorder_810e_support import fake_namespace,receive_frame
    import capture060.hook as hook
    import capture060.recorder as recorder
    import capture060.dataset as dataset
    ns=fake_namespace(remote.spec);ns['Client']=link.Client
    pixels=np.zeros((2,6,128,256),np.uint8);cls,warp=source_warp(root,pixels);ns['Warp']=cls
    output=root/'capture'
    value=dict(output=str(output),frames=3,depth=4,capture_id='c'*32,
               source_model_sha=remote.spec.sha256,source_spec_sha=projection.SPEC_SHA256)
    state=hook.install(ns,arm_path='fixture',ticket_loader=lambda _:value,source_verifier=lambda _:None,recorder_factory=recorder.Recorder)
    assert state is not None
    local=link.Client(path);deadline=time.monotonic()+8
    while not state.recorder.ready and time.monotonic()<deadline:state.recorder.poll();time.sleep(.005)
    assert state.recorder.ready
    submitted=[];packed_hashes=[]
    for index in range(3):
        transforms=receive_frame(ns,index+1);pixels[:]=np.arange(393216,dtype=np.uint8).reshape(pixels.shape)+index
        packed=np.arange(remote.spec.packed_nelem,dtype=np.float32)%251
        packed[:12]=np.arange(12,dtype=np.float32)+index;packed[1]=-0.0
        if not compact:packed[12]=-.0  # Noncanonical map bit forces exact old full-float codec.
        buffer=local.image_buffer()
        image=warp({'img':types.SimpleNamespace(data=b'1234'),'big_img':types.SimpleNamespace(data=b'5678')},transforms,output_buffer=buffer)
        assert image is (buffer if shared_on else pixels)
        submitted.append({n:sha(a) for n,a in zip(('new_img','desire','traffic_convention','action_t'),(image,packed[:8],packed[8:10],packed[10:12]))})
        packed_hashes.append(sha(packed));result=local.infer(image,packed,index+1)
        assert result.shape==(18580,)
        # Replay the whole request after its response, not only adjacent chunks
        # while assembly is in progress. It must never advance recurrence again.
        t.sock.sendall(t.last_request_wire)
        time.sleep(.02)
    local.close();active.clear();thread.join(2);listener.close();remote.close();state.recorder.close(timeout=10)
    assert not thread.is_alive() and not errors,errors
    with dataset.Dataset(output) as saved:
        recorded=[{n:sha(a) for n,a in saved.ort_feeds(i).items()} for i in range(len(saved))]
        emit({'recorded_hashes':recorded,'submitted_hashes':submitted,'packed_hashes':packed_hashes,
              'logical_request_hashes':t.logical,'frames':len(saved),'chunked_requests':t.chunked,
              'native_writes':t.native_writes,'protocol':2,'negotiated_chunks':hello['carrot_request_chunks_active'],
              'compact_requests':t.compact,'dataset_digest':saved.manifest['dataset_digest']})


if __name__=='__main__':
    mode,root=sys.argv[1:3];root=Path(root)
    sys.path.insert(0,str(root/'third_party/jetlink'));sys.path.insert(0,str(root/'tools/jetlink'))
    for key in ('CARROT_TRT_DIRECT_MAP','CARROT_TRT_NATIVE_IMAGE','CARROT_TRT_DEVICE_STATE','CARROT_TRT_INPUT_FASTPATH','CARROT_JETLINK_AIO_WRITE'):
        os.environ[key]='0'
    if mode=='server':server(root)
    else:client(root,int(sys.argv[3]),*(v=='1' for v in sys.argv[4:7]))
