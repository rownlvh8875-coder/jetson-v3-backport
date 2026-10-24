"""Source-backed exception/call-order equivalence; native Warp is CPU_FAKE."""
import ast
import importlib
import os
from pathlib import Path
import sys
import time
import types

import numpy as np
import pytest

from adapters.carrot import recorder_a559 as r
from recorder_810e_support import REFERENCE, Sink, fake_namespace, nav_spec, receive_frame


@pytest.fixture(scope='module')
def source():
    return r.sources(REFERENCE)


def selected(source, path, names, ns):
    nodes=[n for n in ast.parse(source[path]).body if isinstance(n,(ast.ClassDef,ast.FunctionDef)) and n.name in names]
    assert {n.name for n in nodes}==set(names)
    tree=ast.Module(body=[ast.ImportFrom(module='__future__',names=[ast.alias(name='annotations')],level=0),*nodes],type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree),path,'exec'),ns)
    return ns


def hook_package(tmp_path, monkeypatch):
    folder=tmp_path/'capture_a559_order';folder.mkdir()
    for path,raw in r.recorder_files(REFERENCE).items():
        if path.startswith(r.PACKAGE+'/'):(folder/Path(path).name).write_bytes(raw)
    monkeypatch.syspath_prepend(str(tmp_path))
    for name in list(sys.modules):
        if name=='capture_a559_order' or name.startswith('capture_a559_order.'):
            monkeypatch.delitem(sys.modules,name)
    return importlib.import_module('capture_a559_order.hook')


def runtime(source, monkeypatch, fault, wrapped, hook):
    calls=[];error=RuntimeError('original '+fault);pixels=np.zeros((2,6,128,256),np.uint8)
    class Result:
        shape=pixels.shape
        def numpy(self):
            calls.append('read')
            if fault=='warp':raise error
            return pixels
    monkeypatch.setitem(sys.modules,'tinygrad',types.SimpleNamespace(Tensor=types.SimpleNamespace(from_blob=lambda *a,**kw:object())))
    ns=selected(source,r.MODEL,['Warp'],dict(np=np,time=time))
    cls=ns['Warp'];warp=object.__new__(cls)
    warp.size=4;warp.blobs={};warp.inputs={};warp.transforms={k:np.eye(3,dtype=np.float32) for k in ('tfm','big_tfm')}
    def submit(**kw):calls.append('submit');return Result()
    warp.run_warp=submit
    spec=nav_spec()
    class Client:
        def __init__(self):self.spec=spec
        def image_buffer(self):calls.append('reserve');return None
        def infer(self,*args,**kw):
            calls.append('infer')
            if fault=='infer':raise error
            return np.zeros(18580,np.float32)
        def close(self):calls.append('close')
    actors=fake_namespace(spec);actors.update(Warp=cls,Client=Client)
    class Observer(Sink):
        def observe(self,*args):
            calls.append('observe')
            if fault=='observer':raise RuntimeError('recorder observer failed')
            return super().observe(*args)
    observer=Observer()
    cap=None
    if wrapped:
        cap=hook.install(actors,arm_path='fixture',ticket_loader=lambda _:dict(output='fixture',frames=5,depth=4,
            capture_id='b'*32,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA),
            source_verifier=lambda _:None,recorder_factory=lambda *a,**k:observer)
    client=actors['Client']()
    transforms=receive_frame(actors)
    real_fill=selected(source,'openpilot/selfdrive/modeld/jetlink/inputs.py',['fill_inputs'],dict(np=np))['fill_inputs']
    def fill(*args):
        calls.append('prepare')
        if fault=='prepare':raise error
        return real_fill(*args)
    joining_ns=selected(source,r.MODEL,['JoiningModel'],dict(np=np,os=os,time=time,fill_inputs=fill,
        parse_outputs=lambda *a:dict(output='original result'),model_name=lambda _: 'N16-fixture'))
    joining=object.__new__(joining_ns['JoiningModel'])
    joining.preparation=joining.connection=None;joining.warp=warp;joining.client=client
    joining.spec=spec;joining.packed=np.zeros(spec.packed_nelem,np.float32)
    joining.views={n:a.reshape(shape) for (n,shape),a in zip(spec.packed_shapes.items(),np.split(joining.packed,np.cumsum(spec.packed_sizes[:-1])),strict=True)}
    joining.prev_desire=np.zeros(8,np.float32);joining.small_runs=3;joining.ready=joining.join_allowed=True
    joining.next_join=joining.next_status=joining.frame=joining.source_sof=joining.last_slow_log=0
    joining.active=False;joining.reset=True;joining.error=''
    def fallback(*args):calls.append('fallback');return 'original fallback'
    joining.small=types.SimpleNamespace(run=fallback)
    joining.parser=object()
    inputs=dict(desire_pulse=np.eye(8,dtype=np.float32)[1],traffic_convention=np.array([[1,0]],np.float32),action_t=np.array([[.25,.75]],np.float32))
    bufs={k:types.SimpleNamespace(data=b'1234') for k in ('img','big_img')}
    return calls,error,joining,warp,client,bufs,transforms,inputs,cap


@pytest.mark.parametrize('overlap',[False,True])
@pytest.mark.parametrize('fault',['none','prepare','warp','infer','observer'])
def test_original_joining_call_order_and_fallback_preserved(source,tmp_path,monkeypatch,overlap,fault):
    monkeypatch.setenv('JETLINK_CPU_OVERLAP',str(int(overlap)))
    monkeypatch.delenv('SEND_RAW_PRED',raising=False)
    monkeypatch.setitem(sys.modules,'openpilot.common.swaglog',types.SimpleNamespace(cloudlog=types.SimpleNamespace(warning=lambda *a:None,exception=lambda *a:None)))
    h=hook_package(tmp_path,monkeypatch)
    results=[]
    for wrapped in (False,True):
        calls,error,joining,warp,client,bufs,transforms,inputs,cap=runtime(source,monkeypatch,fault,wrapped,h)
        result=joining.run(bufs,transforms,inputs,False)
        results.append((result,[c for c in calls if c!='observe'],joining.error,joining.frame,joining.reset))
        assert calls.count('prepare')==1
        assert calls.count('infer')==int(fault in ('none','infer','observer'))
        if fault=='prepare':
            assert calls==(['reserve','submit','prepare','read','close','fallback'] if overlap else ['prepare','close','fallback'])
        if fault in ('prepare','warp','infer'):
            assert result=='original fallback' and joining.error==str(error)
        else:assert result==dict(output='original result')
    assert results[0]==results[1]


@pytest.mark.parametrize('overlap',[False,True])
@pytest.mark.parametrize('fault',['prepare','warp','infer'])
def test_direct_original_exception_object_survives_wrapper(source,tmp_path,monkeypatch,overlap,fault):
    h=hook_package(tmp_path,monkeypatch)
    calls,error,joining,warp,client,bufs,transforms,inputs,cap=runtime(source,monkeypatch,fault,True,h)
    if fault=='infer':
        image=warp(bufs,transforms,prepare=None)
        with pytest.raises(RuntimeError) as caught:client.infer(image,joining.packed,1)
    else:
        def prepare():
            if fault=='prepare':raise error
        with pytest.raises(RuntimeError) as caught:
            if not overlap:prepare()
            warp(bufs,transforms,prepare=prepare if overlap else None)
    assert caught.value is error
    assert calls.count('read')==int(overlap or fault!='prepare')


def test_diagnostics_owned_telemetry_logging_failure_and_bad_type_boundary(source):
    ns={};exec(compile(source['openpilot/common/runtime_diagnostics.py'],'runtime_diagnostics.py','exec'),ns)
    frames=np.arange(24,dtype=np.float32);image=np.arange(64,dtype=np.uint8)
    before=(frames.tobytes(),image.tobytes());sequence=9
    events=[]
    diag=ns['RuntimeDiagnostics']('fixture',lambda *a,**kw:events.append(kw),interval=0,peak_metric='usb_exchange_ms')
    context=dict(frame_id=5,usb_seq=sequence)
    diag.record(context,usb_exchange_ms=4.5,local_ms=2.)
    context['frame_id']=6
    assert events[0]['peak_sample']['context']==dict(frame_id=5,usb_seq=9)
    def bad_logger(*a,**kw):raise RuntimeError('existing log failure')
    diag.emit=bad_logger
    assert diag.record(context,usb_exchange_ms=1.) is None
    assert before==(frames.tobytes(),image.tobytes()) and sequence==9
    # Internal programming errors are not covered by the emit-only exception
    # guard: characterize the existing behavior, without weakening any gate.
    with pytest.raises(TypeError):diag.record(context,usb_exchange_ms='invalid')
    daemon=ast.parse(source['openpilot/selfdrive/modeld/jetlink/daemon.py'])
    serve=next(n for n in daemon.body if isinstance(n,ast.FunctionDef) and n.name=='_serve_local')
    calls=[n for n in ast.walk(serve) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
    assert sum(n.func.attr=='infer_begin' for n in calls)==1
    assert sum(n.func.attr=='infer_end' for n in calls)==1
    assert not any(n.func.attr in ('infer','record') and isinstance(n.func.value,ast.Name) and n.func.value.id=='client' for n in calls)
