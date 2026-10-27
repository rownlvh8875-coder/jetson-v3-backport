import errno
import json
import subprocess
import sys

import pytest

from tools.pinned_proc_view import AcquisitionError
from tools.proc_view_capability import probe_capability


class View:
    def __init__(self,audit_sink):self.sink=audit_sink
    def __enter__(self):return self
    def __exit__(self,*args):pass
    def scope(self):return {'endpoint_checks_pass':True}


def rejected(error):
    def factory(**kwargs):raise error
    return probe_capability(view_factory=factory)


@pytest.mark.parametrize('reason',['UNSUPPORTED_ABI','UNSUPPORTED_NATIVE','UNSUPPORTED_MOUNT_ID',
    'THREAD_PROFILE','NOT_PROCFS','SELF_MAPPING_UNSUPPORTED','FD_IDENTITY_CHANGED','CLEANUP_FAILED'])
def test_known_exact_reasons_are_projected_without_raw_errors(reason):
    out=rejected(AcquisitionError(reason))
    assert out['schema']==2 and out['reason_code']==reason
    assert out['failure_phase']=='CONSTRUCT' and out['errno_code']=='NONE'
    assert out['status']=='BLOCKED_NATIVE_CAPABILITY' and out['policy_acceptance'] is False


@pytest.mark.parametrize('number,code',[(errno.ENOENT,'ENOENT'),(errno.EACCES,'EACCES'),
    (errno.EPERM,'EPERM'),(errno.ENOSYS,'ENOSYS'),(errno.EINVAL,'EINVAL'),(99999,'OTHER')])
def test_os_error_projects_only_fixed_errno_symbol(number,code):
    out=rejected(OSError(number,'secret description','/private/secret-path'))
    assert out['reason_code']=='NATIVE_OS_ERROR' and out['errno_code']==code
    assert 'secret' not in json.dumps(out) and '/private' not in json.dumps(out)


@pytest.mark.parametrize('error,code',[(AcquisitionError('secret detail'),'UNKNOWN_ACQUISITION'),
    (ValueError('secret value'),'VALUE_ERROR'),(RuntimeError('secret runtime'),'UNEXPECTED_EXCEPTION')])
def test_unknown_errors_never_echo_text_or_type_name(error,code):
    out=rejected(error)
    assert out['reason_code']==code and 'secret' not in json.dumps(out)
    assert type(error).__name__ not in json.dumps(out)


def test_exception_string_is_not_called_by_public_projection():
    class PrivateError(RuntimeError):
        def __str__(self):raise AssertionError('do not stringify')
    out=rejected(PrivateError('secret'))
    assert out['reason_code']=='UNEXPECTED_EXCEPTION'


@pytest.mark.parametrize('phase',['ENTER','SCOPE','CLOSE'])
def test_failure_phase_tracks_the_failing_boundary(phase):
    class Failed(View):
        def __enter__(self):
            if phase=='ENTER':raise AcquisitionError('OWNER_CHANGED')
            return self
        def scope(self):
            if phase=='SCOPE':raise OSError(errno.EIO,'private')
            return super().scope()
        def __exit__(self,*args):
            if phase=='CLOSE':raise AcquisitionError('CLEANUP_FAILED')
    out=probe_capability(view_factory=Failed)
    assert out['failure_phase']==phase and out['status']=='BLOCKED_NATIVE_CAPABILITY'


def test_scope_rejection_uses_closed_error_record_projection():
    class Failed(View):
        def scope(self):return {'endpoint_checks_pass':False,'errors':{'scope':{
            'type':'AcquisitionError','reason':'UNREVIEWED_SUBMOUNT','errno':None,
            'private':'do not emit'}}}
    out=probe_capability(view_factory=Failed)
    assert out['status']=='BLOCKED_SCOPE_PROFILE' and out['reason_code']=='UNREVIEWED_SUBMOUNT'
    assert out['failure_phase']=='SCOPE' and 'private' not in json.dumps(out)


def test_success_has_closed_schema_and_no_failure_reason():
    out=probe_capability(view_factory=View)
    assert out['schema']==2 and out['reason_code']=='NONE' and out['failure_phase']=='COMPLETE'
    assert out['optimization_mode']=='DISABLED'
    assert set(out)=={'schema','status','events','evidence_kind','processes_created','journal_created',
        'sampling_window_started','ticket_created','device_validation','policy_acceptance',
        'negative_pid_witness_allowed','lifetime_acceptance','temporal_visibility_proven',
        'reason_code','failure_phase','errno_code','optimization_mode','bytecode_mode'}


@pytest.mark.parametrize('flag',['-O','-OO'])
def test_optimized_probe_rejects_before_constructing_any_view(flag):
    code='''import json
from tools.proc_view_capability import probe_capability
def forbidden(**kwargs):raise AssertionError("factory must not run")
print(json.dumps(probe_capability(view_factory=forbidden)))
'''
    run=subprocess.run([sys.executable,flag,'-B','-c',code],capture_output=True,check=True,timeout=5)
    out=json.loads(run.stdout)
    assert out['status']=='BLOCKED_RUNTIME_FLAGS' and out['reason_code']=='OPTIMIZED_INTERPRETER'
    assert out['failure_phase']=='RUNTIME' and out['events']==0
