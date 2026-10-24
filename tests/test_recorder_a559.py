"""Exact a559 offline source binding and reversible layouts; CPU_FAKE/FIXTURE."""
import ast
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from adapters.carrot import recorder_060de9 as previous
from recorder_810e_support import REFERENCE


def profile():
    return importlib.import_module('adapters.carrot.recorder_a559')


def test_distinct_a559_profile_required_without_mutating_060():
    assert importlib.util.find_spec('adapters.carrot.recorder_a559') is not None
    r=profile()
    assert r.BASE_SHA=='a559fcd971ccaa5a87befb8ec080f59a2966325b'
    assert r.PROFILE=='RECORDER_A559_EXECUTION_SWITCHES_V1'
    assert previous.BASE_SHA=='060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c'


def test_exact_range_sources_and_canonical_n16_contract():
    r=profile(); before=previous.sources(REFERENCE); after=r.sources(REFERENCE)
    assert {name for name in before if before[name]!=after[name]}=={
        r.MODEL,'openpilot/selfdrive/modeld/jetlink/link.py','openpilot/selfdrive/modeld/jetlink/daemon.py'}
    assert len(r.SOURCE_PINS)==30
    assert hashlib.sha256(r.canonical(json.loads(after[r.SPEC_FILE]))).hexdigest()==r.NAV_SPEC_SHA
    assert len(r.NAV_SPEC_SHA)==64
    assert r.NAV_MODEL_SHA==previous.NAV_MODEL_SHA
    assert len(subprocess.check_output(['git','-C',str(REFERENCE),'rev-list',previous.BASE_SHA+'..'+r.BASE_SHA]).splitlines())==6


def test_reused_hook_behavior_and_fresh_footer_only():
    r=profile(); a=previous.recorder_files(REFERENCE); b=r.recorder_files(REFERENCE)
    hook=r.PACKAGE+'/hook.py'
    behavior=lambda raw:[ast.dump(n) for n in ast.parse(raw).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
    assert behavior(a[hook])==behavior(b[hook])
    for name in ['__init__.py','recorder.py','dataset.py']:
        assert a[r.PACKAGE+'/'+name]==b[r.PACKAGE+'/'+name]
    assert b[r.MODEL]==r.sources(REFERENCE)[r.MODEL]+r.recorder_footer(b).encode()
    assert b[r.MODEL].count(r.PROFILE.encode())==1
    assert hashlib.sha256(b[hook]).hexdigest().encode() in b[r.MODEL]


@pytest.mark.parametrize('layout',['surviving366','cleana559'])
def test_migration_exact_forward_reverse_and_public_bytes(tmp_path,layout):
    r=profile(); out=tmp_path/'candidate'; manifest=r.build_candidate(REFERENCE,out,layout=layout)
    before,after=r.before_files(REFERENCE,layout),r.recorder_files(REFERENCE)
    root=tmp_path/'roundtrip';root.mkdir()
    for name,raw in before.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    stem='carrot-nav-a559-v3-input-recorder'+('' if layout=='surviving366' else '-clean')
    public=Path(__file__).resolve().parents[1]/'patches'
    for label,expected in [('forward',after),('reverse',before)]:
        patch=out/'.recordera559'/(label+'.patch')
        assert patch.read_bytes()==(public/(stem+('.reverse' if label=='reverse' else '')+'.patch')).read_bytes()
        subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
        subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
        assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}==expected
    assert len(manifest['touched_files'])==(3 if layout=='surviving366' else 6)
    assert manifest['base_sha']==r.BASE_SHA


@pytest.mark.parametrize('kind',['existing','reference','symlink'])
def test_candidate_refuses_destination_collision(tmp_path,kind):
    r=profile(); destination=tmp_path/'output'
    if kind=='existing':destination.mkdir();(destination/'user').write_bytes(b'keep')
    elif kind=='reference':destination=REFERENCE
    else:destination.symlink_to(REFERENCE,target_is_directory=True)
    with pytest.raises(ValueError):r.build_candidate(REFERENCE,destination)
    if kind=='existing':assert (destination/'user').read_bytes()==b'keep'
