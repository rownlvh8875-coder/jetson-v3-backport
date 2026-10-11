"""Apply to pinned carrot-jetson. Only TensorRT/CUDA hardware boundaries are fake.

CINQUE_PRODUCTION_ROOT must identify an applied carrot-jetson checkout.
"""
import base64
import copy
import ctypes
import importlib
import json
import os
import pickle
import sys
from pathlib import Path
from types import SimpleNamespace as NS

import numpy as np
import onnx
import pytest
from onnx import helper as H, TensorProto as T

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def prod(monkeypatch):
    target = os.environ.get('CINQUE_PRODUCTION_ROOT')
    if not target:
        pytest.skip('set CINQUE_PRODUCTION_ROOT to a patched pinned carrot-jetson checkout')
    root = Path(target).resolve()
    package = root/'third_party/jetlink'
    saved = {n: m for n, m in sys.modules.items() if n == 'jetlink' or n.startswith('jetlink.')}
    for n in saved: del sys.modules[n]
    monkeypatch.syspath_prepend(str(package))
    try:
        session = importlib.import_module('jetlink.server.session')
        spec = importlib.import_module('jetlink.spec')
        queues = importlib.import_module('jetlink.queues')
        assert Path(session.__file__).resolve().is_relative_to(package)
        print('PRODUCTION_MODULE', session.__file__)
        yield NS(session=session, spec=spec, queues=queues, package=package)
    finally:
        for n in list(sys.modules):
            if n == 'jetlink' or n.startswith('jetlink.'): del sys.modules[n]
        sys.modules.update(saved)


def synthetic_spec(prod):
    d = json.loads((REPO/'artifacts/cinque_v3.json').read_text())
    d['input_shapes'].update(new_img=[2,6,1,1], state_img_q=[2,2,6,1,1],
                             state_desire_q=[2,1,8], state_feat_q=[2,1,3])
    d['output_shapes'] = {'outputs':[1,4], **{'next_'+n: d['input_shapes'][n]
                                for n in ('state_img_q','state_desire_q','state_feat_q')}}
    d['output_slices'] = {'hidden_state':[1,4]}
    return d


def tiny_graph(path, d):
    types = {'uint8':T.UINT8, 'float32':T.FLOAT}
    inputs = [H.make_tensor_value_info(n, types[d['input_dtypes'][n]], s) for n,s in d['input_shapes'].items()]
    outputs = [H.make_tensor_value_info(n, types[d['output_dtypes'][n]], s) for n,s in d['output_shapes'].items()]
    nodes = [H.make_node('Cast', ['new_img'], ['vision'], to=T.FLOAT16),
             H.make_node('Reshape', ['state_img_q','shape'], ['next_state_img_q']),
             H.make_node('Identity', ['state_desire_q'], ['next_state_desire_q']),
             H.make_node('Identity', ['state_feat_q'], ['next_state_feat_q']),
             H.make_node('Constant', [], ['outputs'], value=H.make_tensor('out',T.FLOAT,[1,4],[0]*4))]
    model = H.make_model(H.make_graph(nodes,'fixture',inputs,outputs,
              [H.make_tensor('shape',T.INT64,[5],d['input_shapes']['state_img_q'])]), ir_version=9,
              opset_imports=[H.make_opsetid('',17)])
    H.set_model_props(model, {'model_checkpoint':d['checkpoint'],
         'output_slices':base64.b64encode(pickle.dumps({n:slice(*s) for n,s in d['output_slices'].items()})).decode()})
    onnx.save(model, path)


class CpuEngine:
    """Hardware substitute with persistent input addresses and changing state."""
    def __init__(self, spec, transforms):
        self.inputs = {n:NS(shape=s,dtype=np.dtype(transforms.get(n,spec.input_dtypes[n]))) for n,s in spec.input_shapes.items()}
        self.outputs = {n:NS(shape=s,dtype=np.dtype(transforms.get(n,spec.output_dtypes[n]))) for n,s in spec.output_shapes.items()}
        self.buffers = {n:np.full(i.shape,7,i.dtype) for n,i in self.inputs.items()}
        self.dtype_transforms = transforms.copy()
        self.last_gpu_us = 1
        self.fault = None
        self.seen = []
        self.closed = False
    def host_input(self,n): return self.buffers[n]
    def warm(self):
        self.seen.append({n:v.copy() for n,v in self.buffers.items()})
        self.run()
        return 'CPU fake warm, no CUDA'
    def run(self):
        if self.fault == 'engine': raise RuntimeError('GPU mock failure')
        self.seen.append({n:v.copy() for n,v in self.buffers.items()})
        out = {n:np.ones(i.shape,i.dtype) for n,i in self.outputs.items()}
        for n in self.buffers:
            if n.startswith('state_'): out['next_'+n] = self.buffers[n] + np.array(1,dtype=self.buffers[n].dtype)
        if callable(self.fault): self.fault(out)
        return out
    def close(self): self.closed = True


@pytest.fixture
def live(prod, tmp_path):
    d = synthetic_spec(prod)
    d['sha256'] = 'e' * 64  # synthetic server-state fixture, not the pinned V3 identity
    spec = prod.spec.ModelSpec.from_dict(d)
    cpu_backend = NS(name='cpu-mock',suffix='.plan',tag=lambda:'cpu-mock')
    host = prod.session.EngineHost(prod.session.EngineCache(tmp_path,cpu_backend))
    engine = CpuEngine(spec, dict.fromkeys(('new_img','state_img_q','next_state_img_q'),'float16'))
    try:
        loaded = host._warm(engine, spec)
        host.loaded = loaded
        sent = []
        t = NS(send=lambda mt,seq,parts=(),flags=0: sent.append((mt,seq,b''.join(memoryview(p).cast('B') for p in parts))))
        session = prod.session.Session(t,host)
        session.request = prod.session.Request(spec.sha256,spec.nbytes,spec.frame_skip)
        yield NS(host=host,engine=engine,loaded=loaded,session=session,sent=sent,prod=prod)
    finally: host.close()


def infer(live, frame=1, flags=0, packed=None):
    from jetlink import protocol as P
    s=live.loaded.spec
    packed=np.full(s.packed_nelem,.25,np.float32) if packed is None else packed
    payload=P.pack_infer_req(frame,flags)+np.full(s.warped_shape,frame,np.uint8).tobytes()+packed.tobytes()
    live.session.on_infer(NS(payload=memoryview(payload),seq=frame,msg_type=P.Msg.INFER_REQ))
    return P.unpack_infer_resp(live.sent[-1][2]), live.sent[-1][2]


def test_warm_reset_and_recurrence_use_actual_buffers(live):
    ids={n:id(v) for n,v in live.loaded.host_inputs.items()}
    for n in live.loaded.host_inputs:
        if n.startswith('state_'): assert not np.any(live.loaded.host_inputs[n])
    first,_=infer(live,1)
    second,wire=infer(live,2)
    assert first[0:2] == (1,0) and second[0:2] == (2,0)
    assert wire.__len__() == live.loaded.spec.infer_resp_nbytes
    np.testing.assert_array_equal(live.engine.seen[-1]['state_feat_q'],np.ones((2,1,3)))
    assert ids == {n:id(v) for n,v in live.loaded.host_inputs.items()}


@pytest.mark.parametrize('name',['outputs','next_state_img_q','next_state_desire_q','next_state_feat_q'])
@pytest.mark.parametrize('fault',['nan','inf','missing','shape','dtype'])
def test_validation_failure_preserves_states_and_requires_reload(live,name,fault):
    before={n:v.copy() for n,v in live.loaded.host_inputs.items() if n.startswith('state_')}
    def corrupt(out):
        if fault == 'missing': del out[name]
        elif fault == 'shape': out[name]=out[name].reshape(-1)
        elif fault == 'dtype': out[name]=out[name].astype(np.float32 if out[name].dtype==np.float16 else np.float16)
        else: out[name].flat[0]=np.nan if fault=='nan' else np.inf
    live.engine.fault=corrupt
    header,wire=infer(live)
    assert header[1] != 0
    assert len(wire)==20
    for n,v in before.items(): np.testing.assert_array_equal(live.loaded.host_inputs[n],v)
    live.engine.fault=None
    assert infer(live,2)[0][1] != 0


def test_finite_70000_cannot_narrow_to_fp16_state(live):
    live.engine.fault=lambda out: out.update(next_state_img_q=np.full(live.loaded.spec.output_shapes['next_state_img_q'],70000,np.float32))
    assert infer(live)[0][1] != 0
    assert not np.any(live.loaded.host_inputs['state_img_q'])


@pytest.mark.parametrize('position',[0,1,2])
def test_commit_copy_failure_invalidates_without_claiming_rollback(live,monkeypatch,position):
    original=np.copyto
    states=[live.loaded.host_inputs[n] for n in ('state_img_q','state_desire_q','state_feat_q')]
    def copyto(dst,src,**kw):
        if dst is states[position]: raise ValueError('injected commit copy failure')
        return original(dst,src,**kw)
    monkeypatch.setattr(np,'copyto',copyto)
    assert infer(live)[0][1] != 0
    assert infer(live,2)[0][1] != 0
    assert not live.loaded.valid


def test_readonly_state_commit_failure_is_not_a_success(live):
    live.loaded.host_inputs['state_desire_q'].flags.writeable=False
    assert infer(live)[0][1] != 0
    assert not live.loaded.valid


def test_engine_exception_does_not_deadlock_or_replay_output(live):
    live.engine.fault='engine'
    assert infer(live)[0][1] != 0
    assert live.host.lock.acquire(timeout=.1)
    live.host.lock.release()
    assert infer(live,2)[0][1] != 0


def test_orphan_and_physical_mismatch_rejected_before_warm(prod,tmp_path):
    spec=prod.spec.ModelSpec.from_dict(synthetic_spec(prod))
    engine=CpuEngine(spec,dict.fromkeys(('new_img','state_img_q','next_state_img_q'),'float16'))
    host=prod.session.EngineHost(prod.session.EngineCache(tmp_path))
    try:
        engine.outputs['next_state_img_q'].dtype=np.dtype('float32')
        with pytest.raises(ValueError): host._warm(engine,spec)
        assert not engine.seen
        d=synthetic_spec(prod); del d['output_shapes']['next_state_feat_q']
        with pytest.raises(ValueError): prod.spec.ModelSpec.from_dict(d).validate_stateful()
    finally: host.close()


@pytest.fixture
def gpu(prod, monkeypatch):
    """Fake only TRT parser/compiler/runtime and CUDA calls, not server functions.

    Real ONNX patch/check/save and real TrtEngine allocation/copy/execute paths.
    Memory here is ordinary ctypes memory; it is NOT actual pinned CUDA memory.
    """
    from types import ModuleType
    trt = ModuleType('tensorrt')
    trt.__version__ = '10.3.0.mock'
    trt.Logger = type('Logger', (), {'WARNING':2, '__init__':lambda self,*a:None})
    trt.IProgressMonitor = object
    trt.BuilderFlag = NS(FP16=1)
    trt.MemoryPoolType = NS(WORKSPACE=0)
    trt.TensorIOMode = NS(INPUT=0, OUTPUT=1)
    trt.DataType = NS(FLOAT='float32', HALF='float16', INT8='int8', INT32='int32',
                      INT64='int64', BOOL='bool', UINT8='uint8')
    state = NS(builds=0, allocations=0, pool={}, fail=None, context_fail=False,
               address_fail=False, execute_fail=False, descriptors=None, frees=0,
               flags=[], parsed=[], mutation=None, close_syncs=0)
    class Parser:
        def __init__(self, network, logger): self.network=network
        def parse_from_file(self, path):
            if state.fail=='parse': return False
            m=onnx.load(path)
            ios={}
            for mode,values in ((0,m.graph.input),(1,m.graph.output)):
                for v in values:
                    ios[v.name]={'mode':mode,'shape':[d.dim_value for d in v.type.tensor_type.shape.dim],
                                'dtype':str(np.dtype(onnx.helper.tensor_dtype_to_np_dtype(v.type.tensor_type.elem_type)))}
            self.network.ios=ios
            state.parsed.append(ios)
            return True
        num_errors=1
        def get_error(self,i): return 'injected parser failure'
    class Builder:
        def __init__(self,*a): pass
        def create_network(self,flags):
            state.flags.append(flags)
            return NS(num_layers=5)
        def create_builder_config(self):
            return NS(set_flag=lambda f:None,set_memory_pool_limit=lambda *a:None)
        def build_serialized_network(self,network,config):
            state.builds+=1
            if state.fail=='build': return None
            return json.dumps(network.ios,sort_keys=True).encode()
    class Context:
        def __init__(self,ios): self.ios,self.addresses=ios,{}
        def set_tensor_address(self,n,ptr):
            self.addresses[n]=ptr
            return not state.address_fail
        def execute_async_v3(self,stream):
            if state.execute_fail: return False
            def view(n):
                d=self.ios[n]
                size=int(np.prod(d['shape']))*np.dtype(d['dtype']).itemsize
                return np.frombuffer((ctypes.c_char*size).from_address(self.addresses[n]),dtype=d['dtype']).reshape(d['shape'])
            for n,d in self.ios.items():
                if d['mode']==1:
                    if n.startswith('next_state_'): view(n)[...]=view(n[5:])+1
                    else: view(n)[...]=.5
            return True
    class Runtime:
        def __init__(self,*a): pass
        def deserialize_cuda_engine(self,blob):
            if state.fail=='deserialize': raise RuntimeError('device memory failure')
            ios=json.loads(blob)
            if state.mutation: state.mutation(ios)
            state.descriptors=ios
            return NS(num_io_tensors=len(ios),get_tensor_name=lambda i:list(ios)[i],
               get_tensor_mode=lambda n:ios[n]['mode'],get_tensor_shape=lambda n:tuple(ios[n]['shape']),
               get_tensor_dtype=lambda n:ios[n]['dtype'],
               create_execution_context=lambda:None if state.context_fail else Context(ios))
    trt.Builder, trt.OnnxParser, trt.Runtime = Builder, Parser, Runtime
    monkeypatch.setitem(sys.modules,'tensorrt',trt)
    cuda=ModuleType('jetlink.server.backends.trt.cudart')
    def alloc(size):
        state.allocations+=1
        buf=ctypes.create_string_buffer(size)
        ptr=ctypes.addressof(buf);state.pool[ptr]=buf
        return ptr
    def free(ptr): state.pool.pop(ptr);state.frees+=1
    cuda.malloc=cuda.host_alloc=alloc
    cuda.free=cuda.host_free=free
    cuda.memcpy_h2d_async=cuda.memcpy_d2h_async=lambda dst,src,size,stream:ctypes.memmove(dst,src,size)
    cuda.stream_create=lambda:1
    cuda.stream_destroy=lambda stream:None
    cuda.stream_sync=lambda stream:setattr(state,'close_syncs',state.close_syncs+1)
    cuda.set_device=lambda device:None
    cuda.device_name=lambda device:('CPU_fake_no_GPU',8,7)
    def no_capture(stream): raise RuntimeError('No actual CUDA graphs in CPU fake')
    cuda.stream_begin_capture=no_capture
    monkeypatch.setitem(sys.modules,'jetlink.server.backends.trt.cudart',cuda)
    backend=importlib.import_module('jetlink.server.backends.trt')
    common=importlib.import_module('jetlink.cinque_v3')
    yield NS(prod=prod,trt=trt,cuda=cuda,state=state,backend=backend,common=common)


@pytest.fixture
def source(gpu,tmp_path,monkeypatch):
    d=synthetic_spec(gpu.prod)
    path=tmp_path/'source.onnx'
    tiny_graph(path,d)
    identity=gpu.common.file_identity(path)
    d.update(identity)
    # Bind the full production gate to this exact small fixture. No bypass of
    # identity validation: every altered byte must still fail the hash gate.
    monkeypatch.setattr(gpu.common,'CANONICAL_SPEC',d)
    return NS(path=path,spec=d)


def build(gpu,source,tmp_path):
    backend=gpu.backend.TrtBackend()
    out=tmp_path/(source.spec['sha256'][:16]+'.plan')
    backend.build(source.path,out,meta_extra={'spec':source.spec})
    return backend,out


def test_production_build_load_and_deleted_temp_reload(gpu,source,tmp_path):
    backend,out=build(gpu,source,tmp_path)
    meta=json.loads(out.with_suffix('.json').read_text())
    record=meta['cinque_v3']
    assert record['source']==gpu.common.file_identity(source.path)
    assert record['engine']==gpu.common.file_identity(out)
    assert record['dtype_transforms']==gpu.common.DTYPE_TRANSFORMS
    assert record['semantic_spec']['input_dtypes']['new_img']=='uint8'
    assert 'patched_path' not in json.dumps(record)
    assert not list(tmp_path.glob('tmp*/patched.onnx'))
    source.path.unlink()
    # New backend object consumes persistent metadata, no original/patched file.
    engine=gpu.backend.TrtBackend().load(out)
    try:
        host=gpu.prod.session.EngineHost(gpu.prod.session.EngineCache(tmp_path/'cache',backend))
        loaded=host._warm(engine,gpu.prod.spec.ModelSpec.from_dict(source.spec))
        host.loaded=loaded
        sent=[]
        session=gpu.prod.session.Session(NS(send=lambda mt,seq,parts=(),flags=0:sent.append((mt,seq,b''.join(memoryview(p).cast('B') for p in parts)))),host)
        session.request=gpu.prod.session.Request(source.spec['sha256'],source.spec['nbytes'],4)
        live=NS(loaded=loaded,session=session,sent=sent)
        assert infer(live,1)[0][1]==0
        assert infer(live,2)[0][1]==0
        np.testing.assert_array_equal(engine.host_input('state_feat_q'),2)
    finally: host.close()


@pytest.mark.parametrize('fault',['missing','corrupt','other-engine','source','dtype','semantic','patch-id','patched-hash','runtime','device','list'])
def test_v3_bad_metadata_refused_before_gpu_allocation(gpu,source,tmp_path,fault):
    backend,out=build(gpu,source,tmp_path)
    mp=out.with_suffix('.json');meta=json.loads(mp.read_text())
    if fault=='missing': mp.unlink()
    elif fault=='corrupt': mp.write_text('{')
    elif fault=='list': mp.write_text('[]')
    else:
        if fault=='other-engine': out.write_bytes(out.read_bytes()+b' ')
        elif fault=='source': meta['cinque_v3']['source']['sha256']='0'*64
        elif fault=='dtype': meta['cinque_v3']['dtype_transforms']['state_feat_q']='float16'
        elif fault=='semantic': meta['spec']['input_dtypes']['new_img']='float16'
        elif fault=='patch-id': meta['cinque_v3']['patch_id']='unknown'
        elif fault=='patched-hash': meta['cinque_v3']['patched']['sha256']='1'*64
        elif fault=='runtime': meta['trt_version']='wrong'
        elif fault=='device': meta['device']='other-device'
        mp.write_text(json.dumps(meta))
    from jetlink.server.backends.base import ArtifactInvalid
    with pytest.raises(ArtifactInvalid): backend.load(out)
    assert gpu.state.allocations==0


@pytest.mark.parametrize('fault',['parse','build','metadata-save','engine-save'])
def test_failed_build_preserves_previous_pair(gpu,source,tmp_path,monkeypatch,fault):
    backend,out=build(gpu,source,tmp_path)
    mp=out.with_suffix('.json');before=(out.read_bytes(),mp.read_bytes())
    gpu.state.fail=fault
    original=os.replace
    def replace(src,dst):
        if (fault=='metadata-save' and Path(dst)==mp) or (fault=='engine-save' and Path(dst)==out):
            raise OSError('injected publish failure')
        return original(src,dst)
    monkeypatch.setattr(os,'replace',replace)
    with pytest.raises((OSError,RuntimeError)): backend.build(source.path,out,meta_extra={'spec':source.spec})
    assert (out.read_bytes(),mp.read_bytes())==before


@pytest.mark.parametrize('field',['cinque_v3','backend','trt_version','device'])
def test_meta_extra_cannot_override_protected_fields(gpu,source,tmp_path,field):
    with pytest.raises(ValueError,match='protected'):
        gpu.backend.TrtBackend().build(source.path,tmp_path/'x.plan',meta_extra={'spec':source.spec,field:'fake'})
    assert gpu.state.builds==0


@pytest.mark.parametrize('fault',['shape','dtype','mode','missing','extra'])
def test_engine_contract_rejected_before_buffers(gpu,source,tmp_path,fault):
    backend,out=build(gpu,source,tmp_path)
    def mutate(ios):
        if fault=='shape': ios['new_img']['shape']=[6,2,1,1]
        elif fault=='dtype': ios['new_img']['dtype']='float32'
        elif fault=='mode': ios['new_img']['mode']=1
        elif fault=='missing': del ios['state_feat_q']
        else: ios['extra']=ios['action_t'].copy()
    gpu.state.mutation=mutate
    from jetlink.server.backends.base import ArtifactInvalid
    with pytest.raises(ArtifactInvalid): backend.load(out)
    assert gpu.state.allocations==0


def test_unknown_new_img_graph_is_not_a_v3_model(gpu,tmp_path):
    d=synthetic_spec(gpu.prod);path=tmp_path/'unknown.onnx';tiny_graph(path,d)
    with pytest.raises(ValueError): gpu.backend.TrtBackend().build(path,tmp_path/'x.plan',meta_extra={'spec':d})
    assert gpu.state.builds==0


def test_cache_miss_hit_restart_and_device_error_preserves_cache(gpu,source,tmp_path):
    import shutil
    cache=gpu.prod.session.EngineCache(tmp_path/'cache',gpu.backend.TrtBackend())
    model=cache.model_path(source.spec['sha256']);shutil.copyfile(source.path,model)
    req=gpu.prod.session.Request(source.spec['sha256'],source.spec['nbytes'],4)
    def prepare(load_only):
        host=gpu.prod.session.EngineHost(cache)
        job=gpu.prod.session.Job(req.sha256,load_only)
        spec=host._spec_on_disk(cache.entry(req.sha256),model,req)
        host._run(job,req,cache.entry(req.sha256),model,spec)
        return host,job
    host,job=prepare(False)
    try: assert job.state=='ready';assert gpu.state.builds==1
    finally: host.close()
    model.unlink()
    host,job=prepare(True)
    try: assert job.state=='ready';assert gpu.state.builds==1
    finally: host.close()
    gpu.state.fail='deserialize'
    host,job=prepare(True)
    try:
        assert job.state=='failed'
        assert cache.entry(req.sha256).exists
        assert gpu.state.builds==1
    finally: host.close()


def test_bad_scalar_preserves_history_unless_explicit_reset(live):
    from jetlink import protocol as P
    assert infer(live)[0][1]==0
    before={n:v.copy() for n,v in live.loaded.host_inputs.items() if n.startswith('state_')}
    packed=np.zeros(live.loaded.spec.packed_nelem,np.float32);packed[0]=np.inf
    assert infer(live,2,packed=packed)[0][1]==P.Status.NOT_FINITE
    for n,v in before.items(): np.testing.assert_array_equal(live.loaded.host_inputs[n],v)
    assert infer(live,3,flags=P.Flag.RESET_QUEUES,packed=packed)[0][1]!=0
    for n in before: assert not np.any(live.loaded.host_inputs[n])


def test_hello_resets_in_place_and_invalid_generation_stays_blocked(live):
    assert infer(live)[0][1]==0
    ids={n:id(v) for n,v in live.loaded.host_inputs.items()}
    live.session._greet(NS(payload=memoryview(b'{}'),seq=1))
    for n,v in live.loaded.host_inputs.items():
        if n.startswith('state_'): assert not np.any(v)
    assert ids=={n:id(v) for n,v in live.loaded.host_inputs.items()}
    live.session.request=live.prod.session.Request(live.loaded.spec.sha256,live.loaded.spec.nbytes,4)
    live.loaded.valid=False
    assert infer(live,2)[0][1]!=0
    assert live.host.status(live.loaded.sha256,4)['state']!='ready'


def queued_source(prod,tmp_path):
    d=json.loads((REPO/'tests/tiny_queued.spec.json').read_text())
    types={n:('uint8' if n in ('img','big_img') else 'float32') for n in d['input_shapes']}
    ins=[H.make_tensor_value_info(n,T.UINT8 if types[n]=='uint8' else T.FLOAT,s) for n,s in d['input_shapes'].items()]
    outs=[H.make_tensor_value_info('outputs',T.FLOAT,[1,64])]
    nodes=[H.make_node('Cast',[n],[n+'_f16'],to=T.FLOAT16) for n in ('img','big_img')]
    nodes.append(H.make_node('Constant',[],['outputs'],value=H.make_tensor('out',T.FLOAT,[1,64],[0]*64)))
    path=tmp_path/'v2.onnx'
    onnx.save(H.make_model(H.make_graph(nodes,'queued',ins,outs),opset_imports=[H.make_opsetid('',17)],ir_version=9),path)
    d.update(dict(zip(('sha256','nbytes'),prod.spec.sha256_file(str(path)))))
    # Legacy V2 caches deliberately omit dtype declarations.
    return NS(path=path,spec=d)


def test_v2_v3_v2_keeps_head_patch_queues_prev_feat_and_engine_records(gpu,source,tmp_path):
    v2=queued_source(gpu.prod,tmp_path)
    backend=gpu.backend.TrtBackend()
    out2=tmp_path/(v2.spec['sha256'][:16]+'.plan')
    backend.build(v2.path,out2,meta_extra={'spec':v2.spec})
    meta2=json.loads(out2.with_suffix('.json').read_text())
    assert 'cinque_v3' not in meta2
    assert gpu.state.parsed[-1]['img']['dtype']=='float16'
    assert gpu.state.parsed[-1]['big_img']['dtype']=='float16'
    assert gpu.state.flags[-1]==0  # unchanged TRT10 weak typing/FP16 path
    _,out3=build(gpu,source,tmp_path)
    for out,spec,expected in ((out2,v2.spec,{'img':'float16','big_img':'float16'}),(out3,source.spec,gpu.common.DTYPE_TRANSFORMS),(out2,v2.spec,{'img':'float16','big_img':'float16'})):
        host=gpu.prod.session.EngineHost(gpu.prod.session.EngineCache(tmp_path/'cache',backend))
        engine=backend.load(out)
        try:
            loaded=host._warm(engine,gpu.prod.spec.ModelSpec.from_dict(spec));host.loaded=loaded
            assert engine.dtype_transforms==expected
            assert ('prev_feat' in loaded.spec.packed_shapes)==(out==out2)
            if out==out2:
                packed=np.zeros(loaded.spec.packed_nelem,np.float32)
                packed[-loaded.spec.feat_dim:]=np.arange(loaded.spec.feat_dim,dtype=np.float32)
                for _ in range(loaded.spec.frame_skip):
                    loaded.queues.step_into(np.full(loaded.spec.warped_shape,255,np.uint8),packed,loaded.host_inputs)
                np.testing.assert_array_equal(loaded.host_inputs['features_buffer'].reshape(-1)[-32:],np.arange(32))
        finally: host.close()


@pytest.mark.parametrize('fault',['context','address','execute'])
def test_cuda_failures_explicit_and_allocations_cleaned(gpu,source,tmp_path,fault):
    backend,out=build(gpu,source,tmp_path)
    setattr(gpu.state,{'context':'context_fail','address':'address_fail','execute':'execute_fail'}[fault],True)
    if fault in ('context','address'):
        with pytest.raises(RuntimeError): backend.load(out)
        assert not gpu.state.pool
    else:
        engine=backend.load(out)
        try:
            with pytest.raises(RuntimeError): engine.run()
            assert gpu.state.close_syncs>0
        finally: engine.close()
    assert out.is_file()  # device failures do not delete a verified plan


def test_warm_exception_clears_state_in_same_buffers(prod,tmp_path):
    spec=prod.spec.ModelSpec.from_dict(synthetic_spec(prod))
    engine=CpuEngine(spec,dict.fromkeys(('new_img','state_img_q','next_state_img_q'),'float16'))
    ids={n:id(v) for n,v in engine.buffers.items()}
    def warm_fail():
        for n,v in engine.buffers.items():
            if n.startswith('state_'): v.fill(5)
        raise RuntimeError('warm failed')
    engine.warm=warm_fail
    host=prod.session.EngineHost(prod.session.EngineCache(tmp_path))
    try:
        with pytest.raises(RuntimeError): host._warm(engine,spec)
        for n,v in engine.buffers.items():
            if n.startswith('state_'): assert not np.any(v)
        assert ids=={n:id(v) for n,v in engine.buffers.items()}
        assert host.loaded is None
    finally: host.close()


def test_invalid_generation_snapshot_and_reset_flag_cannot_report_ready(live):
    from jetlink import protocol as P
    live.engine.fault='engine'
    assert infer(live)[0][1]!=0
    assert live.host.snapshot()['state']!='ready'
    live.engine.fault=None
    assert infer(live,2,flags=P.Flag.RESET_QUEUES)[0][1]!=0


def test_v3_wrong_frame_skip_does_not_delete_good_cache(gpu,source,tmp_path):
    import shutil
    cache=gpu.prod.session.EngineCache(tmp_path/'cache',gpu.backend.TrtBackend())
    shutil.copyfile(source.path,cache.model_path(source.spec['sha256']))
    gpu.backend.TrtBackend().build(source.path,cache.entry(source.spec['sha256']).path,meta_extra={'spec':source.spec})
    host=gpu.prod.session.EngineHost(cache)
    try:
        req=gpu.prod.session.Request(source.spec['sha256'],source.spec['nbytes'],8)
        response=host.request(req,None)
        assert response['state']=='failed'
        assert cache.entry(req.sha256).exists
        assert gpu.state.builds==1
    finally: host.close()


def test_corrupt_cache_rebuilds_only_from_verified_source(gpu,source,tmp_path):
    import shutil
    cache=gpu.prod.session.EngineCache(tmp_path/'cache',gpu.backend.TrtBackend())
    model=cache.model_path(source.spec['sha256']);shutil.copyfile(source.path,model)
    entry=cache.entry(source.spec['sha256'])
    gpu.backend.TrtBackend().build(model,entry.path,meta_extra={'spec':source.spec})
    entry.path.write_bytes(b'wrong engine')
    host=gpu.prod.session.EngineHost(cache)
    req=gpu.prod.session.Request(source.spec['sha256'],source.spec['nbytes'],4)
    job=gpu.prod.session.Job(req.sha256,True)
    try:
        host._run(job,req,entry,model,gpu.prod.spec.ModelSpec.from_dict(source.spec))
        assert job.state=='ready'
        assert gpu.state.builds==2
        engine=host.loaded.engine
        assert engine.dtype_transforms==gpu.common.DTYPE_TRANSFORMS
    finally: host.close()


def test_no_dtype_declarations_fail_before_warm(prod,tmp_path):
    d=synthetic_spec(prod);d.pop('input_dtypes');d.pop('output_dtypes')
    with pytest.raises(ValueError): prod.spec.ModelSpec.from_dict(d).validate_stateful()


def test_device_query_error_never_classifies_good_plan_as_corrupt(gpu,source,tmp_path,monkeypatch):
    backend,out=build(gpu,source,tmp_path)
    def bad_device(device): raise RuntimeError('driver unavailable')
    monkeypatch.setattr(gpu.cuda,'device_name',bad_device)
    from jetlink.server.backends.base import ArtifactInvalid
    with pytest.raises(RuntimeError) as err: backend.load(out)
    assert not isinstance(err.value,ArtifactInvalid)
    assert out.is_file()


def test_stream_drain_failure_cannot_free_live_buffers(gpu,source,tmp_path,monkeypatch):
    backend,out=build(gpu,source,tmp_path);engine=backend.load(out)
    original=gpu.cuda.stream_sync
    def fail(stream): raise RuntimeError('stream drain failed')
    monkeypatch.setattr(gpu.cuda,'stream_sync',fail)
    try:
        with pytest.raises(RuntimeError): engine.run()
        assert not engine.idle
        allocated=len(gpu.state.pool)
        with pytest.raises(RuntimeError): engine.close()
        assert len(gpu.state.pool)==allocated
    finally:
        monkeypatch.setattr(gpu.cuda,'stream_sync',original)
        engine.close()


def test_renamed_v3_without_metadata_cannot_fall_back_to_v2(gpu,source,tmp_path):
    backend,out=build(gpu,source,tmp_path)
    renamed=tmp_path/'unrecognized.plan';out.rename(renamed)
    from jetlink.server.backends.base import ArtifactInvalid
    with pytest.raises(ArtifactInvalid): backend.load(renamed)
    assert gpu.state.allocations==0


def test_partial_commit_really_invalidates_and_reload_starts_fresh(live,monkeypatch):
    original=np.copyto
    second=live.loaded.host_inputs['state_desire_q']
    def fail(dst,src,**kw):
        if dst is second: raise ValueError('second commit failed')
        return original(dst,src,**kw)
    monkeypatch.setattr(np,'copyto',fail)
    assert infer(live)[0][1]!=0
    # Evidence of partial commit: explicitly do not claim rollback.
    assert np.all(live.loaded.host_inputs['state_img_q']==1)
    assert not np.any(second)
    assert not live.loaded.valid
    monkeypatch.setattr(np,'copyto',original)
    replacement=CpuEngine(live.loaded.spec,live.engine.dtype_transforms)
    reloaded=live.host._warm(replacement,live.loaded.spec)
    live.host.loaded=reloaded
    live.loaded=reloaded
    assert infer(live,2)[0][1]==0
    assert np.all(reloaded.host_inputs['state_img_q']==1)


def child_load_probe(artifact):
    """Called in a fresh interpreter. Hardware boundaries remain explicitly fake."""
    with pytest.MonkeyPatch.context() as mp:
        pg=prod.__wrapped__(mp);p=next(pg)
        gg=gpu.__wrapped__(p,mp);g=next(gg)
        try:
            spec=json.loads(Path(artifact).with_suffix('.json').read_text())['spec']
            mp.setattr(g.common,'CANONICAL_SPEC',spec)
            engine=g.backend.TrtBackend().load(Path(artifact))
            host=p.session.EngineHost(p.session.EngineCache(Path(artifact).parent/'child-cache',g.backend.TrtBackend()))
            try:
                host.loaded=host._warm(engine,p.spec.ModelSpec.from_dict(spec))
                assert engine.dtype_transforms==g.common.DTYPE_TRANSFORMS
                assert not np.any(engine.host_input('state_feat_q'))
                print('FRESH_PROCESS_LOADED_CPU_MOCK',p.session.__file__)
            finally: host.close()
        finally: gg.close();pg.close()


def test_fresh_process_load_consumes_record_without_source_or_patched(gpu,source,tmp_path):
    import subprocess
    _,out=build(gpu,source,tmp_path)
    source.path.unlink()
    code='import sys;sys.path.insert(0,sys.argv[1]);import test_production_v3 as t;t.child_load_probe(sys.argv[2])'
    result=subprocess.run([sys.executable,'-c',code,str(REPO/'tests'),str(out)],
                          capture_output=True,text=True,timeout=60)
    assert result.returncode==0,result.stdout+result.stderr
    assert 'FRESH_PROCESS_LOADED_CPU_MOCK' in result.stdout
    assert str(gpu.prod.package) in result.stdout


def test_source_copies_match_actual_deployment_modules(prod):
    for name in ('spec.py','queues.py','cinque_v3.py'):
        assert (REPO/'jetlink'/name).read_text()==(prod.package/'jetlink'/name).read_text()
    assert (REPO/'patches/session.py.new').read_text()==(prod.package/'jetlink/server/session.py').read_text()
    common=importlib.import_module('jetlink.cinque_v3')
    assert common.CANONICAL_SPEC==json.loads((REPO/'artifacts/cinque_v3.json').read_text())


def test_real_request_worker_builds_and_serves_v3(gpu,source,tmp_path):
    import shutil,time
    cache=gpu.prod.session.EngineCache(tmp_path/'cache',gpu.backend.TrtBackend())
    shutil.copyfile(source.path,cache.model_path(source.spec['sha256']))
    host=gpu.prod.session.EngineHost(cache)
    try:
        req=gpu.prod.session.Request(source.spec['sha256'],source.spec['nbytes'],4)
        reply=host.request(req,None)
        deadline=time.monotonic()+10
        while host.job is not None and host.job.state=='building' and time.monotonic()<deadline:
            time.sleep(.01)
        assert host.job is not None and host.job.state=='ready'
        assert host.status(req.sha256,4)['state']=='ready'
        assert gpu.state.builds==1
    finally: host.close()


def test_failed_cuda_capture_ends_capture_and_drains_before_reset(gpu,source,tmp_path,monkeypatch):
    backend,out=build(gpu,source,tmp_path);engine=backend.load(out)
    events=[]
    monkeypatch.setattr(gpu.cuda,'stream_begin_capture',lambda stream:events.append('begin'))
    monkeypatch.setattr(gpu.cuda,'stream_end_capture',lambda stream:(events.append('end') or 2),raising=False)
    monkeypatch.setattr(gpu.cuda,'graph_destroy',lambda graph:events.append('destroy'),raising=False)
    monkeypatch.setattr(gpu.cuda,'stream_sync',lambda stream:events.append('sync'))
    gpu.state.execute_fail=True
    try:
        assert engine.capture_graph() is False
        assert events==['begin','end','destroy','sync']
        assert engine.idle
    finally: engine.close()
