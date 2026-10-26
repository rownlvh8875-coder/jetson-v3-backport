import os
import signal
import time

import pytest

from tools.pinned_proc_view import ProcView,_semantic
from tools.proc_view_observer import ObserverError,with_owned_observer
from tools.proc_view_journal import PrivateJournal,verify_journal
from tools.proc_view_sampler import run_diagnostic


class ScopedFixtureView(ProcView):
    """Only test scope policy is injected; native FD IO and owned pipes are real."""
    def __init__(self,**kwargs):
        super().__init__(**kwargs);self._backend='INJECTED_SCOPE_FIXTURE'
    @_semantic('scope')
    def scope(self):
        value=super().scope()
        if value['errors'].get('scope',{}).get('reason')=='UNREVIEWED_SUBMOUNT':
            value['endpoint_checks_pass']=True
            value['mount']={'mount_id':value['root']['mount_id'],'fixture_scope':True}
        value['acquisition_backend']=self._backend
        return value


def observer(ready):
    ready();time.sleep(.02);return {'result':'private fixed fixture'}


def collector(check):
    check();return {'observations':1}


def test_owned_pipe_mapping_ack_ready_result_and_reap():
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,observer,collector,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']=='OWNED_OBSERVER_COMPLETE'
    assert value['protocol_origin_confirmed'] is True and value['mapping_matches'] is True
    assert value['owned_child_reaped'] is True and value['policy_acceptance'] is False


def test_native_unsupported_scope_stops_before_fork(monkeypatch):
    with ProcView() as view:
        if view.scope()['endpoint_checks_pass']:
            monkeypatch.setattr(view,'scope',lambda:{'endpoint_checks_pass':False})
        def forbidden():raise AssertionError('fork after rejected scope')
        monkeypatch.setattr(os,'fork',forbidden)
        with pytest.raises(ObserverError,match='SCOPE'):with_owned_observer(view,observer,collector)


def test_before_ready_failure_never_starts_collector():
    def fail(ready):raise ValueError('private failure fixture')
    def forbidden(check):raise AssertionError('collector started before ready')
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,fail,forbidden,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE' and value['owned_child_reaped'] is True
    assert value['collector_started'] is False


def test_wrong_mapping_pid_does_not_signal_supplied_pid(monkeypatch):
    class Wrong(ScopedFixtureView):
        def mapping_identity(self):return {**super().mapping_identity(),'pid':1}
    targets=[];original=os.kill
    def track(pid,sig):targets.append(pid);return original(pid,sig)
    monkeypatch.setattr(os,'kill',track)
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,observer,collector,view_factory=Wrong,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE' and value['collector_started'] is False
    assert 1 not in targets and value['owned_child_reaped'] is True


def test_large_result_drained_before_reaping_avoids_pipe_deadlock():
    def large(ready):ready();time.sleep(.02);return {'blob':'x'*150000}
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,large,collector,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']=='OWNED_OBSERVER_COMPLETE' and len(value['private_observer']['blob'])==150000


def test_timeout_cleanup_only_owned_child():
    def blocked(ready):time.sleep(5)
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,blocked,collector,view_factory=ScopedFixtureView,timeout=.1)
    assert value['status']!='OWNED_OBSERVER_COMPLETE' and value['owned_child_reaped'] is True


def test_early_child_exit_is_not_a_successful_observation_window():
    def early(ready):ready();return {}
    def slow(check):time.sleep(.05);check();return {}
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,early,slow,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE'


def test_fork_failure_closes_all_new_pipe_descriptors(monkeypatch):
    with ScopedFixtureView() as view:
        before=set(os.listdir('/proc/self/fd'))
        monkeypatch.setattr(os,'fork',lambda:(_ for _ in ()).throw(OSError('fixture fork failure')))
        with pytest.raises(OSError):with_owned_observer(view,observer,collector,view_factory=ScopedFixtureView)
        assert set(os.listdir('/proc/self/fd'))==before


def test_sigchld_autoreap_rejected_before_spawn():
    original=signal.getsignal(signal.SIGCHLD)
    try:
        signal.signal(signal.SIGCHLD,signal.SIG_IGN)
        with ScopedFixtureView() as view:
            with pytest.raises(ObserverError,match='SIGCHLD'):with_owned_observer(view,observer,collector)
    finally:signal.signal(signal.SIGCHLD,original)


def test_parent_journal_is_not_written_by_child(tmp_path):
    path=tmp_path/'journal'
    with PrivateJournal(path) as journal:
        with ScopedFixtureView(audit_sink=journal.sink) as view:
            value=with_owned_observer(view,observer,collector,view_factory=ScopedFixtureView,journal=journal,timeout=2)
        anchor=journal.seal()
    assert value['status']=='OWNED_OBSERVER_COMPLETE'
    verified=verify_journal(path,anchor)
    assert verified['semantic_complete'] is True and verified['proc_sessions']==2


def test_wrong_nonce_rejected_before_collector(monkeypatch):
    import tools.proc_view_observer as module
    real=module._send
    def corrupt(fd,nonce,kind,value,deadline,maximum):
        return real(fd,'0'*64 if kind=='MAP' else nonce,kind,value,deadline,maximum)
    monkeypatch.setattr(module,'_send',corrupt)
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,observer,collector,view_factory=ScopedFixtureView,timeout=2)
    assert value['collector_started'] is False and value['owned_child_reaped'] is True


def test_extra_result_frame_is_rejected(monkeypatch):
    import tools.proc_view_observer as module
    real=module._send
    def duplicate(fd,nonce,kind,value,deadline,maximum):
        real(fd,nonce,kind,value,deadline,maximum)
        if kind=='RESULT':real(fd,nonce,kind,value,deadline,maximum)
    monkeypatch.setattr(module,'_send',duplicate)
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,observer,collector,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE' and value['owned_child_reaped']


def test_swallower_cannot_turn_seen_early_exit_into_success():
    def early(ready):ready();return {}
    def swallow(check):
        time.sleep(.05)
        try:check()
        except ObserverError:pass
        return {}
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,early,swallow,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE'


def test_blocking_collector_is_cooperative_not_hard_preempted():
    def slow(check):time.sleep(.06);return {}
    def alive(ready):ready();time.sleep(.2);return {}
    with ScopedFixtureView() as view:
        begin=time.monotonic()
        value=with_owned_observer(view,alive,slow,view_factory=ScopedFixtureView,timeout=.03)
        elapsed=time.monotonic()-begin
    assert elapsed>=.05 and value['status']!='OWNED_OBSERVER_COMPLETE'


def test_wait_ownership_stolen_never_signals_reused_pid(monkeypatch):
    import tools.proc_view_observer as module
    child=[None];real_fork=os.fork
    def tracked():
        pid=real_fork()
        if pid>0:child[0]=pid
        return pid
    monkeypatch.setattr(os,'fork',tracked)
    signals=[];monkeypatch.setattr(os,'kill',lambda pid,sig:signals.append(pid))
    def steal(check):
        os.waitpid(child[0],0)
        check()
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,observer,steal,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE' and not signals


def test_integrated_stream_runner_covers_parent_and_child(tmp_path):
    class Small(ScopedFixtureView):
        @_semantic('enumerate')
        def enumerate(self):
            value=super().enumerate();value['pids']=[os.getpid()];return value
    def sustained(ready):ready();time.sleep(.15);return {'fresh':True}
    value=run_diagnostic(tmp_path/'record',probe_only=False,view_factory=Small,
                         duration=.02,interval=.01,observer=sustained)
    assert value['public']['status']=='ACQUISITION_WINDOW_OBSERVED'
    verified=verify_journal(tmp_path/'record',value['private_anchor'])
    assert verified['proc_sessions']==2 and verified['semantic_complete']


def test_queued_result_before_reap_rejects_active_collector(monkeypatch):
    import tools.proc_view_observer as module
    real=module._send
    def late_exit(fd,nonce,kind,value,deadline,maximum):
        real(fd,nonce,kind,value,deadline,maximum)
        if kind=='RESULT':time.sleep(.2)
    monkeypatch.setattr(module,'_send',late_exit)
    def slow(check):time.sleep(.05);check();return {}
    with ScopedFixtureView() as view:
        value=with_owned_observer(view,lambda ready:(ready() or {}),slow,view_factory=ScopedFixtureView,timeout=2)
    assert value['status']!='OWNED_OBSERVER_COMPLETE'


def test_inherited_view_cleanup_failure_prevents_ready_or_callback(monkeypatch):
    original=os.close;parent=os.getpid();once=[False]
    with ScopedFixtureView() as view:
        inherited=view._root
        def broken(fd):
            original(fd)
            if os.getpid()!=parent and fd==inherited and not once[0]:
                once[0]=True;raise OSError(5,'inherited cleanup failure')
        monkeypatch.setattr(os,'close',broken)
        value=with_owned_observer(view,observer,collector,view_factory=ScopedFixtureView,timeout=2)
    assert value['collector_started'] is False and value['owned_child_reaped'] is True


def test_timeout_incomplete_child_stream_retains_anchor_without_success(tmp_path):
    def blocked(ready):time.sleep(2)
    value=run_diagnostic(tmp_path/'record',probe_only=False,view_factory=ScopedFixtureView,
        duration=.001,interval=.01,observer=blocked,observer_timeout=.03)
    assert value['public']['status']=='INCOMPLETE_SEMANTIC_JOURNAL'
    assert value['public']['semantic_stream_complete'] is False
    assert value['private_anchor']['sha256']==value['public']['journal_sha256']
    with pytest.raises(Exception):verify_journal(tmp_path/'record',value['private_anchor'])
