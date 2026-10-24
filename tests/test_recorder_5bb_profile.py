"""Fixed5bb source/profile binding and exact reversible expected PRE layouts."""
import ast
import copy
import hashlib
import json
from pathlib import Path
import subprocess

import pytest

from adapters.carrot import recorder_5bb as r,recorder_a559 as old
from recorder_810e_support import REFERENCE

BEFORE={
'__init__.py':'e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca',
'format.py':'f0bf4d1abbbc8bc89e02213198743d507fd57a6546a85b48f54fd46ea346cd25',
'recorder.py':'d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada',
'dataset.py':'25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7',
'hook.py':'1e82abdfc93ab23f7add69c8f248677538ec2c20b47868b7bc06cb0195a18256',
}


def behavior(raw):
    return ast.Module(body=[n for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))],type_ignores=[])


def test_only_infer_acceptance_and_forwarding_changes_behavior():
    before,after=old.recorder_files(REFERENCE),r.recorder_files(REFERENCE)
    hook=r.PACKAGE+'/hook.py'
    original=behavior(before[hook]);expected=copy.deepcopy(original)
    node,=[n for n in ast.walk(expected) if isinstance(n,ast.FunctionDef) and n.name=='infer']
    node.args.args.append(ast.arg(arg='nav_metadata'));node.args.defaults.append(ast.Constant(value=None))
    call,=[n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='original_infer']
    call.keywords.append(ast.keyword(arg='nav_metadata',value=ast.Name(id='nav_metadata',ctx=ast.Load())))
    assert ast.dump(behavior(after[hook]))==ast.dump(expected)
    for name in ('__init__.py','recorder.py','dataset.py'):
        assert before[r.PACKAGE+'/'+name]==after[r.PACKAGE+'/'+name]
    assert after[r.MODEL]==r.sources(REFERENCE)[r.MODEL]+r.recorder_footer(after).encode()
    assert after[r.MODEL].count(r.PROFILE.encode())==1
    assert hashlib.sha256(after[hook]).hexdigest().encode() in after[r.MODEL]


def test_exact33_sources_n16_and_historical_expected_pre():
    assert len(r.SOURCE_PINS)==33
    source=r.sources(REFERENCE)
    assert hashlib.sha256(source[r.MODEL]).hexdigest()=='6e04d29bca6b1802ecc012f8f8ea154f28ec7854961dbf4fd4b6b963328eccee'
    assert hashlib.sha256(r.canonical(json.loads(source[r.SPEC_FILE]))).hexdigest()==r.NAV_SPEC_SHA
    pre=r.before_files(REFERENCE,'survivinga559')
    assert {n:hashlib.sha256(pre[r.PACKAGE+'/'+n]).hexdigest() for n in BEFORE}==BEFORE
    assert b'RECORDER_' not in pre[r.MODEL]


@pytest.mark.parametrize('layout',['survivinga559','clean5bb'])
def test_disposable_forward_reverse_restores_exact_pre(tmp_path,layout):
    out=tmp_path/'candidate';manifest=r.build_candidate(REFERENCE,out,layout=layout)
    root=tmp_path/'layout';root.mkdir()
    before,after=r.before_files(REFERENCE,layout),r.recorder_files(REFERENCE)
    for name,raw in before.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    for direction,expected in [('forward',after),('reverse',before)]:
        patch=out/'.recorder5bb'/(direction+'.patch')
        subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
        subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
        assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}==expected
        for name,raw in expected.items():compile(raw,name,'exec',dont_inherit=True)
    assert {row['path'] for row in manifest['touched_files']}==(
        {r.MODEL,r.PACKAGE+'/format.py',r.PACKAGE+'/hook.py'} if layout=='survivinga559' else set(after))
    assert manifest['dataset_fields']==['new_img','desire','traffic_convention','action_t']
    assert manifest['state_tensors_stored'] is False


@pytest.mark.parametrize('kind',['existing','reference','symlink','wrong_layout'])
def test_candidate_does_not_overwrite_or_guess_pre(tmp_path,kind):
    out=tmp_path/'out'
    if kind=='existing':out.mkdir();(out/'keep').write_bytes(b'preserved')
    elif kind=='reference':out=REFERENCE
    elif kind=='symlink':out.symlink_to(REFERENCE,target_is_directory=True)
    with pytest.raises(ValueError):
        r.build_candidate(REFERENCE,out,layout='surviving366' if kind=='wrong_layout' else 'survivinga559')
    if kind=='existing':assert (out/'keep').read_bytes()==b'preserved'
