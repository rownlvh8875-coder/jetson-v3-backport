"""Current carrot-wip protocol-3 CPU_FAKE software integration evidence.

CARROT_CANDIDATE_ROOT must name the disposable adapted current-source tree.
An absent variable is an explicit optional local skip; an incorrect configured
candidate is always a failure. The rolling required-check runner sets it.
"""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

import pytest


HELPER = Path(__file__).with_name('current_carrot_loopback_peer.py')


def run_pair(scenario):
    value = os.environ.get('CARROT_CANDIDATE_ROOT')
    if not value:
        pytest.skip('CARROT_CANDIDATE_ROOT is required for current-source CPU_FAKE integration')
    root = Path(value).resolve()
    assert (root / 'third_party/jetlink/jetlink/server/session.py').is_file(), root
    assert (root / 'openpilot/selfdrive/modeld/jetlink/daemon.py').is_file(), root

    def environment(role):
        result = os.environ.copy()
        paths = [root / 'third_party/jetlink']
        if role == 'client':
            paths.insert(0, root)
        result['PYTHONPATH'] = os.pathsep.join(map(str, paths))
        result['PYTHONUNBUFFERED'] = '1'
        result.pop('CARROT_JETLINK_V3', None)
        return result

    server = subprocess.Popen([sys.executable, str(HELPER), 'server', scenario],
                              env=environment('server'), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
    try:
        startup = queue.Queue()
        threading.Thread(target=lambda: startup.put(server.stdout.readline()), daemon=True).start()
        try:
            first = startup.get(timeout=20)
        except queue.Empty:
            pytest.fail('current CPU_FAKE EngineHost did not warm/listen within 20 seconds')
        assert first, server.stderr.read()
        ready = json.loads(first)
        assert ready['host'] == '127.0.0.1'
        assert Path(ready['module']).is_relative_to(root)
        client = subprocess.run([sys.executable, str(HELPER), 'client', scenario, str(ready['port'])],
                                env=environment('client'), capture_output=True, text=True, timeout=25)
        assert client.returncode == 0, client.stdout + client.stderr
        client_report = json.loads(client.stdout.strip().splitlines()[-1])
        assert Path(client_report['module']).is_relative_to(root)
        for module in client_report['glue_modules'].values():
            assert Path(module).is_relative_to(root)
        out, err = server.communicate(timeout=10)
        assert server.returncode == 0, out + err
        server_report = json.loads(out.strip().splitlines()[-1])
        assert server_report['has_openpilot_imports'] is False
        assert client_report['evidence'] == server_report['evidence'] == 'CPU_FAKE'
        assert client_report['protocol'] == server_report['protocol'] == 3
        print('CURRENT_CARROT_LOOPBACK_EVIDENCE', json.dumps(
            {'scenario': scenario, 'server_module': ready['module'],
             'client': client_report, 'server': server_report}, sort_keys=True))
        return client_report, server_report
    finally:
        if server.poll() is None:
            server.terminate()
            server.communicate(timeout=5)


def test_current_daemon_ipc_parser_runs_two_changing_full_size_frames():
    client, server = run_pair('daemon_continuous')
    assert client['prepared'] and client['approval_recorded']
    assert client['ipc_frames'] == client['diagnostic_frames'] == client['phase_frames'] == 2
    assert client['output_nbytes'] == 73808
    assert client['finite_parsed'] and client['changing_outputs']
    assert client['parsed_shapes'] == {'plan': [1, 33, 15], 'lead': [1, 3, 6, 4], 'action': [1, 4]}
    assert client['daemon_link_failed'] is False
    assert client['frame_timeout'] == 3.0 and client['ipc_timeout'] == .15
    assert server['infer_request_sizes'] == [393272, 393272]
    assert server['infer_response_sizes'] == [73828, 73828]
    assert server['images'] == [42, 133]
    assert server['state_seen'] == [[0., 0., 0.], [1., 1., 1.]]
    assert server['valid'] is True
    assert all(hello['protocol'] == 3 and hello['carrot_host'] == 'jetson' for hello in server['hellos'])
    assert server['engine_requests'][0]['sha256'] == server['hellos'][0]['loaded']


def test_current_invalid_next_state_closes_ipc_and_resets_active_joining_model():
    client, server = run_pair('daemon_invalid_state')
    assert client['initial_remote_active'] and client['remote_plan_shape'] == [1, 33, 15]
    assert client['fallback_returned'] and client['next_internal_frame_finite']
    assert client['fault_written'] and client['small_resets'] == 1 and client['small_runs'] == 2
    assert client['daemon_link_failed'] and client['ipc_closed_by_daemon']
    assert server['valid'] is False and server['state_preserved'] is True
    assert server['infer_response_sizes'] == [73828, 20]
    assert server['infer_response_statuses'][0] == 0 and server['infer_response_statuses'][1] != 0


@pytest.mark.parametrize('scenario', ['daemon_timeout', 'daemon_disconnect', 'daemon_wrong_frame',
                                     'daemon_stale_sequence', 'daemon_nonfinite', 'daemon_truncated'])
def test_current_wire_fault_keeps_internal_model_and_closes_ipc(scenario):
    client, server = run_pair(scenario)
    assert client['fallback_returned'] and client['next_internal_frame_finite']
    assert client['small_runs'] == 2 and client['small_resets'] == 0
    assert client['fault_written'] is False  # An external output was never adopted.
    assert client['daemon_link_failed'] and client['ipc_closed_by_daemon']
    assert client['fallback_seconds'] < 1.0
    assert len(server['infer_request_sizes']) == 1
    assert client['frame_timeout'] == 3.0 and client['ipc_timeout'] == .15


def test_current_telemetry_identity_change_rejects_before_ipc_reply_and_falls_back():
    client, server = run_pair('daemon_identity_change')
    assert client['initial_remote_active'] and client['fallback_returned']
    assert client['fault_written'] and client['small_resets'] == 1
    assert client['daemon_link_failed'] and client['ipc_closed_by_daemon']
    assert server['telemetry_identity_changed'] is True


@pytest.mark.parametrize('scenario', ['prepare_wrong_sha', 'prepare_wrong_size'])
def test_current_preparation_rejects_ready_identity_mismatch(scenario):
    client, server = run_pair(scenario)
    assert client['preparation_rejected']
    assert server['infer_request_sizes'] == []


def test_current_approved_spec_change_is_rejected_onroad_without_overwriting_approval():
    client, server = run_pair('prepare_changed_spec')
    assert client['prepared'] and client['approval_recorded']
    assert client['preparation_rejected'] and client['approval_preserved']
    assert server['infer_request_sizes'] == []


def test_current_previous_connection_response_with_stale_sequence_cannot_satisfy_new_frame():
    client, server = run_pair('previous_connection')
    assert client['rejected'] and client['dead']
    assert client['prior_seq'] != client['fresh_seq']
    assert client['failure_seconds'] < 4.0
    assert len(server['infer_request_sizes']) == 2
