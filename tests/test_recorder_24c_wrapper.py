"""The unchanged explicit wrapper remains source-compatible on exact24c."""
import functools
import inspect

import numpy as np
import pytest

from adapters.carrot import recorder_24c as profile
from test_recorder_5bb_wrapper import wrapper


@pytest.mark.parametrize('form',['omitted','none','tuple','reset_keyword','reset_positional','all_positional','all_keyword','bare_defaults'])
def test_metadata_identity_and_single_observer_before_single_infer(form):
    trace=[];metadata=(0x7531,98765432101,99265432101);result=object()
    image=np.full((2,6,128,256),41,np.uint8);packed=np.arange(65595,dtype=np.float32)
    before=image.tobytes(),packed.tobytes();client=object()
    class Capture:
        def observe(self,owner,img,context,reset):
            trace.append('observe');assert owner is client and img is image and context is packed
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):
        trace.append(('infer',frame,reset,source_sof,nav_metadata));return result
    value=wrapper(profile,Capture(),original)
    args=[client,image,packed,19];kw=dict(source_sof=123);want=None;reset=False;sof=123
    if form=='none':kw['nav_metadata']=None
    elif form=='tuple':kw['nav_metadata']=metadata;want=metadata
    elif form=='reset_keyword':kw.update(reset=True,nav_metadata=metadata);reset=True;want=metadata
    elif form=='reset_positional':args.append(True);reset=True
    elif form=='all_positional':args.extend([True,123,metadata]);kw={};reset=True;want=metadata
    elif form=='all_keyword':args=[client];kw=dict(image=image,packed=packed,frame=19,reset=True,source_sof=123,nav_metadata=metadata);reset=True;want=metadata
    elif form=='bare_defaults':kw={};sof=0
    assert value(*args,**kw) is result
    assert trace[0]=='observe' and len(trace)==2
    assert trace[1][:4]==('infer',19,reset,sof) and trace[1][4] is want
    assert before==(image.tobytes(),packed.tobytes())
    assert value.__wrapped__ is original
    assert inspect.signature(value)==inspect.signature(original)==inspect.signature(value,follow_wrapped=False)


@pytest.mark.parametrize('key',['unsupported_nav','want_state','navmetadata'])
def test_unsupported_keywords_still_reject_before_any_observation(key):
    class Capture:
        def observe(self,*a):pytest.fail('unexpected observation')
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):pytest.fail('unexpected infer')
    with pytest.raises(TypeError,match='unexpected keyword argument'):
        wrapper(profile,Capture(),original)(object(),object(),object(),1,**{key:True})


@pytest.mark.parametrize('fault',['observer','original'])
def test_direct_wrapper_exception_preserved_without_retry(fault):
    trace=[];error=RuntimeError('unchanged '+fault)
    class Capture:
        def observe(self,*a):
            trace.append('observe')
            if fault=='observer':raise error
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):trace.append('infer');raise error
    with pytest.raises(RuntimeError) as caught:wrapper(profile,Capture(),original)(object(),object(),object(),1,nav_metadata=(1,2,3))
    assert caught.value is error
    assert trace==(['observe'] if fault=='observer' else ['observe','infer'])
