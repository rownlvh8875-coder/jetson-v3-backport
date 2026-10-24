"""Sixteen source-backed execution/input/output/transport combinations."""
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


@pytest.mark.parametrize('shared',[True,False])
@pytest.mark.parametrize('chunks',[True,False])
@pytest.mark.parametrize('compact',[True,False])
@pytest.mark.parametrize('overlap',[True,False])
def test_source_joining_observer_and_engine_identity(tmp_path,shared,chunks,compact,overlap):
    paths=['third_party/jetlink/jetlink','tools/jetlink/host_reader.py','tools/jetlink/server.py',
           'openpilot/selfdrive/modeld/jetlink','openpilot/common/runtime_diagnostics.py']
    raw=subprocess.check_output(['git','-C',str(REFERENCE),'archive',r.BASE_SHA,*paths])
    with tarfile.open(fileobj=io.BytesIO(raw)) as stream:
        for m in stream:
            if m.isfile():
                assert not Path(m.name).is_absolute() and '..' not in Path(m.name).parts
                p=tmp_path/m.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(stream.extractfile(m).read())
    folder=tmp_path/'capturea559';folder.mkdir()
    for name,raw in r.recorder_files(REFERENCE).items():
        if name.startswith(r.PACKAGE+'/'):(folder/Path(name).name).write_bytes(raw)
    helper=Path(__file__).with_name('fixtures')/'recorder_a559_wire.py'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',OPENBLAS_NUM_THREADS='1')
    server=subprocess.Popen([sys.executable,'-B',str(helper),'server',str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        messages=queue.Queue();threading.Thread(target=lambda:messages.put(server.stdout.readline()),daemon=True).start()
        ready=json.loads(messages.get(timeout=20))
        assert Path(ready['session_module']).is_relative_to(tmp_path)
        client=subprocess.run([sys.executable,'-B',str(helper),'client',str(tmp_path),str(ready['port']),
            *[str(int(v)) for v in [shared,chunks,compact,overlap]]],capture_output=True,text=True,env=env,timeout=35)
        assert client.returncode==0,client.stdout+client.stderr
        out,err=server.communicate(timeout=10)
        assert server.returncode==0,out+err
        c,s=json.loads(client.stdout.strip().splitlines()[-1]),json.loads(out.strip().splitlines()[-1])
        assert c['recorded_hashes']==c['submitted_hashes']==s['engine_hashes']
        assert c['packed_hashes']==s['engine_packed_hashes']
        assert c['logical_request_hashes']==s['session_request_hashes']
        assert c['frames']==s['executions']==5
        assert c['protocol']==s['protocol']==2 and c['negotiated_chunks'] is chunks
        assert c['chunked_requests']==c['native_writes']==(5 if chunks else 0)
        assert c['compact_reply'] is compact
        assert len(set(c['reply_elements']))==1
        assert c['reply_elements'][0]==(2066 if compact else 18580)
        assert c['desire_pulses']==[0.,1.,0.,0.,1.]
        assert len(set(c['scalar_hashes']))==5
        assert c['single_reservation_per_frame'] and c['diagnostics_peak_correlated']
        assert c['diagnostics_events']==5
        assert not s['openpilot_loaded']
        with (tmp_path/'wire-a559-receipt.json').open('x') as file:
            json.dump(dict(shared=shared,chunks=chunks,compact=compact,overlap=overlap,client=c,server=s),file,sort_keys=True)
    finally:
        if server.poll() is None:server.terminate();server.communicate(timeout=5)
