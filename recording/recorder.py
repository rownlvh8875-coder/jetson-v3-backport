"""Opt-in observer: bounded memfd slots and an isolated, non-realtime writer.

Construction/close are startup/shutdown operations. observe never waits for disk,
writer progress or a slot. The caller must still shield the observer boundary.
This module imports no inference, camera, CUDA or vehicle code.
"""
from __future__ import annotations
from collections import deque
import mmap
import os
from pathlib import Path
import shutil
import socket
import struct
import subprocess
import sys
import time
import numpy as np
from . import format as f

CONTROL_BYTES=4096
RESERVE_BYTES=64*1024*1024
DEPTHS=(4,8,16)


class Recorder:
    def __init__(self,output,provenance,frames=256,depth=4,fault=None,measure=False):
        self.count=0;self.frames=frames;self.ready=False;self.reason=None
        self.high_water=0;self.depth=depth;self.process=None;self.sock=None
        self.mapping=None;self.slots=None;self.fd=None;self.free=deque()
        self.measure=measure;self.copy_ns=[];self.put_ns=[]
        try:
            f.expected_size(frames);f.validate_provenance(provenance)
            if type(depth) is not int or depth not in DEPTHS:raise ValueError('queue depth')
            config=f.canonical(dict(output=str(Path(output).absolute()),provenance=provenance,
                                    frames=frames,depth=depth,fault=fault or {}))
            if len(config)>CONTROL_BYTES-8:raise ValueError('config length')
            self.fd=os.memfd_create('v3-input-observer',flags=0)
            os.ftruncate(self.fd,CONTROL_BYTES+depth*f.RECORD_BYTES)
            self.mapping=mmap.mmap(self.fd,0)
            # Touch every allocated page outside the observer path.
            self.mapping[:]=bytes(len(self.mapping))
            self.mapping[4:8]=struct.pack('<I',len(config));self.mapping[8:8+len(config)]=config
            self.slots=np.ndarray((depth,),f.RECORD_DTYPE,buffer=self.mapping,offset=CONTROL_BYTES)
            self.free=deque(range(depth))
            self.sock,child=socket.socketpair(socket.AF_UNIX,socket.SOCK_DGRAM)
            self.sock.setblocking(False)
            try:
                environment=dict(os.environ,OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
                environment['PYTHONPATH']=os.pathsep.join(str(Path(p or os.getcwd()).absolute()) for p in sys.path)
                # -S avoids site hooks and NumPy import while still inheriting
                # modeld's realtime policy. Demote before importing either.
                bootstrap=("import os; os.sched_setscheduler(0,os.SCHED_OTHER,os.sched_param(0)); "
                           "os.setpriority(os.PRIO_PROCESS,0,10); import site; site.main(); "
                           "import runpy; runpy.run_module("+repr(__name__)+",run_name='__main__')")
                self.process=subprocess.Popen([sys.executable,'-S','-c',bootstrap,'--writer',str(self.fd),str(child.fileno())],
                    pass_fds=(self.fd,child.fileno()),stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,close_fds=True,env=environment)
            finally:child.close()
        except Exception:self.stop('SETUP_ERROR')

    def stop(self,reason='STOPPED'):
        """Nonblocking cancellation. Never cleans up/rebinds a live writer's memory."""
        if self.reason is None:self.reason=reason
        self.ready=False
        try:
            if self.mapping is not None:self.mapping[0]=1
        except Exception:pass

    def poll(self):
        try:
            if self.reason is not None:return
            for _ in range(self.depth+2):
                try:packet=self.sock.recv(128)
                except BlockingIOError:break
                if packet==b'R':self.ready=True
                elif len(packet)==3 and packet[:1]==b'A':
                    slot=struct.unpack('<H',packet[1:])[0]
                    if slot>=self.depth or slot in self.free:raise ValueError('bad credit')
                    self.free.append(slot)
                elif packet.startswith(b'E'):
                    self.stop('WRITER_'+packet[1:].decode('ascii'));return
                else:raise ValueError('bad writer packet')
            if self.process is not None and self.process.poll() is not None:
                if self.process.returncode!=0 or self.count<self.frames:self.stop('WRITER_EXIT')
        except Exception:self.stop('WRITER_PROTOCOL')

    def observe(self,new_img,desire,traffic_convention,action_t,metadata):
        """Copy borrowed logical inputs exactly once; all failures disable only capture.

        False before READY is explicit pre-roll (no recording has started). False
        after a failure is terminal, never a silent gap in a COMPLETE sequence.
        """
        try:
            if self.reason is not None or self.count>=self.frames:return False
            self.poll()
            if not self.ready or self.reason is not None:return False
            values=(new_img,desire,traffic_convention,action_t)
            for (name,(shape,dtype)),value in zip(f.INPUTS.items(),values):
                if not isinstance(value,np.ndarray) or value.shape!=shape or value.dtype!=np.dtype(dtype) or not value.flags.c_contiguous:
                    self.stop('INPUT_CONTRACT');return False
            if not self.free:self.stop('QUEUE_FULL');return False
            slot=self.free.popleft();record=self.slots[slot]
            start=time.perf_counter_ns() if self.measure else 0
            record['index']=self.count
            for key in ('main_frame_id','extra_frame_id','model_timestamp_ns','monotonic_ns','main_sof_ns','extra_sof_ns'):
                value=metadata[key]
                if type(value) is not int or not 0<=value<2**64:raise ValueError('metadata integer')
                record[key]=value
            flags,selection=metadata['flags'],metadata['selection']
            if type(flags) is not int or flags not in (0,1) or selection not in ((0,0),(0,1)):
                raise ValueError('flags/camera roles')
            record['flags']=flags;record['reserved']=0
            record['selection']=selection
            record['expected_interval_ns']=f.EXPECTED_INTERVAL_NS
            transforms=metadata['transforms']
            if len(transforms)!=2:raise ValueError('transform count')
            for index,value in enumerate(transforms):
                if not isinstance(value,np.ndarray) or value.shape!=(3,3) or value.dtype!=np.dtype('<f4'):raise ValueError('transform contract')
                np.copyto(record['transforms'][index],value,casting='no')
            for name,value in zip(f.INPUTS,values):np.copyto(record[name],value,casting='no')
            copied=time.perf_counter_ns() if self.measure else 0
            self.sock.send(struct.pack('<H',slot))
            if self.measure:
                self.copy_ns.append(copied-start);self.put_ns.append(time.perf_counter_ns()-copied)
            self.count+=1;self.high_water=max(self.high_water,self.depth-len(self.free))
            return True
        except BlockingIOError:self.stop('QUEUE_SEND_FULL');return False
        except Exception:self.stop('OBSERVER_ERROR');return False

    def close(self,timeout=10):
        """Off-hot-path shutdown; only reaps the private recorder child."""
        if self.count!=self.frames and self.reason is None:self.stop('INCOMPLETE')
        try:
            if self.process is not None:
                try:self.process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    self.stop('WRITER_TIMEOUT');self.process.terminate()
                    try:self.process.wait(timeout=2)
                    except subprocess.TimeoutExpired:self.process.kill();self.process.wait(timeout=2)
                self.poll()
        except Exception:self.stop('CLOSE_ERROR')
        self.slots=None
        for name in ('mapping','sock'):
            try:
                obj=getattr(self,name)
                if obj is not None:obj.close()
            except Exception:pass
            setattr(self,name,None)
        try:
            if self.fd is not None:os.close(self.fd)
        except Exception:pass
        self.fd=None


def _directory(output,required):
    # No symlink ancestors, no operating-route output, no recursive creation.
    output=Path(output)
    if not output.is_absolute() or '..' in output.parts:raise ValueError('output path')
    if '/data/media/0/realdata' in str(output):raise ValueError('route output forbidden')
    for ancestor in (output.parent,*output.parent.parents):
        if ancestor.is_symlink():raise ValueError('symlink parent')
    if not output.parent.is_dir():raise ValueError('output parent missing')
    if shutil.disk_usage(output.parent).free<required:raise OSError('space gate')
    output.mkdir(mode=0o700)  # exclusive: never reuse or remove an existing output
    return output


def _put(fd,data,offset,fault):
    if fault.get('short_write') and offset>=f.HEADER_BYTES:
        os.pwrite(fd,data[:-1],offset);raise OSError('short write injection')
    if os.pwrite(fd,data,offset)!=len(data):raise OSError('short write')


def _fsync(fd,fault):
    if fault.get('fsync'):raise OSError('fsync injection')
    os.fsync(fd)


def _manifest(config,first,last,intervals,data):
    diagnostic=dict(expected_ns=f.EXPECTED_INTERVAL_NS,min_ns=int(min(intervals)) if intervals else 0,
                    max_ns=int(max(intervals)) if intervals else 0)
    diagnostic.update({f'p{p}_ns':float(np.percentile(intervals,p)) if intervals else 0.0 for p in (50,95,99)})
    value=dict(schema=1,kind='v3-logical-input-dataset',status='COMPLETE',expected_frames=config['frames'],
               frames=config['frames'],continuity='CONTIGUOUS',spec_digest=f.SPEC_DIGEST,target_sha256=f.TARGET_SHA,
               provenance=config['provenance'],inputs={n:dict(shape=list(s),dtype=d) for n,(s,d) in f.INPUTS.items()},
               files={'frames.bin':dict(bytes=data.stat().st_size,sha256=f.file_sha(data))},
               capture_start_ns=first,capture_end_ns=last,interval_diagnostic=diagnostic,
               no_gps_raw_camera=True,state_tensors_stored=False)
    value['dataset_digest']=f.dataset_digest(value)
    return value


def _writer(memfd,sockfd):
    import json
    channel=socket.socket(fileno=sockfd);channel.settimeout(.1)
    memory=mmap.mmap(memfd,0);data_fd=None;directory_fd=None
    try:
        # modeld is realtime; only this exec child drops to ordinary scheduling.
        os.sched_setscheduler(0,os.SCHED_OTHER,os.sched_param(0));os.setpriority(os.PRIO_PROCESS,0,10)
        length=struct.unpack('<I',memory[4:8])[0]
        config=json.loads(memory[8:8+length]);fault=config['fault']
        total=f.expected_size(config['frames']);f.validate_provenance(config['provenance'])
        if fault.get('low_space'):raise OSError('space gate injection')
        directory=_directory(config['output'],total+RESERVE_BYTES)
        data=directory/'frames.bin.partial'
        data_fd=os.open(data,os.O_CREAT|os.O_EXCL|os.O_RDWR|os.O_NOFOLLOW,0o600)
        os.posix_fallocate(data_fd,0,total)
        _put(data_fd,f.header_bytes(config['provenance'],config['frames']),0,fault)
        (directory/'status.partial').write_bytes(b'INCOMPLETE\n')
        channel.send(b'R')
        previous=None;intervals=[];first=last=0;count=0
        deadline=time.monotonic()+30
        while count<config['frames']:
            if memory[0]:raise RuntimeError('observer stopped')
            if time.monotonic()>deadline:raise TimeoutError('capture deadline')
            try:packet=channel.recv(16)
            except socket.timeout:continue
            if len(packet)!=2:raise ValueError('slot packet')
            slot=struct.unpack('<H',packet)[0]
            if slot>=config['depth']:raise ValueError('slot index')
            if fault.get('delay'):time.sleep(fault['delay'])
            if fault.get('exception'):raise RuntimeError('writer injection')
            if fault.get('crash'):os._exit(31)
            record=np.ndarray((),f.RECORD_DTYPE,buffer=memory,offset=CONTROL_BYTES+slot*f.RECORD_BYTES)
            f.validate_record(record,previous)
            if int(record['index'])!=count:raise ValueError('record order')
            if count==0:first=int(record['monotonic_ns']);deadline=time.monotonic()+config['frames']*.05+10
            else:intervals.append(int(record['model_timestamp_ns'])-int(previous['model_timestamp_ns']))
            last=int(record['monotonic_ns'])
            _put(data_fd,record.tobytes(),f.HEADER_BYTES+count*f.RECORD_BYTES,fault)
            previous=record.copy();del record
            count+=1;channel.send(b'A'+packet)
        if memory[0]:raise RuntimeError('observer stopped')
        _fsync(data_fd,fault);os.close(data_fd);data_fd=None
        manifest=_manifest(config,first,last,intervals,data)
        if fault.get('manifest'):raise OSError('manifest injection')
        temp=directory/'manifest.json.partial'
        with temp.open('xb') as stream:
            stream.write(f.canonical(manifest));stream.flush();_fsync(stream.fileno(),fault)
        if memory[0]:raise RuntimeError('observer stopped')
        # Hard links are no-overwrite publication. COMPLETE is the final operation.
        os.link(data,directory/'frames.bin');data.unlink()
        os.link(temp,directory/'manifest.json');temp.unlink()
        (directory/'status.partial').unlink()
        directory_fd=os.open(directory,os.O_DIRECTORY|os.O_RDONLY);_fsync(directory_fd,fault)
        os.close(directory_fd);directory_fd=None
        if memory[0]:raise RuntimeError('observer stopped')
        os.link(directory/'manifest.json',directory/'COMPLETE')
        return 0
    except Exception as exc:
        try:channel.send(b'E'+type(exc).__name__.encode('ascii'))
        except Exception:pass
        return 1
    finally:
        for descriptor in (data_fd,directory_fd):
            if descriptor is not None:
                try:os.close(descriptor)
                except Exception:pass
        channel.close();memory.close()


if __name__=='__main__':
    if len(sys.argv)!=4 or sys.argv[1]!='--writer':raise SystemExit(2)
    raise SystemExit(_writer(int(sys.argv[2]),int(sys.argv[3])))
