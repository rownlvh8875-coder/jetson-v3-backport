"""CPU_FAKE/FIXTURE: no device, inference, USB or production path access."""
import time
import hashlib
import numpy as np
import pytest
from recording import format as f
from recording.recorder import Recorder


def provenance():
    return dict(carrot_head=f.BASE_SHA, recorder_source_sha=hashlib.sha256(f.canonical({'recorder.py':'5'*64})).hexdigest(),
                source_model_sha='2'*64, source_spec_sha='3'*64,
                source_kind='existing_jetlink_nonstate',capture_id='4'*32,
                source_files={'recorder.py':'5'*64})


def inputs():
    result={n:np.zeros(s,dtype=d) for n,(s,d) in f.INPUTS.items()}
    result['new_img'].flat[:256]=np.arange(256,dtype=np.uint8)
    result['desire'][0]=-0.0
    return result


def metadata(i):
    tick=1_000_000_000+i*50_000_000
    return dict(main_frame_id=100+i,extra_frame_id=200+i,
                model_timestamp_ns=tick,monotonic_ns=tick+10,
                main_sof_ns=tick,extra_sof_ns=tick+1,selection=(0,1),
                transforms=(np.eye(3,dtype=np.float32),np.eye(3,dtype=np.float32)),flags=int(i==0))


def ready(rec):
    deadline=time.monotonic()+8
    while not rec.ready and rec.reason is None and time.monotonic()<deadline:
        rec.poll();time.sleep(.005)
    return rec.ready


def finish(rec):
    rec.close(timeout=10)
    return rec


def test_exact_complete_and_collision(tmp_path):
    out=tmp_path/'capture'
    rec=Recorder(out,provenance(),frames=3)
    assert ready(rec)
    data=inputs()
    for i in range(3):
        assert rec.observe(**data,metadata=metadata(i))
        time.sleep(.02)
    finish(rec)
    assert rec.count==3 and rec.reason is None
    assert {p.name for p in out.iterdir()}=={'frames.bin','manifest.json','COMPLETE'}
    raw=np.memmap(out/'frames.bin',dtype=f.RECORD_DTYPE,mode='r',offset=f.HEADER_BYTES,shape=(3,))
    for i in range(3):
        for name in data:assert raw[i][name].tobytes()==data[name].tobytes()
    old=f.file_sha(out/'frames.bin')
    again=Recorder(out,provenance(),frames=3)
    assert not ready(again);finish(again)
    assert again.reason is not None and old==f.file_sha(out/'frames.bin')


@pytest.mark.parametrize('fault',['short_write','fsync','manifest','exception','crash','low_space'])
def test_writer_failures_never_complete_or_raise(tmp_path,fault):
    rec=Recorder(tmp_path/fault,provenance(),frames=1,fault={fault:True})
    if ready(rec):assert rec.observe(**inputs(),metadata=metadata(0))
    finish(rec)
    assert rec.reason is not None
    assert not (tmp_path/fault/'COMPLETE').exists()


def test_slow_writer_overflow_bounded_and_nonblocking(tmp_path):
    rec=Recorder(tmp_path/'slow',provenance(),frames=16,depth=4,fault={'delay':.5})
    assert ready(rec)
    data=inputs();start=time.monotonic()
    accepted=[rec.observe(**data,metadata=metadata(i)) for i in range(8)]
    elapsed=time.monotonic()-start
    assert sum(accepted)<=4 and rec.reason=='QUEUE_FULL'
    assert elapsed<.3  # writer .5s wait cannot appear in observer
    assert rec.high_water<=4
    finish(rec)
    assert not (tmp_path/'slow'/'COMPLETE').exists()


@pytest.mark.parametrize('bad',['shape','dtype','readonly','noncontiguous','nan','gap'])
def test_bad_input_only_invalidates_recorder(tmp_path,bad):
    rec=Recorder(tmp_path/bad,provenance(),frames=2)
    assert ready(rec);data=inputs()
    assert rec.observe(**data,metadata=metadata(0));time.sleep(.03)
    meta=metadata(1)
    if bad=='shape':data['desire']=data['desire'][:1]
    if bad=='dtype':data['desire']=data['desire'].astype(np.float64)
    if bad=='readonly':
        # Read-only source arrays are valid: observer only reads/copies.
        data['desire'].flags.writeable=False
    if bad=='noncontiguous':data['new_img']=np.zeros((2,6,128,512),np.uint8)[...,::2]
    if bad=='nan':data['action_t'][0,0]=np.nan
    if bad=='gap':meta['main_frame_id']+=1
    rec.observe(**data,metadata=meta);finish(rec)
    assert (tmp_path/bad/'COMPLETE').exists()==(bad=='readonly')


def test_stop_and_child_death_isolated(tmp_path):
    rec=Recorder(tmp_path/'stopped',provenance(),frames=2)
    assert ready(rec)
    rec.stop('TEST_STOP')
    assert not rec.observe(**inputs(),metadata=metadata(0))
    finish(rec)
    assert not (tmp_path/'stopped'/'COMPLETE').exists()


def test_bad_setup_is_contained(tmp_path):
    for frames in (0,1025):
        rec=Recorder(tmp_path/'bad',provenance(),frames=frames)
        assert not rec.observe(**inputs(),metadata=metadata(0))
        finish(rec);assert rec.reason=='SETUP_ERROR'
    parent=tmp_path/'not_a_directory';parent.write_text('keep')
    rec=Recorder(parent/'out',provenance(),frames=1)
    assert not ready(rec);finish(rec)
    assert parent.read_text()=='keep'


@pytest.mark.parametrize('change',[{'selection':(0,)},{'flags':2},{'model_timestamp_ns':0}])
def test_bad_metadata_is_never_a_complete_dataset(tmp_path,change):
    rec=Recorder(tmp_path/'metadata',provenance(),frames=1)
    assert ready(rec)
    meta=metadata(0);meta.update(change)
    rec.observe(**inputs(),metadata=meta);finish(rec)
    assert not (tmp_path/'metadata'/'COMPLETE').exists()


def test_writer_demotes_before_site_and_numpy_import(monkeypatch,tmp_path):
    import recording.recorder as module
    calls=[]
    class Process:
        returncode=None
        def poll(self):return None
        def wait(self,timeout):self.returncode=0;return 0
    def popen(command,**kwargs):
        assert command[1:3]==['-S','-c']
        assert kwargs['env']['OPENBLAS_NUM_THREADS']=='1'
        code=command[3]
        import ast
        nodes=ast.parse(code).body
        imports=[(i,n.names[0].name) for i,n in enumerate(nodes) if isinstance(n,ast.Import)]
        assert imports[0][1]=='os'
        demote=next(i for i,n in enumerate(nodes) if isinstance(n,ast.Expr) and 'sched_setscheduler' in ast.unparse(n))
        assert demote<next(i for i,n in imports if n=='site')
        assert demote<next(i for i,n in imports if n=='runpy')
        calls.append(command);return Process()
    monkeypatch.setattr(module.subprocess,'Popen',popen)
    rec=Recorder(tmp_path/'never-created',provenance(),frames=1)
    assert calls;rec.close()
    assert not (tmp_path/'never-created').exists()
