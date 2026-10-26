"""Independent literal scenarios for process-generation observation bounds."""
from tools.comma_process_sampler import GenerationTracker
from tools import comma_process_sampler as sampler
import pytest


class ScenarioReader:
    clock_id='CLOCK_BOOTTIME'

    def __init__(self,scans,exit_probes=None):
        self.scenarios=iter(scans);self.exits=exit_probes or {};self.metadata_requests=[]

    def enumerate(self):
        self.current=next(self.scenarios)
        self.probe_end=self.current['end_ns']
        return {**{k:self.current[k] for k in ['start_ns','end_ns','pids','complete','scope']},
                'scope_end':self.current.get('scope_end',self.current['scope']),
                'visibility_supported':self.current.get('visibility_supported',True)}

    def probe(self,pid):
        value=dict(self.current.get('probes',{}).get(pid,self.exits.get(pid,dict(status='ABSENT',start_ns=self.current['end_ns'],end_ns=self.current['end_ns']+1))))
        width=value['end_ns']-value['start_ns'];value['start_ns']=max(value['start_ns'],self.probe_end)
        value['end_ns']=value['start_ns']+width;self.probe_end=value['end_ns']
        value.setdefault('pid',pid)
        return value

    def metadata(self,identity):
        self.metadata_requests.append((identity['pid'],identity['start_ticks']))
        return {'available':True,'cmdline_sha256':'f'*64}


def scan(t,pids,probes=None,complete=True,scope='same'):
    return dict(start_ns=t,end_ns=t+10,pids=pids,probes=probes or {},complete=complete,scope=scope)


def present(pid,start,t,ppid=1):
    return dict(status='PRESENT',pid=pid,start_ticks=start,ppid=ppid,start_ns=t,end_ns=t+1)


def replay(reader):
    tracker=GenerationTracker()
    for _ in range(3):tracker.poll(reader)
    return tracker.result()


def test_preceding_complete_absence_and_direct_exit_bound_full_lifetime():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    a=replay(r)['actors'].get('42:7',{})
    assert a.get('lifetime')=={'status':'BOUNDED','birth_not_before_ns':100,'exit_not_after_ns':311,'upper_ns':211,'under_10_seconds':True,'birth_proof':'RECORDED_COMPLETE_PID_LIST_ABSENCE'}


def test_initially_present_process_remains_left_censored():
    r=ScenarioReader([scan(100,[42],{42:present(42,7,111)}),scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    a=replay(r)['actors'].get('42:7',{})
    assert a.get('lifetime',{}).get('status')=='LEFT_CENSORED'


def test_partial_pid_list_never_becomes_birth_absence_proof():
    r=ScenarioReader([scan(100,[],complete=False),scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    assert replay(r)['actors'].get('42:7',{}).get('lifetime',{}).get('status')=='LEFT_CENSORED'


def test_unreadable_exit_probe_does_not_confirm_exit():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(300,[])],
        {42:dict(status='UNREADABLE',start_ns=310,end_ns=311,error='PermissionError')})
    assert replay(r)['actors'].get('42:7',{}).get('lifetime',{}).get('status')=='RIGHT_CENSORED'


def test_pid_reuse_uses_prior_positive_generation_read_start():
    r=ScenarioReader([scan(100,[42],{42:present(42,7,111)}),scan(200,[42],{42:present(42,8,211)}),scan(300,[])])
    out=replay(r)
    assert set(out['actors'])=={'42:7','42:8'}
    assert out['actors']['42:8']['lifetime']=={'status':'BOUNDED','birth_not_before_ns':111,'exit_not_after_ns':311,'upper_ns':200,'under_10_seconds':True,'birth_proof':'PRIOR_POSITIVE_DIFFERENT_GENERATION'}
    assert out['actors']['42:7']['exit_probe']['start_ticks']==8


@pytest.mark.parametrize('end,under',[(9_999_999_999,True),(10_000_000_000,False),(10_000_000_001,False)])
def test_ten_second_boundary_is_strict(end,under):
    r=ScenarioReader([scan(0,[]),scan(100,[42],{42:present(42,7,111)}),scan(200,[])],
                     {42:dict(status='ABSENT',start_ns=end-1,end_ns=end)})
    assert replay(r)['actors']['42:7']['lifetime']['under_10_seconds'] is under


def test_visibility_change_invalidates_all_lifetime_bounds():
    r=ScenarioReader([scan(100,[],scope='old'),scan(200,[42],{42:present(42,7,211)},scope='new'),scan(300,[],scope='new')])
    assert replay(r)['actors']['42:7']['lifetime']['status']=='CLOCK_OR_SCOPE_UNKNOWN'


def test_non_boot_clock_never_becomes_wall_lifetime_proof():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    r.clock_id='CLOCK_MONOTONIC'
    assert replay(r)['actors']['42:7']['lifetime']['status']=='CLOCK_OR_SCOPE_UNKNOWN'


def test_transient_scope_end_change_cannot_be_hidden_by_restored_scope():
    middle=scan(200,[42],{42:present(42,7,211)},complete=False);middle['scope_end']='different'
    r=ScenarioReader([scan(100,[]),middle,scan(300,[])])
    assert replay(r)['actors']['42:7']['lifetime']['status']=='CLOCK_OR_SCOPE_UNKNOWN'


def test_backwards_scan_clock_invalidates_lifetime():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(150,[])])
    assert replay(r)['actors']['42:7']['lifetime']['status']=='CLOCK_OR_SCOPE_UNKNOWN'


def test_pid_list_is_retained_as_evidence_not_just_a_count():
    r=ScenarioReader([scan(100,[1,9]),scan(200,[1,9,42],{42:present(42,7,211)}),scan(300,[1,9])])
    assert replay(r)['scans'][0]['pids']==[1,9]


def test_listed_but_unreadable_generation_is_not_absence():
    r=ScenarioReader([scan(100,[42],{42:dict(status='UNREADABLE',start_ns=111,end_ns=112,error='PermissionError')}),
                      scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    assert replay(r)['actors']['42:7']['lifetime']['status']=='LEFT_CENSORED'


def test_cached_existing_generation_metadata_not_reloaded_in_hot_loop():
    r=ScenarioReader([scan(100,[42],{42:present(42,7,111)}),scan(200,[42],{42:present(42,7,211)}),scan(300,[42],{42:present(42,7,311)})])
    replay(r)
    assert r.metadata_requests==[(42,7)]


def test_metadata_permission_failure_does_not_erase_generation_observation():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    def fail(_):raise PermissionError('fixture')
    r.metadata=fail
    a=replay(r)['actors']['42:7']
    assert a['metadata']=={'available':False,'error':'PermissionError'}
    assert a['lifetime']['status']=='BOUNDED'


@pytest.mark.parametrize('pids',[[42,42],[-1],[True]])
def test_malformed_pid_enumeration_rejected(pids):
    r=ScenarioReader([scan(100,pids)])
    with pytest.raises(ValueError):GenerationTracker().poll(r)


def test_probe_cannot_attribute_a_different_pid_to_listed_pid():
    r=ScenarioReader([scan(100,[42],{42:present(43,7,111)})])
    with pytest.raises(ValueError):GenerationTracker().poll(r)


def test_metadata_failure_and_unreadable_probe_details_are_retained():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(300,[])],
        {42:dict(status='UNREADABLE',start_ns=310,end_ns=311,error='PermissionError')})
    a=replay(r)['actors']['42:7']
    assert a['errors']==[{'status':'UNREADABLE','pid':42,'start_ns':310,'end_ns':311,'error':'PermissionError'}]


def stat_bytes(pid,start,comm='worker (odd) name)'):
    return (f'{pid} ({comm}) '+' '.join(['S','1']+['0']*17+[str(start)])).encode()


def test_real_proc_reader_parse_and_absence_brackets(tmp_path):
    root=tmp_path/'proc';(root/'42').mkdir(parents=True)
    (root/'42'/'stat').write_bytes(stat_bytes(42,123))
    stamps=iter([10,11,20,21])
    r=sampler.ProcReader(root,now=lambda:next(stamps),scope=lambda:'fixture')
    assert r.probe(42)=={'status':'PRESENT','pid':42,'ppid':1,'start_ticks':123,'start_ns':10,'end_ns':11}
    assert r.probe(99)=={'status':'ABSENT','pid':99,'start_ns':20,'end_ns':21,'error':'FileNotFoundError','errno':2}


def test_proc_reader_retains_complete_private_pid_membership(tmp_path):
    root=tmp_path/'proc';root.mkdir();(root/'9').mkdir();(root/'42').mkdir();(root/'self').mkdir()
    stamps=iter([10,20])
    r=sampler.ProcReader(root,now=lambda:next(stamps),scope=lambda:'fixture')
    result=r.enumerate()
    assert result['pids']==[9,42] and result['complete'] is True
    assert result['start_ns']==10 and result['end_ns']==20


@pytest.mark.parametrize('raw',[b'not a stat',stat_bytes(43,10),b'42 (x) S 1'])
def test_malformed_or_mismatched_stat_is_explicit_unreadable(tmp_path,raw):
    root=tmp_path/'proc';(root/'42').mkdir(parents=True);(root/'42'/'stat').write_bytes(raw)
    r=sampler.ProcReader(root,now=lambda:10,scope=lambda:'fixture')
    assert r.probe(42)['status']=='UNREADABLE'


def test_enumeration_failure_is_recorded_not_empty_absence(tmp_path):
    r=sampler.ProcReader(tmp_path/'missing',now=lambda:10,scope=lambda:'fixture')
    result=r.enumerate()
    assert result['complete'] is False and result['errors'][0]['type']=='FileNotFoundError'


class TimedReader:
    clock_id='CLOCK_BOOTTIME'

    def __init__(self,new_metadata_seconds=0):
        self.t=0;self.n=0;self.cost=new_metadata_seconds;self.metadata_requests=[]

    def now_ns(self):return self.t
    def sleep(self,seconds):self.t+=round(seconds*1e9)
    def enumerate(self):
        start=self.t;self.n+=1;self.t+=1_000_000
        pids=[42,99] if self.n==3 else [42]
        return dict(start_ns=start,end_ns=self.t,pids=pids,complete=True,scope='fixture',scope_end='fixture',visibility_supported=True)
    def probe(self,pid):
        t=self.t;self.t+=1_000_000
        return present(pid,7,t) if pid==42 or self.n==3 else dict(status='ABSENT',start_ns=t,end_ns=self.t,pid=pid)
    def metadata(self,identity):
        self.metadata_requests.append(identity['pid'])
        self.sleep(2 if identity['pid']==42 else self.cost)
        return {'available':True}


def test_baseline_and_final_metadata_costs_are_explicitly_outside_fast_window():
    r=TimedReader()
    result=sampler.collect(r,duration=1,interval=.25)
    assert result['baseline_seconds']>=2 and result['final_metadata_seconds']>=2
    assert result['fast_elapsed_seconds']==pytest.approx(1)
    assert result['cadence']['met'] is True
    assert r.metadata_requests.count(42)==2


def test_last_scan_metadata_overrun_is_not_hidden_by_missing_next_start():
    r=TimedReader(new_metadata_seconds=.8)
    result=sampler.collect(r,duration=1,interval=.25)
    assert result['cadence']['met'] is False
    assert result['cadence']['max_work_seconds']>.8


def test_collector_never_retries_to_find_a_passing_window():
    r=TimedReader(new_metadata_seconds=.8)
    result=sampler.collect(r,duration=1,interval=.25)
    assert len([s for s in result['scans'] if s['phase']=='BASELINE'])==1
    assert result['status']=='COLLECTED_CADENCE_NOT_MET'


def test_prepared_baseline_does_not_repeat_metadata_in_observed_window():
    r=TimedReader();prepared=sampler.prepare(r);before=r.now_ns()
    result=sampler.collect(r,duration=.5,interval=.25,prepared=prepared)
    assert result['fast_start_ns']==before
    assert r.metadata_requests.count(42)==2


def test_observer_child_ready_before_collector_and_large_pipe_drained():
    import os
    def observer(ready):ready();return {'data':'x'*200000,'pid':os.getpid()}
    def collector():return {'pid':os.getpid()}
    result=sampler.with_observer(observer,collector,timeout=5)
    assert result['observer']['data']=='x'*200000
    assert result['observer']['pid']!=result['collector']['pid']
    assert result['owned_child_reaped'] is True


def test_observer_failure_before_ready_never_runs_collector():
    def observer(ready):raise ValueError('sensitive detail must be absent')
    def collector():raise AssertionError('must not run')
    result=sampler.with_observer(observer,collector,timeout=5)
    assert result['status']=='OBSERVER_FAILED_BEFORE_READY'
    assert result['observer_error']=='ValueError'
    assert 'sensitive detail' not in repr(result)
    assert result['owned_child_reaped'] is True


def test_collector_failure_reaps_only_owned_observer():
    import os
    def observer(ready):ready();return {'ok':True}
    def collector():raise ValueError('sensitive detail')
    result=sampler.with_observer(observer,collector,timeout=5)
    assert result['status']=='COLLECTOR_FAILED'
    assert result['collector_error']=='ValueError'
    assert result['owned_child_reaped'] is True
    assert result['observer_parent_pid']==os.getpid()


def test_export_keeps_generation_membership_and_exact_reuse_witness():
    r=ScenarioReader([scan(100,[42],{42:present(42,7,111)}),scan(200,[42],{42:present(42,8,211)}),scan(300,[])])
    result=replay(r)
    assert result['scans'][0]['generations']=={42:7}
    assert 'probes' not in result['scans'][0]
    assert result['actors']['42:8']['birth_witness']=={'scan_index':0,'probe':present(42,7,111)}


def test_nonzero_observer_exit_never_returns_observed_success():
    import os
    def observer(ready):
        original=os._exit
        os._exit=lambda code:original(7)
        ready();return {'ok':True}
    result=sampler.with_observer(observer,lambda:{'ok':True},timeout=5)
    assert result['status']=='OBSERVER_EXIT_FAILED'
    assert result['owned_child_reaped'] is True


def test_fork_failure_closes_both_owned_pipe_descriptors(monkeypatch):
    import os
    owned=[];original=os.pipe
    def pipe():
        fds=original();owned.extend(fds);return fds
    def fail():raise OSError('fixture fork failure')
    with monkeypatch.context() as patch:
        patch.setattr(os,'pipe',pipe);patch.setattr(os,'fork',fail)
        try:
            with pytest.raises(OSError):sampler.with_observer(lambda ready:None,lambda:None)
            for fd in owned:
                with pytest.raises(OSError):os.fstat(fd)
        finally:
            for fd in owned:
                try:os.close(fd)
                except OSError:pass


def test_restricted_visibility_cannot_prove_birth_or_exit():
    first=scan(100,[]);first['visibility_supported']=False
    r=ScenarioReader([first,scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    assert replay(r)['actors']['42:7']['lifetime']['status']=='VISIBILITY_UNKNOWN'


@pytest.mark.parametrize('mount,expected',[
    ('10 1 0:5 / /proc rw,nosuid - proc proc rw',True),
    ('10 1 0:5 / /proc rw - proc proc rw,hidepid=0',True),
    ('10 1 0:5 / /proc rw - proc proc rw,hidepid=2',False),
    ('10 1 0:5 /123 /proc rw - proc proc rw',False),
    ('10 1 0:5 / /proc rw - tmpfs tmpfs rw',False),
    ('',False),
])
def test_negative_pid_evidence_requires_unrestricted_whole_proc_mount(mount,expected):
    assert sampler.proc_visibility_supported(mount)==expected


def test_sigchld_autoreap_is_rejected_before_fork():
    import signal
    previous=signal.signal(signal.SIGCHLD,signal.SIG_IGN)
    try:
        with pytest.raises(RuntimeError,match='SIGCHLD'):
            sampler.with_observer(lambda ready:None,lambda:None)
    finally:signal.signal(signal.SIGCHLD,previous)


def test_fork_with_active_threads_is_rejected():
    import threading
    stop=threading.Event();worker=threading.Thread(target=stop.wait);worker.start()
    try:
        with pytest.raises(RuntimeError,match='thread'):
            sampler.with_observer(lambda ready:None,lambda:None)
    finally:stop.set();worker.join()


def test_lost_wait_ownership_never_signals_recycled_pid(monkeypatch):
    import os
    def observer(ready):ready();return {'ok':True}
    def collector():os.waitpid(-1,0);return {'reaped':True}
    killed=[]
    monkeypatch.setattr(os,'kill',lambda *args:killed.append(args))
    result=sampler.with_observer(observer,collector,timeout=5)
    assert result['status']=='OBSERVER_WAIT_OWNERSHIP_LOST'
    assert killed==[]


def test_timeout_cleanup_targets_only_owned_observer():
    import subprocess,sys,time,os
    sibling=subprocess.Popen([sys.executable,'-c','import time;time.sleep(10)'])
    try:
        def observer(ready):ready();time.sleep(10)
        result=sampler.with_observer(observer,lambda:None,timeout=.15)
        assert result['owned_child_reaped'] is True
        assert result['owned_child_terminated'] is True
        assert sibling.poll() is None
        with pytest.raises(ChildProcessError):os.waitpid(result['observer_pid_private'],os.WNOHANG)
    finally:sibling.terminate();sibling.wait(timeout=3)


def test_generation_reappearing_after_proven_exit_is_contradiction():
    r=ScenarioReader([scan(100,[42],{42:present(42,7,111)}),scan(200,[]),scan(300,[42],{42:present(42,7,311)})])
    out=replay(r)
    assert out['actors']['42:7']['lifetime']['status']=='CLOCK_OR_SCOPE_UNKNOWN'
    assert out['actors']['42:7']['errors'][-1]['error']=='GENERATION_REAPPEARED_AFTER_EXIT'


def test_fast_window_head_delay_is_included_in_cadence():
    r=TimedReader();called=[]
    def delayed():
        if not called:r.sleep(.8);called.append(True)
    result=sampler.collect(r,duration=1,check=delayed)
    assert result['cadence']['met'] is False
    assert result['cadence']['head_gap_seconds']>=.8


def test_exit_confirmation_must_return_requested_pid():
    r=ScenarioReader([scan(100,[]),scan(200,[42],{42:present(42,7,211)}),scan(300,[])],{42:present(43,8,310)})
    with pytest.raises(ValueError,match='Probe identity'):replay(r)


def test_export_retains_each_positive_stat_bracket_and_parent():
    r=ScenarioReader([scan(100,[42],{42:present(42,7,111)}),scan(200,[42],{42:present(42,7,211)}),scan(300,[])])
    result=replay(r)
    assert result['scans'][0]['positive_read_offsets_ns']=={42:[11,1,1]}
    assert result['scans'][1]['positive_read_offsets_ns']=={42:[11,1,1]}


def test_cooperative_collector_detects_observer_failure_during_window():
    import time
    checks=[]
    def observer(ready):ready();time.sleep(.03);raise ValueError('private')
    def collector(check):
        for _ in range(100):check();checks.append(True);time.sleep(.01)
    result=sampler.with_observer(observer,collector,timeout=2,cooperative=True)
    assert len(checks)<100
    assert result['status']=='OBSERVER_FAILED'
    assert result['collector_error']=='RuntimeError'
    assert result['owned_child_reaped'] is True


def test_cooperative_deadline_checked_inside_collector():
    import time
    def observer(ready):ready();time.sleep(10)
    def collector(check):
        while True:check();time.sleep(.01)
    result=sampler.with_observer(observer,collector,timeout=.1,cooperative=True)
    assert result['collector_error']=='TimeoutError'
    assert result['owned_child_reaped'] is True


def test_scope_failure_does_not_erase_complete_pid_list(tmp_path):
    root=tmp_path/'proc';(root/'42').mkdir(parents=True)
    def unavailable():raise FileNotFoundError(2,'scope fixture')
    r=sampler.ProcReader(root,now=lambda:10,scope=unavailable,visibility=lambda:True)
    result=r.enumerate()
    assert result['pids']==[42] and result['pid_list_complete'] is True
    assert result['complete'] is False
    assert {e['field'] for e in result['errors']}=={'scope_before','scope_after'}


def test_missing_namespace_error_retains_exact_field(monkeypatch):
    import os
    original=os.readlink
    def missing(path,*args,**kwargs):
        if str(path)=='/proc/self/ns/pid':raise FileNotFoundError(2,'fixture')
        return original(path,*args,**kwargs)
    monkeypatch.setattr(os,'readlink',missing)
    r=sampler.ProcReader(now=lambda:10)
    with pytest.raises(sampler.ScopeReadError) as caught:r._scope()
    assert caught.value.field=='pid_namespace' and caught.value.errno==2


@pytest.mark.parametrize('field',['complete','visibility_supported'])
def test_unavailable_baseline_fails_before_fast_loop_with_retained_evidence(field):
    r=TimedReader();original=r.enumerate
    def unavailable():
        result=original();result[field]=False;return result
    r.enumerate=unavailable
    with pytest.raises(sampler.BaselinePreconditionError) as caught:sampler.collect(r,duration=60)
    assert r.n==1
    assert caught.value.evidence['scans'][0]['pids']==[42]
    assert '42:7' in caught.value.evidence['actors']


def test_empty_baseline_is_not_sixty_seconds_of_process_evidence():
    r=TimedReader();original=r.enumerate
    def empty():
        result=original();result['pids']=[];return result
    r.enumerate=empty
    with pytest.raises(sampler.BaselinePreconditionError):sampler.collect(r,duration=60)
    assert r.n==1


@pytest.mark.parametrize('field',['complete','visibility_supported'])
def test_empty_or_unconfirmed_mid_window_loop_cannot_pass_process_cadence(field):
    r=TimedReader();original=r.enumerate
    def broken():
        result=original()
        if r.n==3:
            result[field]=False
            if field=='complete':result['pids']=[]
        return result
    r.enumerate=broken
    result=sampler.collect(r,duration=1)
    assert result['cadence']['timing_met'] is True
    assert result['cadence']['coverage_met'] is False
    assert result['cadence']['met'] is False
