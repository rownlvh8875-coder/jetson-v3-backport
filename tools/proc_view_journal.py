"""Private diagnostic journal; no runtime policy or public process-data emitter."""
import base64
import hashlib
import json
import math
import os
import secrets
import stat

_MAX_BYTES=64*1024*1024
_LINE=2*1024*1024
_RESERVE=2048
_KINDS={'PROC_EVENT','SCOPE','SCAN','PROBE','METADATA','OBSERVER','SUMMARY','OUTCOME'}
SCOPE_CORE=('root','owner','credentials','owner_status','boot_sha256','mount_namespace','pid_namespace','mount','acquisition_backend')


def _need(condition,reason):
    if not condition:raise JournalError(reason)


def _integer(value,low,high):
    return type(value) is int and low<=value<=high


def _cleanup(fds,primary=None,errors=None,*,quiet=False):
    found=[]
    for fd in fds:
        if fd>=0:
            try:os.close(fd)
            except OSError as error:found.append({'type':type(error).__name__,'errno':error.errno})
    if errors is not None:errors.extend(found)
    if found:
        if primary is not None:
            primary.private_cleanup_errors=getattr(primary,'private_cleanup_errors',[])+found
        elif not quiet:
            error=JournalError('CLEANUP_FAILED');error.private_cleanup_errors=found;raise error


def _wire(value,depth=0):
    _need(depth<=24,'PAYLOAD_DEPTH')
    if value is None or type(value) is bool:return value
    if type(value) is int:
        _need(-(2**63)<=value<2**63,'PAYLOAD_INTEGER');return value
    if type(value) is float:
        _need(math.isfinite(value),'PAYLOAD_FLOAT');return value
    if type(value) is str:
        _need(len(value)<=1024*1024,'PAYLOAD_STRING');return value
    if type(value) is bytes:
        _need(len(value)<=1024*1024,'PAYLOAD_BYTES')
        return {'_bytes_base64':base64.b64encode(value).decode('ascii')}
    if type(value) in (list,tuple):
        _need(len(value)<=65536,'PAYLOAD_ARRAY')
        return [_wire(v,depth+1) for v in value]
    _need(type(value) is dict and len(value)<=65536,'PAYLOAD_TYPE')
    _need(all(type(k) is str and len(k)<=128 for k in value),'PAYLOAD_KEY')
    result={k:_wire(v,depth+1) for k,v in value.items()}
    if {'_bytes_base64','_dict_items'} & set(result):
        return {'_dict_items':[[k,v] for k,v in sorted(result.items())]}
    return result


def canonical(value):
    try:return _dump(_wire(value))
    except (ValueError,TypeError,RecursionError):raise JournalError('CANONICAL') from None


def _dump(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def _check_wire(value,depth=0):
    _need(depth<=24,'PAYLOAD_DEPTH')
    if type(value) is dict:
        if set(value)=={'_bytes_base64'}:
            try:
                text=value['_bytes_base64'];decoded=base64.b64decode(text,validate=True)
                _need(type(text) is str and len(decoded)<=1024*1024 and base64.b64encode(decoded).decode('ascii')==text,'BASE64')
            except (ValueError,TypeError):raise JournalError('BASE64') from None
            return
        if set(value)=={'_dict_items'}:
            pairs=value['_dict_items'];_need(type(pairs) is list and len(pairs)<=65536,'DICT_ESCAPE')
            _need(all(type(p) is list and len(p)==2 and type(p[0]) is str and len(p[0])<=128 for p in pairs),'DICT_ESCAPE')
            keys=[p[0] for p in pairs]
            _need(keys==sorted(set(keys)) and bool({'_bytes_base64','_dict_items'}&set(keys)),'DICT_ESCAPE')
            for _,item in pairs:_check_wire(item,depth+1)
            return
        _need(not ({'_bytes_base64','_dict_items'}&set(value)),'DICT_ESCAPE')
        _need(len(value)<=65536 and all(type(k) is str and len(k)<=128 for k in value),'PAYLOAD_KEY')
        for item in value.values():_check_wire(item,depth+1)
    elif type(value) is list:
        _need(len(value)<=65536,'PAYLOAD_ARRAY')
        for item in value:_check_wire(item,depth+1)
    else:_wire(value,depth)


def _pairs(pairs):
    value={}
    for key,item in pairs:
        _need(key not in value,'DUPLICATE_KEY');value[key]=item
    return value


def parse_canonical(raw):
    _need(type(raw) is bytes and 0<len(raw)<=_LINE,'LINE_SIZE')
    try:value=json.loads(raw,object_pairs_hook=_pairs,parse_constant=lambda _:(_ for _ in ()).throw(JournalError('NONFINITE')))
    except (ValueError,UnicodeError,RecursionError):raise JournalError('JSON') from None
    _check_wire(value);_need(_dump(value)==raw,'NONCANONICAL')
    return value


def decode_wire(value):
    """Closed data-only decoding after canonical validation; never object hooks."""
    _check_wire(value)
    def decode(item):
        if type(item) is list:return [decode(v) for v in item]
        if type(item) is dict:
            if set(item)=={'_bytes_base64'}:return base64.b64decode(item['_bytes_base64'],validate=True)
            if set(item)=={'_dict_items'}:return {key:decode(v) for key,v in item['_dict_items']}
            return {key:decode(v) for key,v in item.items()}
        return item
    return decode(value)


def _parent(path):
    text=os.fspath(path)
    _need(type(text) is str and text.startswith('/') and all(p not in {'','.','..'} for p in text.split('/')[1:]),'PATH')
    parts=text.split('/')[1:]
    fd=os.open('/',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        for part in parts[:-1]:
            nxt=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC,dir_fd=fd)
            old=fd;fd=nxt;_cleanup([old])
        node=os.fstat(fd)
        _need(node.st_uid==os.geteuid() and stat.S_IMODE(node.st_mode)==0o700,'PARENT_PRIVATE')
        return fd,parts[-1]
    except BaseException as error:
        _cleanup([fd],primary=error);raise


def _file(fd):
    node=os.fstat(fd)
    _need(stat.S_ISREG(node.st_mode) and node.st_nlink==1 and node.st_uid==os.geteuid()
          and stat.S_IMODE(node.st_mode)==0o600,'FILE_PRIVATE')
    return node


class JournalError(RuntimeError):
    pass


class PrivateJournal:
    def __init__(self,path,*,max_bytes=16*1024*1024,max_events=200000):
        _need(_integer(max_bytes,4096,_MAX_BYTES) and _integer(max_events,2,200000),'BOUNDS')
        self._owner=os.getpid();self._fd=self._parent_fd=-1;self.state='OPEN';self._busy=False
        self.cleanup_errors=[]
        self._max_bytes,self._max_events=max_bytes,max_events
        self._head='0'*64;self._count=0;self._used=0;self._hash=hashlib.sha256()
        try:
            self._parent_fd,self._name=_parent(path)
            self._fd=os.open(self._name,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW|os.O_CLOEXEC,0o600,dir_fd=self._parent_fd)
            self._identity=_file(self._fd)
            self._append('HEADER',{'schema':1,'privacy':'PRIVATE','session':secrets.token_hex(16)},terminal=False)
        except BaseException as error:
            self.abort(error);raise

    def __enter__(self):return self

    def __exit__(self,kind,error,traceback):
        if self.state!='SEALED':self.abort(error)

    def _guard(self):
        _need(os.getpid()==self._owner,'OWNER')
        _need(self.state=='OPEN','FAILED_OR_CLOSED')

    def _append(self,kind,data,*,terminal=False):
        self._guard()
        try:
            _need(not self._busy,'REENTRANT_WRITE');self._busy=True
            record={'sequence':self._count+1,'previous':self._head,'kind':kind,'data':data}
            digest=hashlib.sha256(canonical(record)).hexdigest()
            raw=canonical({'record':record,'sha256':digest})+b'\n'
            _need(len(raw)<=_LINE,'LINE_SIZE')
            _need(self._count+1<=(self._max_events if terminal else self._max_events-1) and
                  self._used+len(raw)+(0 if terminal else _RESERVE)<=self._max_bytes,'BUDGET')
            remaining=memoryview(raw)
            while remaining:
                count=os.write(self._fd,remaining)
                _need(type(count) is int and 0<count<=len(remaining),'SHORT_WRITE')
                remaining=remaining[count:]
            _need(self.state=='OPEN','FAILED_OR_CLOSED')
            self._head=digest;self._count+=1;self._used+=len(raw);self._hash.update(raw)
        except BaseException:
            self.state='FAILED';raise
        finally:self._busy=False

    def append(self,kind,data):
        try:
            self._guard();_need(kind in _KINDS and type(data) is dict,'EVENT')
            self._append(kind,data)
        except (OSError,ValueError,TypeError) as error:
            self.state='FAILED';raise JournalError('APPEND_FAILED') from error
        except BaseException:
            self.state='FAILED';raise

    def sink(self,event):self.append('PROC_EVENT',event)

    def detach_in_child(self):
        _need(os.getpid()!=self._owner,'NOT_CHILD')
        for name in ('_fd','_parent_fd'):
            fd=getattr(self,name);setattr(self,name,-1)
            if fd>=0:os.close(fd)
        self.state='DETACHED_CHILD'

    def seal(self):
        self._guard()
        try:
            self._append('END',{'events_before_end':self._count,'previous':self._head,'complete':True},terminal=True)
            node=_file(self._fd)
            named=os.stat(self._name,dir_fd=self._parent_fd,follow_symlinks=False)
            _need((node.st_dev,node.st_ino)==(named.st_dev,named.st_ino)==(self._identity.st_dev,self._identity.st_ino),'FILE_REPLACED')
            os.fsync(self._fd);os.fsync(self._parent_fd)
            fds=[self._fd,self._parent_fd];self._fd=self._parent_fd=-1
            _cleanup(fds,errors=self.cleanup_errors)
            self.state='SEALED'
            return {'schema':1,'events':self._count,'bytes':self._used,'head':self._head,'sha256':self._hash.hexdigest()}
        except BaseException as error:
            self.state='FAILED'
            raise JournalError('SEAL_FAILED') from error

    def abort(self,primary=None):
        if self.state=='SEALED':return
        self.state='FAILED'
        fds=[self._fd,self._parent_fd];self._fd=self._parent_fd=-1
        _cleanup(fds,primary=primary,errors=self.cleanup_errors,quiet=True)


def verify_journal(path,anchor):
    _need(type(anchor) is dict and set(anchor)=={'schema','events','bytes','head','sha256'},'ANCHOR')
    _need(type(anchor['schema']) is int and anchor['schema']==1 and
          _integer(anchor['events'],2,200000) and _integer(anchor['bytes'],1,_MAX_BYTES),'ANCHOR')
    for key in ('head','sha256'):
        _need(type(anchor[key]) is str and len(anchor[key])==64 and all(c in '0123456789abcdef' for c in anchor[key]),'ANCHOR')
    parent,filename=_parent(path);fd=-1;primary=None
    try:
        fd=os.open(filename,os.O_RDONLY|os.O_NOFOLLOW|os.O_CLOEXEC|os.O_NONBLOCK,dir_fd=parent)
        node=_file(fd);_need(node.st_size==anchor['bytes'],'SIZE')
        head='0'*64;count=0;whole=hashlib.sha256();kinds={};ended=False;summary=None;outcome=None;sessions={};consumed=0
        scans=[];positive=set();backends=set();raw_scans=0;bound={}
        with os.fdopen(fd,'rb',closefd=False) as source:
            while True:
                raw=source.readline(min(_LINE+1,anchor['bytes']-consumed+1))
                if not raw:break
                consumed+=len(raw);_need(consumed<=anchor['bytes'],'BYTE_BUDGET')
                _need(not ended and len(raw)<=_LINE and raw.endswith(b'\n'),'FRAMING')
                whole.update(raw);value=parse_canonical(raw[:-1])
                _need(type(value) is dict and set(value)=={'record','sha256'},'RECORD')
                record=value['record']
                _need(type(record) is dict and set(record)=={'sequence','previous','kind','data'},'RECORD')
                _need(type(record['sequence']) is int and record['sequence']==count+1 and record['previous']==head,'SEQUENCE')
                _need(value['sha256']==hashlib.sha256(_dump(record)).hexdigest(),'CHAIN')
                kind=record['kind'];_need(type(kind) is str and kind in _KINDS|{'HEADER','END'},'EVENT')
                _need(outcome is None or kind=='END','AFTER_OUTCOME')
                _need(type(record['data']) is dict,'DATA')
                if count==0:
                    header=record['data']
                    _need(kind=='HEADER' and set(header)=={'schema','privacy','session'} and
                        type(header['schema']) is int and header['schema']==1 and header['privacy']=='PRIVATE' and
                        type(header['session']) is str and len(header['session'])==32 and
                        all(c in '0123456789abcdef' for c in header['session']),'HEADER')
                else:_need(kind!='HEADER','HEADER')
                if kind=='END':
                    _need(type(record['data'].get('events_before_end')) is int and record['data'].get('complete') is True and
                        record['data']=={'events_before_end':count,'previous':head,'complete':True},'FOOTER')
                    ended=True
                if kind=='PROC_EVENT':_proc_event(record['data'],sessions)
                data=record['data']
                if kind in {'SCOPE','SCAN','PROBE','METADATA'}:_bind_fact(kind,data,sessions,bound)
                if kind=='SCOPE' and type(data.get('value')) is dict:
                    backends.add(data['value'].get('acquisition_backend'))
                if kind=='SCAN' and data.get('phase')=='RAW_PID_LIST':raw_scans+=1
                if kind=='SCAN' and data.get('phase')=='SCAN_COMPLETE':
                    _need(len(scans)<4096 and _integer(data.get('start_ns'),0,2**63-1) and
                        _integer(data.get('end_ns'),data['start_ns'],2**63-1),'SCAN_BOUNDS')
                    scans.append((data['start_ns'],data['end_ns']))
                if kind=='PROBE' and type(data.get('value')) is dict and data['value'].get('status')=='PRESENT':
                    probe=data['value'];_need(_integer(probe.get('pid'),1,2**31-1) and
                        _integer(probe.get('start_ticks'),0,2**63-1),'PROBE_BOUNDS')
                    positive.add((probe['pid'],probe['start_ticks']));_need(len(positive)<=8192,'ACTOR_BUDGET')
                if kind=='SUMMARY':
                    _need(summary is None,'SUMMARY_DUPLICATE');summary=record['data']
                if kind=='OUTCOME':
                    _need(outcome is None,'OUTCOME_DUPLICATE')
                    outcome=record['data']
                count+=1;_need(count<=anchor['events'],'COUNT')
                kinds[kind]=kinds.get(kind,0)+1;head=value['sha256']
        _need(ended and count==anchor['events'] and head==anchor['head'] and whole.hexdigest()==anchor['sha256'],'ANCHOR_MISMATCH')
        _need(all(s['closed'] and not s['calls'] for s in sessions.values()),'UNCLOSED_PROC_STREAM')
        _need(_file(fd).st_size==node.st_size,'FILE_CHANGED')
        return {'complete':True,'events':count,'kinds':kinds,'sha256':whole.hexdigest(),
                'summary':summary,'outcome':outcome,'semantic_complete':bool(sessions),
                'successful_proc_sessions':sum(s['ready'] and not s['failed'] for s in sessions.values()),
                'facts':{'scans':scans,'raw_scans':raw_scans,'positive_actors':len(positive),
                    'backends':sorted({b for b in backends if type(b) is str}|{s['backend'] for s in sessions.values()}),
                    'sessions':{key:{k:v for k,v in bucket.items() if k not in {'pids','seen','actors','last_raw'}}|
                        {'positive_actors':len(bucket['actors'])} for key,bucket in bound.items() if type(key) is str}},
                'proc_sessions':len(sessions),'policy_acceptance':False}
    except BaseException as error:
        if isinstance(error,JournalError) or not isinstance(error,Exception):primary=error;raise
        primary=JournalError('VERIFY_FAILED');raise primary from error
    finally:
        _cleanup([fd,parent],primary=primary)


def _proc_event(value,sessions):
    _need(set(value)=={'schema','session','sequence','timestamp_ns','event','details'} and
          type(value['schema']) is int and value['schema']==1,'PROC_SCHEMA')
    session=value['session'];event=value['event'];details=value['details']
    _need(type(session) is str and len(session)==32 and all(c in '0123456789abcdef' for c in session)
          and type(event) is str and type(details) is dict,'PROC_SCHEMA')
    if event=='VIEW_BEGIN':
        _need(session not in sessions and len(sessions)<16,'PROC_BEGIN')
        _need(details.get('backend') in {'NATIVE_GLIBC_LP64_STATX','INJECTED_TEST_BACKEND'},'PROC_BACKEND')
        sessions[session]={'sequence':0,'clock':0,'attempts':0,'calls':[],'closed':False,'ready':False,'failed':False,
                           'backend':details['backend'],'last':{}}
    _need(session in sessions,'PROC_BEGIN');state=sessions[session]
    _need(not state['closed'] and _integer(value['sequence'],1,2**63-1) and
          value['sequence']==state['sequence']+1 and _integer(value['timestamp_ns'],state['clock'],2**63-1),'PROC_SEQUENCE')
    state['sequence']=value['sequence'];state['clock']=value['timestamp_ns']
    if event=='VIEW_BEGIN':return
    if event=='VIEW_READY':
        _need(not state['ready'] and not state['failed'],'PROC_READY');state['ready']=True
    elif event=='VIEW_FAILED':
        _need(not state['ready'] and not state['failed'],'PROC_FAILED');state['failed']=True
    elif event=='VIEW_CLOSED':
        _need((state['ready'] or state['failed']) and not state['calls'] and
              details.get('remaining_fds')==0 and details.get('cleanup_errors')==[] and
              type(details.get('attempts')) is int and details['attempts']==state['attempts'],'PROC_CLOSED')
        state['closed']=True
    elif event=='ATTEMPT':
        _need(type(details.get('sequence')) is int and details['sequence']==state['attempts']+1 and
              details.get('status') in {'OK','FAILED'} and details.get('scheme')=='DIRFD','PROC_ATTEMPT')
        state['attempts']+=1
    elif event in {'CALL_BEGIN','CALL_RESULT','CALL_FAILED'}:
        method=details.get('method')
        _need(method in {'scope','mapping_identity','compare_child_mapping','enumerate','probe','identity','read','link','metadata'},'PROC_METHOD')
        _need(state['ready'],'PROC_READY')
        if event=='CALL_BEGIN':
            _need(len(state['calls'])<64,'PROC_DEPTH');state['calls'].append((method,state['clock']))
        else:
            _need(state['calls'] and state['calls'][-1][0]==method,'PROC_CALL_PAIR')
            _,begin=state['calls'].pop()
            if event=='CALL_RESULT':
                state['last'][method]={'digest':hashlib.sha256(_dump(details.get('value'))).hexdigest(),
                    'used':False,'begin':begin,'clock':state['clock'],'sequence':state['sequence']}
    else:raise JournalError('PROC_EVENT')


def _bind_fact(kind,data,sessions,buckets):
    key=data.get('session')
    if type(key) not in (str,type(None)):raise JournalError('FACT_SESSION')
    _need(key in buckets or len(buckets)<17,'FACT_SESSION_BUDGET')
    bucket=buckets.setdefault(key,{'bound':True,'baseline_pass':False,'raw_scans':0,'scans':[],
        'actors':set(),'pids':set(),'seen':set(),'frame_positive':0,'last_raw':None,
        'core':None,'before_scopes':0,'after_scopes':0,'final_pass':False,
        'before_seq':0,'before_begin':0,'before_clock':0,'enumerate_seq':0,
        'after_seq':0,'after_clock':0,'completed_seq':0,'completed_end':0})
    state=sessions.get(key)
    def matches(method,value,*,after=0,begin_at=0,timed=False):
        previous=state['last'].get(method) if state else None
        okay=bool(previous and not previous['used'] and previous['sequence']>after and
            previous['begin']>=begin_at and previous['digest']==hashlib.sha256(_dump(value)).hexdigest())
        if timed:
            okay=bool(okay and type(value) is dict and _integer(value.get('start_ns'),begin_at,2**63-1) and
                _integer(value.get('end_ns'),value['start_ns'],2**63-1) and
                previous['begin']<=value['start_ns']<=value['end_ns']<=previous['clock'])
        if previous:previous['used']=True
        bucket['bound'] &= okay
        return okay
    if kind=='SCOPE':
        value=data.get('value');phase=data.get('phase')
        after=bucket['completed_seq'] if phase in {'SCAN_BEFORE','FINAL'} else bucket['enumerate_seq'] if phase=='SCAN_AFTER' else 0
        begin_at=bucket['completed_end'] if phase in {'SCAN_BEFORE','FINAL'} else bucket['last_raw'][1] if phase=='SCAN_AFTER' and bucket['last_raw'] else 0
        okay=matches('scope',value,after=after,begin_at=begin_at)
        previous=state['last'].get('scope') if state else None
        valid=bool(type(value) is dict and value.get('endpoint_checks_pass') is True and all(k in value for k in SCOPE_CORE))
        core=hashlib.sha256(_dump({k:value[k] for k in SCOPE_CORE})).hexdigest() if valid else None
        if data.get('phase')=='BASELINE':
            bucket['baseline_pass']=okay and valid;bucket['core']=core
        else:bucket['bound'] &= bool(valid and core==bucket['core'])
        if data.get('phase')=='SCAN_BEFORE':
            bucket['bound'] &= bucket['raw_scans']==len(bucket['scans'])
            bucket['before_scopes']+=1
            if previous:
                bucket['before_seq']=previous['sequence'];bucket['before_begin']=previous['begin']
                bucket['before_clock']=previous['clock']
        elif data.get('phase')=='SCAN_AFTER':
            bucket['after_scopes']+=1
            bucket['bound'] &= bucket['before_scopes']==bucket['after_scopes']==bucket['raw_scans']
            if previous:bucket['after_seq']=previous['sequence'];bucket['after_clock']=previous['clock']
        elif data.get('phase')=='FINAL':
            bucket['final_pass']=bool(okay and valid and core==bucket['core'] and
                bucket['before_scopes']==bucket['after_scopes']==bucket['raw_scans']==len(bucket['scans']))
    elif kind=='SCAN' and data.get('phase')=='RAW_PID_LIST':
        raw=data.get('value',{});matches('enumerate',raw,after=bucket['before_seq'],begin_at=bucket['before_clock'],timed=True)
        previous=state['last'].get('enumerate') if state else None
        if previous:bucket['enumerate_seq']=previous['sequence']
        pids=raw.get('pids',[])
        _need(type(pids) is list and len(pids)<=8192 and len(set(pids))==len(pids) and
              all(type(p) is int and 0<p<2**31 for p in pids) and raw.get('pid_list_read') is True,'FACT_PIDS')
        bucket['bound'] &= bucket['raw_scans']==len(bucket['scans'])
        bucket['bound'] &= bucket['before_scopes']==bucket['raw_scans']+1
        bucket['raw_scans']+=1;bucket['pids']=set(pids);bucket['seen']=set();bucket['frame_positive']=0
        bucket['last_raw']=(raw.get('start_ns'),raw.get('end_ns'))
    elif kind=='SCAN' and data.get('phase')=='SCAN_COMPLETE':
        span=(data.get('start_ns'),data.get('end_ns'));raw=bucket['last_raw']
        _need(len(bucket['scans'])<4096,'SCAN_BUDGET')
        okay=bool(raw and all(type(t) is int for t in span+raw) and
            span[0]<=bucket['before_begin']<=raw[0]<=raw[1]<=span[1] and state and span[1]>=state['clock'] and
            len(bucket['scans'])+1==bucket['raw_scans']==bucket['before_scopes']==bucket['after_scopes'] and
            bucket['seen']==bucket['pids'] and bucket['frame_positive']>0)
        bucket['bound'] &= okay;bucket['scans'].append(span)
        if state:bucket['completed_seq']=state['sequence']
        bucket['completed_end']=span[1]
    elif kind=='PROBE':
        raw=data.get('value',{});okay=matches('probe',raw,after=bucket['after_seq'],begin_at=bucket['after_clock'],timed=True);pid=raw.get('pid')
        if pid in bucket['pids'] and pid not in bucket['seen']:
            bucket['seen'].add(pid)
            if okay and raw.get('status')=='PRESENT':
                bucket['frame_positive']+=1
                _need(_integer(pid,1,2**31-1) and _integer(raw.get('start_ticks'),0,2**63-1),'FACT_PROBE')
                bucket['actors'].add((pid,raw['start_ticks']));_need(len(bucket['actors'])<=8192,'ACTOR_BUDGET')
    elif kind=='METADATA' and data.get('value',{}).get('available') is True:
        matches('metadata',data['value'].get('private'))
