"""Real disposable Git identity, expanded source attestation and strict replay."""
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

from adapters.carrot import recorder_5bb as r,recorder_060de9 as old
from recorder_810e_support import REFERENCE
from test_v3_input_recorder import inputs,metadata,ready,finish


def package(root,monkeypatch):
    name='input_recording'
    package=types.ModuleType(name);package.__path__=[str(root/r.PACKAGE)]
    for key in list(sys.modules):
        if key==name or key.startswith(name+'.'):monkeypatch.delitem(sys.modules,key)
    monkeypatch.setitem(sys.modules,name,package)
    monkeypatch.syspath_prepend(str(root/Path(r.PACKAGE).parent))
    return importlib.import_module(name+'.hook')


@pytest.fixture
def tree(tmp_path,monkeypatch):
    root=tmp_path/'profile';root.mkdir()
    for name,raw in {**r.sources(REFERENCE),**r.recorder_files(REFERENCE)}.items():
        path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    subprocess.run(['git','-C',str(root),'init','-q'],check=True)
    common=subprocess.check_output(['git','-C',str(REFERENCE),'rev-parse','--path-format=absolute','--git-common-dir']).decode().strip()
    (root/'.git/objects/info/alternates').write_text(str(Path(common)/'objects')+'\n')
    subprocess.run(['git','-C',str(root),'update-ref','HEAD',r.BASE_SHA],check=True)
    h=package(root,monkeypatch)
    return root,h


def test_exact_5bb_prearm_profile_with_real_git_identity(tree):
    root,h=tree
    h._verify_source({'__file__':str(root/r.MODEL)})


@pytest.mark.parametrize('name',list(r.SOURCE_PINS))
def test_transport_source_drift_blocks_before_ticket_creation(tree,monkeypatch,name):
    root,h=tree
    target=root/name;target.write_bytes(target.read_bytes()+b'\n# drift\n')
    with pytest.raises(ValueError):h._verify_source({'__file__':str(root/r.MODEL)})
    monkeypatch.setattr(h,'_discovery_directory',lambda **kw:pytest.fail('arming reached after transport drift'))
    with pytest.raises(ValueError):
        h.arm_discovered(output_root=root,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA,offroad=True)


@pytest.mark.parametrize('drift',['head','footer','hook'])
def test_updater_or_package_drift_denies_arm_without_repatch(tree,monkeypatch,drift):
    root,h=tree
    if drift=='head':subprocess.run(['git','-C',str(root),'update-ref','HEAD',old.BASE_SHA],check=True)
    elif drift=='footer':(root/r.MODEL).write_bytes(r.sources(REFERENCE)[r.MODEL])
    else:(root/r.PACKAGE/'hook.py').write_bytes(b'# replaced hook\n')
    before={n:p.read_bytes() for n,p in [(r.MODEL,root/r.MODEL),(r.PACKAGE+'/hook.py',root/r.PACKAGE/'hook.py')]}
    monkeypatch.setattr(h,'_discovery_directory',lambda **kw:pytest.fail('ticket namespace touched'))
    with pytest.raises(ValueError):h.arm_discovered(output_root=root,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA,offroad=True)
    assert before=={n:(root/n).read_bytes() for n in before}


def test_default_off_without_ticket_does_not_import_capture_package(monkeypatch):
    import builtins
    calls=[]
    def absent(path):calls.append(path);raise FileNotFoundError(path)
    original=builtins.__import__
    def guarded(name,*a,**kw):
        assert 'input_recording' not in name
        return original(name,*a,**kw)
    monkeypatch.setattr(builtins,'__import__',guarded)
    ns={'os':types.SimpleNamespace(lstat=absent)}
    exec(r.FOOTER,ns)
    assert calls==['/dev/shm/carrot-v3-input-capture/arm.ticket']
    assert '_m18_input_capture' not in ns


def test_5bb_dataset_exact_reader_and_wrong_profile_denial(tree,tmp_path,capsys):
    root,h=tree
    module=importlib.import_module(h.__package__+'.recorder')
    value=dict(schema=1,capture_id='b'*32,output_root=str(tmp_path),output=str(tmp_path/'dataset'),
        frames=3,depth=4,carrot_head=r.BASE_SHA,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA)
    rec=module.Recorder(tmp_path/'dataset',h._provenance(value),frames=3)
    assert ready(rec),rec.reason
    data=inputs()
    for i in range(3):
        assert rec.observe(**data,metadata=metadata(i))
        import time;time.sleep(.02)
    finish(rec)
    with r.dataset_class(REFERENCE)(tmp_path/'dataset') as dataset:
        for i in range(3):
            assert {n:a.tobytes() for n,a in dataset.ort_feeds(i).items()}=={n:a.tobytes() for n,a in data.items()}
        assert dataset.manifest['provenance']['carrot_head']==r.BASE_SHA
    with pytest.raises(ValueError):old.dataset_class(REFERENCE)(tmp_path/'dataset')
    from tools.v3_input_dataset_5bb import main
    assert main(['validate',str(tmp_path/'dataset'),'--reference',str(REFERENCE)])==0
    assert json.loads(capsys.readouterr().out)['profile']==r.PROFILE


@pytest.mark.parametrize('kind',['missing','empty_git'])
def test_reader_bad_reference_returns_json_failure(tmp_path,capsys,kind):
    from tools.v3_input_dataset_5bb import main
    reference=tmp_path/'invalid-reference'
    if kind=='empty_git':
        reference.mkdir();subprocess.run(['git','-C',str(reference),'init','-q'],check=True)
    assert main(['validate',str(tmp_path/'absent-dataset'),'--reference',str(reference)])==1
    assert json.loads(capsys.readouterr().out)['status']=='FAIL'
