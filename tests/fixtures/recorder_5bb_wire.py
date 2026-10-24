"""5bb JoiningModel/fill_inputs through the real transport input boundary.

Actual FfsTransport framing/bounded-send executes on loopback sockets;
native Writer executes on a private regular file before byte-exact socket relay.
Actual ReadAheadTransport, CarrotSession.handle, Session and EngineHost execute.
Regular-file AIO bytes are checked before relay: identity, not USB timing.
Native deferred ownership is tested separately. The historical hook is tested
unchanged. A separate boundary_probe replaces ONLY the fixture's infer wrapper
to locate the valid observation point; it is not an installable recorder.
Synthetic ticket/source-verifier injection isolates the API review. The fixture
retains the a559 dataset binding; it cannot attest a deployable5bb capture.
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
    shared=types.ModuleType('exact5bb_shared')
    exec(compile((root/'openpilot/selfdrive/modeld/jetlink/shared_input.py').read_bytes(),'shared_input.py','exec'),shared.__dict__)
    from jetlink import output_projection as projection, deferred_map
    contracts=dict(ModelSpec=type(spec),DEFAULT_SPEC=spec,JETSON_SPEC=spec,re=__import__('re'),math=__import__('math'),
        OUTPUT_WIDTHS={'lane_lines':(528,),'lane_lines_prob':(8,),'road_edges':(264,),'meta':(55,),
                      'desire_pred':(32,),'pose':(12,),'wide_from_device_euler':(6,),
                      'road_transform':(12,),'plan':(990,4955),'lead':(144,102),'lead_prob':(3,),'desire_state':(8,)})
    selected(root,'openpilot/selfdrive/modeld/jetlink/contracts.py',['slice_range','validate_model_spec'],contracts)
    link=types.ModuleType('exact5bb_link')
    link.__dict__.update(shared_input=shared,ModelSpec=type(spec),projection=projection,deferred_map=deferred_map,
        DEFAULT_SPEC=spec,validate_model_spec=contracts['validate_model_spec'])
    tree=ast.parse((root/'openpilot/selfdrive/modeld/jetlink/link.py').read_bytes())
    tree.body=[n for n in tree.body if not(isinstance(n,ast.ImportFrom) and n.module.startswith(('openpilot.','jetlink')))]
    exec(compile(tree,'exact5bb-link.py','exec'),link.__dict__)
    return link,shared


def source_warp(root,pixels,calls):
    class Result:
        shape=pixels.shape
        def numpy(self):calls.append('read');return pixels
        def _buffer(self):return self
        def copyout(self,dest):calls.append('read');dest[:]=memoryview(pixels).cast('B')
    sys.modules['tinygrad']=types.SimpleNamespace(Tensor=types.SimpleNamespace(from_blob=lambda *a,**k:object()))
    ns=selected(root,'openpilot/selfdrive/modeld/jetlink/model.py',['Warp'],dict(np=np,time=time))
    cls=ns['Warp'];warp=object.__new__(cls)
    warp.size=4;warp.blobs={};warp.inputs={};warp.transforms={k:np.eye(3,dtype=np.float32) for k in ('tfm','big_tfm')}
    def submit(**kw):calls.append('submit');return Result()
    warp.run_warp=submit
    return cls,warp


def server(root):
    from jetlink.server import session as S
    from jetlink.server.cache import EngineCache
    from jetlink.spec import ModelSpec
    from jetlink.transport.tcp import TcpTransport
    from jetlink.transport.base import LinkError
    from jetlink import protocol as P,request_chunks as C,deferred_map,packed_codec,output_projection
    from host_reader import ReadAheadTransport
    # Values from exact5bb hud_wifi/hud_protocol/hud_navi/wifi_protocol. Those
    # non-inference handlers stay inactive; their OS/network workers never start.
    ns=selected(root,'tools/jetlink/server.py',['CarrotSession'],dict(Session=S.Session,P=P,json=json,request_chunks=C,deferred_map=deferred_map,packed_codec=packed_codec,output_projection=output_projection,
        LinkError=LinkError,Message=__import__('jetlink.transport.base',fromlist=['Message']).Message,
        HUD_WIFI_REQUEST=0x4020,HUD_MESSAGE=0x4000,NAVI_MESSAGE=0x4001,WIFI_MESSAGE=0x4002))
    seen=[];packed=[];requests=[];maps=[];navigation=[];generations=[]
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
            maps.append(sha(self.buffers['nav_map']));navigation.append(sha(self.buffers['navigation']))
            generations.append(float(self.buffers['state_feat_q'].flat[0]))
            return {'outputs':np.zeros(spec.output_shapes['outputs'],np.float32),
                    **{out:self.buffers[n]+1 for n,out in spec.state_pairs.items()}}
        def close(self):pass
    class Session(ns['CarrotSession']):
        def __init__(self,t,host):
            S.Session.__init__(self,t,host)
            self.request_chunks=C.Receiver();self.telemetry.health=None
            self.deferred_maps=deferred_map.Receiver();self.deferred_negotiated=False
        def _send_json(self,kind,seq,obj,flags=0):
            # Metadata/native host identity boundary only; no client/receiver/
            # inference function is replaced. Actual capability descriptor.
            if kind==P.Msg.HELLO_RESP:obj={**obj,'carrot_host':'jetson',C.CAPABILITY:C.descriptor(),deferred_map.CAPABILITY:deferred_map.descriptor()}
            return S.Session._send_json(self,kind,seq,obj,flags)
        def _infer(self,loaded,msg):
            requests.append(sha(msg.payload));return super()._infer(loaded,msg)
        def close(self):S.Session.close(self)
    backend=types.SimpleNamespace(name='CPU_FAKE',suffix='.fixture',tag=lambda:'CPU_FAKE',describe=lambda:{'backend':'trt','device':'CPU_FAKE','runtime_version':'CPU_FAKE','carrot_host':'jetson'})
    with tempfile.TemporaryDirectory() as cache:
        host=S.EngineHost(EngineCache(Path(cache),backend));host.loaded=host._warm(Engine(),spec);seen.clear();packed.clear();maps.clear();navigation.clear();generations.clear()
        listener=TcpTransport.listen('127.0.0.1',0)
        emit({'port':listener.getsockname()[1],'session_module':S.__file__})
        t,_=TcpTransport.accept(listener);t.rx_align=P.GADGET_TX_ALIGN
        reader=ReadAheadTransport(t);session=Session(reader,host)
        try:session.serve_forever()
        except LinkError:pass
        finally:session.close();reader.close();t.close();listener.close();host.close()
        emit({'engine_hashes':seen,'engine_packed_hashes':packed,'session_request_hashes':requests,
              'map_hashes':maps,'navigation_hashes':navigation,'state_generations':generations,
              'executions':len(seen),'protocol':t.protocol_version,'openpilot_loaded':any(n.startswith('openpilot.') for n in sys.modules)})


def client(root,port,shared_on,chunks,compact_reply,overlap,defer_nav,quantum,completion_deferred,hook_mode):
    from jetlink.client import JetlinkClient
    from jetlink import protocol as P,request_chunks as C,output_projection as projection,deferred_map
    from jetlink.transport.base import StreamTransport,LinkError,LinkTimeout
    from jetlink.transport.ffs import FfsTransport
    from jetlink.transport.request_writer import Writer,library
    class SocketFfs(FfsTransport):
        def __init__(self):
            StreamTransport.__init__(self)
            self.sock=socket.create_connection(('127.0.0.1',port))
            self._write_guard=types.SimpleNamespace(arm=lambda budget:True,disarm=lambda:True)
            self._request_writer=None;self.logical=[];self.chunked=0;self.native_batches=0;self.compact=0
            self.current_wire=None
        def _prepare_bounded_requests(self):
            self.file=tempfile.TemporaryFile();self.native=Writer(self.file.fileno(),library(),regular=True,deferred=completion_deferred,quantum=quantum);self.offset=0
            def relay(packets,budget):
                self.native.send(packets,budget)
                self.native.poll()
                length=sum(map(len,packets));data=os.pread(self.file.fileno(),length,self.offset);self.offset+=length
                assert data==b''.join(packets)
                if self.current_wire is not None:self.current_wire.append(data)
                self.native_batches+=1;self.chunked+=1
                # Repeat each complete logical envelope. Host reassembly
                # must still yield exactly one EngineHost invocation per attempt.
                pos=0
                for packet in packets:
                    part=data[pos:pos+len(packet)];pos+=len(packet)
                    self.sock.sendall(part+part)
            self._request_writer=types.SimpleNamespace(send=relay,deferred=completion_deferred,quantum=quantum,poll=self.native.poll)
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
    # Evaluate the actual daemon.main keyword expression, without executing its
    # OS/USB launcher or changing any Params. No duplicated switch semantics.
    tree=ast.parse((root/'openpilot/selfdrive/modeld/jetlink/daemon.py').read_bytes())
    option,=[kw.value for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
             and n.func.id=='JetlinkClient' for kw in n.keywords if kw.arg=='allow_request_chunks']
    allowed=eval(compile(ast.Expression(option),'<reviewed-5bb-switch>','eval'),{'os':os})
    assert allowed is chunks
    t=SocketFfs();remote=JetlinkClient(t,allow_request_chunks=allowed,allow_output_projection=True)
    hello=remote.hello();remote.spec=remote.ensure_engine(projection.MODEL_SHA256,814591107)
    # Observe actual stages; assertions never replace their behavior.
    def instrument(name):
        original=getattr(remote,name)
        def call(*args,**kwargs):
            if name=='infer_begin': current=np.frombuffer(memoryview(args[1]).cast('B'),dtype=np.float32)
            else: current=joining.packed
            first=current[:12].copy();value=original(*args,**kwargs)
            assert current[:12].tobytes()==first.tobytes()
            sentinel_phases.append(dict(phase=name,sha256=sha(first)))
            return value
        setattr(remote,name,call)
    for stage in ('infer_begin','flush_map','infer_end'):instrument(stage)
    assert hello['protocol']==2 and hello['carrot_request_chunks_active'] is chunks
    link,shared=load_modules(root,remote.spec)
    for name in ('openpilot','openpilot.selfdrive','openpilot.selfdrive.modeld','openpilot.selfdrive.modeld.jetlink','openpilot.common'):
        module=types.ModuleType(name);module.__path__=[];sys.modules[name]=module
    diagnostic=types.ModuleType('5bb_diagnostics')
    exec(compile((root/'openpilot/common/runtime_diagnostics.py').read_bytes(),'runtime_diagnostics.py','exec'),diagnostic.__dict__)
    events=[]
    for name,value in {
        'openpilot.common.params':types.SimpleNamespace(Params=lambda:types.SimpleNamespace(get_bool=lambda k:k=='IsOffroad')),
        'openpilot.common.runtime_diagnostics':types.SimpleNamespace(RuntimeDiagnostics=lambda *a,**kw:diagnostic.RuntimeDiagnostics(*a,interval=0,**kw)),
        'openpilot.common.swaglog':types.SimpleNamespace(cloudlog=types.SimpleNamespace(event=lambda *a,**k:events.append(k),warning=lambda *a:None,exception=lambda *a:None)),
        'openpilot.selfdrive.modeld.jetlink.shared_input':shared}.items():sys.modules[name]=value
    sys.modules['openpilot.selfdrive.modeld.jetlink'].shared_input=shared
    os.environ['JETLINK_RAM_INPUT']='1' if shared_on else '0';os.environ.pop('SEND_RAW_PRED',None)
    active=threading.Event();active.set()
    daemon=dict(json=json,time=time,np=np,PacketReader=link.PacketReader,REQUEST=link.REQUEST,REPLY=link.REPLY,
        send=link.send,send_parts=link.send_parts,host_attached=active.is_set,
        HUD_USB_CAPABILITY='unused',NAVI_CAPABILITY='unused',PUMP_CAPABILITY='unused',deferred_map=deferred_map,
        update_affinity=lambda:None,publish=lambda *a,**k:None,check_loaded=lambda *a:None,log=logging.getLogger('fixture'))
    selected(root,'openpilot/selfdrive/modeld/jetlink/daemon.py',['_serve_local'],daemon)
    listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);path=str(root/'ipc.sock')
    listener.bind(path);listener.listen(1);listener.settimeout(.05);errors=[]
    def serve():
        try:daemon['_serve_local'](listener,remote,hello,None,types.SimpleNamespace(sent=lambda sof:None))
        except Exception as e:errors.append(repr(e))
    thread=threading.Thread(target=serve,daemon=True);thread.start()
    sys.path.insert(0,str(root));sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
    from recorder_810e_support import fake_namespace,receive_frame
    import capture5bb.hook as hook
    import capture5bb.recorder as recorder
    import capture5bb.dataset as dataset
    ns=fake_namespace(remote.spec);ns['Client']=link.Client
    calls=[];orders=[];warp_outputs=[];buffers=[];observed=[];submitted=[];packed_hashes=[];replies=[];maps=[];navigation=[];map_used=[];sentinel_phases=[]
    pixels=np.zeros((2,6,128,256),np.uint8);cls,warp=source_warp(root,pixels,calls);ns['Warp']=cls
    original_warp=cls.__call__
    def traced_warp(self,*args,**kwargs):
        calls.append('warp_enter')
        assert kwargs['output_buffer'] is buffers[-1]
        assert (kwargs['prepare'] is not None) is overlap
        result=original_warp(self,*args,**kwargs)
        warp_outputs.append(result);calls.append('warp_return');return result
    cls.__call__=traced_warp
    original_buffer=link.Client.image_buffer
    def image_buffer(self):
        calls.append('reserve');value=original_buffer(self);buffers.append(value);return value
    link.Client.image_buffer=image_buffer
    original_infer=link.Client.infer
    def checked_infer(self,image,packed,frame,reset=False,source_sof=0,**kwargs):
        calls.append('infer')
        assert image is warp_outputs[-1] and image is (buffers[-1] if shared_on else pixels)
        expected=['reserve','warp_enter','submit','prepare','read','warp_return','observe','infer'] if overlap else ['prepare','reserve','warp_enter','submit','read','warp_return','observe','infer']
        assert calls==expected,calls
        hashes={n:sha(a) for n,a in zip(('new_img','desire','traffic_convention','action_t'),(image,packed[:8],packed[8:10],packed[10:12]))}
        assert hashes==observed[-1]
        submitted.append(hashes);packed_hashes.append(sha(packed));orders.append(list(calls))
        before=packed.copy()
        maps.append(sha(joining.views['nav_map']));navigation.append(sha(joining.views['navigation']))
        result=original_infer(self,image,packed,frame,reset,source_sof=source_sof,**kwargs)
        assert packed.tobytes()==before.tobytes()
        map_used.append(remote.last_map_used)
        assert self.shared is None or not self.shared.busy
        replies.append(result.size);return result
    link.Client.infer=checked_infer
    class TrackingRecorder(recorder.Recorder):
        def observe(self,image,desire,traffic,action,metadata):
            calls.append('observe')
            assert image is warp_outputs[-1]
            before={n:sha(a) for n,a in zip(('new_img','desire','traffic_convention','action_t'),(image,desire,traffic,action))}
            value=super().observe(image,desire,traffic,action,metadata)
            assert before=={n:sha(a) for n,a in zip(('new_img','desire','traffic_convention','action_t'),(image,desire,traffic,action))}
            observed.append(before);return value
    output=root/'capture'
    value=dict(output=str(output),frames=5,depth=4,capture_id='c'*32,
               source_model_sha=remote.spec.sha256,source_spec_sha=projection.SPEC_SHA256)
    state=hook.install(ns,arm_path='fixture',ticket_loader=lambda _:value,source_verifier=lambda _:None,recorder_factory=TrackingRecorder)
    assert state is not None
    if hook_mode=='boundary_probe':
        # Experimental observation probe only. Bypass the historical wrapper's
        # closed signature; retain its actual _Capture.observe and metadata.
        # This is evidence that a future reviewed fix is possible, not reuse.
        historical=link.Client.infer
        def probe(self,image,packed,frame,reset=False,source_sof=0,**kwargs):
            state.observe(self,image,packed,reset)
            return historical.__wrapped__(self,image,packed,frame,reset,source_sof=source_sof,**kwargs)
        link.Client.infer=probe
    local=link.Client(path);deadline=time.monotonic()+8
    while not state.recorder.ready and time.monotonic()<deadline:state.recorder.poll();time.sleep(.005)
    assert state.recorder.ready and local.project_output is compact_reply
    fill_ns=selected(root,'openpilot/selfdrive/modeld/jetlink/inputs.py',['fill_inputs'],dict(np=np))
    def fill(*args):calls.append('prepare');return fill_ns['fill_inputs'](*args)
    parse_ns=selected(root,'openpilot/selfdrive/modeld/jetlink/contracts.py',['parse_outputs'],dict(projection=projection))
    model_ns=selected(root,'openpilot/selfdrive/modeld/jetlink/model.py',['JoiningModel'],dict(np=np,os=os,time=time,fill_inputs=fill,parse_outputs=parse_ns['parse_outputs'],model_name=lambda spec:'N16-fixture'))
    joining=object.__new__(model_ns['JoiningModel'])
    joining.preparation=joining.connection=None;joining.warp=warp;joining.client=local
    joining.spec=remote.spec;joining.packed=np.zeros(remote.spec.packed_nelem,np.float32)
    joining.views={n:a.reshape(shape) for (n,shape),a in zip(remote.spec.packed_shapes.items(),np.split(joining.packed,np.cumsum(remote.spec.packed_sizes[:-1])),strict=True)}
    joining.prev_desire=np.zeros(8,np.float32);joining.small_runs=3;joining.ready=joining.join_allowed=True
    joining.next_join=joining.next_status=joining.frame=joining.source_sof=joining.last_slow_log=0
    joining.active=False;joining.reset=True;joining.error=''
    def no_fallback(*a):raise AssertionError('unexpected local fallback: '+joining.error+' daemon='+repr(errors))
    joining.small=types.SimpleNamespace(run=no_fallback)
    joining.parser=types.SimpleNamespace(parse_outputs=lambda outputs:dict(keys=sorted(outputs)))
    pulse_values=[]
    for index,pulse in enumerate([0,1,1,0,1]):
        pixels[:]=np.arange(393216,dtype=np.uint8).reshape(pixels.shape)+index
        transforms={k:np.eye(3,dtype=np.float32)*(index+1) for k in ('img','big_img')}
        main=types.SimpleNamespace(frame_id=100+index,timestamp_sof=1_000_000_000+index*50_000_000)
        extra=types.SimpleNamespace(frame_id=200+index,timestamp_sof=main.timestamp_sof-3_000_000)
        camera=ns['CameraGapTrace']();camera.result=(object(),main,object(),extra)
        assert camera.receive(object(),object()) is camera.result
        joining.source_sof=main.timestamp_sof
        inputs={'desire_pulse':np.eye(8,dtype=np.float32)[1]*pulse,
                'traffic_convention':np.eye(2,dtype=np.float32)[index%2].reshape(1,2),
                'action_t':np.array([[index/4,(4-index)/4]],np.float32),
                'nav_map':np.full((256,256),17+index,np.float32),
                'navigation':(np.arange(47,dtype=np.float32)+index*100).reshape(1,47)}
        stamp=time.monotonic_ns();joining.set_nav_metadata((7,stamp,stamp+500_000_000))
        calls.clear()
        try:
            result=joining.run({'img':types.SimpleNamespace(data=b'1234'),'big_img':types.SimpleNamespace(data=b'5678')},transforms,inputs,False)
        except AssertionError:
            if hook_mode!='historical' or not defer_nav:raise
            assert index==0 and "unexpected keyword argument 'nav_metadata'" in joining.error
            assert observed==submitted==[] and calls.count('prepare')==1
            assert calls.count('infer')==calls.count('observe')==0
            local.close();active.clear();thread.join(2);listener.close();remote.close();state.recorder.close(timeout=10)
            assert not thread.is_alive() and not errors,errors
            emit(dict(status='RECORDER_API_INCOMPATIBLE',original_infer_calls=calls.count('infer'),
                      observer_calls=calls.count('observe'),frames=len(observed),
                      error="unexpected keyword argument 'nav_metadata'",hook_mode=hook_mode))
            return
        assert isinstance(result,dict) and joining.client is local and joining.error==''
        pulse_values.append(float(joining.views['desire'][1]))
        assert len(buffers)==index+1 and len(warp_outputs)==index+1
        # Replay the whole request after its response, not only adjacent chunks
        # while assembly is in progress. It must never advance recurrence again.
        t.sock.sendall(t.last_request_wire)
        time.sleep(.02)
    local.close();active.clear();thread.join(2);listener.close();remote.close();state.recorder.close(timeout=10)
    assert not thread.is_alive() and not errors,errors
    assert pulse_values==[0.,1.,0.,0.,1.]
    with dataset.Dataset(output) as saved:
        recorded=[{n:sha(a) for n,a in saved.ort_feeds(i).items()} for i in range(len(saved))]
        scalar_hashes=[sha(np.concatenate([saved.ort_feeds(i)[n].reshape(-1) for n in ('desire','traffic_convention','action_t')])) for i in range(len(saved))]
        assert len(set(scalar_hashes))==5
        for i in range(5):
            row=saved.record(i)
            assert int(row['main_frame_id'])==100+i and int(row['extra_frame_id'])==200+i
            assert int(row['flags'])==int(i==0)
            assert np.array_equal(row['transforms'],np.stack([np.eye(3,dtype=np.float32)*(i+1)]*2))
        emit({'recorded_hashes':recorded,'submitted_hashes':submitted,'packed_hashes':packed_hashes,
              'logical_request_hashes':t.logical,'map_hashes':maps,'navigation_hashes':navigation,
              'map_used':map_used,'sentinel_phases':sentinel_phases,'defer_nav':local.deferred_nav,
              'quantum':quantum,'completion_deferred':completion_deferred,'frames':len(saved),'chunked_requests':t.chunked,
              'native_batches':t.native_batches,'protocol':2,'negotiated_chunks':hello['carrot_request_chunks_active'],
              'nav_u8_requests':t.compact,'dataset_digest':saved.manifest['dataset_digest'],
              'scalar_hashes':scalar_hashes,'orders':orders,'desire_pulses':pulse_values,'reply_elements':replies,
              'hook_mode':hook_mode,'compact_reply':local.project_output,'diagnostics_events':len(events),'single_reservation_per_frame':len(buffers)==5,
              'diagnostics_peak_correlated':len(events)==5 and [e['peak_sample']['context']['frame_id'] for e in events]==list(range(1,6))
                  and all(e['peak_sample']['context']['usb_seq']==e['usb_seq'] for e in events)})


if __name__=='__main__':
    mode,root=sys.argv[1:3];root=Path(root)
    sys.path.insert(0,str(root/'third_party/jetlink'));sys.path.insert(0,str(root/'tools/jetlink'))
    for key in ('CARROT_TRT_DIRECT_MAP','CARROT_TRT_NATIVE_IMAGE','CARROT_TRT_DEVICE_STATE','CARROT_TRT_INPUT_FASTPATH','CARROT_JETLINK_AIO_WRITE'):
        os.environ[key]='0'
    if mode=='server':server(root)
    else:
        shared,chunks,compact,overlap,defer_nav=[v=='1' for v in sys.argv[4:9]]
        quantum=int(sys.argv[9]);completion_deferred=sys.argv[10]=='1';hook_mode=sys.argv[11]
        for key,val in [('JETLINK_CPU_OVERLAP',overlap),('JETLINK_REQUEST_CHUNKS',chunks),('JETLINK_COMPACT_REPLY',compact),('JETLINK_DEFER_NAV',defer_nav)]:os.environ[key]=str(int(val))
        client(root,int(sys.argv[3]),shared,chunks,compact,overlap,defer_nav,quantum,completion_deferred,hook_mode)
