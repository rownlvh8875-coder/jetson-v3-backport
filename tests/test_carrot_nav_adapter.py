"""Actual source contract and managed selection CPU_FAKE/FIXTURE gates."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest
from adapters.carrot import nav

ROOT=Path(__file__).resolve().parents[1]
REFERENCE=Path(os.environ.get('CARROT_NAV_REFERENCE_ROOT',ROOT/'.reference/m05-carrot-nav-366d6eae'))


def check(body,root):
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH=os.pathsep.join((str(root/'third_party/jetlink'),str(root))))
    r=subprocess.run([sys.executable,'-c',body],env=env,cwd=root,capture_output=True,text=True,timeout=20)
    assert r.returncode==0,r.stdout+r.stderr


@pytest.fixture(scope='session')
def nav_candidate(tmp_path_factory):
    out=tmp_path_factory.mktemp('nav')/'candidate'
    manifest=nav.build_nav_candidate(REFERENCE,out)
    assert manifest['base_sha']=='366d6eae9aa9962104391e1d997fe956dea8f64d'
    return out


def test_actual_nav_dtype_roundtrip_preserves_legacy_pin_and_projection(nav_candidate):
    check('''
import json
from pathlib import Path
from jetlink.spec import ModelSpec
from jetlink import output_projection as p
from openpilot.selfdrive.modeld.jetlink.contracts import DEFAULT_SPEC,JETSON_SPEC
for spec in (DEFAULT_SPEC,JETSON_SPEC):
 assert 'input_dtypes' not in spec.to_dict() and 'output_dtypes' not in spec.to_dict()
 assert ModelSpec.from_dict(spec.to_dict()).to_dict()==spec.to_dict()
assert p.eligible(JETSON_SPEC) and len(JETSON_SPEC.state_pairs)==5
assert JETSON_SPEC.packed_nelem==65595 and JETSON_SPEC.output_nelem==18580
assert JETSON_SPEC.packed_shapes['nav_map']==(1,1,256,256)
assert JETSON_SPEC.packed_shapes['navigation']==(1,47)
raw=json.loads(Path('openpilot/selfdrive/modeld/jetlink/cinque_v3.json').read_text())
assert ModelSpec.from_dict(raw).to_dict()==raw
''',nav_candidate)


def test_only_six_reviewed_files_change_and_critical_nav_sources_untouched(nav_candidate):
    manifest=json.loads((nav_candidate/'.jetlink-candidate/manifest.json').read_text())
    assert len(manifest['touched_files'])==6
    for name in ('model.py','link.py','daemon.py','selection.py','contracts.py','warp.py','inputs.py'):
        path='openpilot/selfdrive/modeld/jetlink/'+name
        assert (nav_candidate/path).read_bytes()==(REFERENCE/path).read_bytes()
    for path in ('third_party/jetlink/jetlink/client.py','third_party/jetlink/jetlink/protocol.py','third_party/jetlink/jetlink/protocol_v3.py','third_party/jetlink/jetlink/queues.py','third_party/jetlink/jetlink/output_projection.py','openpilot/selfdrive/modeld/parse_model_outputs.py'):
        assert (nav_candidate/path).read_bytes()==(REFERENCE/path).read_bytes()
    for entry in manifest['touched_files']:
        assert hashlib.sha256((nav_candidate/entry['path']).read_bytes()).hexdigest()==entry['after_sha256']


def test_dispatch_precedes_exact_nav_legacy_branch_and_preserves_it(nav_candidate):
    path='openpilot/selfdrive/modeld/jetlink/mac.py'
    old=(REFERENCE/path).read_text();new=(nav_candidate/path).read_text()
    marker="  if is_jetson(peer):"
    assert new[new.index(marker):]==old[old.index(marker):]
    assert new.index('return prepare_managed(')<new.index(marker)


def test_unknown_managed_sha_is_rejected_before_client_or_approval(nav_candidate,monkeypatch):
    monkeypatch.setenv('CARROT_CANDIDATE_ROOT',str(nav_candidate))
    from test_current_carrot_adapter import run_check
    run_check("""
peer['loaded']='a'*64
try:prepare(True)
except ValueError:pass
else:raise AssertionError('unknown model adopted')
assert not client.calls and not list(cache.rglob('selected.json'))
""")


def test_managed_v3_v2_switch_and_legacy_nav_pin_are_distinct(nav_candidate,monkeypatch):
    monkeypatch.setenv('CARROT_CANDIDATE_ROOT',str(nav_candidate))
    from test_current_carrot_adapter import run_check
    run_check("""
prepare(True)
peer['loaded']=mac.SPEC.sha256;client.result=mac.SPEC
try:prepare(False)
except mac.PreparationDeferred:pass
else:raise AssertionError('onroad switch accepted')
assert prepare(True).sha256==mac.SPEC.sha256
peer.clear();peer.update(protocol=2,backend='trt',carrot_host='jetson')
client.result=mac.JETSON_SPEC
result=mac.prepare(client,peer,lambda:True,lambda:True,lambda *a:None,cache)
assert result.sha256==mac.JETSON_SPEC.sha256 and client.calls[-1][0]==mac.JETSON_SPEC.sha256
""")


def test_base_drift_rejected_before_candidate_creation(tmp_path,monkeypatch):
    monkeypatch.setattr(nav,'git',lambda root,*args:b'badbase\n' if args[0]=='rev-parse' else b'')
    with pytest.raises(ValueError,match='base'):nav.build_nav_candidate(REFERENCE,tmp_path/'out')
    assert not (tmp_path/'out').exists()


def test_collision_rejected(nav_candidate):
    with pytest.raises(ValueError):nav.build_nav_candidate(REFERENCE,nav_candidate)


def test_generated_patch_reverses_and_reapplies_exactly(nav_candidate,tmp_path):
    manifest=json.loads((nav_candidate/'.jetlink-candidate/manifest.json').read_text())
    patch=nav_candidate/'.jetlink-candidate/candidate.patch'
    assert hashlib.sha256(patch.read_bytes()).hexdigest()==manifest['patch_sha256']
    for entry in manifest['touched_files']:
        p=tmp_path/entry['path'];p.parent.mkdir(parents=True,exist_ok=True)
        p.write_bytes((nav_candidate/entry['path']).read_bytes())
    for args in (('--reverse','--check'),('--reverse',)):
        subprocess.run(['git','apply',*args,str(patch)],cwd=tmp_path,check=True,capture_output=True)
    for entry in manifest['touched_files']:
        p=tmp_path/entry['path']
        assert (not p.exists()) if entry['before_sha256'] is None else hashlib.sha256(p.read_bytes()).hexdigest()==entry['before_sha256']
    for args in (('--check',),()):
        subprocess.run(['git','apply',*args,str(patch)],cwd=tmp_path,check=True,capture_output=True)
    for entry in manifest['touched_files']:
        assert hashlib.sha256((tmp_path/entry['path']).read_bytes()).hexdigest()==entry['after_sha256']
