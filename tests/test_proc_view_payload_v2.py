import hashlib
import json
from pathlib import Path
import subprocess
import sys

import pytest

from tools.proc_view_capability import build_payload


def bundle(forbid_load=False):
    root=Path(__file__).resolve().parents[1]
    names=('proc_view_scope_model','pinned_proc_view','proc_view_capability')
    sources={n:(root/'tools'/f'{n}.py').read_bytes() for n in names}
    sources['pinned_proc_view']=(b'raise RuntimeError("BUNDLE_EXECUTED")\n' if forbid_load else b'''
class AcquisitionError(RuntimeError):pass
class ProcView:
    def __init__(self,**kwargs):raise AcquisitionError("UNSUPPORTED_NATIVE")
''')
    pins={n:hashlib.sha256(v).hexdigest() for n,v in sources.items()}
    return build_payload(sources,pins)


def run(script,flags=('-B',)):
    return subprocess.run([sys.executable,'-E',*flags,'-c',script],capture_output=True,timeout=5,check=True)


def test_v2_payload_emits_closed_fixed_failure_fields():
    value=json.loads(run(bundle()['script']).stdout)
    assert value['schema']==2 and value['reason_code']=='UNSUPPORTED_NATIVE'
    assert value['failure_phase']=='CONSTRUCT' and value['errno_code']=='NONE'


@pytest.mark.parametrize('flags',[('-O','-B'),('-OO','-B'),()])
def test_runtime_guard_precedes_all_bundled_module_execution(flags):
    output=run(bundle(forbid_load=True)['script'],flags)
    value=json.loads(output.stdout)
    assert value['schema']==2 and value['status']=='BLOCKED_RUNTIME_FLAGS'
    assert value['failure_phase']=='RUNTIME' and value['events']==0
    assert value['reason_code']==('BYTECODE_ENABLED' if not flags else 'OPTIMIZED_INTERPRETER')
    assert b'BUNDLE_EXECUTED' not in output.stdout+output.stderr


def test_identity_rejection_is_also_schema2_without_private_data():
    payload=bundle();pin=payload['source_pins']['pinned_proc_view']
    value=json.loads(run(payload['script'].replace(pin,'0'*64,1)).stdout)
    assert value['schema']==2 and value['status']=='BLOCKED_PAYLOAD_IDENTITY'
    assert value['reason_code']=='PAYLOAD_IDENTITY' and value['failure_phase']=='PAYLOAD'
    assert value['evidence_kind']=='NO_ACQUISITION' and value['policy_acceptance'] is False


def test_payload_restores_aliases_and_bytecode_flag_after_rejection():
    payload=bundle(forbid_load=True)
    script='''import sys,types
names=('tools','tools.proc_view_scope_model','tools.pinned_proc_view','tools.proc_view_capability')
saved={n:sys.modules.get(n) for n in names}
before=sys.dont_write_bytecode
exec(SCRIPT)
if any(sys.modules.get(n) is not v for n,v in saved.items()) or sys.dont_write_bytecode!=before:
    raise RuntimeError('ALIASES_NOT_RESTORED')
'''.replace('SCRIPT',repr(payload['script']))
    value=json.loads(run(script).stdout)
    assert value['schema']==2 and value['status']=='BLOCKED_PAYLOAD_EXECUTION'
