"""Opt-in owned-pipe diagnostic observer; never signal an operating process."""
import math
import os
import secrets
import select
import signal
import struct
import threading
import time

from tools.pinned_proc_view import ProcView
from tools.proc_view_journal import canonical,parse_canonical,decode_wire


def _need(value,reason):
    if not value:raise ObserverError(reason)


def _remaining(deadline):
    value=deadline-time.monotonic()
    if value<=0:raise TimeoutError('DEADLINE')
    return min(value,.1)


def _write(fd,data,deadline):
    pending=memoryview(data)
    while pending:
        if not select.select([],[fd],[],_remaining(deadline))[1]:continue
        try:count=os.write(fd,pending)
        except BlockingIOError:continue
        _need(count>0,'PIPE_WRITE');pending=pending[count:]


def _exact(fd,count,deadline):
    raw=bytearray()
    while len(raw)<count:
        if not select.select([fd],[],[],_remaining(deadline))[0]:continue
        try:part=os.read(fd,count-len(raw))
        except BlockingIOError:continue
        if not part:raise ObserverError('PIPE_EOF')
        raw.extend(part)
    return bytes(raw)


def _send(fd,nonce,kind,value,deadline,maximum):
    raw=canonical({'schema':1,'nonce':nonce,'kind':kind,'value':value})
    _need(len(raw)<=maximum,'FRAME_BUDGET')
    _write(fd,struct.pack('!I',len(raw))+raw,deadline)


def _receive(fd,nonce,deadline,maximum):
    size=struct.unpack('!I',_exact(fd,4,deadline))[0]
    _need(0<size<=maximum,'FRAME_BUDGET')
    value=decode_wire(parse_canonical(_exact(fd,size,deadline)))
    _need(type(value) is dict and set(value)=={'schema','nonce','kind','value'} and
          type(value['schema']) is int and value['schema']==1 and value['nonce']==nonce and
          value['kind'] in {'MAP','READY','RESULT','ERROR','PROC_EVENT'},'FRAME')
    return value


class ObserverError(RuntimeError):
    pass


def with_owned_observer(view,observer,collector,*,view_factory=None,journal=None,timeout=10,max_bytes=262144):
    _need(type(timeout) in (int,float) and math.isfinite(timeout) and 0<timeout<=120 and
          type(max_bytes) is int and 1024<=max_bytes<=1024*1024,'BOUNDS')
    _need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'SIGCHLD')
    _need(threading.active_count()==1 and threading.get_native_id()==os.getpid(),'THREAD_PROFILE')
    _need(view.scope().get('endpoint_checks_pass') is True,'SCOPE')
    view_factory=view_factory or ProcView
    deadline=time.monotonic()+timeout;nonce=secrets.token_hex(32);pipes=[]
    try:
        read_fd,write_fd=os.pipe2(os.O_CLOEXEC|os.O_NONBLOCK);pipes.extend([read_fd,write_fd])
        control_read,control_write=os.pipe2(os.O_CLOEXEC|os.O_NONBLOCK);pipes.extend([control_read,control_write])
        pid=os.fork()
    except BaseException:
        for fd in pipes:
            try:os.close(fd)
            except OSError:pass
        raise
    if pid==0:
        os.close(read_fd);os.close(control_write);sent=False
        try:
            try:
                view.detach_in_child()
                if journal is not None:journal.detach_in_child()
                def child_sink(event):_send(write_fd,nonce,'PROC_EVENT',event,deadline,max_bytes)
                with view_factory(audit_sink=child_sink) as child_view:
                    mapping=child_view.mapping_identity()
                    _send(write_fd,nonce,'MAP',mapping,deadline,max_bytes)
                    _need(_exact(control_read,1,deadline)==b'A','ACK')
                    def ready():
                        nonlocal sent
                        _need(not sent,'DUPLICATE_READY')
                        _send(write_fd,nonce,'READY',{},deadline,max_bytes);sent=True
                    payload=observer(ready)
                    _need(sent,'READY_NOT_CALLED')
                _send(write_fd,nonce,'RESULT',payload,deadline,max_bytes)
                code=0
            except BaseException:
                _send(write_fd,nonce,'ERROR',{'error':'CHILD_CALLBACK_OR_SCOPE_ERROR'},deadline,max_bytes)
                code=1
            os.close(write_fd);os.close(control_read);os._exit(code)
        except BaseException:os._exit(1)
    os.close(write_fd);os.close(control_read)
    result={'status':'OWNED_OBSERVER_REJECTED','owned_child_pid_private':pid,
            'owned_child_reaped':False,'collector_started':False,
            'protocol_origin_confirmed':False,'mapping_matches':False,'policy_acceptance':False,
            'cleanup_errors':[],'early_exit_observed':False,'private_child_events':[]}
    authority=True;pending=[];frame_count=0;wire_count=0
    def receive_one():
        nonlocal frame_count,wire_count
        frame=_receive(read_fd,nonce,deadline,max_bytes)
        frame_count+=1;wire_count+=len(canonical(frame))
        _need(frame_count<=20000 and wire_count<=min(32*1024*1024,max_bytes*32),'PROTOCOL_BUDGET')
        return frame
    def relay(frame):
        if frame['kind']!='PROC_EVENT':return False
        _need(type(frame['value']) is dict,'CHILD_STREAM')
        if journal is not None:journal.append('PROC_EVENT',frame['value'])
        else:result['private_child_events'].append(frame['value'])
        return True
    def next_message():
        if pending:return pending.pop(0)
        while True:
            frame=receive_one()
            if not relay(frame):return frame
    def wait_once():
        nonlocal authority
        _need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL and threading.active_count()==1,'WAIT_POLICY_CHANGED')
        try:got,status=os.waitpid(pid,os.WNOHANG)
        except ChildProcessError:
            authority=False;raise ObserverError('WAIT_OWNERSHIP_LOST') from None
        if got:
            result['owned_child_reaped']=True;result['child_exit_status']=status
        return bool(got)
    def check():
        _remaining(deadline)
        while not pending and select.select([read_fd],[],[],0)[0]:
            frame=receive_one()
            if not relay(frame):
                pending.append(frame)
                if frame['kind'] in {'RESULT','ERROR'}:
                    result['early_exit_observed']=True;raise ObserverError('EARLY_RESULT')
        if wait_once():
            result['early_exit_observed']=True;raise ObserverError('EARLY_EXIT')
    def reap_by(limit):
        while not wait_once():
            if time.monotonic()>=limit:return False
            time.sleep(.005)
        return True
    try:
        frame=next_message()
        _need(frame['kind']=='MAP' and type(frame['value']) is dict and
              type(frame['value'].get('pid')) is int and frame['value']['pid']==pid,'MAPPING_PID')
        mapped=view.compare_child_mapping(frame['value'])
        _need(mapped.get('mapping_matches') is True,'MAPPING')
        result.update(protocol_origin_confirmed=True,mapping_matches=True)
        _write(control_write,b'A',deadline)
        frame=next_message();_need(frame['kind']=='READY','READY')
        result['collector_started']=True;result['private_collector']=collector(check)
        _remaining(deadline);_need(not result['early_exit_observed'],'EARLY_EXIT')
        frame=next_message();_need(frame['kind']=='RESULT','RESULT')
        result['private_observer']=frame['value']
        while True:
            if not select.select([read_fd],[],[],_remaining(deadline))[0]:continue
            extra=os.read(read_fd,1);_need(not extra,'EXTRA_FRAME');break
        _need(result['owned_child_reaped'] or reap_by(deadline),'CHILD_EXIT_TIMEOUT')
        _need(result.get('child_exit_status')==0,'CHILD_EXIT_FAILED')
        result['status']='OWNED_OBSERVER_COMPLETE'
    except Exception as error:
        result['status']='OWNED_OBSERVER_TIMEOUT' if isinstance(error,TimeoutError) else 'OWNED_OBSERVER_REJECTED'
        result['error_type']=type(error).__name__
    finally:
        if not result['owned_child_reaped']:
            try:
                if not wait_once() and authority:
                    # Only the fork-return direct unreaped child; never a mapped PID.
                    _need(signal.getsignal(signal.SIGCHLD)==signal.SIG_DFL,'WAIT_POLICY_CHANGED')
                    os.kill(pid,signal.SIGTERM)
                    if not reap_by(time.monotonic()+.25):
                        os.kill(pid,signal.SIGKILL)
                        _need(reap_by(time.monotonic()+.25),'CLEANUP_TIMEOUT')
            except Exception as error:
                result['cleanup_errors'].append({'type':type(error).__name__,'errno':getattr(error,'errno',None)})
        for fd in (read_fd,control_write):
            try:os.close(fd)
            except OSError as error:result['cleanup_errors'].append({'type':type(error).__name__,'errno':error.errno})
    if result['cleanup_errors'] or not result['owned_child_reaped']:result['status']='OWNED_OBSERVER_CLEANUP_UNCONFIRMED'
    if journal is not None:
        # Collector's process evidence is already in SCAN/PROBE/METADATA/SUMMARY.
        # Do not duplicate arbitrary callback objects or Python int-keyed maps.
        recorded={k:v for k,v in result.items() if k not in {'private_collector','private_child_events'}}
        recorded['collector_returned']='private_collector' in result
        journal.append('OBSERVER',recorded)
    return result
