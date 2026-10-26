import os

import pytest

from test_pinned_proc_view import FixtureNative,tree
from tools.pinned_proc_view import AcquisitionError,ProcView,_semantic
from tools.proc_view_journal import JournalError,PrivateJournal,verify_journal
from tools.proc_view_sampler import CollectionError,ProcViewReader,collect_acquisition,public_summary,run_diagnostic
from tools.comma_process_sampler import GenerationTracker,prepare,BaselinePreconditionError


def test_sink_covers_acquisition_semantics_and_cleanup_before_seal(tree,tmp_path):
    path=tmp_path/'journal'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            assert view.scope()['endpoint_checks_pass'] is True
            assert view.probe(42)['status']=='PRESENT'
            with view.generation(42) as actor:actor.metadata()
        anchor=journal.seal()
    result=verify_journal(path,anchor)
    assert result['complete'] and result['kinds']['PROC_EVENT']>10
    assert b'VIEW_BEGIN' in path.read_bytes() and b'VIEW_CLOSED' in path.read_bytes()
    assert b'CALL_RESULT' in path.read_bytes()


def test_sink_gets_every_attempt_after_tail_eviction(tree):
    events=[]
    with ProcView(tree,native=FixtureNative(),audit_sink=events.append) as view:
        for _ in range(40):view.probe(42)
        count=view._operation_count
        assert view.audit()['complete'] is False
    attempts=[e for e in events if e['event']=='ATTEMPT']
    assert len(attempts)==count
    assert events[0]['event']=='VIEW_BEGIN' and events[-1]['event']=='VIEW_CLOSED'


def test_sink_failure_poison_preserves_primary_and_closes_handles(tree):
    enabled=[False]
    def sink(event):
        if enabled[0]:raise OSError('private sink fixture')
    view=ProcView(tree,native=FixtureNative(),audit_sink=sink)
    enabled[0]=True
    with pytest.raises(AcquisitionError,match='STREAM_FAILED'):view.probe(42)
    with pytest.raises(AcquisitionError):view.enumerate()
    view.close()
    assert not view._fds and view.audit()['stream_failed'] is True


def test_sink_reentrancy_cannot_be_swallowed_into_success(tree):
    holder={}
    def sink(event):
        if holder:
            try:holder['view'].probe(42)
            except AcquisitionError:pass
    with ProcView(tree,native=FixtureNative(),audit_sink=sink) as view:
        holder['view']=view
        with pytest.raises(AcquisitionError):view.enumerate()
        holder.clear()
        assert view.audit()['stream_failed'] is True


def test_no_sink_preserves_previous_bounded_tail_contract(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        assert view.probe(42)['negative_pid_witness_allowed'] is False
        assert view.audit()['stream_enabled'] is False


class Clock:
    def __init__(self):self.tick=1_000_000_000
    def now(self):return self.tick
    def sleep(self,seconds):self.tick+=round(seconds*1e9)
    def work(self,n=1000):self.tick+=n


class ControlledView:
    _backend='INJECTED_TEST_BACKEND'
    def __init__(self,clock):self.clock=clock;self.number=500;self.missing=False;self.scope_ok=True;self.drift=False;self.metadata_calls=0
    def scope(self):
        self.clock.work()
        return {'endpoint_checks_pass':self.scope_ok,'root':{'inode':1},'owner':{'pid':1,'start_ticks':500},
                'credentials':[[1000]*3,[1000]*3,[]],'owner_status':{},'boot_sha256':'a'*64,
                'mount_namespace':'mnt:[1]','pid_namespace':{'status':'ENOENT','errno':2},
                'mount':{'mount_id':42 if self.drift else 41},'acquisition_backend':self._backend}
    def enumerate(self):
        begin=self.clock.now();self.clock.work()
        return {'pids':[1,42],'start_ns':begin,'end_ns':self.clock.now(),'pid_list_read':True}
    def probe(self,pid):
        begin=self.clock.now();self.clock.work()
        return {'pid':pid,'start_ns':begin,'end_ns':self.clock.now(),'status':'NOT_FOUND' if self.missing else 'PRESENT',
                'ppid':1,'start_ticks':self.number}
    def generation(self,pid):
        view=self
        class Actor:
            def __enter__(self):return self
            def __exit__(self,*_):pass
            def identity(self):return {'pid':pid,'ppid':1,'start_ticks':view.number}
            def metadata(self):view.metadata_calls+=1;return {'identity':self.identity(),'fields':{'cmdline':b'secret\0'}}
        return Actor()
    def audit(self):return {'stream_failed':False,'stream_enabled':True}


def test_provider_never_promotes_missing_to_absent_or_legacy_baseline(tmp_path):
    clock=Clock();view=ControlledView(clock)
    with PrivateJournal(tmp_path/'journal') as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)
        scan=reader.enumerate()
        assert scan['complete'] is False and scan['visibility_supported'] is False
        view.missing=True
        assert reader.probe(42)['status']=='UNREADABLE'
        view.missing=False
        with pytest.raises(BaselinePreconditionError):prepare(reader)


def test_provider_metadata_rejects_reused_generation_before_read(tmp_path):
    clock=Clock();view=ControlledView(clock)
    with PrivateJournal(tmp_path/'journal') as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)
        view.number=700
        result=reader.metadata({'pid':42,'start_ticks':500})
        assert result['available'] is False and view.metadata_calls==0


def test_collector_retains_positive_frames_but_no_lifetime_authority(tmp_path):
    clock=Clock();view=ControlledView(clock);path=tmp_path/'journal'
    with PrivateJournal(path) as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)
        result=collect_acquisition(reader,duration=.03,interval=.01)
        assert result['status']=='ACQUISITION_WINDOW_OBSERVED'
        assert result['scans']==3 and result['positive_actors']==2
        assert result['cadence']['timing_met'] is True
        assert result['policy_acceptance'] is False
        assert all(a['lifetime']['status']!='BOUNDED' for a in result['private_tracker']['actors'].values())
        anchor=journal.seal()
    assert verify_journal(path,anchor)['complete']


def test_bad_baseline_stops_before_first_enumeration(tmp_path):
    clock=Clock();view=ControlledView(clock);view.scope_ok=False
    view.enumerate=lambda:(_ for _ in ()).throw(AssertionError('fast loop executed'))
    with PrivateJournal(tmp_path/'journal') as journal:
        with pytest.raises(CollectionError,match='BASELINE_SCOPE'):
            ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)


def test_scope_drift_mid_window_stops_without_retry(tmp_path):
    clock=Clock();view=ControlledView(clock)
    with PrivateJournal(tmp_path/'journal') as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep);view.drift=True
        with pytest.raises(CollectionError,match='SCOPE_CHANGED'):collect_acquisition(reader,duration=.03,interval=.01)


def test_metadata_overrun_is_not_hidden_by_last_window_tail(tmp_path):
    clock=Clock();view=ControlledView(clock)
    original=view.generation
    def expensive(pid):clock.work(600_000_000);return original(pid)
    view.generation=expensive
    with PrivateJournal(tmp_path/'journal') as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)
        result=collect_acquisition(reader,duration=.03,interval=.01)
        assert result['cadence']['timing_met'] is False
        assert result['status']=='ACQUISITION_CADENCE_NOT_MET'


def test_public_summary_is_fresh_allowlist_and_forces_authority_false(tree,tmp_path):
    path=tmp_path/'journal'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal)
            result=collect_acquisition(reader,duration=.001,interval=.01)
        anchor=journal.seal()
    result['policy_acceptance']=True;result['secret']='/private/device/path token'
    summary=public_summary(result,verify_journal(path,anchor))
    assert summary['policy_acceptance'] is False and summary['lifetime_acceptance'] is False
    assert 'secret' not in str(summary) and '/private' not in str(summary) and 'cmdline' not in str(summary)
    assert summary['journal_sha256']==anchor['sha256']


def test_runner_defaults_to_single_capability_probe_without_window(tree,tmp_path):
    def factory(**kwargs):return ProcView(tree,native=FixtureNative(),**kwargs)
    def forbidden(ready):raise AssertionError('observer was started')
    value=run_diagnostic(tmp_path/'journal',view_factory=factory,observer=forbidden)
    assert value['public']['status']=='CAPABILITY_PROFILE_SUPPORTED'
    assert value['public']['scans']==0 and value['public']['policy_acceptance'] is False
    assert value['public']['semantic_stream_complete'] is True


def test_runner_keeps_one_rejected_baseline_receipt_no_fast_loop(tree,tmp_path):
    class Denied(ProcView):
        def scope(self):return {**super().scope(),'endpoint_checks_pass':False}
        def enumerate(self):raise AssertionError('fast loop after rejected baseline')
    def factory(**kwargs):return Denied(tree,native=FixtureNative(),**kwargs)
    value=run_diagnostic(tmp_path/'journal',view_factory=factory,probe_only=False)
    assert value['public']['status']=='BLOCKED_CAPABILITY_OR_SCOPE'
    assert value['public']['scans']==0
    assert verify_journal(tmp_path/'journal',value['private_anchor'])['complete'] is True


def test_runner_closes_stream_then_seals_verified_window(tree,tmp_path):
    def factory(**kwargs):return ProcView(tree,native=FixtureNative(),**kwargs)
    value=run_diagnostic(tmp_path/'journal',probe_only=False,view_factory=factory,duration=.001,interval=.01)
    assert value['public']['status']=='ACQUISITION_WINDOW_OBSERVED'
    assert value['public']['semantic_stream_complete'] is True
    assert value['public']['evidence_kind']=='INJECTED_FIXTURE'


def test_summary_only_journal_cannot_claim_acquisition_window(tmp_path):
    clock=Clock();path=tmp_path/'journal'
    with PrivateJournal(path) as journal:
        result=collect_acquisition(ProcViewReader(ControlledView(clock),journal,now=clock.now,sleep=clock.sleep),duration=.01,interval=.01)
        anchor=journal.seal()
    with pytest.raises(CollectionError):public_summary(result,verify_journal(path,anchor))


def test_native_interval_below_quarter_second_is_not_enabled(tmp_path):
    clock=Clock();view=ControlledView(clock)
    with PrivateJournal(tmp_path/'journal') as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)
        view._backend='NATIVE_GLIBC_LP64_STATX'
        with pytest.raises(CollectionError,match='INTERVAL'):collect_acquisition(reader,duration=.01,interval=.01)


def test_constructor_only_plus_fictional_baseline_cannot_claim_capability(tree,tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:session=view._stream_session
        journal.append('SCOPE',{'phase':'BASELINE','session':session,'value':{'endpoint_checks_pass':True,'acquisition_backend':'INJECTED_TEST_BACKEND'}})
        journal.append('OUTCOME',{'status':'CAPABILITY_PROFILE_SUPPORTED','source_session':session,
            'scans':0,'positive_actors':0,'cadence':{'timing_met':False,'elapsed_ns':0,'max_gap_or_work_ns':0}})
        anchor=journal.seal()
    with pytest.raises(CollectionError):public_summary({},verify_journal(path,anchor))


def test_free_probe_cannot_become_semantically_verified_actor(tree,tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal);raw=view.enumerate();session=view._stream_session
            start=raw['start_ns'];end=raw['end_ns']
            journal.append('SCAN',{'phase':'RAW_PID_LIST','session':session,'value':raw})
            journal.append('PROBE',{'session':session,'value':{'pid':42,'status':'PRESENT','ppid':1,
                'start_ticks':999,'start_ns':start,'end_ns':end}})
            journal.append('SCAN',{'session':session,'phase':'SCAN_COMPLETE','start_ns':start,'end_ns':end})
        journal.append('SUMMARY',{'status':'ACQUISITION_WINDOW_OBSERVED','source_session':session,'scans':1,'positive_actors':1,
            'cadence':{'timing_met':True,'elapsed_ns':end-start,'max_gap_or_work_ns':end-start},'fast_start_ns':start,'fast_end_ns':end})
        anchor=journal.seal()
    with pytest.raises(CollectionError):public_summary({},verify_journal(path,anchor))


def test_rejected_run_reports_partial_observations_not_zero(tree,tmp_path):
    class Drift(ProcView):
        calls=0
        @_semantic('scope')
        def scope(self):
            value=super().scope();self.calls+=1
            if self.calls>=4:value['boot_sha256']='0'*64
            return value
    def factory(**kwargs):return Drift(tree,native=FixtureNative(),**kwargs)
    value=run_diagnostic(tmp_path/'record',probe_only=False,view_factory=factory,duration=.1,interval=.01)
    assert value['public']['status']=='ACQUISITION_REJECTED'
    assert value['public']['scans']>=1 and value['public']['positive_actors']>=1
    assert value['public']['timing_known'] is False


def test_cancellation_checked_during_each_poll_not_only_after_whole_scan(tmp_path):
    clock=Clock();view=ControlledView(clock);calls=[0]
    def check():
        calls[0]+=1
        if calls[0]>=3:raise CollectionError('CANCEL')
    with PrivateJournal(tmp_path/'record') as journal:
        reader=ProcViewReader(view,journal,now=clock.now,sleep=clock.sleep)
        with pytest.raises(CollectionError,match='CANCEL'):collect_acquisition(reader,duration=.001,interval=.01,check=check)
    assert view.metadata_calls<=1


def test_completed_scan_cannot_omit_listed_probes_and_claim_zero_actor_window(tree,tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal);scan=reader.enumerate();session=view._stream_session
            begin=scan['start_ns'];end=reader.now_ns()
            journal.append('SCAN',{'phase':'SCAN_COMPLETE','session':session,'start_ns':begin,'end_ns':end})
        journal.append('SUMMARY',{'status':'ACQUISITION_WINDOW_OBSERVED','source_session':session,'scans':1,'positive_actors':0,
            'fast_start_ns':begin,'fast_end_ns':end,
            'cadence':{'timing_met':True,'elapsed_ns':end-begin,'max_gap_or_work_ns':end-begin}})
        anchor=journal.seal()
    with pytest.raises(CollectionError):public_summary({},verify_journal(path,anchor))


@pytest.mark.parametrize('pids,complete',[([42,42],True),([2**31],True),([42],False)])
def test_replay_matches_live_raw_pid_list_contract(tree,tmp_path,pids,complete):
    class Bad(ProcView):
        @_semantic('enumerate')
        def enumerate(self):return {**super().enumerate(),'pids':pids,'pid_list_read':complete}
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with Bad(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            raw=view.enumerate()
            journal.append('SCAN',{'phase':'RAW_PID_LIST','session':view._stream_session,'value':raw})
        anchor=journal.seal()
    with pytest.raises(JournalError):verify_journal(path,anchor)


@pytest.mark.parametrize('field,changed',[('boot_sha256','0'*64),('endpoint_checks_pass',False)])
def test_replay_scope_continuity_matches_live_rejection(tree,tmp_path,field,changed):
    class Changed(ProcView):
        calls=0
        @_semantic('scope')
        def scope(self):
            value=super().scope();self.calls+=1
            if self.calls>=2:value[field]=changed
            return value
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with Changed(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal);session=view._stream_session
            with pytest.raises(CollectionError):reader.enumerate()
        anchor=journal.seal()
    verified=verify_journal(path,anchor)
    assert verified['facts']['sessions'][session]['bound'] is False


def test_pre_list_probe_cannot_be_reused_as_current_frame_probe(tree,tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal);old=view.probe(42)
            scan=reader.enumerate();session=view._stream_session
            journal.append('PROBE',{'session':session,'value':old})
            journal.append('SCAN',{'phase':'SCAN_COMPLETE','session':session,'start_ns':scan['start_ns'],'end_ns':reader.now_ns()})
        anchor=journal.seal()
    facts=verify_journal(path,anchor)['facts']['sessions'][session]
    assert facts['bound'] is False and facts['positive_actors']==0


def test_cached_enumeration_before_scope_before_is_not_current_raw_list(tree,tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal);old=view.enumerate();reader._scope('SCAN_BEFORE')
            session=view._stream_session
            journal.append('SCAN',{'phase':'RAW_PID_LIST','session':session,'value':old})
        anchor=journal.seal()
    assert verify_journal(path,anchor)['facts']['sessions'][session]['bound'] is False


def test_cached_final_scope_before_scan_completion_is_not_final_witness(tree,tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        with ProcView(tree,native=FixtureNative(),audit_sink=journal.sink) as view:
            reader=ProcViewReader(view,journal);scan=reader.enumerate()
            for pid in scan['pids']:reader.probe(pid)
            old=view.scope();session=view._stream_session
            journal.append('SCAN',{'phase':'SCAN_COMPLETE','session':session,'start_ns':scan['start_ns'],'end_ns':reader.now_ns()})
            journal.append('SCOPE',{'phase':'FINAL','session':session,'value':old})
        anchor=journal.seal()
    assert verify_journal(path,anchor)['facts']['sessions'][session]['final_pass'] is False
