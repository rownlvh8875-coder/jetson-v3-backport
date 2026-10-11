"""The installer-free experiment helper refuses unverified/dirty targets."""
import importlib.util
import json
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

def tool():
    sp=importlib.util.spec_from_file_location('experiment',ROOT/'tools/experimental_patch.py')
    m=importlib.util.module_from_spec(sp); sp.loader.exec_module(m); return m

def git(root,*args):
    return subprocess.check_output(['git','-C',str(root),*args])

@pytest.fixture
def tree(tmp_path):
    tmp_path=tmp_path/'checkout'
    tmp_path.mkdir()
    git(tmp_path,'init','-q')
    git(tmp_path,'config','core.autocrlf','false')
    (tmp_path/'value').write_bytes(b'old\n')
    git(tmp_path,'add','value')
    git(tmp_path,'-c','user.name=fixture','-c','user.email=fixture@example.invalid','commit','-qm','base')
    return tmp_path

def record(tree,tmp_path):
    import hashlib
    sha=lambda b:hashlib.sha256(b).hexdigest()
    (tree/'value').write_bytes(b'new\n')
    patch=git(tree,'diff','--binary')
    (tree/'value').write_bytes(b'old\n')
    patchfile=tmp_path/'experiment.patch'; patchfile.write_bytes(patch)
    return {'base_sha':git(tree,'rev-parse','HEAD').decode().strip(), 'patch':str(patchfile),
            'patch_sha256':sha(patch),'files':{'value':{'before_sha256':sha(b'old\n'),'after_sha256':sha(b'new\n')}}}

def test_apply_reverse_reapply_preserves_original(tree,tmp_path):
    t=tool(); r=record(tree,tmp_path)
    t.execute(tree,r,'preflight'); t.execute(tree,r,'apply')
    assert (tree/'value').read_bytes()==b'new\n'
    with pytest.raises(ValueError): t.execute(tree,r,'apply')
    t.execute(tree,r,'reverse')
    assert (tree/'value').read_bytes()==b'old\n' and not git(tree,'status','--porcelain')
    t.execute(tree,r,'apply')

@pytest.mark.parametrize('fault',['head','dirty','untracked','patch','modified_applied'])
def test_refuses_wrong_basis_and_preserves_user_data(tree,tmp_path,fault):
    t=tool(); r=record(tree,tmp_path)
    action='apply'
    if fault=='head': r['base_sha']='0'*40
    elif fault=='dirty': (tree/'value').write_bytes(b'user change\n')
    elif fault=='untracked': (tree/'user.txt').write_bytes(b'user change\n')
    elif fault=='patch': Path(r['patch']).write_bytes(b'corrupt')
    else:
        t.execute(tree,r,'apply'); (tree/'value').write_bytes(b'user change\n'); action='reverse'
    before={p.name:p.read_bytes() for p in tree.iterdir() if p.is_file()}
    with pytest.raises((ValueError,subprocess.CalledProcessError)): t.execute(tree,r,action)
    assert before=={p.name:p.read_bytes() for p in tree.iterdir() if p.is_file()}
