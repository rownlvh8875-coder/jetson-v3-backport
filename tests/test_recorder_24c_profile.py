"""Exact24c binding, wrong-source rejection, reversible surviving5bb migration."""
import ast
import hashlib
import importlib
import json
from pathlib import Path
import subprocess
import sys
import types

import pytest

from adapters.carrot import recorder_24c as r, recorder_5bb as old
from recorder_810e_support import REFERENCE
from test_v3_input_recorder import inputs, metadata, ready, finish


def behavior(raw):
    return ast.dump(ast.Module(body=[n for n in ast.parse(raw).body
        if isinstance(n,(ast.FunctionDef,ast.ClassDef))],type_ignores=[]))


def test_rebinding_keeps_every_recorder_function_and_four_fields():
    before,after=old.recorder_files(REFERENCE),r.recorder_files(REFERENCE)
    for leaf in ('hook.py','format.py','recorder.py','dataset.py','__init__.py'):
        name=r.PACKAGE+'/'+leaf
        assert behavior(before[name])==behavior(after[name])
    for leaf in ('__init__.py','recorder.py','dataset.py'):
        assert before[r.PACKAGE+'/'+leaf]==after[r.PACKAGE+'/'+leaf]
    assert after[r.MODEL]==r.sources(REFERENCE)[r.MODEL]+r.recorder_footer(after).encode()
    assert after[r.MODEL].count(b'RECORDER_24C_HUD_HOST_V1')==1
    assert b'RECORDER_5BB_DEFERRED_NAV_V1' not in after[r.MODEL]
    assert hashlib.sha256(after[r.PACKAGE+'/hook.py']).hexdigest().encode() in after[r.MODEL]


def test_exact24c_hotpath_n16_and_surviving5bb_pre():
    source,before=r.sources(REFERENCE),old.sources(REFERENCE)
    assert r.BASE_SHA=='24c1ba5e4b3428f56fa0e402f5a10097e2e94c32'
    assert len(source)==len(r.SOURCE_PINS)==41
    assert [n for n in old.SOURCE_PINS if source[n]!=before[n]]==['openpilot/selfdrive/modeld/jetlink/host_release.json']
    spec=json.loads(source[r.SPEC_FILE])
    assert hashlib.sha256(r.canonical(spec)).hexdigest()=='63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71'
    assert r.NAV_MODEL_SHA=='01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a'
    pre=r.before_files(REFERENCE,'surviving5bb')
    assert {n:raw for n,raw in pre.items() if n!=r.MODEL}=={n:raw for n,raw in old.recorder_files(REFERENCE).items() if n!=r.MODEL}
    assert pre[r.MODEL]==source[r.MODEL] and b'RECORDER_' not in pre[r.MODEL]


def test_disposable_migration_restores_pre_and_never_writes_index(tmp_path):
    out=tmp_path/'candidate';manifest=r.build_candidate(REFERENCE,out,layout='surviving5bb')
    tree=tmp_path/'pre';tree.mkdir()
    before,after=r.before_files(REFERENCE,'surviving5bb'),r.recorder_files(REFERENCE)
    for name,raw in before.items():
        p=tree/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    subprocess.run(['git','-C',str(tree),'init','-q'],check=True)
    subprocess.run(['git','-C',str(tree),'-c','core.autocrlf=false','add','.'],check=True)
    index=tree/'.git/index';index_before=index.read_bytes()
    for direction,expected in [('forward',after),('reverse',before)]:
        patch=out/'.recorder24c'/(direction+'.patch')
        for args in [('apply','--check'),('apply',)]:
            subprocess.run(['git','-C',str(tree),'-c','core.autocrlf=false',*args,str(patch)],check=True)
        actual={p.relative_to(tree).as_posix():p.read_bytes() for p in tree.rglob('*') if p.is_file() and '.git' not in p.relative_to(tree).parts}
        assert actual==expected
        assert index.read_bytes()==index_before
        for name,raw in expected.items():compile(raw,name,'exec',dont_inherit=True)
    assert {row['path'] for row in manifest['touched_files']}=={r.MODEL,r.PACKAGE+'/format.py',r.PACKAGE+'/hook.py'}
    assert manifest['layout']=='surviving5bb' and manifest['actual_deployment']=='NOT_RUN'
    assert manifest['dataset_fields']==['new_img','desire','traffic_convention','action_t']
    assert not manifest['state_tensors_stored']


@pytest.mark.parametrize('kind',['existing','reference','symlink','wrong_layout'])
def test_candidate_refuses_overwrite_reference_symlink_and_wrong_pre(tmp_path,kind):
    out=tmp_path/'out'
    if kind=='existing':out.mkdir();(out/'keep').write_bytes(b'preserved')
    elif kind=='reference':out=REFERENCE
    elif kind=='symlink':out.symlink_to(REFERENCE,target_is_directory=True)
    with pytest.raises(ValueError):
        r.build_candidate(REFERENCE,out,layout='survivinga559' if kind=='wrong_layout' else 'surviving5bb')
    if kind=='existing':assert (out/'keep').read_bytes()==b'preserved'


@pytest.fixture
def tree(tmp_path,monkeypatch):
    root=tmp_path/'profile';root.mkdir()
    for name,raw in {**r.sources(REFERENCE),**r.recorder_files(REFERENCE)}.items():
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    subprocess.run(['git','-C',str(root),'init','-q'],check=True)
    common=subprocess.check_output(['git','-C',str(REFERENCE),'rev-parse','--path-format=absolute','--git-common-dir']).decode().strip()
    (root/'.git/objects/info/alternates').write_text(str(Path(common)/'objects')+'\n')
    subprocess.run(['git','-C',str(root),'update-ref','HEAD',r.BASE_SHA],check=True)
    package=types.ModuleType('input_recording');package.__path__=[str(root/r.PACKAGE)]
    for key in list(sys.modules):
        if key=='input_recording' or key.startswith('input_recording.'):monkeypatch.delitem(sys.modules,key)
    monkeypatch.setitem(sys.modules,'input_recording',package)
    monkeypatch.syspath_prepend(str(root/Path(r.PACKAGE).parent))
    return root,importlib.import_module('input_recording.hook')


def test_exact_source_verifier_accepts24c(tree):
    root,hook=tree
    hook._verify_source({'__file__':str(root/r.MODEL)})


@pytest.mark.parametrize('name',[
 'openpilot/selfdrive/modeld/jetlink/model.py','openpilot/selfdrive/modeld/jetlink/link.py',
 'openpilot/selfdrive/modeld/jetlink/daemon.py','openpilot/selfdrive/modeld/jetlink/shared_input.py',
 'openpilot/selfdrive/modeld/jetlink/inputs.py','openpilot/selfdrive/modeld/jetlink/prepare.py',
 'openpilot/selfdrive/modeld/jetlink/jetson_model.json','openpilot/selfdrive/modeld/camera_gap.py',
 'openpilot/selfdrive/modeld/camera_sync.py','openpilot/selfdrive/modeld/modeld.py',
 'openpilot/system/manager/process.py','third_party/jetlink/jetlink/spec.py',
 'third_party/jetlink/jetlink/server/session.py','third_party/jetlink/jetlink/queues.py',
 'third_party/jetlink/jetlink/client.py','third_party/jetlink/jetlink/protocol.py',
 'third_party/jetlink/jetlink/request_chunks.py','third_party/jetlink/jetlink/packed_codec.py',
 'third_party/jetlink/jetlink/block_codec.py','third_party/jetlink/jetlink/transport/base.py',
 'third_party/jetlink/jetlink/transport/ffs.py','third_party/jetlink/jetlink/transport/request_writer.py',
 'third_party/jetlink/jetlink/transport/request_writer.c','tools/jetlink/host_reader.py',
 'tools/jetlink/host_usb.py','tools/jetlink/server.py','openpilot/selfdrive/modeld/jetlink/host_release.json',
 'openpilot/common/runtime_diagnostics.py','third_party/jetlink/jetlink/output_projection.py',
 'third_party/jetlink/jetlink/deferred_map.py','openpilot/selfdrive/navigation/map_client.py',
 'tools/jetlink/host_lpm.py','openpilot/selfdrive/modeld/jetlink/contracts.py',
 'openpilot/selfdrive/carrot/cluster/cluster_h264_pipeline.py','openpilot/selfdrive/carrot/cluster/main.py',
 'tools/jetlink/hud.py','tools/jetlink/hud_protocol.py','tools/jetlink/hud_camera.py',
 'tools/jetlink/hud_navi.py','tools/jetlink/hud_nav_map.py','openpilot/selfdrive/carrot/cluster/cluster_renderer.py'])
def test_each_inference_transport_hud_pin_drift_denies_before_ticket(tree,monkeypatch,name):
    root,hook=tree
    assert name in r.SOURCE_PINS
    p=root/name;p.write_bytes(p.read_bytes()+b'\n# offline drift\n')
    monkeypatch.setattr(hook,'_discovery_directory',lambda **kw:pytest.fail('ticket namespace reached'))
    with pytest.raises(ValueError):hook._verify_source({'__file__':str(root/r.MODEL)})
    with pytest.raises(ValueError):hook.arm_discovered(output_root=root,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA,offroad=True)


@pytest.mark.parametrize('kind',['old_head','removed_footer','hook','format'])
def test_updater_and_package_drift_fail_closed_without_repair(tree,monkeypatch,kind):
    root,hook=tree
    if kind=='old_head':subprocess.run(['git','-C',str(root),'update-ref','HEAD',old.BASE_SHA],check=True)
    elif kind=='removed_footer':(root/r.MODEL).write_bytes(r.sources(REFERENCE)[r.MODEL])
    else:(root/r.PACKAGE/(kind+'.py')).write_bytes(b'# offline replaced package\n')
    before={n:p.read_bytes() for n,p in [(r.MODEL,root/r.MODEL),(r.PACKAGE+'/hook.py',root/r.PACKAGE/'hook.py')]}
    monkeypatch.setattr(hook,'_discovery_directory',lambda **kw:pytest.fail('ticket namespace reached'))
    with pytest.raises(ValueError):hook.arm_discovered(output_root=root,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA,offroad=True)
    assert before=={n:(root/n).read_bytes() for n in before}


def test_no_ticket_means_no_import_copy_process_or_dataset(monkeypatch):
    import builtins
    paths=[];imports=[]
    def absent(path):paths.append(path);raise FileNotFoundError(path)
    def no_import(name,*args,**kw):imports.append(name);raise AssertionError('no-ticket import')
    monkeypatch.setattr(builtins,'__import__',no_import)
    scope={'os':types.SimpleNamespace(lstat=absent)}
    exec(r.FOOTER,scope)
    assert paths==['/dev/shm/carrot-v3-input-capture/arm.ticket'] and imports==[]
    assert '_m18_input_capture' not in scope


def test_strict24c_reader_preserves_four_fields_and_rejects5bb_binding(tree,tmp_path,capsys):
    root,hook=tree;recmod=importlib.import_module(hook.__package__+'.recorder')
    ticket=dict(schema=1,capture_id='b'*32,output_root=str(tmp_path),output=str(tmp_path/'dataset'),
        frames=3,depth=4,carrot_head=r.BASE_SHA,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA)
    rec=recmod.Recorder(tmp_path/'dataset',hook._provenance(ticket),frames=3)
    assert ready(rec),rec.reason
    data=inputs()
    for i in range(3):
        assert rec.observe(**data,metadata=metadata(i))
        import time;time.sleep(.02)
    finish(rec)
    with r.dataset_class(REFERENCE)(tmp_path/'dataset') as dataset:
        assert len(dataset)==3
        assert set(dataset.manifest['inputs'])=={'new_img','desire','traffic_convention','action_t'}
        assert dataset.manifest['provenance']['carrot_head']==r.BASE_SHA
        assert not dataset.manifest['state_tensors_stored']
        for i in range(3):assert {n:a.tobytes() for n,a in dataset.ort_feeds(i).items()}=={n:a.tobytes() for n,a in data.items()}
    with pytest.raises(ValueError):old.dataset_class(REFERENCE)(tmp_path/'dataset')
    from tools.v3_input_dataset_24c import main
    assert main(['validate',str(tmp_path/'dataset'),'--reference',str(REFERENCE)])==0
    assert json.loads(capsys.readouterr().out)['profile']=='RECORDER_24C_HUD_HOST_V1'


def test_existing_private_output_root_contract_needs_no_storage_migration(tree,tmp_path):
    _,hook=tree
    parent=tmp_path/'data';parent.mkdir();root=parent/'v3_input_capture';root.mkdir(mode=0o700)
    capture_id='d'*32
    # Pure validation only; neither output child nor synthetic ticket is created.
    value=hook._output_paths(dict(output_root=str(root),output=str(root/capture_id),capture_id=capture_id))
    assert value==root/capture_id
    assert list(root.iterdir())==[]
