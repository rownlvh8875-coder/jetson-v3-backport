"""Distinct exact060de9 deployment/source binding; CPU_FAKE/FIXTURE only."""
import ast
import hashlib
import importlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from adapters.carrot import recorder_810e as old
from recorder_810e_support import REFERENCE


def profile():
    return importlib.import_module('adapters.carrot.recorder_060de9')


def test_distinct_profile_exists_without_changing_historical810e():
    assert importlib.util.find_spec('adapters.carrot.recorder_060de9') is not None
    r = profile()
    assert r.BASE_SHA == '060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c'
    assert r.PROFILE == 'RECORDER_060DE9_REQUEST_CHUNKS_V1'
    assert old.BASE_SHA == '810e14aaf51176f1a50a113939dc2e70907b394b'
    assert old.PROFILE == 'RECORDER_810E_SHARED_INPUT_V1'


def test_hot_path_and_n16_are_exact_unchanged_git_blobs():
    r = profile()
    before, after = old.sources(REFERENCE), r.sources(REFERENCE)
    for name in old.SOURCE_PINS:
        assert before[name] == after[name], name
    assert r.NAV_MODEL_SHA == old.NAV_MODEL_SHA
    assert hashlib.sha256(r.canonical(json.loads(after[r.SPEC_FILE]))).hexdigest() == old.NAV_SPEC_SHA
    assert set(r.TRANSPORT_PINS) <= set(r.SOURCE_PINS)


@pytest.mark.parametrize('layout', ['surviving366', 'clean060de9'])
def test_both_migrations_restore_exact_before_layout(tmp_path, layout):
    r = profile()
    out = tmp_path/'candidate'
    manifest = r.build_candidate(REFERENCE, out, layout=layout)
    before, after = r.before_files(REFERENCE, layout), r.recorder_files(REFERENCE)
    root = tmp_path/'roundtrip';root.mkdir()
    for name, raw in before.items():
        p = root/name;p.parent.mkdir(parents=True, exist_ok=True);p.write_bytes(raw)
    public = Path(__file__).resolve().parents[1]/'patches'
    stem = 'carrot-nav-060de9-v3-input-recorder' + ('' if layout=='surviving366' else '-clean')
    for label, expected in [('forward', after), ('reverse', before)]:
        patch = out/'.recorder060'/f'{label}.patch'
        assert patch.read_bytes() == (public/(stem+('.reverse' if label=='reverse' else '')+'.patch')).read_bytes()
        subprocess.run(['git','-C',str(root),'apply','--check',str(patch)],check=True)
        subprocess.run(['git','-C',str(root),'apply',str(patch)],check=True)
        assert {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()} == expected
    assert len(manifest['touched_files']) == (3 if layout=='surviving366' else 6)
    assert manifest['base_sha'] == r.BASE_SHA and manifest['profile'] == r.PROFILE


def test_generated_behavior_nodes_unchanged_and_new_footer_binding():
    r = profile();a,b = old.recorder_files(REFERENCE),r.recorder_files(REFERENCE)
    hook = r.PACKAGE+'/hook.py'
    def behavior(raw):
        return {n.name:ast.dump(n) for n in ast.parse(raw).body
                if isinstance(n,(ast.ClassDef,ast.FunctionDef))}
    assert behavior(a[hook]) == behavior(b[hook])
    for name in ('__init__.py','recorder.py','dataset.py'):
        assert a[r.PACKAGE+'/'+name] == b[r.PACKAGE+'/'+name]
    assert r.PROFILE.encode() in b[r.MODEL]
    assert b[r.MODEL] == r.sources(REFERENCE)[r.MODEL]+r.recorder_footer(b).encode()
    assert hashlib.sha256(b[hook]).hexdigest().encode() in b[r.MODEL]
