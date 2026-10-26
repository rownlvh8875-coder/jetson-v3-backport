"""Read-only generation/lifetime diagnostic; never an installation policy."""
import copy
import hashlib
import json
import os
from pathlib import Path
import time


class ScopeReadError(OSError):
    def __init__(self,field,error):
        super().__init__(error.errno,field)
        self.field=field


class BaselinePreconditionError(RuntimeError):
    """No fast window was run; evidence retains the failed baseline."""
    def __init__(self,evidence):
        super().__init__('Process baseline preconditions unavailable')
        self.evidence=evidence


def _span(value):
    return all(type(value.get(k)) is int and value[k]>=0 for k in ('start_ns','end_ns')) and value['end_ns']>=value['start_ns']


def _probe_identity(probe,pid):
    if probe.get('pid')!=pid or probe.get('status') not in {'PRESENT','ABSENT','UNREADABLE'}:
        raise ValueError('Probe identity')
    if probe['status']=='PRESENT' and (type(probe.get('start_ticks')) is not int or probe['start_ticks']<0 or type(probe.get('ppid')) is not int or probe['ppid']<0):
        raise ValueError('Probe identity')


def proc_visibility_supported(mountinfo):
    """Support negative PID witnesses only on one whole, unrestricted proc mount.

    Missing hidepid means the kernel default (0); restricted/unknown layouts are
    not absence evidence. This does not attest exe/cmdline read permissions.
    """
    try:
        rows=[line.split() for line in mountinfo.splitlines() if line.split()[4]=='/proc']
        if len(rows)!=1:return False
        row=rows[0];separator=row.index('-')
        if row[3]!='/' or row[separator+1]!='proc':return False
        options=row[5].split(',')+row[separator+3].split(',')
        return all(option=='hidepid=0' for option in options if option.startswith('hidepid'))
    except (IndexError,ValueError):return False


class ProcReader:
    """Cheap direct /proc reader; optional reviewed sanitized metadata provider."""
    clock_id='CLOCK_BOOTTIME'

    def __init__(self,root='/proc',*,now=None,scope=None,visibility=None,metadata=None,sleep=time.sleep):
        self.root=Path(root)
        if now is None and not hasattr(time,'CLOCK_BOOTTIME'):
            raise RuntimeError('CLOCK_BOOTTIME unavailable; no mixed-clock fallback')
        self.now_ns=now or (lambda:time.clock_gettime_ns(time.CLOCK_BOOTTIME))
        self.scope=scope or self._scope
        self.visibility=visibility or self._visibility
        self._metadata=metadata
        self.sleep=sleep

    def _scope(self):
        if self.root!=Path('/proc'):raise ValueError('Explicit fixture scope required')
        def read(field,operation):
            try:return operation()
            except OSError as error:raise ScopeReadError(field,error) from error
        ns=[read(field,lambda kind=kind:os.readlink(self.root/'self/ns'/kind))
            for field,kind in [('pid_namespace','pid'),('mount_namespace','mnt')]]
        mountinfo=read('mountinfo',lambda:(self.root/'self/mountinfo').read_text())
        mounts=[line for line in mountinfo.splitlines() if line.split()[4]=='/proc']
        boot=read('boot_id',lambda:(self.root/'sys/kernel/random/boot_id').read_bytes())
        node=read('proc_directory',self.root.stat)
        return hashlib.sha256(json.dumps([os.geteuid(),os.getegid(),os.getgroups(),ns,mounts,boot.hex(),
            node.st_dev,node.st_ino],sort_keys=True).encode()).hexdigest()

    def _visibility(self):
        if self.root!=Path('/proc'):return False
        return proc_visibility_supported((self.root/'self/mountinfo').read_text())

    def enumerate(self):
        start=self.now_ns();errors=[];pids=[];list_complete=False
        def attempt(field,operation):
            try:return operation()
            except (OSError,ValueError) as e:
                errors.append({'field':field,'scope_field':getattr(e,'field',None),
                    'type':type(e).__name__,'errno':getattr(e,'errno',None)})
        before=attempt('scope_before',self.scope)
        visible_before=attempt('visibility_before',self.visibility)
        def listing():
            for path in self.root.iterdir():
                if path.name.isdecimal():pids.append(int(path.name))
            return True
        list_complete=attempt('pid_list',listing) is True
        pids.sort()
        after=attempt('scope_after',self.scope)
        visible_after=attempt('visibility_after',self.visibility)
        visible=visible_before is True and visible_after is True
        return {'start_ns':start,'end_ns':self.now_ns(),'pids':pids,'scope':before,'scope_end':after,
                'complete':list_complete and not errors and before is not None and before==after,'errors':errors,
                'pid_list_complete':list_complete,
                'visibility_supported':visible}

    def probe(self,pid):
        if type(pid) is not int or pid<=0:raise ValueError('PID')
        out={'pid':pid,'start_ns':self.now_ns()}
        try:
            fd=os.open(self.root/str(pid)/'stat',os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK)
            try:raw=os.read(fd,16385)
            finally:os.close(fd)
            left=raw.find(b'(');right=raw.rfind(b')');fields=raw[right+2:].split()
            if len(raw)>16384 or left<=0 or right<=left or raw[right+1:right+2]!=b' ' or len(fields)<20:
                raise ValueError('stat layout')
            if int(raw[:left].strip())!=pid:raise ValueError('PID path mismatch')
            parent,start=int(fields[1]),int(fields[19])
            if parent<0 or start<0:raise ValueError('stat values')
            out.update(status='PRESENT',ppid=parent,start_ticks=start)
        except FileNotFoundError as e:out.update(status='ABSENT',error=type(e).__name__,errno=e.errno)
        except (OSError,ValueError) as e:out.update(status='UNREADABLE',error=type(e).__name__,errno=getattr(e,'errno',None))
        out['end_ns']=self.now_ns()
        return out

    def metadata(self,identity):
        return self._metadata(identity) if self._metadata else {'available':False,'reason':'NO_METADATA_PROVIDER'}


class GenerationTracker:
    def __init__(self):
        self.scans=[];self.actors={};self.clock_id=None;self.scope=None;self.context_changed=False;self.last_read_ns=0;self.visibility_unknown=False

    def _clock(self,value):
        if not _span(value) or value['start_ns']<self.last_read_ns:self.context_changed=True
        self.last_read_ns=max(self.last_read_ns,value['end_ns'])

    def poll(self, reader):
        scan=reader.enumerate();scan=dict(scan,probes={})
        pids=scan['pids']
        if not isinstance(pids,list) or any(type(p) is not int or p<=0 for p in pids) or len(pids)!=len(set(pids)):
            raise ValueError('PID enumeration')
        if self.clock_id is None:self.clock_id=reader.clock_id;self.scope=scan['scope']
        self.context_changed |= reader.clock_id!=self.clock_id or scan['scope']!=self.scope or scan.get('scope_end')!=self.scope or self.scope is None
        self.visibility_unknown |= scan.get('visibility_supported') is not True
        previous=self.scans[-1] if self.scans else None
        self._clock(scan)
        for pid in scan['pids']:
            probe=reader.probe(pid);scan['probes'][pid]=probe
            _probe_identity(probe,pid)
            self._clock(probe)
            if probe['status']!='PRESENT':continue
            k=f"{pid}:{probe['start_ticks']}"
            if k in self.actors and self.actors[k]['exit_probe'] is not None:
                self.context_changed=True
                self.actors[k]['errors'].append({'error':'GENERATION_REAPPEARED_AFTER_EXIT','probe':copy.deepcopy(probe)})
            if k not in self.actors:
                birth=None;proof=None;witness=None
                if previous and previous['complete'] and previous['scope']==scan['scope'] and pid not in previous['pids']:
                    birth=previous['start_ns'];proof='RECORDED_COMPLETE_PID_LIST_ABSENCE'
                    witness={'scan_index':len(self.scans)-1,'absent_pid':pid}
                elif previous and previous['complete'] and previous['scope']==scan['scope']:
                    old=previous['probes'].get(pid)
                    if old and old['status']=='PRESENT' and old['start_ticks']!=probe['start_ticks']:
                        birth=old['start_ns'];proof='PRIOR_POSITIVE_DIFFERENT_GENERATION'
                        witness={'scan_index':len(self.scans)-1,'probe':copy.deepcopy(old)}
                try:metadata=reader.metadata(probe)
                except (OSError,ValueError) as exc:metadata={'available':False,'error':type(exc).__name__}
                self.actors[k]={'identity':probe,'metadata':metadata,'first_read_start_ns':probe['start_ns'],
                    'last_read_end_ns':probe['end_ns'],'birth_ns':birth,'birth_proof':proof,'birth_witness':witness,'exit_probe':None,'errors':[]}
            self.actors[k]['last_read_end_ns']=probe['end_ns']
        for k,a in self.actors.items():
            if a['exit_probe'] is not None:continue
            p=scan['probes'].get(a['identity']['pid'])
            if p and p['status']=='PRESENT' and p['start_ticks']==a['identity']['start_ticks']:continue
            confirm=reader.probe(a['identity']['pid'])
            _probe_identity(confirm,a['identity']['pid'])
            self._clock(confirm)
            if confirm['status']=='ABSENT' or (confirm['status']=='PRESENT' and confirm['start_ticks']!=a['identity']['start_ticks']):
                a['exit_probe']=confirm
            else:a['errors'].append(confirm)
        self.scans.append(scan)
        return scan

    def result(self):
        out=copy.deepcopy({'actors':self.actors,'scans':self.scans,'clock_id':self.clock_id,'context_changed':self.context_changed})
        # Keep exact PID membership/generation evidence, but avoid exporting every
        # repeated positive stat timestamp. Exact reused-generation witnesses and
        # exit probes remain on actors; all failed probes remain on scans.
        for scan in out['scans']:
            probes=scan.pop('probes')
            scan['generations']={pid:p['start_ticks'] for pid,p in probes.items() if p['status']=='PRESENT'}
            scan['positive_read_offsets_ns']={pid:[p['start_ns']-scan['start_ns'],p['end_ns']-p['start_ns'],p['ppid']]
                for pid,p in probes.items() if p['status']=='PRESENT'}
            scan['probe_failures']=[dict(p,pid=pid) for pid,p in probes.items() if p['status']!='PRESENT']
        for a in out['actors'].values():
            if self.context_changed or self.clock_id!='CLOCK_BOOTTIME':life={'status':'CLOCK_OR_SCOPE_UNKNOWN'}
            elif self.visibility_unknown:life={'status':'VISIBILITY_UNKNOWN'}
            elif a['birth_ns'] is None:life={'status':'LEFT_CENSORED'}
            elif a['exit_probe'] is None:life={'status':'RIGHT_CENSORED'}
            else:
                upper=a['exit_probe']['end_ns']-a['birth_ns']
                life=({'status':'BOUNDED','birth_not_before_ns':a['birth_ns'],'exit_not_after_ns':a['exit_probe']['end_ns'],
                      'upper_ns':upper,'under_10_seconds':upper<10_000_000_000,'birth_proof':a['birth_proof']}
                      if upper>=0 else {'status':'CLOCK_OR_SCOPE_UNKNOWN'})
            a['lifetime']=life
        return out


def prepare(reader):
    """Populate the heavy metadata cache explicitly outside the fast window."""
    begin=reader.now_ns();tracker=GenerationTracker();scan=tracker.poll(reader)
    scan['phase']='BASELINE';scan['finished_ns']=reader.now_ns()
    if (scan.get('complete') is not True or scan.get('visibility_supported') is not True or tracker.context_changed
        or not any(p['status']=='PRESENT' for p in scan['probes'].values())):
        raise BaselinePreconditionError(tracker.result())
    return {'tracker':tracker,'start_ns':begin,'end_ns':scan['finished_ns']}


def collect(reader,*,duration=60,interval=.25,prepared=None,progress=lambda _:None,check=lambda:None):
    if not (0<duration<=300 and .01<=interval<=.5):raise ValueError('bounded duration/interval')
    prepared=prepared or prepare(reader);tracker=prepared['tracker']
    start=reader.now_ns();deadline=start+round(duration*1e9);due=start;fast=[];reported=-1
    while reader.now_ns()<deadline:
        check();scan=tracker.poll(reader);scan['phase']='FAST';scan['finished_ns']=reader.now_ns();fast.append(scan)
        elapsed=(scan['finished_ns']-start)/1e9
        if int(elapsed//15)>reported:reported=int(elapsed//15);progress(elapsed)
        due+=round(interval*1e9)
        now=reader.now_ns()
        if due>now:reader.sleep((due-now)/1e9)
        else:due=now
    end=reader.now_ns()
    gaps=[(b['start_ns']-a['start_ns'])/1e9 for a,b in zip(fast,fast[1:])]
    work=[(s['finished_ns']-s['start_ns'])/1e9 for s in fast]
    tail=(end-fast[-1]['start_ns'])/1e9 if fast else float('inf')
    head=(fast[0]['start_ns']-start)/1e9 if fast else float('inf')
    cadence={'requested_seconds':interval,'limit_seconds':.5,'head_gap_seconds':head,'max_start_gap_seconds':max(gaps,default=0),
             'max_work_seconds':max(work,default=0),'end_gap_seconds':tail}
    cadence['timing_met']=bool(fast) and max(head,cadence['max_start_gap_seconds'],cadence['max_work_seconds'],tail)<=.5
    cadence['coverage_met']=bool(fast) and all(s.get('complete') is True and s.get('visibility_supported') is True and
        any(p['status']=='PRESENT' for p in s['probes'].values()) for s in fast)
    cadence['met']=cadence['timing_met'] and cadence['coverage_met']
    final_begin=reader.now_ns()
    check()
    for a in tracker.actors.values():
        check()
        if a['exit_probe'] is None:
            try:a['final_metadata']=reader.metadata(a['identity'])
            except (OSError,ValueError) as e:a['final_metadata']={'available':False,'error':type(e).__name__}
    check()
    result=tracker.result()
    result.update(status='COLLECTED_CADENCE_MET' if cadence['met'] else 'COLLECTED_CADENCE_NOT_MET',
        baseline_seconds=(prepared['end_ns']-prepared['start_ns'])/1e9,fast_start_ns=start,fast_end_ns=end,
        fast_elapsed_seconds=(end-start)/1e9,final_metadata_seconds=(reader.now_ns()-final_begin)/1e9,cadence=cadence,
        evidence_only_not_policy_acceptance=True)
    if tracker.context_changed:result['status']='COLLECTED_CLOCK_OR_SCOPE_UNCONFIRMED'
    return result


def with_observer(observer,collector,*,timeout=100,max_bytes=2*1024*1024,cooperative=False):
    """Run one owned observer child and drain its bounded framed pipe before reap.

    Call before creating threads or importing native telemetry. observer(ready)
    must call ready once after initializing its receive window. This helper never
    terminates an operating process: cleanup can target only its unreaped direct
    fork child, whose PID cannot be reused while wait ownership is retained.
    In cooperative mode collector(check) must invoke check at every bounded
    iteration; it detects early observer exit and enforces the common deadline.
    Callbacks that block indefinitely or ignore check are not supported.
    """
    import select
    import signal
    import struct
    import threading
    if not hasattr(os,'fork'):raise RuntimeError('POSIX fork required')
    if signal.getsignal(signal.SIGCHLD)!=signal.SIG_DFL:raise RuntimeError('Default SIGCHLD required for wait ownership')
    if threading.active_count()!=1:raise RuntimeError('No active threads permitted before fork')
    if timeout<=0 or max_bytes<=0:raise ValueError('bounded observer protocol')
    read_fd,write_fd=os.pipe()
    try:pid=os.fork()
    except BaseException:
        os.close(read_fd);os.close(write_fd);raise
    if pid==0:
        os.close(read_fd);sent=False
        def write_all(data):
            view=memoryview(data)
            while view:
                count=os.write(write_fd,view)
                if count<=0:raise OSError('short pipe write')
                view=view[count:]
        def ready():
            nonlocal sent
            if sent:raise ValueError('duplicate ready')
            write_all(b'R');sent=True
        try:
            try:
                value=observer(ready)
                payload={'result':value} if sent else {'error':'ReadyNotCalled'}
            except BaseException as exc:payload={'error':type(exc).__name__}
            if not sent:write_all(b'E')
            raw=json.dumps(payload,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
            if len(raw)>max_bytes:raw=b'{"error":"ObserverPayloadTooLarge"}'
            write_all(struct.pack('!Q',len(raw))+raw)
            os.close(write_fd);os._exit(0)
        except BaseException:os._exit(1)
    os.close(write_fd)
    result={'observer_pid_private':pid,'observer_parent_pid':os.getpid(),'owned_child_reaped':False}
    try:result['owned_child_identity_private']=ProcReader().probe(pid)
    except (OSError,ValueError,RuntimeError) as e:result['owned_child_identity_private']={'status':'UNREADABLE','error':type(e).__name__}
    deadline=time.monotonic()+timeout
    def exact(count):
        value=bytearray()
        while len(value)<count:
            remaining=deadline-time.monotonic()
            if remaining<=0:raise TimeoutError('observer deadline')
            if not select.select([read_fd],[],[],min(remaining,.25))[0]:continue
            block=os.read(read_fd,count-len(value))
            if not block:raise EOFError('observer pipe')
            value.extend(block)
        return bytes(value)
    def reap(deadline):
        while True:
            got,status=os.waitpid(pid,os.WNOHANG)
            if got:
                result['owned_child_reaped']=True;result['observer_exit_status']=status;return
            if time.monotonic()>=deadline:raise TimeoutError('observer reap')
            time.sleep(.01)
    def check_observer():
        if time.monotonic()>=deadline:raise TimeoutError('observer deadline')
        got,status=os.waitpid(pid,os.WNOHANG)
        if got:
            result.update(owned_child_reaped=True,observer_exit_status=status)
            raise RuntimeError('observer exited during collection')
    try:
        ready=exact(1)
        if ready not in (b'R',b'E'):raise ValueError('observer protocol')
        if ready==b'R':
            try:result['collector']=collector(check_observer) if cooperative else collector()
            except BaseException as exc:result.update(status='COLLECTOR_FAILED',collector_error=type(exc).__name__)
        size=struct.unpack('!Q',exact(8))[0]
        if size>max_bytes:raise ValueError('observer frame size')
        payload=json.loads(exact(size))
        if 'error' in payload:
            result.update(status='OBSERVER_FAILED_BEFORE_READY' if ready==b'E' else 'OBSERVER_FAILED',observer_error=payload['error'])
        else:result['observer']=payload['result'];result.setdefault('status','OBSERVED')
        if not result['owned_child_reaped']:reap(deadline)
        if result['observer_exit_status']!=0:result['status']='OBSERVER_EXIT_FAILED'
    except ChildProcessError:result['status']='OBSERVER_WAIT_OWNERSHIP_LOST'
    except BaseException as exc:result.update(status='OBSERVER_PROTOCOL_FAILED',protocol_error=type(exc).__name__)
    finally:
        os.close(read_fd)
        if not result['owned_child_reaped']:
            # Positive wait ownership is retained until here; a child that exits
            # between wait and signal remains a zombie and cannot recycle PID.
            try:
                got,status=os.waitpid(pid,os.WNOHANG)
                if got:result.update(owned_child_reaped=True,observer_exit_status=status)
                else:
                    os.kill(pid,signal.SIGTERM);result['owned_child_terminated']=True
                    try:reap(time.monotonic()+2)
                    except TimeoutError:
                        os.kill(pid,signal.SIGKILL)
                        try:reap(time.monotonic()+2)
                        except TimeoutError:result['status']='OWNED_OBSERVER_CLEANUP_NOT_CONFIRMED'
            except ChildProcessError:result['status']='OBSERVER_WAIT_OWNERSHIP_LOST'
    return result
