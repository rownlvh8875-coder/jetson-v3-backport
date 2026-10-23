"""Offline provenance diagnostics; invented symbols, never actual private source."""
import ast
import copy
import hashlib
import importlib.util
import json
import marshal
from pathlib import Path
import struct
import subprocess
import sys

import pytest


def api():
    from tools import analyze_u32_provenance as tool
    return tool


SOURCE=b'''from dataclasses import dataclass
import example.messaging as messaging
SCHEMA_VERSION=6
@dataclass(frozen=True)
class DistinctInputSnapshot: value:int
class DistinctTraceObserver:
 def publish(self, pm):
  msg=messaging.new_message("distinctReplayMessage")
  pm.send("distinctReplayMessage",msg)
'''


def test_fingerprints_are_distinct_and_public_output_has_no_private_symbols():
    p=api().source_profile(SOURCE)
    assert p['category']=='OBSERVER_WITH_PUBLISH'
    assert len(p['fingerprints'])>=3
    assert len({x['value'] for x in p['fingerprints']})==len(p['fingerprints'])
    public=api().public_profile(p)
    assert 'DistinctTraceObserver' not in json.dumps(public)
    assert 'distinctReplayMessage' not in json.dumps(public)
    assert public['source_sha256']==hashlib.sha256(SOURCE).hexdigest()


def test_source_and_pyc_are_never_executed(tmp_path):
    marker=tmp_path/'must-not-exist'
    source=('open('+repr(str(marker))+',"w").write("bad")\n').encode()
    api().source_profile(source)
    if sys.version_info[:2]==(3,12):api().parse_pyc(pyc(source))
    assert not marker.exists()
    tree=ast.parse(Path(api().__file__).read_text())
    forbidden={'exec','eval','__import__','marshal.loads','marshal.load','types.CodeType'}
    assert not [n for n in ast.walk(tree) if isinstance(n,ast.Call) and ast.unparse(n.func) in forbidden]


def pyc(source=SOURCE):
    if sys.version_info[:2]!=(3,12):pytest.skip('fixture marshal format requires CPython3.12')
    return importlib.util.MAGIC_NUMBER+struct.pack('<III',0,100,len(source))+marshal.dumps(compile(source,'/private/example.py','exec',dont_inherit=True))


def test_pyc_code_metadata_and_header_are_data_only():
    result=api().parse_pyc(pyc())
    assert result['header']['mode']=='TIMESTAMP_BASED'
    assert result['header']['source_bytes']==len(SOURCE)
    assert result['code']['filename']=='/private/example.py'
    assert 'example.messaging' in result['code']['names']
    assert 'DistinctTraceObserver' in [c['name'] for c in result['code']['children']]
    assert result['executed'] is False


@pytest.mark.parametrize('flags',[1,3])
def test_pep552_hash_header(flags):
    b=pyc();b=b[:4]+struct.pack('<I',flags)+b'12345678'+b[16:]
    h=api().parse_pyc(b)['header']
    assert h['mode']=='HASH_BASED' and h['source_hash_hex']==b'12345678'.hex()


@pytest.mark.parametrize('fault',['magic','flags','truncated','trailing','length','reference','cycle','depth'])
def test_malformed_or_resource_unsafe_pyc_rejected(fault):
    b=pyc()
    if fault=='magic':b=b'nope'+b[4:]
    if fault=='flags':b=b[:4]+struct.pack('<I',2)+b[8:]
    if fault=='truncated':b=b[:25]
    if fault=='trailing':b+=b'garbage'
    if fault=='length':b=b[:16]+b's'+struct.pack('<i',2**30)
    if fault=='reference':b=b[:16]+b'r'+struct.pack('<i',999)
    if fault=='cycle':b=b[:16]+b'\xa9\x01r'+struct.pack('<i',0)
    if fault=='depth':b=b[:16]+b')\x01'*120+b'N'
    with pytest.raises(ValueError):api().parse_pyc(b)


def test_reference_context_separates_static_dynamic_and_generic():
    profile=api().source_profile(SOURCE)
    static=api().reference_context(b'from private.observer import DistinctTraceObserver\nx=DistinctTraceObserver()\n',profile,module='private.observer')
    assert any(r['kind']=='STATIC_IMPORT' for r in static)
    dynamic=api().reference_context(b'import importlib\nimportlib.import_module("private.observer")\n',profile,module='private.observer')
    assert any(r['kind']=='DYNAMIC_LITERAL_TARGET' for r in dynamic)
    unknown=api().reference_context(b'import importlib\nimportlib.import_module(selected_name)\n',profile,module='private.observer')
    assert any(r['kind']=='DYNAMIC_UNRESOLVED' for r in unknown)
    assert api().reference_context(b'obj.publish()\n',profile,module='private.observer')==[]


def proof():
    t=api()
    return dict(source_sha256=t.U32_SHA,baseline_digest=t.BASELINE,patch_sha256=t.PATCH,
                evidence_sha256='a'*64,requirements={k:True for k in t.REQUIREMENTS},
                blockers={k:False for k in t.BLOCKERS})


def test_accepted_unknown_requires_bound_complete_isolation_proof():
    p=proof();v=api().isolation_decision(p)
    assert v['proposal']=='U32_UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION'
    assert v['installation_authorized'] is False


@pytest.mark.parametrize('kind',['missing_requirement','unknown_requirement','blocker','unknown_blocker','wrong_source','wrong_baseline','wrong_patch','missing_evidence'])
def test_accepted_unknown_rejections(kind):
    p=proof()
    if kind=='missing_requirement':p['requirements'].pop(api().REQUIREMENTS[0])
    if kind=='unknown_requirement':p['requirements'][api().REQUIREMENTS[1]]='UNKNOWN'
    if kind=='blocker':p['blockers'][api().BLOCKERS[0]]=True
    if kind=='unknown_blocker':p['blockers'][api().BLOCKERS[1]]='UNKNOWN'
    if kind=='wrong_source':p['source_sha256']='b'*64
    if kind=='wrong_baseline':p['baseline_digest']='b'*64
    if kind=='wrong_patch':p['patch_sha256']='b'*64
    if kind=='missing_evidence':p.pop('evidence_sha256')
    assert api().isolation_decision(p)['proposal']=='HOLD'


def test_registration_or_external_mutation_is_not_certified_observer_only():
    p=api().source_profile(b'import controls\ncontrols.register_callback(handler)\ncontrols.input=value\n')
    assert p['registration_calls'] and p['external_assignments']
    assert p['category'] in ('MUTATING_RUNTIME_HELPER','CONTROL_RELEVANT','UNKNOWN')


def test_baseline_preservation_is_exact_and_does_not_mutate_inputs():
    a={'head':'a','entries':[{'tree_digest':'b'}],'flags':{'IsOffroad':'1'},'source_hashes':{'p':'c'},'model_hashes':{'m':'d'},'routes_inventory':{'sha256':'e'},'proc':{'processes':[{'pid':1}]},'inventory_digest':'f','tracked_status':[],'branch':'x','boot_id':'z'}
    b=copy.deepcopy(a);saved=copy.deepcopy(a)
    assert api().baseline_preserved(a,b)
    b['entries'][0]['tree_digest']='changed'
    assert not api().baseline_preserved(a,b) and a==saved


def test_shared_constant_graph_cannot_expand_without_bound(tmp_path):
    # Build data bytes directly: CodeType validation itself would traverse this
    # adversarial shared graph before our parser could be tested.
    def graph(depth,slot=0):
        return b'\xa9\x01N' if depth==0 else b'\xa9\x02'+graph(depth-1,slot+1)+b'r'+struct.pack('<i',slot+1)
    empty=b's'+struct.pack('<i',0)
    string=lambda s:b'z'+bytes([len(s)])+s
    payload=(b'c'+struct.pack('<iiiii',0,0,0,1,0)+empty+b')\x01'+graph(50)+
             b')\x00'*2+empty+string(b'fixture')+string(b'<module>')*2+struct.pack('<i',1)+empty*2)
    path=tmp_path/'graph.pyc';path.write_bytes(bytes.fromhex('cb0d0d0a')+struct.pack('<III',0,1,4)+payload)
    script='''import sys
from pathlib import Path
from tools.analyze_u32_provenance import parse_pyc
try:parse_pyc(Path(sys.argv[1]).read_bytes())
except ValueError:sys.exit(0)
sys.exit(3)
'''
    result=subprocess.run([sys.executable,'-B','-c',script,str(path)],capture_output=True,timeout=2)
    assert result.returncode==0


@pytest.mark.parametrize('field',['requirements','blockers'])
def test_malformed_policy_structure_is_hold(field):
    p=proof();p[field]=None
    assert api().isolation_decision(p)['proposal']=='HOLD'


def test_top_level_writes_and_singletons_are_not_pure_definitions():
    assert api().source_profile(b'open("fixture","w").write("x")\n')['category']!='PURE_DEFINITION_ONLY'
    p=api().source_profile(b'observer=factory()\n')
    assert p['module_singletons'] and p['category']=='UNKNOWN'


def test_definition_scope_signature_and_unbound_symbol_import_are_explicit():
    p=api().source_profile(SOURCE)
    method=next(d for d in p['definitions'] if d['name']=='publish')
    assert method['qualname']=='DistinctTraceObserver.publish' and 'pm' in method['parameters']
    rows=api().reference_context(b'from unrelated import DistinctTraceObserver\n',p,module='private.observer')
    assert not any(r['kind']=='STATIC_IMPORT' for r in rows)


def legacy_receipt():
    file=Path(__file__).resolve().parents[1]/'artifacts/m192_attested_dirty_baseline_20261024.json'
    return copy.deepcopy(json.loads(file.read_text())['attestation']['result'])


def composed_proof(receipt):
    p=proof();p['boundary_hashes']=dict(api().BOUNDARY_PINS)
    p['legacy_receipt_sha256']=api().receipt_digest(receipt)
    return p


def test_m193_scoped_policy_composes_without_faking_legacy_pass_or_runtime_absence():
    legacy=legacy_receipt();p=composed_proof(legacy);original=copy.deepcopy(legacy)
    result=api().compose_attestation(legacy,p,checker_sha256=api().FROZEN_CHECKER_SHA)
    assert result['status']=='ATTESTED_DIRTY_BASELINE_PASS'
    assert result['legacy_M192_status']=='ATTESTED_DIRTY_BASELINE_PARTIAL'
    assert result['policy']=='M193_SCOPED_ISOLATION_V1' and result['installation_authorized'] is False
    assert 'runtime_reference_absent' not in p and legacy==original


@pytest.mark.parametrize('fault',['legacy_drift','missing_check','extra_check','receipt_mismatch','checker_drift','boundary_drift','policy_hold'])
def test_composition_cannot_override_structural_failures_or_unbound_review(fault):
    legacy=legacy_receipt();p=composed_proof(legacy);checker=api().FROZEN_CHECKER_SHA
    if fault=='legacy_drift':legacy['checks']['EXACT_PRIVATE_INVENTORY']=False
    if fault=='missing_check':legacy['checks'].pop('OFFROAD')
    if fault=='extra_check':legacy['checks']['UNKNOWN_NEW_CHECK']=True
    if fault=='receipt_mismatch':p['legacy_receipt_sha256']='0'*64
    if fault=='checker_drift':checker='0'*64
    if fault=='boundary_drift':p['boundary_hashes']['B01']='0'*64
    if fault=='policy_hold':p['blockers'][api().BLOCKERS[0]]=True
    if fault in ('legacy_drift','missing_check','extra_check'):p['legacy_receipt_sha256']=api().receipt_digest(legacy)
    assert api().compose_attestation(legacy,p,checker_sha256=checker)['status']!='ATTESTED_DIRTY_BASELINE_PASS'


@pytest.mark.parametrize('bad',[None,[],{'status':float('nan')}])
def test_malformed_composition_is_anonymous_failure(bad):
    result=api().compose_attestation(bad,proof(),checker_sha256=api().FROZEN_CHECKER_SHA)
    assert result['status']=='ATTESTED_DIRTY_BASELINE_FAIL'
