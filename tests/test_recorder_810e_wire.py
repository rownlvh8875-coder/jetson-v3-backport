"""Separate package namespaces and actual810e server/daemon wire, CPU_FAKE."""
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
from adapters.carrot import recorder_810e as r
from recorder_810e_support import REFERENCE


@pytest.mark.parametrize('shared',[True,False])
def test_server_consumes_same_bytes_as_strict_dataset(tmp_path,shared):
    archive=subprocess.check_output(['git','-C',str(REFERENCE),'archive',r.BASE_SHA,'third_party/jetlink/jetlink'])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        for member in stream:
            if member.isfile():
                assert member.name.startswith('third_party/jetlink/jetlink/') and '..' not in Path(member.name).parts
                p=tmp_path/member.name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(stream.extractfile(member).read())
    (tmp_path/'nav.json').write_bytes(r.sources(REFERENCE)[r.SPEC_FILE])
    folder=tmp_path/'capture810';folder.mkdir()
    for name,raw in r.recorder_files(REFERENCE).items():
        if name.startswith(r.PACKAGE+'/'):(folder/Path(name).name).write_bytes(raw)
    helper=Path(__file__).with_name('fixtures')/'recorder_810e_wire.py'
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',OPENBLAS_NUM_THREADS='1')
    server=subprocess.Popen([sys.executable,'-B',str(helper),'server',str(tmp_path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,env=env)
    try:
        messages=queue.Queue();threading.Thread(target=lambda:messages.put(server.stdout.readline()),daemon=True).start()
        line=messages.get(timeout=20)
        assert line,server.stderr.read()
        ready=json.loads(line)
        assert Path(ready['module']).is_relative_to(tmp_path)
        client=subprocess.run([sys.executable,'-B',str(helper),'client',str(tmp_path),str(ready['port']),str(int(shared))],
                              capture_output=True,text=True,env=env,timeout=30)
        assert client.returncode==0,client.stdout+client.stderr
        out,err=server.communicate(timeout=10);assert server.returncode==0,out+err
        c,s=json.loads(client.stdout.strip().splitlines()[-1]),json.loads(out.strip().splitlines()[-1])
        assert c['recorded_hashes']==s['engine_input_hashes']
        assert c['frames']==3 and c['protocol']==s['protocol']==2
        assert not s['openpilot_loaded']
    finally:
        if server.poll() is None:server.terminate();server.communicate(timeout=5)
