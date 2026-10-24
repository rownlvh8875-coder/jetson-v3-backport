"""Actual810e Warp/Client/memfd source; QCOM and engine replies are CPU fixtures."""
import ast
import copy
import json
import logging
import os
import socket
import threading
import time
import types

import numpy as np
import pytest

from adapters.carrot import recorder_810e as r
from recorder_810e_support import (blob, selected, nav_spec, package, ticket,
                                  fake_namespace, Sink, receive_frame)


def modules():
    spec=nav_spec()
    shared=types.ModuleType('exact810_shared')
    exec(compile(blob('openpilot/selfdrive/modeld/jetlink/shared_input.py'),'shared_input.py','exec'),shared.__dict__)
    projection=types.ModuleType('exact810_projection')
    exec(compile(blob('third_party/jetlink/jetlink/output_projection.py'),'output_projection.py','exec'),projection.__dict__)
    contracts=dict(ModelSpec=type(spec), DEFAULT_SPEC=spec, JETSON_SPEC=spec,
        OUTPUT_WIDTHS={'lane_lines':(528,), 'lane_lines_prob':(8,), 'road_edges':(264,),
                      'meta':(55,), 'desire_pred':(32,), 'pose':(12,), 'wide_from_device_euler':(6,),
                      'road_transform':(12,), 'plan':(990,4955), 'lead':(144,102),
                      'lead_prob':(3,), 'desire_state':(8,)}, re=__import__('re'), math=__import__('math'))
    selected('openpilot/selfdrive/modeld/jetlink/contracts.py',['slice_range','validate_model_spec'],contracts)
    link=types.ModuleType('exact810_link')
    link.__dict__.update(shared_input=shared,ModelSpec=type(spec),projection=projection,
                         DEFAULT_SPEC=spec,validate_model_spec=contracts['validate_model_spec'])
    tree=ast.parse(blob('openpilot/selfdrive/modeld/jetlink/link.py'))
    tree.body=[n for n in tree.body if not (isinstance(n,ast.ImportFrom)
               and n.module.startswith(('openpilot.','jetlink')))]
    exec(compile(tree,'link.py','exec'),link.__dict__)
    return link,shared


def source_warp(monkeypatch, pixels):
    # Both __call__ and read_result execute unchanged. Only QCOM Tensor is fake.
    class Result:
        shape=pixels.shape
        drained=0; copies=0
        def numpy(self):self.drained+=1;return pixels
        def _buffer(self):return self
        def copyout(self,destination):self.copies+=1;destination[:]=memoryview(pixels).cast('B')
    result=Result()
    Tensor=types.SimpleNamespace(from_blob=lambda *a,**k:object())
    monkeypatch.setitem(__import__('sys').modules,'tinygrad',types.SimpleNamespace(Tensor=Tensor))
    ns=dict(np=np,time=time);selected(r.MODEL,['Warp'],ns)
    cls=ns['Warp']; warp=object.__new__(cls)
    warp.size=4;warp.blobs={};warp.inputs={};warp.transforms={k:np.eye(3,dtype=np.float32) for k in ('tfm','big_tfm')}
    warp.run_warp=lambda **kw:result
    return cls,warp,result


@pytest.mark.parametrize('kind',['none','valid','dtype','shape','readonly','noncontiguous'])
def test_source_warp_buffer_results_exceptions_and_single_prepare(tmp_path,monkeypatch,kind):
    h=package(tmp_path,monkeypatch); pixels=np.arange(393216,dtype=np.uint8).reshape(2,6,128,256)
    cls,warp,gpu=source_warp(monkeypatch,pixels)
    ns=fake_namespace();ns['Warp']=cls;sink=Sink()
    cap=h.install(ns,arm_path='fixture',ticket_loader=lambda _:ticket(h,tmp_path),
        source_verifier=lambda _:None,recorder_factory=lambda *a,**k:sink)
    ns['Client']();transforms=receive_frame(ns)
    dest=None if kind=='none' else np.empty_like(pixels)
    if kind=='dtype':dest=dest.astype(np.float32)
    if kind=='shape':dest=dest.reshape(-1)
    if kind=='readonly':dest.flags.writeable=False
    if kind=='noncontiguous':dest=np.empty((2,6,128,512),np.uint8)[...,::2]
    prepared=[]
    args=({'img':types.SimpleNamespace(data=b'1234'),'big_img':types.SimpleNamespace(data=b'5678')},transforms)
    if kind in ('none','valid'):
        output=warp(*args,prepare=lambda:prepared.append(1),output_buffer=dest)
        assert output is (pixels if dest is None else dest)
        assert cap.warped is output
        assert output.tobytes()==pixels.tobytes()
        assert gpu.drained==(1 if dest is None else 0) and gpu.copies==(0 if dest is None else 1)
    else:
        with pytest.raises(ValueError,match='invalid warp destination'):warp(*args,prepare=lambda:prepared.append(1),output_buffer=dest)
        assert gpu.drained==1 and gpu.copies==0 and cap.disabled
    assert prepared==[1]


def test_original_prepare_exception_identity_and_fence_drain(tmp_path,monkeypatch):
    h=package(tmp_path,monkeypatch); pixels=np.zeros((2,6,128,256),np.uint8)
    cls,warp,gpu=source_warp(monkeypatch,pixels); ns=fake_namespace();ns['Warp']=cls
    cap=h.install(ns,arm_path='fixture',ticket_loader=lambda _:ticket(h,tmp_path),
        source_verifier=lambda _:None,recorder_factory=lambda *a,**k:Sink())
    error=RuntimeError('original prepare')
    def prepare():raise error
    with pytest.raises(RuntimeError) as actual:
        warp({'img':types.SimpleNamespace(data=b'1234'),'big_img':types.SimpleNamespace(data=b'1234')},
             {'img':np.eye(3),'big_img':np.eye(3)},prepare=prepare)
    assert actual.value is error and gpu.drained==1 and cap.warped is None


def pair(link,shared):
    a,b=socket.socketpair()
    reader=shared.Reader.offer(a,nav_spec());link.send(a,reader.nonce)
    writer=shared.Writer.receive(b,nav_spec(),link.receive,time.monotonic()+.15)
    a.close();b.close();return reader,writer


def test_memfd_identity_copy_does_not_own_or_hold_slot(tmp_path,monkeypatch):
    h=package(tmp_path,monkeypatch);link,shared=modules();reader,writer=pair(link,shared)
    try:
        image=writer.begin();image[:]=37
        ns=fake_namespace();sink=Sink()
        cap=h.install(ns,arm_path='fixture',ticket_loader=lambda _:ticket(h,tmp_path),
            source_verifier=lambda _:None,recorder_factory=lambda *a,**k:sink)
        client=ns['Client']();transforms=receive_frame(ns)
        assert ns['Warp']()(image,transforms,output_buffer=image) is image
        packed=np.arange(65595,dtype=np.float32);packed[0]=-0.0
        before=(writer.generation,writer.busy,image.tobytes(),packed.tobytes())
        client.infer(image,packed,1)
        assert before==(writer.generation,writer.busy,image.tobytes(),packed.tobytes())
        assert cap.warped is None and sink.identities==[id(writer.image)]
        token=writer.token(image,packed,1,0,100)
        _,_,_,remote,scalars=reader.read(token)
        assert not remote.flags.writeable
        assert remote.tobytes()==sink.records[0][0].tobytes()
        assert scalars[:12].tobytes()==b''.join(v.tobytes() for v in sink.records[0][1:4])
        assert writer.busy and writer.generation==reader.generation==1
        writer.complete();assert not writer.busy
        cap.stop('fixture writer failure');assert writer.begin() is image
        writer.close()
        with pytest.raises(ConnectionError):writer.begin()
        with pytest.raises(ValueError):writer.token(image,packed,2,0,100)
        # An exported old array remains a retired lease, never a new session.
        r2,w2=pair(link,shared)
        try:
            assert w2.begin() is not image and w2.nonce!=writer.nonce
            assert not np.shares_memory(image,w2.image)
            assert not np.any(w2.image)
        finally:r2.close();w2.close()
    finally:reader.close();writer.close()


@pytest.mark.parametrize('fault',['expired','duplicate','foreign','retired'])
def test_shared_slot_original_rejections(fault):
    link,shared=modules();reader,writer=pair(link,shared)
    try:
        image=writer.begin();packed=np.zeros(65595,np.float32)
        token=writer.token(image,packed,1,0,100)
        if fault=='expired':
            fields=list(shared.TOKEN.unpack(token));fields[3]=time.monotonic_ns()-151_000_000;token=shared.TOKEN.pack(*fields)
        elif fault=='duplicate':reader.read(token)
        elif fault=='foreign':
            fields=list(shared.TOKEN.unpack(token));fields[1]=b'x'*16;token=shared.TOKEN.pack(*fields)
        elif fault=='retired':reader.close()
        with pytest.raises(ValueError):reader.read(token)
    finally:reader.close();writer.close()


@pytest.mark.parametrize('shared_on',[True,False])
@pytest.mark.parametrize('fault',['none','timeout','disconnect','stale'])
def test_actual_client_ipc_infer_alias_fallback_and_retirement(tmp_path,monkeypatch,shared_on,fault):
    h=package(tmp_path,monkeypatch);link,shared=modules()
    monkeypatch.setenv('JETLINK_RAM_INPUT','1' if shared_on else '0')
    monkeypatch.setenv('SEND_RAW_PRED','1')
    endpoint=str(tmp_path/'local.sock');listener=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
    listener.bind(endpoint);listener.listen(1)
    seen=[];errors=[]
    def server():
        reader=None
        try:
            conn,_=listener.accept()
            with conn:
                link.send(conn,json.dumps({'spec':nav_spec().to_dict(),'ram_input_v1':True}).encode())
                request=link.receive(conn)
                if bytes(request)==shared.SETUP:
                    reader=shared.Reader.offer(conn,nav_spec());link.send(conn,reader.nonce);request=link.receive(conn)
                    fid,flags,sof,image,packed=reader.read(request)
                else:
                    fid,flags,sof=link.REQUEST.unpack_from(request)
                    image=np.frombuffer(request,np.uint8,393216,link.REQUEST.size).reshape(2,6,128,256)
                    packed=np.frombuffer(request,np.float32,65595,link.REQUEST.size+393216)
                seen.append((image.copy(),packed.copy()))
                if fault=='timeout':time.sleep(.2)
                if fault=='disconnect':return
                try:link.send_parts(conn,link.REPLY.pack(fid+(fault=='stale'),1,2,3),np.zeros(18580,np.float32))
                except BrokenPipeError:pass
        except Exception as exc:errors.append(exc)
        finally:
            if reader:reader.close()
    thread=threading.Thread(target=server);thread.start()
    ns=fake_namespace();ns['Client']=link.Client;sink=Sink()
    cap=h.install(ns,arm_path='fixture',ticket_loader=lambda _:ticket(h,tmp_path),
        source_verifier=lambda _:None,recorder_factory=lambda *a,**k:sink)
    client=ns['Client'](endpoint) # production .15s timeout is unchanged
    transforms=receive_frame(ns)
    pixels=np.arange(393216,dtype=np.uint8).reshape(2,6,128,256)
    target=client.image_buffer();image=ns['Warp']()(pixels,transforms,output_buffer=target)
    assert image is (target if shared_on else pixels)
    mapping=client.shared
    packed=np.arange(65595,dtype=np.float32);packed[1]=-0.0
    if fault=='none':
        output=client.infer(image,packed,7);assert output.shape==(18580,)
        assert mapping is None or (not mapping.busy and mapping.generation==1)
    else:
        with pytest.raises((ValueError,ConnectionError,TimeoutError)):client.infer(image,packed,7)
        assert mapping is None or mapping.closed
    thread.join(timeout=2);assert not thread.is_alive() and not errors
    assert seen[0][0].tobytes()==sink.records[0][0].tobytes()
    assert seen[0][1][:12].tobytes()==b''.join(v.tobytes() for v in sink.records[0][1:4])
    assert cap.warped is None
    client.close();listener.close()
