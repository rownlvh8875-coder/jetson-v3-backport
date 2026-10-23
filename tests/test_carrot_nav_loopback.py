"""Actual Nav comma candidate versus reviewed WIP host; separate processes.

CPU_FAKE hardware boundary only. TCP framing, JetlinkClient, preparation,
daemon IPC, Nav parser and JoiningModel execute from their actual sources.
"""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import pytest

ROOT=Path(__file__).resolve().parents[1]
HELPER=Path(__file__).with_name('current_carrot_loopback_peer.py')


def run_pair(scenario):
    comma=Path(os.environ['CARROT_NAV_CANDIDATE_ROOT']).resolve()
    host=Path(os.environ['CARROT_HOST_CANDIDATE_ROOT']).resolve()
    def env(root,client):
        paths=[root/'third_party/jetlink']
        if client:paths.insert(0,root)
        return dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONUNBUFFERED='1',PYTHONPATH=os.pathsep.join(map(str,paths)))
    server=subprocess.Popen([sys.executable,str(HELPER),'server',scenario],env=env(host,False),stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        ready=queue.Queue();threading.Thread(target=lambda:ready.put(server.stdout.readline()),daemon=True).start()
        line=ready.get(timeout=20);assert line,server.stderr.read()
        hello=json.loads(line);assert Path(hello['module']).is_relative_to(host)
        client=subprocess.run([sys.executable,str(HELPER),'client',scenario,str(hello['port'])],env=env(comma,True),capture_output=True,text=True,timeout=25)
        assert client.returncode==0,client.stdout+client.stderr
        out,err=server.communicate(timeout=10);assert server.returncode==0,out+err
        c,s=json.loads(client.stdout.strip().splitlines()[-1]),json.loads(out.strip().splitlines()[-1])
        assert Path(c['module']).is_relative_to(comma)
        assert all(Path(p).is_relative_to(comma) for p in c['glue_modules'].values())
        assert c['evidence']==s['evidence']=='CPU_FAKE' and c['protocol']==s['protocol']==3
        assert not s['has_openpilot_imports']
        print('NAV_CROSS_NAMESPACE_EVIDENCE',json.dumps({'scenario':scenario,'client':c,'host':s},sort_keys=True))
        return c,s
    finally:
        if server.poll() is None:server.terminate();server.communicate(timeout=5)


def test_v3_p3_nav_daemon_ipc_and_actual_parser():
    c,s=run_pair('daemon_continuous')
    assert c['prepared'] and c['approval_recorded'] and c['ipc_frames']==2
    assert c['finite_parsed'] and c['changing_outputs'] and not c['daemon_link_failed']
    assert c['parsed_shapes']=={'plan':[1,33,15],'lead':[1,3,6,4],'action':[1,4]}
    assert s['state_seen']==[[0.,0.,0.],[1.,1.,1.]] and s['valid']


@pytest.mark.parametrize('scenario',['daemon_invalid_state','daemon_identity_change','daemon_timeout','daemon_disconnect','daemon_wrong_frame','daemon_stale_sequence','daemon_nonfinite','daemon_truncated'])
def test_nav_joining_model_faults_restore_real_local_fallback_path(scenario):
    c,s=run_pair(scenario)
    assert c['fallback_returned'] and c['next_internal_frame_finite'] and c['ipc_closed_by_daemon']
    assert c['daemon_link_failed'] and c['frame_timeout']==3 and c['ipc_timeout']==.15
    assert c['small_runs']==2
    if scenario in ('daemon_invalid_state','daemon_identity_change'):
        assert c['initial_remote_active'] and c['small_resets']==1 and c['fault_written']
    else:assert c['small_resets']==0 and not c['fault_written']
    if scenario=='daemon_invalid_state':assert not s['valid'] and s['state_preserved']


@pytest.mark.parametrize('scenario',['prepare_wrong_sha','prepare_wrong_size','prepare_changed_spec'])
def test_nav_ready_identity_and_spec_reject_before_adoption(scenario):
    c,s=run_pair(scenario)
    assert c['preparation_rejected']
    if scenario=='prepare_changed_spec':assert c['approval_preserved']


def test_nav_reconnect_does_not_accept_previous_connection_reply():
    c,s=run_pair('previous_connection')
    assert c['rejected'] and c['dead'] and c['prior_seq']!=c['fresh_seq']
    # _expect discards stale seq until the unchanged production3s deadline.
    # Match the existing WIP regression's4s harness envelope, not a new1s gate.
    assert c['frame_timeout']==3.0 and 2.8<=c['failure_seconds']<4.0
