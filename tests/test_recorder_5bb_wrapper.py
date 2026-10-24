"""Exact5bb explicit metadata forwarding; accepted calls must reach real wrapper.

The observed bug is argument binding before observe/infer. Historical a559 is
a negative control; fixed5bb must preserve arguments/order instead of retrying.
"""
import ast
import functools
import inspect

import numpy as np
import pytest

from adapters.carrot import recorder_a559 as historical
from adapters.carrot import recorder_5bb as target
from recorder_810e_support import REFERENCE


def wrapper(profile,capture,original):
    raw=profile.recorder_files(REFERENCE)[profile.PACKAGE+'/hook.py']
    node,=[n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name=='infer']
    namespace=dict(capture=capture,original_infer=original,functools=functools)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),
                 '<generated-infer-wrapper>','exec'),namespace)
    return namespace['infer']


@pytest.mark.parametrize('form',['omitted','none','tuple','reset_keyword','reset_positional','all_positional','all_keyword','bare_defaults'])
def test_exact_metadata_call_reaches_observer_then_original_once(form):
    calls=[];metadata=(0x7531,98765432101,99265432101);result=object()
    image=np.full((2,6,128,256),41,np.uint8);packed=np.arange(65595,dtype=np.float32)
    before=image.tobytes(),packed.tobytes()
    class Capture:
        def observe(self,client,observed_image,observed_packed,reset):
            calls.append(('observe',client,observed_image,observed_packed,reset))
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):
        calls.append(('infer',self,image,packed,frame,reset,source_sof,nav_metadata))
        return result
    value=wrapper(target,Capture(),original);client=object()
    args=[client,image,packed,19];kwargs=dict(source_sof=123)
    expected=None;expected_reset=False;expected_sof=123
    if form=='none':kwargs['nav_metadata']=None
    elif form=='tuple':kwargs['nav_metadata']=metadata;expected=metadata
    elif form=='reset_keyword':kwargs.update(reset=True,nav_metadata=metadata);expected=metadata;expected_reset=True
    elif form=='reset_positional':args.append(True);expected_reset=True
    elif form=='all_positional':args.extend([True,123,metadata]);kwargs={};expected=metadata;expected_reset=True
    elif form=='all_keyword':
        args=[client];kwargs=dict(image=image,packed=packed,frame=19,reset=True,source_sof=123,nav_metadata=metadata)
        expected=metadata;expected_reset=True
    elif form=='bare_defaults':kwargs={};expected_sof=0
    assert value(*args,**kwargs) is result
    assert [row[0] for row in calls]==['observe','infer']
    assert calls[0][1] is client and calls[0][2] is image and calls[0][3] is packed
    row=calls[1]
    assert row[1] is client and row[2] is image and row[3] is packed
    assert row[4:7]==(19,expected_reset,expected_sof)
    assert row[7] is expected
    assert before==(image.tobytes(),packed.tobytes())


def test_wraps_retains_original_and_reports_real_explicit_signature():
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):pass
    value=wrapper(target,object(),original)
    assert value.__wrapped__ is original
    assert inspect.signature(value)==inspect.signature(original)
    assert inspect.signature(value,follow_wrapped=False)==inspect.signature(original)
    assert inspect.signature(value).parameters['nav_metadata'].default is None


@pytest.mark.parametrize('key',['unsupported_nav','want_state','navmetadata'])
def test_unsupported_argument_rejected_without_observation_or_original(key):
    calls=[]
    class Capture:
        def observe(self,*args):calls.append('observe')
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):
        calls.append('infer')
    value=wrapper(target,Capture(),original)
    with pytest.raises(TypeError,match='unexpected keyword argument'):
        value(object(),object(),object(),1,**{key:True})
    assert calls==[]


def test_historical_negative_control_still_exposes_original_incompatibility():
    class Capture:
        def observe(self,*args):pytest.fail('historical observer body reached')
    def original(*args,**kwargs):pytest.fail('historical original reached')
    value=wrapper(historical,Capture(),original)
    with pytest.raises(TypeError,match='nav_metadata'):
        value(object(),object(),object(),1,nav_metadata=None)
