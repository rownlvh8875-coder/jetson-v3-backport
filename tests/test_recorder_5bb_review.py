"""Exact5bb review regressions: expected a559 API rejection is not compatibility.

No profile generator, deployment patch, device access, or ticket is produced.
"""
import ast
import functools
import hashlib
import inspect
import json
import subprocess
from types import SimpleNamespace

import numpy as np
import pytest

from adapters.carrot import recorder_a559 as historical
from recorder_810e_support import REFERENCE

TARGET = '5bbbe160822c7cae4245d7a8e96b40d158941ff7'


def exact(path):
    return subprocess.check_output(['git','-C',str(REFERENCE),'show',TARGET+':'+path])


def infer_wrapper(capture, original):
    raw=historical.recorder_files(REFERENCE)[historical.PACKAGE+'/hook.py']
    assert hashlib.sha256(raw).hexdigest()=='1e82abdfc93ab23f7add69c8f248677538ec2c20b47868b7bc06cb0195a18256'
    node,=[n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.FunctionDef) and n.name=='infer']
    namespace=dict(capture=capture,original_infer=original,functools=functools)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),
                 '<unchanged-a559-wrapper>','exec'),namespace)
    return namespace['infer']


@pytest.mark.parametrize('nav_metadata',[None,(77,100,500)])
@pytest.mark.parametrize('disabled',[False,True])
def test_unchanged_hook_rejects_new_keyword_before_any_observation(nav_metadata,disabled):
    calls=[]
    capture=SimpleNamespace(disabled=disabled,observe=lambda *a:calls.append('observe'))
    def original(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None):
        calls.append('infer')
    wrapped=infer_wrapper(capture,original)
    # functools.wraps' reported signature can hide the incompatible closure.
    assert 'nav_metadata' in inspect.signature(wrapped).parameters
    assert 'nav_metadata' not in inspect.signature(wrapped,follow_wrapped=False).parameters
    image=np.full((2,6,128,256),37,np.uint8)
    packed=np.arange(65595,dtype=np.float32)
    before=image.tobytes(),packed.tobytes()
    with pytest.raises(TypeError,match="unexpected keyword argument 'nav_metadata'"):
        wrapped(object(),image,packed,1,nav_metadata=nav_metadata)
    assert calls==[] and before==(image.tobytes(),packed.tobytes())


def test_unchanged_hook_control_without_keyword_observes_and_forwards_once():
    calls=[];result=object()
    capture=SimpleNamespace(observe=lambda *a:calls.append(('observe',a)))
    def original(*args,**kwargs):
        calls.append(('infer',args,kwargs));return result
    wrapped=infer_wrapper(capture,original)
    image=object();packed=object();client=object()
    assert wrapped(client,image,packed,9,True,source_sof=17) is result
    assert [row[0] for row in calls]==['observe','infer']
    assert calls[0][1]==(client,image,packed,True)
    assert calls[1][1]==(client,image,packed,9,True) and calls[1][2]==dict(source_sof=17)


def test_exact_range_n16_and_host_contract_are_separate_from_recorder_compatibility():
    behind,ahead=subprocess.check_output(['git','-C',str(REFERENCE),'rev-list','--left-right','--count',
        historical.BASE_SHA+'...'+TARGET]).decode().split()
    assert (behind,ahead)==('0','10')
    spec=json.loads(exact(historical.SPEC_FILE))
    assert spec['sha256']==historical.NAV_MODEL_SHA
    assert hashlib.sha256(historical.canonical(spec)).hexdigest()==historical.NAV_SPEC_SHA
    release=json.loads(exact('openpilot/selfdrive/modeld/jetlink/host_release.json'))
    assert release['source_commit']=='0fb6c73926ef8d54f8434108bd060d47de011cbe'
    assert release['bundle']['sha256']=='2f51b10b2d6a356d39e0d923e66633a3e80c5b92096603713b39fa540db40162'
    assert release['bundle']['size']==64748504


def test_exact_default_keyword_even_without_map_and_no_footer_repair():
    tree=ast.parse(exact(historical.MODEL))
    option,=[n for n in ast.walk(tree) if isinstance(n,ast.Assign)
              and any(isinstance(t,ast.Name) and t.id=='map_options' for t in n.targets)]
    expression=compile(ast.Expression(option.value),'<exact-map-options>','eval')
    for value in (None,(77,100,500)):
        model=SimpleNamespace(client=SimpleNamespace(deferred_nav=True),nav_metadata=value)
        assert eval(expression,dict(self=model))==dict(nav_metadata=value)
    link=ast.parse(exact('openpilot/selfdrive/modeld/jetlink/link.py'))
    selection=next(n.value for n in ast.walk(link) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Attribute) and t.attr=='deferred_nav' for t in n.targets))
    getenv=next(n for n in ast.walk(selection) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Attribute) and n.func.attr=='getenv')
    assert [ast.literal_eval(v) for v in getenv.args]==['JETLINK_DEFER_NAV','1']
    pure=exact(historical.MODEL)
    assert b'RECORDER_' not in pure and b'input_recording' not in pure
    assert historical.BASE_SHA!=TARGET
