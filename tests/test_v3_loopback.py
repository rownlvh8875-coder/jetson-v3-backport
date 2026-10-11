"""Real vendored comma client ↔ real Jetson session, in separate interpreters.

Only the hardware engine and deliberate response-wire corruption are synthetic.
No device discovery, device connection, SSH, LAN, ONNX, or CUDA is involved.
Run with CINQUE_PRODUCTION_ROOT and CINQUE_COMMA_ROOT pointing at the applied
pinned development checkouts. Each child has exactly one vendored PYTHONPATH.
"""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading

import pytest


HELPER = Path(__file__).with_name('v3_loopback_peer.py')


def run_pair(scenario):
    roots = {}
    for role, variable in (('server', 'CINQUE_PRODUCTION_ROOT'),
                           ('client', 'CINQUE_COMMA_ROOT')):
        value = os.environ.get(variable)
        if not value:
            pytest.skip(f'set {variable} to the applied pinned development checkout')
        roots[role] = Path(value).resolve()
        assert (roots[role] / 'third_party/jetlink/jetlink').is_dir()

    def environment(role):
        env = os.environ.copy()
        env['PYTHONPATH'] = str(roots[role] / 'third_party/jetlink')
        if role == 'client':
            env['PYTHONPATH'] = str(roots[role]) + os.pathsep + env['PYTHONPATH']
        env['PYTHONUNBUFFERED'] = '1'
        return env

    server = subprocess.Popen(
        [sys.executable, str(HELPER), 'server', scenario],
        env=environment('server'), stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True)
    try:
        # The helper emits the port only after the real host has warmed.
        startup = queue.Queue()
        threading.Thread(target=lambda: startup.put(server.stdout.readline()),
                         daemon=True).start()
        try:
            first = startup.get(timeout=20)
        except queue.Empty:
            pytest.fail('loopback server did not warm/listen within 20 seconds')
        assert first, server.stderr.read()
        ready = json.loads(first)
        assert ready['host'] == '127.0.0.1'
        assert Path(ready['module']).is_relative_to(roots['server'])
        print('JETSON_PROCESS_MODULE', ready['module'])
        client = subprocess.run(
            [sys.executable, str(HELPER), 'client', scenario, str(ready['port'])],
            env=environment('client'), capture_output=True, text=True, timeout=30)
        assert client.returncode == 0, client.stdout + client.stderr
        client_report = json.loads(client.stdout.strip().splitlines()[-1])
        assert Path(client_report['module']).is_relative_to(roots['client'])
        for module in client_report.get('glue_modules', {}).values():
            assert Path(module).is_relative_to(roots['client'])
        print('COMMA_PROCESS_MODULE', client_report['module'])
        out, err = server.communicate(timeout=10)
        assert server.returncode == 0, out + err
        report = json.loads(out.strip().splitlines()[-1])
        print('LOOPBACK_EVIDENCE', json.dumps({'scenario': scenario,
                                             'client': client_report,
                                             'server': report}, sort_keys=True))
        return client_report, report
    finally:
        if server.poll() is None:
            server.terminate()
            server.communicate(timeout=5)


def test_canonical_v3_continuous_state_and_only_driving_output_cross_wire():
    client, server = run_pair('continuous')
    assert client['frames'] == 6
    assert client['seed'] == 73
    assert server['infer_request_sizes'] == [393272] * 6
    assert server['infer_response_sizes'] == [73828] * 6
    assert client['output_nbytes'] == 73808
    assert len(set(server['images'])) == 6
    assert server['state_seen'][0] == [0.0, 0.0, 0.0]
    assert all(all(v > 0 for v in row) for row in server['state_seen'][1:])
    assert server['valid'] is True
    assert server['engine_requests'][0]['cinque_v3_stateful_v2'] == server['hello_capabilities'][0]
    assert server['engine_requests'][0]['session_id'] == server['hello_sessions'][0]
    assert len(server['ready_generations'][0]) == 32


@pytest.mark.parametrize('fault', [
    'missing_capability', 'unsupported_capability', 'wrong_capability_spec',
    'wrong_spec', 'wrong_dtype', 'wrong_model_size', 'wrong_model_sha',
    'not_ready', 'missing_generation', 'invalid_generation', 'wrong_session',
])
def test_v3_negotiation_and_full_ready_contract_fail_closed(fault):
    client, server = run_pair(fault)
    assert client['rejected'] is True
    assert server['infer_request_sizes'] == []


@pytest.mark.parametrize('fault', [
    'missing_header', 'truncated', 'excess', 'nan', 'inf',
    'wrong_frame_id', 'stale_sequence', 'deadline', 'disconnect',
])
def test_real_client_rejects_faulted_response_and_cannot_resume(fault):
    client, server = run_pair(fault)
    assert client['rejected'] is True
    assert client['dead'] is True
    assert client['resume_rejected'] is True
    assert client['failure_seconds'] < 2.0
    assert len(server['infer_request_sizes']) == 1


def test_real_invalid_next_state_sends_header_only_and_requires_reload():
    client, server = run_pair('invalid_state')
    assert client['rejected'] and client['dead'] and client['resume_rejected']
    assert client['failure_seconds'] < 2.0
    assert server['infer_response_sizes'] == [73828, 20, 20]
    assert server['valid'] is False
    assert server['state_preserved'] is True
    assert all(v > 0 for v in server['state_seen'][1])
    assert client['probe_status'] != 0


def test_real_reload_worker_recovers_with_fresh_generation_and_zero_state():
    client, server = run_pair('invalid_state_reload')
    assert client['rejected'] and client['dead'] and client['resume_rejected']
    assert client['fresh_generation'] and client['recovered']
    assert server['infer_response_sizes'] == [73828, 20, 20, 73828]
    assert server['state_preserved'] is True
    assert server['valid'] is True
    assert server['hardware_loads'] == 1
    assert server['reload_first_state'] == [0.0, 0.0, 0.0]


def test_second_hello_revokes_approval_until_explicit_reapproval():
    client, server = run_pair('hello_again')
    assert client['approval_revoked'] is True
    assert client['fresh_session'] is True
    assert server['infer_response_sizes'] == [73828, 73828]


def test_generic_stateful_model_cannot_use_protocol2_v3_exception():
    client, server = run_pair('generic_stateful')
    assert client['rejected'] is True
    assert server['infer_request_sizes'] == []


def test_canonical_v3_requires_explicit_approval_after_hello():
    client, server = run_pair('no_approval')
    assert client['rejected'] is True
    assert server['engine_requests'] == []
    assert server['infer_request_sizes'] == []


def test_late_previous_connection_output_cannot_satisfy_new_connection():
    client, server = run_pair('previous_connection')
    assert client['rejected'] and client['dead']
    assert client['prior_seq'] != client['fresh_seq']
    assert client['failure_seconds'] < 2.0
    assert len(server['infer_request_sizes']) == 2


def test_actual_comma_daemon_local_ipc_preparation_parser_and_two_frames():
    client, server = run_pair('daemon_continuous')
    assert client['prepared'] and client['approval_recorded']
    assert client['ipc_frames'] == 2 and client['diagnostic_frames'] == 2
    assert client['phase_frames'] == 2 and client['daemon_link_failed'] is False
    assert client['parsed_shapes'] == {'plan': [1, 33, 15], 'lead': [1, 3, 6, 4], 'action': [1, 4]}
    assert client['finite_parsed'] and client['changing_outputs']
    assert server['infer_request_sizes'] == [393272, 393272]
    assert server['infer_response_sizes'] == [73828, 73828]
    assert server['state_seen'][0] == [0.0, 0.0, 0.0]
    assert all(v > 0 for v in server['state_seen'][1])
    assert server['valid'] is True


def test_actual_server_state_failure_closes_daemon_ipc_and_joining_model_falls_back():
    client, server = run_pair('daemon_fallback')
    assert client['prepared'] and client['approval_recorded']
    assert client['initial_remote_active'] and client['remote_plan_shape'] == [1, 33, 15]
    assert client['fallback_returned'] and client['next_internal_frame_finite']
    assert client['fault_written'] and client['small_resets'] == 1 and client['small_runs'] == 2
    assert client['active_model_after_failure'] == 'Internal model'
    assert client['selected_model_after_failure'] == 'Cinque v3'
    assert client['daemon_link_failed'] and server['valid'] is False
    assert server['infer_response_sizes'] == [73828, 20]
    assert server['state_preserved'] is True
