"""Current comma approval behavior, isolated from the backport package namespace."""
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

REPO = Path(__file__).resolve().parents[1]


def run_check(body):
    root = Path(os.environ.get('CARROT_CANDIDATE_ROOT', REPO / '.candidate/current')).resolve()
    assert (root / 'openpilot/selfdrive/modeld/jetlink/mac.py').is_file(), 'build candidate first'
    setup = '''
import copy, json, tempfile
from pathlib import Path
from types import SimpleNamespace as NS
from openpilot.selfdrive.modeld.jetlink import mac, selection
from openpilot.common.jetlink_peer import is_managed_jetson_peer
from jetlink.spec import ModelSpec
raw = json.loads(Path(ARTIFACT).read_text())
spec = ModelSpec.from_dict(raw)
peer = {'protocol':3, 'backend':'trt', 'device':'CPU_FAKE', 'carrot_host':'jetson',
        'carrot_model_selection_v1':{'version':1, 'selection':'host'}, 'loaded':spec.sha256}
class Client:
  def __init__(self, result=spec):
    self.result=result; self.spec=None; self.t=NS(); self.calls=[]
    self.progress_cb=None; self._should_stop=lambda:False
  def state(self): return {'loaded':peer['loaded']}
  def ensure_engine(self, sha, nbytes, **kwargs):
    self.calls.append((sha,nbytes,kwargs))
    if hasattr(self.t, 'check'): self.t.check()
    self.spec=self.result
    return self.result
client=Client()
def prepare(offroad=True, target=client):
  return mac.prepare(target, peer, lambda:offroad, lambda:True, lambda *a:None, cache)
'''.replace('ARTIFACT', repr(str(REPO / 'artifacts/cinque_v3.json')))
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=os.pathsep.join((str(root / 'third_party/jetlink'), str(root))))
    source = setup + '\nwith tempfile.TemporaryDirectory() as directory:\n  cache=Path(directory)\n' + '\n'.join('  '+line for line in body.splitlines())
    result = subprocess.run([sys.executable, '-c', source], env=env, cwd=root,
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr


def test_first_model_approved_only_offroad_and_exact_reconnect():
    run_check('''
try: prepare(False)
except mac.PreparationDeferred: pass
else: raise AssertionError('onroad first adoption accepted')
assert not client.calls
assert prepare(True).sha256 == spec.sha256
assert selection.approved_spec(cache / 'managed-jetson').to_dict() == spec.to_dict()
assert prepare(False).to_dict() == spec.to_dict()
assert len(client.calls) == 2
''')


def test_same_sha_changed_spec_rejected_without_overwriting_approval():
    run_check('''
prepare(True)
changed=copy.deepcopy(raw); changed['checkpoint']='unexpected'
client.result=ModelSpec.from_dict(changed)
try: prepare(False)
except ValueError: pass
else: raise AssertionError('changed approved contract accepted')
assert selection.approved_spec(cache / 'managed-jetson').checkpoint == spec.checkpoint
''')


@pytest.mark.parametrize('change', ["peer['loaded']=None", "peer['loaded']='BAD'", "peer['carrot_model_selection_v1']['version']=True", "peer['carrot_model_selection_v1']['version']=2", "peer['backend']='ort'"])
def test_malformed_or_unloaded_managed_peer_cannot_fall_into_legacy(change):
    run_check(change + '''
try: prepare(True)
except (ValueError, mac.PreparationDeferred): pass
else: raise AssertionError('invalid managed identity accepted')
assert not client.calls
''')


def test_live_identity_change_before_approval_rejected():
    run_check('''
client.state=lambda:{'loaded':'a'*64}
try: prepare(True)
except selection.ModelChanged: pass
else: raise AssertionError('stale HELLO model accepted')
assert not client.calls
''')


def test_ready_wrong_sha_size_and_invalid_spec_rejected():
    run_check('''
for field,value in [('sha256','a'*64),('nbytes',0),('input_shapes',dict(raw['input_shapes'],new_img=[2,6,256,128]))]:
  changed=copy.deepcopy(raw); changed[field]=value
  client.result=ModelSpec.from_dict(changed)
  try: prepare(True)
  except ValueError: pass
  else: raise AssertionError('invalid ready contract accepted: '+field)
assert not (cache/'managed-jetson/selected.json').exists()
''')


def test_known_v3_identity_requires_exact_seed_contract():
    run_check('''
for field,value in [('nbytes',spec.nbytes+1),('checkpoint','wrong'),('input_dtypes',dict(raw['input_dtypes'],new_img='float16'))]:
  changed=copy.deepcopy(raw); changed[field]=value
  client.result=ModelSpec.from_dict(changed)
  try: prepare(True)
  except ValueError: pass
  else: raise AssertionError('known V3 identity mismatch accepted: '+field)
''')


def test_missing_engine_never_downloads_or_selects_another_big_model():
    run_check('''
from jetlink.client import EngineMissing
def missing(*a,**kw): raise EngineMissing('CPU fixture missing engine')
client.ensure_engine=missing
mac.model_file=lambda *a,**kw: (_ for _ in ()).throw(AssertionError('download attempted'))
try: prepare(True)
except mac.PreparationDeferred: pass
else: raise AssertionError('missing engine did not defer')
assert not (cache/'managed-jetson/selected.json').exists()
''')


def test_v2_v3_switch_requires_offroad_and_legacy_v2_path_stays_fixed():
    run_check('''
prepare(True)
peer['loaded']=mac.SPEC.sha256; client.result=mac.SPEC
try: prepare(False)
except mac.PreparationDeferred: pass
else: raise AssertionError('onroad V3 to V2 switch accepted')
assert prepare(True).sha256 == mac.SPEC.sha256
peer['loaded']=spec.sha256; client.result=spec
try: prepare(False)
except mac.PreparationDeferred: pass
else: raise AssertionError('onroad V2 to V3 switch accepted')
assert prepare(True).sha256 == spec.sha256
peer.clear(); peer.update(protocol=2, backend='trt',carrot_host='jetson')
client.result=mac.SPEC
mac.prepare(client,peer,lambda:True,lambda:True,lambda *a:None,cache)
assert client.calls[-1][0] == mac.SPEC.sha256
''')
