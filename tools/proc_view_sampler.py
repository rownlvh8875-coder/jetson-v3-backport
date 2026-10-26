"""Opt-in private acquisition diagnostics; strict sampler/default unchanged."""
import hashlib
import math
import time

from tools.comma_process_sampler import GenerationTracker
from tools.pinned_proc_view import AcquisitionError,ProcView
from tools.proc_view_journal import canonical,JournalError,PrivateJournal,verify_journal,SCOPE_CORE as _CORE

_STATES={'ACQUISITION_WINDOW_OBSERVED','ACQUISITION_CADENCE_NOT_MET',
         'CAPABILITY_PROFILE_SUPPORTED','BLOCKED_CAPABILITY_OR_SCOPE','OBSERVER_REJECTED','ACQUISITION_REJECTED'}


def _need(condition,reason):
    if not condition:raise CollectionError(reason)


class CollectionError(RuntimeError):
    pass


class ProcViewReader:
    clock_id='CLOCK_BOOTTIME'

    def __init__(self,view,journal,*,now=None,sleep=None):
        self.view,self.journal=view,journal
        self.session=getattr(view,'_stream_session',None);self.check=lambda:None
        _need(now is None or view._backend.startswith('INJECTED_'),'TEST_CLOCK_ONLY')
        self.now_ns=now or (lambda:time.clock_gettime_ns(time.CLOCK_BOOTTIME))
        self.sleep=sleep or time.sleep
        audit=view.audit();_need(audit['stream_enabled'] and not audit['stream_failed'],'STREAM_REQUIRED')
        if not view._backend.startswith('INJECTED_'):
            _need(view._audit_sink==journal.sink,'STREAM_BINDING')
        self._baseline=self._scope('BASELINE')

    def _scope(self,phase):
        self.check()
        value=self.view.scope();self.journal.append('SCOPE',{'phase':phase,'session':self.session,'value':value})
        _need(value.get('endpoint_checks_pass') is True,'BASELINE_SCOPE' if phase=='BASELINE' else 'SCOPE_UNAVAILABLE')
        _need(all(key in value for key in _CORE),'SCOPE_SCHEMA')
        digest=hashlib.sha256(canonical({k:value[k] for k in _CORE})).hexdigest()
        if hasattr(self,'_baseline'):_need(digest==self._baseline,'SCOPE_CHANGED')
        return digest

    def enumerate(self):
        begin=self.now_ns();scope=self._scope('SCAN_BEFORE')
        raw=self.view.enumerate()
        self.journal.append('SCAN',{'phase':'RAW_PID_LIST','session':self.session,'value':raw})
        pids=raw['pids']
        _need(type(pids) is list and len(pids)<=8192 and len(set(pids))==len(pids) and
              all(type(p) is int and 0<p<2**31 for p in pids),'PID_LIST')
        end_scope=self._scope('SCAN_AFTER')
        value={'start_ns':begin,'end_ns':self.now_ns(),'pids':pids,
               'scope':scope,'scope_end':end_scope,'complete':False,
               'pid_list_complete':raw.get('pid_list_read') is True,'errors':[],
               'visibility_supported':False,'negative_pid_witness_allowed':False}
        _need(value['pid_list_complete'],'PID_LIST_INCOMPLETE')
        return value

    def probe(self,pid):
        self.check()
        raw=self.view.probe(pid)
        self.journal.append('PROBE',{'session':self.session,'value':raw})
        _need(raw.get('pid')==pid,'PROBE_PID')
        if raw.get('status')=='NOT_FOUND':
            return {**raw,'status':'UNREADABLE','error':'UNADMITTED_PROC_VIEW_NOT_FOUND',
                    'raw_status':'NOT_FOUND','negative_pid_witness_allowed':False}
        _need(raw.get('status') in {'PRESENT','UNREADABLE'},'PROBE_STATUS')
        return {**raw,'negative_pid_witness_allowed':False}

    def metadata(self,identity):
        self.check()
        _need(type(identity.get('pid')) is int and type(identity.get('start_ticks')) is int,'IDENTITY')
        try:
            with self.view.generation(identity['pid']) as actor:
                before=actor.identity()
                if before['start_ticks']!=identity['start_ticks']:
                    value={'available':False,'reason':'GENERATION_CHANGED'}
                else:
                    raw=actor.metadata();after=actor.identity()
                    _need(before==after and raw['identity']==before,'METADATA_GENERATION_CHANGED')
                    value={'available':True,'private':raw}
        except (OSError,AcquisitionError) as error:
            if self.view.audit()['stream_failed']:raise CollectionError('STREAM_FAILED') from error
            value={'available':False,'error':type(error).__name__,
                   'errno':getattr(error,'errno',None),'private_partial':getattr(error,'private_partial',None)}
        self.journal.append('METADATA',{'session':self.session,'identity':identity,'value':value})
        return value


def collect_acquisition(reader,*,duration=60,interval=.25,check=lambda:None):
    previous=reader.check;reader.check=check
    try:return _collect_acquisition(reader,duration=duration,interval=interval,check=check)
    finally:reader.check=previous


def _collect_acquisition(reader,*,duration,interval,check):
    _need(type(duration) in (int,float) and math.isfinite(duration) and 0<duration<=300 and
          type(interval) in (int,float) and math.isfinite(interval) and .01<=interval<=.5,'BOUNDS')
    _need(interval>=.25 or reader.view._backend.startswith('INJECTED_'),'NATIVE_INTERVAL')
    begin=reader.now_ns();deadline=begin+round(duration*1e9);due=begin
    tracker=GenerationTracker();starts=[];work=[];last=begin
    while reader.now_ns()<deadline:
        _need(len(starts)<4096,'SCAN_BUDGET');check()
        scan=tracker.poll(reader);finished=reader.now_ns()
        _need(not tracker.context_changed,'CLOCK_OR_SCOPE_CHANGED')
        _need(len(tracker.actors)<=8192,'ACTOR_BUDGET')
        _need(any(p['status']=='PRESENT' for p in scan['probes'].values()),'EMPTY_POSITIVE_SCAN')
        starts.append(scan['start_ns']);work.append(finished-scan['start_ns'])
        reader.journal.append('SCAN',{'phase':'SCAN_COMPLETE','session':reader.session,'start_ns':scan['start_ns'],'end_ns':finished})
        due+=round(interval*1e9)
        if due>finished:reader.sleep((due-finished)/1e9)
        else:due=finished
        _need(reader.now_ns()>=last,'CLOCK_REVERSED');last=reader.now_ns()
    check();end=reader.now_ns();reader._scope('FINAL')
    _need(starts,'NO_SCANS')
    gaps=[b-a for a,b in zip(starts,starts[1:])]
    maximum=max([starts[0]-begin,end-starts[-1]]+gaps+work)
    timing=0<=maximum<=500_000_000
    value={'schema':1,'status':'ACQUISITION_WINDOW_OBSERVED' if timing else 'ACQUISITION_CADENCE_NOT_MET',
           'source_session':reader.session,
           'scans':len(starts),'positive_actors':len(tracker.actors),
           'cadence':{'timing_met':timing,'max_gap_or_work_ns':maximum,'elapsed_ns':end-begin},
           'fast_start_ns':begin,'fast_end_ns':end,
           'policy_acceptance':False,'negative_pid_witness_allowed':False,'lifetime_acceptance':False,
           'temporal_visibility_proven':False,'private_tracker':tracker.result()}
    reader.journal.append('SUMMARY',{k:v for k,v in value.items() if k!='private_tracker'})
    return value


def public_summary(result,verified):
    _need(verified.get('complete') is True,'UNVERIFIED_JOURNAL')
    value=verified.get('outcome') or verified.get('summary');_need(type(value) is dict and value.get('status') in _STATES,'SUMMARY')
    for key in ('scans','positive_actors'):
        _need(type(value.get(key)) is int and 0<=value[key]<=8192,'SUMMARY_COUNT')
    cadence=value.get('cadence');_need(type(cadence) is dict and type(cadence.get('timing_met')) is bool,'SUMMARY_CADENCE')
    for key in ('max_gap_or_work_ns','elapsed_ns'):
        _need(type(cadence.get(key)) is int and 0<=cadence[key]<2**63,'SUMMARY_CADENCE')
    digest=verified.get('sha256')
    _need(type(digest) is str and len(digest)==64 and all(c in '0123456789abcdef' for c in digest),'SUMMARY_DIGEST')
    _need(type(verified.get('events')) is int and 2<=verified['events']<=200000,'SUMMARY_EVENTS')
    all_facts=verified.get('facts');_need(type(all_facts) is dict,'SUMMARY_FACTS')
    facts=all_facts.get('sessions',{}).get(value.get('source_session'))
    backends=all_facts.get('backends')
    _need(type(backends) is list and backends and all(b in
        {'NATIVE_GLIBC_LP64_STATX','INJECTED_TEST_BACKEND','INJECTED_SCOPE_FIXTURE'} for b in backends),'SUMMARY_BACKEND')
    evidence='INJECTED_FIXTURE' if any(b.startswith('INJECTED_') for b in backends) else 'NATIVE_LOCAL_PROCFS'
    if value['status'] in {'ACQUISITION_WINDOW_OBSERVED','ACQUISITION_CADENCE_NOT_MET','CAPABILITY_PROFILE_SUPPORTED'}:
        _need(verified.get('semantic_complete') is True and verified.get('successful_proc_sessions',0)>0 and
              facts and facts.get('bound') is True and facts.get('baseline_pass') is True,'NO_SUCCESSFUL_PROC_STREAM')
    if value['status'] in {'ACQUISITION_WINDOW_OBSERVED','ACQUISITION_CADENCE_NOT_MET'}:
        spans=facts['scans'];start=value.get('fast_start_ns');end=value.get('fast_end_ns')
        _need(spans and len(spans)==facts['raw_scans']==value['scans'] and
              facts.get('final_pass') is True and
              facts['positive_actors']==value['positive_actors'] and
              type(start) is int and type(end) is int and start<=spans[0][0]<=spans[-1][1]<=end,'SUMMARY_RELATIONSHIP')
        maximum=max([spans[0][0]-start,end-spans[-1][0]]+[b-a for a,b in spans]+
                    [b[0]-a[0] for a,b in zip(spans,spans[1:])])
        _need(maximum==cadence['max_gap_or_work_ns'] and end-start==cadence['elapsed_ns'] and
              cadence['timing_met']==(maximum<=500_000_000) and
              (value['status']=='ACQUISITION_WINDOW_OBSERVED')==cadence['timing_met'],'SUMMARY_CADENCE_MISMATCH')
    timed=value['status'] in {'ACQUISITION_WINDOW_OBSERVED','ACQUISITION_CADENCE_NOT_MET'}
    observed_scans=len(facts['scans']) if facts else 0
    observed_actors=facts['positive_actors'] if facts else 0
    return {'schema':1,'status':value['status'],'scans':observed_scans,
        'positive_actors':observed_actors,'pid_lists':facts['raw_scans'] if facts else 0,'journal_sha256':digest,
        'journal_events':verified['events'],'timing_met':cadence['timing_met'] if timed else False,'timing_known':timed,
        'semantic_stream_complete':verified.get('semantic_complete') is True,'evidence_kind':evidence,
        'device_validation':False,
        'elapsed_ns':cadence['elapsed_ns'] if timed else None,'max_gap_or_work_ns':cadence['max_gap_or_work_ns'] if timed else None,
        'policy_acceptance':False,'negative_pid_witness_allowed':False,
        'lifetime_acceptance':False,'temporal_visibility_proven':False}


def run_diagnostic(output,*,probe_only=True,duration=60,interval=.25,observer=None,view_factory=ProcView,observer_timeout=None):
    """One explicit private/local run; default is capability-only, no fast window.

    No SSH/device dispatcher. Actual use requires separate OFF/source gates.
    """
    _need(type(probe_only) is bool,'PROBE_ONLY')
    value={'schema':1,'status':'BLOCKED_CAPABILITY_OR_SCOPE','scans':0,'positive_actors':0,
           'cadence':{'timing_met':False,'max_gap_or_work_ns':0,'elapsed_ns':0}}
    journal=PrivateJournal(output);phase='BASELINE'
    try:
        try:
            with view_factory(audit_sink=journal.sink) as view:
                value['source_session']=view._stream_session
                reader=ProcViewReader(view,journal)
                if probe_only:value['status']='CAPABILITY_PROFILE_SUPPORTED'
                else:
                    phase='WINDOW'
                    if observer is None:value=collect_acquisition(reader,duration=duration,interval=interval)
                    else:
                        from tools.proc_view_observer import with_owned_observer
                        observed=with_owned_observer(view,observer,
                            lambda check:collect_acquisition(reader,duration=duration,interval=interval,check=check),
                            view_factory=view_factory,journal=journal,
                            timeout=observer_timeout if observer_timeout is not None else min(120,max(1,duration+10)))
                        if observed['status']=='OWNED_OBSERVER_COMPLETE':value=observed['private_collector']
                        else:value['status']='OBSERVER_REJECTED'
        except (AcquisitionError,CollectionError,OSError,ValueError) as error:
            value['status']='BLOCKED_CAPABILITY_OR_SCOPE' if phase=='BASELINE' else 'ACQUISITION_REJECTED'
            journal.append('SCOPE',{'phase':'REJECTION','error_type':type(error).__name__})
        journal.append('OUTCOME',{k:v for k,v in value.items() if k!='private_tracker'})
        anchor=journal.seal()
        try:verified=verify_journal(output,anchor)
        except JournalError as error:
            status='INCOMPLETE_SEMANTIC_JOURNAL' if str(error)=='UNCLOSED_PROC_STREAM' else 'JOURNAL_VERIFICATION_FAILED'
            return {'public':{'schema':1,'status':status,'scans':None,'positive_actors':None,
                'journal_sha256':anchor['sha256'],'journal_events':anchor['events'],
                'semantic_stream_complete':False,'device_validation':False,'policy_acceptance':False,
                'negative_pid_witness_allowed':False,'lifetime_acceptance':False,'temporal_visibility_proven':False},
                'private_anchor':anchor,'private_verification_reason':str(error)}
        return {'public':public_summary(value,verified),'private_anchor':anchor}
    finally:
        if journal.state!='SEALED':journal.abort()
