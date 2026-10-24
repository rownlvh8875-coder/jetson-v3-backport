"""Unchanged hook rejection versus an experimental observation boundary.

32 switch combinations for each observer; 4 supported native AIO partitions.
Passing negative cases preserve the compatibility blocker, not deployment PASS.
"""
import io
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tarfile
import threading

import pytest

from adapters.carrot import recorder_a559 as r
from recorder_810e_support import REFERENCE

TARGET='5bbbe160822c7cae4245d7a8e96b40d158941ff7'

@pytest.mark.parametrize('hook_mode',['historical','boundary_probe'])
@pytest.mark.parametrize('defer_nav',[True,False])
@pytest.mark.parametrize('shared',[True,False])
@pytest.mark.parametrize('chunks',[True,False])
@pytest.mark.parametrize('compact',[True,False])
@pytest.mark.parametrize('overlap',[True,False])
def test_source_joining_observer_and_engine_identity(tmp_path,shared,chunks,compact,overlap,defer_nav,hook_mode):
    run_case(tmp_path,shared,chunks,compact,overlap,defer_nav,8192,True,hook_mode)


@pytest.mark.parametrize("quantum,deferred",[(32768,True),(32768,False)])
@pytest.mark.parametrize("shared,nav",[(True,True),(False,False)])
def test_supported_writer_partitions(tmp_path,quantum,deferred,shared,nav):
    run_case(tmp_path,shared,True,True,True,nav,quantum,deferred,'boundary_probe')


def run_case(tmp_path,shared,chunks,compact,overlap,defer_nav,quantum,deferred,hook_mode):
    paths=['third_party/jetlink/jetlink','tools/jetlink/host_reader.py','tools/jetlink/server.py',
           'openpilot/selfdrive/modeld/jetlink','openpilot/common/runtime_diagnostics.py']
    raw=subprocess.check_output(['git','-C',str(REFERENCE),'archive',TARGET,*paths])
    with tarfile.open(fileobj=io.BytesIO(raw)) as stream:
        for m in stream:
            if m.isfile():
                assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                p=tmp_path/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(stream.extractfile(m).read())
    folder=tmp_path/'capture5bb';folder.mkdir()
    for name,raw in r.recorder_files(REFERENCE).items():
        if name.startswith(r.PACKAGE+'/'):(folder/Path(name).name).write_bytes(raw)
    helper=Path(__file__).with_name('fixtures')/'recorder_5bb_wire.py'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',OPENBLAS_NUM_THREADS='1')
    server=subprocess.Popen([sys.executable,'-B',str(helper),'server',str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        messages=queue.Queue();threading.Thread(target=lambda:messages.put(server.stdout.readline()),daemon=True).start()
        ready=json.loads(messages.get(timeout=20))
        assert Path(ready['session_module']).is_relative_to(tmp_path)
        client=subprocess.run([sys.executable,'-B',str(helper),'client',str(tmp_path),str(ready['port']),
            *[str(int(v)) for v in [shared,chunks,compact,overlap,defer_nav]],str(quantum),str(int(deferred)),hook_mode],capture_output=True,text=True,env=env,timeout=35)
        assert client.returncode==0,client.stdout+client.stderr
        out,err=server.communicate(timeout=10)
        assert server.returncode==0,out+err
        c,s=json.loads(client.stdout.strip().splitlines()[-1]),json.loads(out.strip().splitlines()[-1])
        with (tmp_path/'wire-5bb-receipt.json').open('x') as file:
            json.dump(dict(shared=shared,chunks=chunks,compact=compact,overlap=overlap,
                defer_nav=defer_nav,quantum=quantum,deferred=deferred,hook_mode=hook_mode,
                client=c,server=s),file,sort_keys=True)
        if hook_mode=='historical' and defer_nav:
            assert c['status']=='RECORDER_API_INCOMPATIBLE'
            assert c['original_infer_calls']==c['observer_calls']==c['frames']==s['executions']==0
            return
        assert c['recorded_hashes']==c['submitted_hashes']==s['engine_hashes']
        assert c['defer_nav'] is defer_nav
        assert c['navigation_hashes']==s['navigation_hashes']
        assert c['map_used']==([False,True,True,True,True] if defer_nav else [False]*5)
        assert s['map_hashes']==([c['map_hashes'][0],*c['map_hashes'][:-1]] if defer_nav else c['map_hashes'])
        if defer_nav:
            assert c['packed_hashes'][0]==s['engine_packed_hashes'][0]
            assert all(a!=b for a,b in zip(c['packed_hashes'][1:],s['engine_packed_hashes'][1:]))
        else:assert c['packed_hashes']==s['engine_packed_hashes']
        assert s['state_generations']==[0,1,2,3,4]
        for phase in ('infer_begin','flush_map','infer_end'):
            expected=[] if phase=='flush_map' and not defer_nav else c['scalar_hashes']
            assert [v['sha256'] for v in c['sentinel_phases'] if v['phase']==phase]==expected
        assert c['logical_request_hashes']==s['session_request_hashes']
        assert c['frames']==s['executions']==5
        assert c['protocol']==s['protocol']==2 and c['negotiated_chunks'] is chunks
        assert c['chunked_requests']==c['native_batches']==((10 if defer_nav else 5) if chunks else 0)
        assert c['compact_reply'] is compact
        assert len(set(c['reply_elements']))==1
        assert c['reply_elements'][0]==(2066 if compact else 18580)
        assert c['desire_pulses']==[0.,1.,0.,0.,1.]
        assert len(set(c['scalar_hashes']))==5
        assert c['single_reservation_per_frame'] and c['diagnostics_peak_correlated']
        assert c['diagnostics_events']==5
        assert not s['openpilot_loaded']
    finally:
        if server.poll() is None:server.terminate();server.communicate(timeout=5)
