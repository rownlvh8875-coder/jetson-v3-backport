"""RECORDER_810E_SHARED_INPUT_V1, CPU_FAKE/FIXTURE only; no device access."""
import copy
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types
import os
import time

import numpy as np
import pytest

from adapters.carrot import recorder_810e as r
from recorder_810e_support import package, nav_spec, ticket, fake_namespace, Sink, receive_frame

REFERENCE = Path(__file__).resolve().parents[1] / '.reference/m15-carrot-nav-366d6eae'


def test_exact_source_and_nav_contract():
    source = r.sources(REFERENCE)
    assert hashlib.sha256(source[r.MODEL]).hexdigest() == '103dc0c7eb1b4998ddbf0a498be55ffd02fd51b195ce20cb7ea44ba3dbce6c42'
    assert r.BASE_SHA == '810e14aaf51176f1a50a113939dc2e70907b394b'
    assert r.PROFILE == 'RECORDER_810E_SHARED_INPUT_V1'
    assert hashlib.sha256(r.canonical(json.loads(source[r.SPEC_FILE]))).hexdigest() == r.NAV_SPEC_SHA


def test_original_joining_model_calls_one_buffer_one_warp_and_same_images():
    from recorder_810e_support import blob
    tree=ast.parse(blob(r.MODEL))
    cls=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='JoiningModel')
    run=next(n for n in cls.body if isinstance(n,ast.FunctionDef) and n.name=='run')
    calls=[n for n in ast.walk(run) if isinstance(n,ast.Call)]
    reservations=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='image_buffer']
    warps=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='warp']
    inferences=[n for n in calls if isinstance(n.func,ast.Attribute) and n.func.attr=='infer']
    assert len(reservations)==len(warps)==len(inferences)==1
    assert next(k.value for k in warps[0].keywords if k.arg=='output_buffer') is reservations[0]
    assignment=next(n for n in ast.walk(run) if isinstance(n,ast.Assign) and n.value is warps[0])
    assert assignment.targets[0].id==inferences[0].args[0].id=='images'


def test_distinct_profile_preserves_historical_sources():
    files = r.recorder_files(REFERENCE)
    assert len(files) == 6
    assert r.BASE_SHA.encode() in files[r.PACKAGE + '/format.py']
    assert r.NAV_SPEC_SHA.encode() in files[r.PACKAGE + '/hook.py']
    assert b'output_buffer=output_buffer' in files[r.PACKAGE + '/hook.py']
    assert b'366d6eae' not in files[r.PACKAGE + '/format.py']
    from recording import format as old_format, hook as old_hook
    assert old_format.BASE_SHA == old_hook.BASE_SHA == '366d6eae9aa9962104391e1d997fe956dea8f64d'


@pytest.mark.parametrize('layout', ['surviving366', 'clean810e'])
def test_migration_roundtrip(tmp_path, layout):
    manifest = r.build_candidate(REFERENCE, tmp_path / 'candidate', layout=layout)
    before, after = r.before_files(REFERENCE, layout), r.recorder_files(REFERENCE)
    import subprocess
    target = tmp_path / 'roundtrip';target.mkdir()
    for n,b in before.items():
        q=target/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    patch=tmp_path/'candidate/.recorder810/forward.patch'
    reverse=patch.with_name('reverse.patch')
    stem='carrot-nav-810e-v3-input-recorder'+('' if layout=='surviving366' else '-clean')
    public=Path(__file__).resolve().parents[1]/'patches'
    assert (public/(stem+'.patch')).read_bytes()==patch.read_bytes()
    assert (public/(stem+'.reverse.patch')).read_bytes()==reverse.read_bytes()
    for p, expected in ((patch, after),(reverse,before)):
        subprocess.run(['git','-C',str(target),'apply','--check',str(p)],check=True)
        subprocess.run(['git','-C',str(target),'apply',str(p)],check=True)
        assert {q.relative_to(target).as_posix():q.read_bytes() for q in target.rglob('*') if q.is_file()} == expected
    assert manifest['profile']==r.PROFILE
    assert len(manifest['touched_files']) == (3 if layout=='surviving366' else 6)


def test_actual_n16_not_old_nonstate_contract(tmp_path, monkeypatch):
    h = package(tmp_path, monkeypatch)
    spec = nav_spec()
    assert spec.stateful and len(spec.state_pairs) == 5
    contract = h._contract(spec, ticket(h, tmp_path))
    assert contract[2] == 65595
    assert contract[1] == ((0, 8, (8,)), (8, 10, (1, 2)), (10, 12, (1, 2)))


def test_borrowed_alias_and_scalar_bits(tmp_path, monkeypatch):
    h = package(tmp_path, monkeypatch); ns = fake_namespace(); sink = Sink()
    cap = h.install(ns, arm_path='fixture', ticket_loader=lambda _:ticket(h,tmp_path),
                    source_verifier=lambda _:None, recorder_factory=lambda *a,**k:sink)
    assert cap is not None
    client = ns['Client'](); assert not cap.disabled
    transforms = receive_frame(ns)
    image = np.arange(393216,dtype=np.uint8).reshape(2,6,128,256)
    shared = np.zeros_like(image)
    packed = np.arange(65595,dtype=np.float32);packed[1] = -0.0
    saved = packed[:12].tobytes()
    result = ns['Warp']()(image,transforms,output_buffer=shared)
    assert result is shared
    assert client.infer(result,packed,1) is client
    assert client.calls[0][0] is shared
    assert sink.identities == [id(shared)]
    assert sink.records[0][0].tobytes() == shared.tobytes() == image.tobytes()
    assert b''.join(x.tobytes() for x in sink.records[0][1:4]) == saved
    assert cap.warped is None


@pytest.mark.parametrize('change', ['sha','spec','pair','packed_order','packed_size'])
def test_contract_rejects_unreviewed_source(tmp_path, monkeypatch, change):
    h = package(tmp_path,monkeypatch); spec = copy.deepcopy(nav_spec())
    value = ticket(h,tmp_path)
    if change == 'sha': value['source_model_sha'] = '0'*64
    elif change == 'spec': value['source_spec_sha'] = '0'*64
    elif change == 'pair': spec.output_shapes.pop('next_state_map_features_q')
    else:
        class Altered(type(spec)):
            @property
            def packed_shapes(self):
                fields = super().packed_shapes
                return dict(reversed(tuple(fields.items()))) if change == 'packed_order' else dict(fields, navigation=(1,48))
        spec = Altered.from_dict(spec.to_dict())
    with pytest.raises(ValueError): h._contract(spec,value)


def test_off_ignores_legacy_environment_and_changes_nothing(tmp_path,monkeypatch):
    h = package(tmp_path,monkeypatch); ns=fake_namespace()
    before = tuple(ns[n].__dict__.copy() for n in ('Warp','Client','CameraGapTrace'))
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE','forbidden')
    def forbidden(*a,**k): pytest.fail('OFF did enabled work')
    assert h.install(ns,ticket_loader=forbidden,recorder_factory=forbidden,source_verifier=forbidden) is None
    assert before == tuple(ns[n].__dict__.copy() for n in ('Warp','Client','CameraGapTrace'))


def test_no_ticket_footer_checks_once_without_package_import(monkeypatch):
    import builtins
    called=[]
    def absent(path):called.append(path);raise FileNotFoundError(path)
    original=builtins.__import__
    def guarded(name,*a,**kw):
        assert 'input_recording' not in name
        return original(name,*a,**kw)
    monkeypatch.setattr(builtins,'__import__',guarded)
    namespace={'os':types.SimpleNamespace(lstat=absent)}
    exec(r.FOOTER,namespace)
    assert called==['/dev/shm/carrot-v3-input-capture/arm.ticket']
    assert '_m18_input_capture' not in namespace


def test_candidate_never_overwrites_destination(tmp_path):
    target=tmp_path/'user';target.mkdir();(target/'keep').write_bytes(b'original')
    with pytest.raises(ValueError):r.build_candidate(REFERENCE,target)
    assert list(target.iterdir())==[target/'keep']
    assert (target/'keep').read_bytes()==b'original'


def source_tree(tmp_path,h,monkeypatch):
    root=tmp_path/'source'
    files=r.sources(REFERENCE); files.update(r.recorder_files(REFERENCE))
    for n,b in files.items():
        q=root/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    original=h.subprocess.check_output
    monkeypatch.setattr(h.subprocess,'check_output',lambda argv,**kw:
                        r.BASE_SHA.encode()+b'\n' if argv[-2:]==['rev-parse','HEAD'] else original(argv,**kw))
    return root


@pytest.mark.parametrize('drift',['none','footer_lost','link','context'])
def test_whole_patched_source_and_arming_preflight(tmp_path,monkeypatch,drift):
    h=package(tmp_path,monkeypatch); root=source_tree(tmp_path,h,monkeypatch)
    if drift == 'footer_lost': (root/r.MODEL).write_bytes(r.sources(REFERENCE)[r.MODEL])
    elif drift in ('link','context'):
        n='openpilot/selfdrive/modeld/jetlink/link.py' if drift=='link' else 'openpilot/system/manager/process.py'
        q=root/n;q.write_bytes(q.read_bytes()+b'\n# drift\n')
    ns={'__file__':str(root/r.MODEL)}
    if drift=='none': h._verify_source(ns)
    else:
        with pytest.raises(ValueError):h._verify_source(ns)
    # No discovery directory/arm file may be made if the source/footer is lost.
    monkeypatch.setattr(h,'__file__',str(root/r.PACKAGE/'hook.py'))
    def reached(*a,**kw): raise AssertionError('filesystem arming reached')
    monkeypatch.setattr(h,'_discovery_directory',reached)
    if drift!='none':
        with pytest.raises(ValueError):h.arm_discovered(output_root=tmp_path,source_model_sha=r.NAV_MODEL_SHA,
                                                     source_spec_sha=r.NAV_SPEC_SHA,offroad=True)


@pytest.mark.parametrize('name',r.PACKAGE_FILES)
@pytest.mark.parametrize('missing',[False,True])
def test_every_recorder_module_drift_denies_arm_before_ticket(tmp_path,monkeypatch,name,missing):
    h=package(tmp_path,monkeypatch);root=source_tree(tmp_path,h,monkeypatch)
    q=root/r.PACKAGE/name
    if missing:q.unlink()
    else:q.write_bytes(q.read_bytes()+b'\n# unexpected package drift\n')
    with pytest.raises((ValueError,OSError)):h._verify_source({'__file__':str(root/r.MODEL)})
    monkeypatch.setattr(h,'__file__',str(root/r.PACKAGE/'hook.py'))
    monkeypatch.setattr(h,'_discovery_directory',lambda **kw:pytest.fail('ticket namespace touched after profile drift'))
    with pytest.raises((ValueError,OSError)):h.arm_discovered(output_root=tmp_path,source_model_sha=r.NAV_MODEL_SHA,
                                                 source_spec_sha=r.NAV_SPEC_SHA,offroad=True)


@pytest.fixture
def activation(tmp_path,monkeypatch):
    h=package(tmp_path,monkeypatch)
    directory=tmp_path/'volatile'/'capture';directory.parent.mkdir()
    monkeypatch.setattr(h,'DISCOVERY_DIRECTORY',directory)
    monkeypatch.setattr(h,'_require_volatile_parent',lambda:None)
    monkeypatch.setattr(h,'_verify_source',lambda ns:None)
    monkeypatch.setattr(h,'_modeld_import_context',lambda ns:True)
    monkeypatch.setattr(h,'_boot_id',lambda:'fixture-boot')
    return h


def arm(h,tmp_path):
    out=tmp_path/'private';out.mkdir(exist_ok=True)
    return h.arm_discovered(output_root=out,source_model_sha=r.NAV_MODEL_SHA,
        source_spec_sha=r.NAV_SPEC_SHA,offroad=True,frames=10)


@pytest.mark.parametrize('fault',['valid','expired','boot','source','spec','malformed','moved','symlink','fifo'])
def test_discovery_security_and_terminal_restart(activation,tmp_path,fault):
    h=activation; value=arm(h,tmp_path); path=h.DISCOVERY_DIRECTORY/'arm.ticket'
    if fault in ('expired','boot','source','spec'):
        if fault=='expired':
            value['armed_monotonic_ns']=0;value['expires_monotonic_ns']=1
        elif fault=='boot':value['boot_id']='wrong'
        elif fault=='source':value['carrot_head']='0'*40
        else:value['source_spec_sha']='0'*64
        path.write_bytes(h.canonical(value))
    elif fault=='malformed':path.write_bytes(b'{invalid')
    elif fault=='moved':
        value['ticket_path']=str(path)+'other';path.write_bytes(h.canonical(value))
    elif fault in ('symlink','fifo'):
        path.unlink()
        if fault=='symlink':path.symlink_to(tmp_path/'absent')
        else:os.mkfifo(path)
    ns=fake_namespace();sink=Sink()
    state=h.install_discovered(ns,recorder_factory=lambda *a,**k:sink)
    if fault=='valid':
        assert state is not None
        ns['Client']();assert not state.disabled
        assert not path.exists()
        state.stop('fixture writer failure')
    else:
        # A spec-mismatched ticket must not start a writer, even before Client.
        assert state is None
    assert h.install_discovered(fake_namespace(),recorder_factory=lambda *a,**k:pytest.fail('second writer')) is None


@pytest.mark.parametrize('fault',['writer','output_collision'])
def test_setup_failure_preserves_inference(activation,tmp_path,fault):
    h=activation;value=arm(h,tmp_path)
    ns=fake_namespace(); original=ns['Client'].infer
    def factory(*a,**k):raise OSError(fault)
    assert h.install_discovered(ns,recorder_factory=factory) is None
    assert ns['Client'].infer is original
    assert h.install_discovered(fake_namespace(),recorder_factory=factory) is None
