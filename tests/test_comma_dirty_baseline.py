"""CPU fixtures for exact private attestation; no device or production imports."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]
PATCH = (REPO / 'patches/carrot-nav-v3-input-recorder.patch').read_bytes()
M18 = json.loads((REPO / 'artifacts/m18_v3_input_recorder_validation_20261023.json').read_text())['manifest']


def api():
    from tools import check_comma_dirty_baseline as checker
    return checker


def fixture():
    c = api()
    entries = []
    for i in range(1, 49):
        node = dict(path=f'private/items/item{i:02d}', kind='file', mode=420,
                    uid=1000, gid=1000, mtime_ns=10, ctime_ns=11, bytes=1,
                    sha256=hashlib.sha256(bytes([i])).hexdigest(), git_blob_oid='1' * 40)
        entries.append(dict(id=f'U{i:02d}', path=node['path'], root=copy.deepcopy(node),
                            nodes=[node], regular_files=1, bytes=1,
                            tree_digest=c.digest([node])))
    snapshot = dict(branch='carrot-nav', head=c.BASE_SHA, flags={'IsOffroad':'1','IsOnroad':'0'},
                    tracked_status=[], entries=entries, inventory_digest=c.inventory_digest(entries),
                    recursive_regular_files=48, recursive_bytes=48,
                    source_hashes=dict(M18['source_pins']), model_hashes={'model.bin':'3'*64},
                    routes_inventory={'files':1,'sha256':'4'*64},
                    proc={'processes':[dict(pid=10,start_ticks='20',exe='/fixture/python',cwd='/fixture/root')],
                          'other_inaccessible_processes':[]}, nonce='a'*32,
                    boot_id='00000000-0000-0000-0000-000000000001',params_binding_digest='8'*64)
    files = copy.deepcopy(M18['touched_files'])
    classes = dict(c.BASELINE_CLASSES)
    provenance = {ident:dict(status=status,sha256=entries[int(ident[1:])-1]['root']['sha256'])
                  for ident,status in [('U32','SAFE_UNUSED_OBSERVER'),('U46','SAFE_GENERATED_LEGACY')]}
    expected = dict(schema=1, snapshot=copy.deepcopy(snapshot), classifications=classes,
                    provenance=provenance, patch={'sha256':c.PATCH_SHA,'files':files},
                    isolation=dict(status='PASS',baseline_digest=snapshot['inventory_digest'],
                                   patch_sha256=c.PATCH_SHA,evidence_sha256='6'*64,
                                   package_shadow=False,dynamic_import_risk='ASSESSED_NO_PATCH_OVERLAP'))
    return expected, snapshot


def check(expected, observed):
    return api().verify(expected, observed, patch=PATCH, challenge='a'*32)


def test_exact_fixture_pass_and_inputs_immutable():
    e,a=fixture();original=copy.deepcopy((e,a));r=check(e,a)
    assert r['status']=='ATTESTED_DIRTY_BASELINE_PASS'
    assert r['ready_to_retry_M19'] is True and (e,a)==original


@pytest.mark.parametrize('field,value', [('branch','other'),('head','0'*40),
    ('flags',{'IsOffroad':'0','IsOnroad':'1'}),('tracked_status',[' M source.py']),
    ('source_hashes',{'source.py':'f'*64}),('model_hashes',{'model.bin':'f'*64}),
    ('routes_inventory',{'files':2,'sha256':'4'*64}),('nonce','b'*32)])
def test_identity_and_preservation_drift_fail(field,value):
    e,a=fixture();a[field]=value
    assert check(e,a)['status']=='ATTESTED_DIRTY_BASELINE_FAIL'


@pytest.mark.parametrize('field,value',[('sha256','f'*64),('mode',384),('uid',0),('gid',0),
                                      ('mtime_ns',999),('ctime_ns',999),('bytes',2)])
def test_node_drift_even_with_recomputed_claimed_digest_fails(field,value):
    e,a=fixture();a['entries'][0]['nodes'][0][field]=value
    a['entries'][0]['root'][field]=value
    a['entries'][0]['tree_digest']=api().digest(a['entries'][0]['nodes'])
    a['inventory_digest']=api().inventory_digest(a['entries'])
    assert check(e,a)['status']=='ATTESTED_DIRTY_BASELINE_FAIL'


@pytest.mark.parametrize('action',['missing','extra','duplicate_id','duplicate_path','escape','symlink'])
def test_namespace_and_node_identity_drift_fail(action):
    e,a=fixture()
    if action=='missing':a['entries'].pop()
    elif action=='extra':a['entries'].append(copy.deepcopy(a['entries'][0]))
    elif action=='duplicate_id':a['entries'][1]['id']='U01'
    elif action=='duplicate_path':a['entries'][1]['path']=a['entries'][0]['path']
    elif action=='escape':a['entries'][0]['nodes'][0]['path']='../outside'
    else:a['entries'][0]['nodes'][0].update(kind='symlink',target='/private/outside')
    assert check(e,a)['status']=='ATTESTED_DIRTY_BASELINE_FAIL'


def test_process_generation_drift_fails():
    e,a=fixture();a['proc']['processes'][0]['start_ticks']='21'
    assert check(e,a)['status']=='ATTESTED_DIRTY_BASELINE_FAIL'


def test_same_PID_on_different_boot_is_rejected():
    e,a=fixture();a['boot_id']='00000000-0000-0000-0000-000000000002'
    assert check(e,a)['ready_to_retry_M19'] is False


def test_same_process_with_resolution_environment_drift_is_rejected():
    e,a=fixture();a['proc']['processes'][0]['resolution_env']={'PYTHONPATH':'/private/other-root'}
    assert check(e,a)['ready_to_retry_M19'] is False


@pytest.mark.parametrize('ident',['U32','U46'])
def test_unresolved_provenance_fails_gate(ident):
    e,a=fixture();e['provenance'][ident]['status']='USER_CUSTOM_UNKNOWN'
    r=check(e,a);assert r['status']=='ATTESTED_DIRTY_BASELINE_PARTIAL'
    assert r['ready_to_retry_M19'] is False


def test_unknown_cannot_be_accepted_with_boolean_or_unbound_claim():
    e,a=fixture();e['provenance']['U32'].update(status='USER_CUSTOM_UNKNOWN',accepted=True,
        decision='UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION')
    assert check(e,a)['ready_to_retry_M19'] is False


def test_explicit_reviewed_unknown_acceptance_is_exact_patch_and_baseline_bound():
    e,a=fixture();p=e['provenance']['U32']
    p.update(status='USER_CUSTOM_UNKNOWN',decision='UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION',
             baseline_digest=a['inventory_digest'],patch_sha256=api().PATCH_SHA,evidence_sha256='7'*64,
             path_disjoint=True,import_shadow_absent=True,runtime_reference_absent=True,
             target_overlap_absent=True,dynamic_import_risk='ASSESSED_NO_PATCH_OVERLAP')
    assert check(e,a)['ready_to_retry_M19'] is True  # reviewed hypothetical fixture, not actual U32
    for key in ('path_disjoint','import_shadow_absent','runtime_reference_absent','target_overlap_absent'):
        broken=copy.deepcopy(e);broken['provenance']['U32'][key]=False
        assert check(broken,a)['ready_to_retry_M19'] is False
    p['sha256']='0'*64;assert check(e,a)['ready_to_retry_M19'] is False


def test_classification_cannot_relabel_runtime_dependency():
    e,a=fixture();e['classifications']['U01']='SAFE_BACKUP_NOT_REFERENCED'
    assert check(e,a)['ready_to_retry_M19'] is False


def test_forged_matching_source_hashes_do_not_replace_M18_pins():
    e,a=fixture();e['snapshot']['source_hashes'][api().MODEL]=a['source_hashes'][api().MODEL]='f'*64
    assert check(e,a)['ready_to_retry_M19'] is False


def test_changed_after_hash_is_not_an_approved_patch_profile():
    e,a=fixture();e['patch']['files'][0]['after_sha256']='f'*64
    assert check(e,a)['ready_to_retry_M19'] is False


@pytest.mark.parametrize('part',['package_shadow','dynamic_import_risk','patch_binding','baseline_binding'])
def test_isolation_proof_fail_closed(part):
    e,a=fixture()
    key,value={'package_shadow':('package_shadow',True),'dynamic_import_risk':('dynamic_import_risk','UNKNOWN'),
               'patch_binding':('patch_sha256','0'*64),'baseline_binding':('baseline_digest','0'*64)}[part]
    e['isolation'][key]=value;assert check(e,a)['ready_to_retry_M19'] is False


def test_patch_bytes_and_target_collision_fail():
    e,a=fixture();assert api().verify(e,a,patch=PATCH+b'\n',challenge='a'*32)['ready_to_retry_M19'] is False
    target=e['patch']['files'][0]['path']
    for s in (e['snapshot'],a):
        row=s['entries'][0];row['path']=target
        row['root']['path']=row['nodes'][0]['path']=target
        row['tree_digest']=api().digest(row['nodes']);s['inventory_digest']=api().inventory_digest(s['entries'])
    e['isolation']['baseline_digest']=a['inventory_digest']
    assert check(e,a)['status']=='ATTESTED_DIRTY_BASELINE_FAIL'


def test_parent_package_collision_fail():
    e,a=fixture();parent=e['patch']['files'][0]['path'].rsplit('/',1)[0]
    for s in (e['snapshot'],a):
        row=s['entries'][0];row['path']=parent
        row['root']=row['nodes'][0]=dict(path=parent,kind='dir',mode=493,uid=1000,gid=1000,
            mtime_ns=10,ctime_ns=11,bytes=4096)
        row['regular_files']=row['bytes']=0;row['tree_digest']=api().digest(row['nodes'])
        s['recursive_regular_files']=s['recursive_bytes']=47;s['inventory_digest']=api().inventory_digest(s['entries'])
    assert check(e,a)['ready_to_retry_M19'] is False


def test_public_output_has_no_paths_argv_environment_or_source():
    e,a=fixture();a['proc']['processes'][0].update(argv=['private-secret'],resolution_env={'TOKEN':'private-secret'})
    output=json.dumps(check(e,a))
    assert 'private/' not in output and '/fixture/' not in output and 'private-secret' not in output
    assert all(row['path'] not in output for row in a['entries'])


def test_cli_requires_exact_private_manifest_digest_and_rejects_duplicate_json(tmp_path):
    e,a=fixture();ep=tmp_path/'expected.json';ap=tmp_path/'actual.json'
    ep.write_text(json.dumps(e));ap.write_text(json.dumps(a))
    args=[sys.executable,'-B',str(REPO/'tools/check_comma_dirty_baseline.py'),'verify',str(ep),str(ap),
          '--patch',str(REPO/'patches/carrot-nav-v3-input-recorder.patch'),'--expected-sha256',
          hashlib.sha256(ep.read_bytes()).hexdigest(),'--challenge','a'*32]
    good=subprocess.run(args,capture_output=True,text=True);assert good.returncode==0,good.stderr
    assert json.loads(good.stdout)['status']=='ATTESTED_DIRTY_BASELINE_PASS'
    args[-3]='0'*64;bad=subprocess.run(args,capture_output=True,text=True)
    assert bad.returncode!=0 and str(tmp_path) not in bad.stdout+bad.stderr
    assert api().load_json(b'{"x":1,"x":2}') is None


def test_collector_does_not_mutate_files_or_git_index(tmp_path):
    c=api();root=tmp_path/'repo';root.mkdir()
    subprocess.run(['git','init','-q','-b','carrot-nav',str(root)],check=True)
    (root/'tracked.py').write_text('value=1\n')
    subprocess.run(['git','-C',str(root),'add','tracked.py'],check=True)
    subprocess.run(['git','-C',str(root),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid',
                    'commit','-qm','fixture'],check=True)
    (root/'overlay').mkdir();(root/'overlay'/'data.bin').write_bytes(b'payload')
    params=tmp_path/'params';params.mkdir();(params/'IsOffroad').write_text('1');(params/'IsOnroad').write_text('0')
    models=tmp_path/'models';models.mkdir();(models/'weights.bin').write_bytes(b'weights')
    routes=tmp_path/'routes';routes.mkdir();(routes/'anonymous').write_bytes(b'route fixture')
    def state():return {str(p.relative_to(tmp_path)):(p.stat().st_mode,p.stat().st_size,p.stat().st_mtime_ns,p.stat().st_ctime_ns,
        hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None) for p in tmp_path.rglob('*')}
    before=state();out=c.collect(dict(root=str(root),params_root=str(params),model_root=str(models),
        route_root=str(routes),source_paths=['tracked.py'],nonce='a'*32))
    assert state()==before and out['tracked_status']==[]
    assert len(out['entries'])==1 and out['entries'][0]['regular_files']==1
    assert out['source_hashes']['tracked.py']==hashlib.sha256(b'value=1\n').hexdigest()
    assert out['inventory_digest']==c.inventory_digest(out['entries'])


def test_schema_is_public_and_has_no_concrete_device_paths():
    schema=json.loads((REPO/'artifacts/comma366_dirty_baseline_schema.json').read_text())
    assert schema['$schema'].startswith('https://json-schema.org/')
    assert '/data/' not in json.dumps(schema) and '192.168.' not in json.dumps(schema)


def test_collector_offroad_refusal_does_not_create_anything(tmp_path):
    root=tmp_path/'root';root.mkdir();params=tmp_path/'params';params.mkdir()
    (params/'IsOffroad').write_text('0');(params/'IsOnroad').write_text('1')
    before={str(p):p.stat().st_mtime_ns for p in tmp_path.rglob('*')}
    with pytest.raises(ValueError):api().collect({'root':str(root),'params_root':str(params),'nonce':'a'*32})
    assert before=={str(p):p.stat().st_mtime_ns for p in tmp_path.rglob('*')}


@pytest.mark.parametrize('path',['../escape','a/../../escape','/absolute','a\\b','.git/config'])
def test_private_relative_path_escape_is_rejected(path):
    with pytest.raises(ValueError):api()._relative(path)


def test_explicit_bound_Params_alias_read_is_readonly_and_drift_rejected(tmp_path):
    target=tmp_path/'target';target.mkdir();(target/'IsOffroad').write_text('1');(target/'IsOnroad').write_text('0')
    alias=tmp_path/'alias';alias.symlink_to(target,target_is_directory=True)
    cfg={'params_root':str(target),'params_alias':str(alias)}
    before=[(p.stat().st_mtime_ns,p.stat().st_ctime_ns,p.read_bytes()) for p in target.iterdir()]
    flags,binding=api().read_flags(cfg)
    assert flags=={'IsOffroad':'1','IsOnroad':'0'} and len(binding)==64
    assert before==[(p.stat().st_mtime_ns,p.stat().st_ctime_ns,p.read_bytes()) for p in target.iterdir()]
    other=tmp_path/'different';other.mkdir();alias.unlink();alias.symlink_to(other,target_is_directory=True)
    with pytest.raises(ValueError):api().read_flags(cfg)


def test_unapproved_Params_symlink_remains_rejected(tmp_path):
    target=tmp_path/'target';target.mkdir();alias=tmp_path/'alias';alias.symlink_to(target,target_is_directory=True)
    with pytest.raises(ValueError):api().read_flags({'params_root':str(alias)})


@pytest.mark.parametrize('field',['environment','classifications','isolation','provenance'])
def test_malformed_private_structure_returns_anonymous_failure(field):
    e,a=fixture()
    if field=='environment':a['proc']['processes'][0]['resolution_env']=None
    else:e[field]=None
    result=check(e,a)
    assert result['status']=='ATTESTED_DIRTY_BASELINE_FAIL'
    assert 'private/' not in json.dumps(result)
