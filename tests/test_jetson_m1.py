"""CPU fixtures for isolated M1 writes; no GPU or real-model acceptance."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest
from tools import jetson_m1 as m1


def test_storage_requires_six_gib_and_accepts_boundary():
    with pytest.raises(m1.GateError, match='BLOCKED_STORAGE'):
        m1.storage_gate((6 << 30) - 1)
    m1.storage_gate(6 << 30)


def test_identity_checks_both_full_hash_and_byte_count(tmp_path):
    source = tmp_path / 'fixture.onnx'
    source.write_bytes(b'cpu-fixture-only')
    expected = {'sha256': hashlib.sha256(source.read_bytes()).hexdigest(), 'nbytes': source.stat().st_size}
    assert m1.identity_gate(source, expected) == expected
    for wrong in ({**expected, 'nbytes': expected['nbytes'] + 1}, {**expected, 'sha256': '0' * 64}):
        with pytest.raises(m1.GateError, match='FAIL_IDENTITY'):
            m1.identity_gate(source, wrong)


@pytest.mark.parametrize('bad', ['/opt/carrot-jetlink/dev', '/opt/carrot-jetlink/cache', '/run/carrot-data/runtime/dev', '/run/carrot-data'])
def test_operating_aliases_and_ancestors_refused(bad):
    with pytest.raises(m1.GateError, match='ISOLATION'):
        m1.validate_root(Path(bad))


def test_root_and_output_symlink_escape_or_collision_refused(tmp_path):
    dev = tmp_path / 'dev'
    dev.mkdir()
    outside = tmp_path / 'outside'
    outside.mkdir()
    (dev / 'escape').symlink_to(outside, target_is_directory=True)
    with pytest.raises(m1.GateError, match='ISOLATION'):
        m1.inside(dev, dev / 'escape' / 'plan')
    (dev / 'old.plan').write_bytes(b'preserve')
    with pytest.raises(m1.GateError, match='COLLISION'):
        m1.new_output(dev, dev / 'old.plan')
    assert (dev / 'old.plan').read_bytes() == b'preserve'
    alias = tmp_path / 'alias'
    alias.symlink_to(dev, target_is_directory=True)
    with pytest.raises(m1.GateError, match='ISOLATION'):
        m1.validate_root(alias)


def test_new_output_is_confined(tmp_path):
    dev = tmp_path / 'dev'
    dev.mkdir()
    assert m1.new_output(dev, dev / 'build.plan') == dev / 'build.plan'
    with pytest.raises(m1.GateError, match='ISOLATION'):
        m1.new_output(dev, tmp_path / 'other.plan')


@pytest.mark.parametrize('value', [None, {'IsOffroad': '0', 'IsOnroad': '1', 'issued_monotonic': 99}, {'IsOffroad': '1', 'IsOnroad': '0', 'issued_monotonic': 50}, {'IsOffroad': '1', 'IsOnroad': '0', 'issued_monotonic': 101}])
def test_offroad_lease_absent_false_stale_or_future_refused(tmp_path, value):
    lease = tmp_path / 'lease.json'
    if value is not None:
        lease.write_text(json.dumps(value))
    with pytest.raises(m1.GateError, match='OFFROAD'):
        m1.check_offroad_lease(lease, now=100)


def test_offroad_lease_fresh_exact_values(tmp_path):
    lease = tmp_path / 'lease.json'
    lease.write_text(json.dumps({'IsOffroad': '1', 'IsOnroad': '0', 'issued_monotonic': 99}))
    m1.check_offroad_lease(lease, now=100)


def test_guard_stops_only_its_child_on_authorization_loss(tmp_path):
    calls = 0
    def authorized():
        nonlocal calls
        calls += 1
        if calls > 1:
            raise m1.GateError('OFFROAD: controller lost')
    with (tmp_path / 'child.log').open('wb') as sink:
        with pytest.raises(m1.GateError, match='OFFROAD'):
            m1.run_guarded([sys.executable, '-c', 'import time;time.sleep(60)'], authorized, sink, poll=0.01)


def test_guard_reaps_successful_child(tmp_path):
    with (tmp_path / 'child.log').open('wb') as sink:
        assert m1.run_guarded([sys.executable, '-c', 'print("fixture")'], lambda: None, sink, poll=0.01) == 0


@pytest.mark.parametrize('signal_name', ['SIGTERM', 'SIGHUP'])
def test_guard_supervisor_signal_reaps_detached_child(tmp_path, signal_name):
    import os
    import signal
    import time
    pid_file = tmp_path / 'pid'
    child_code = f'import os,time;from pathlib import Path;Path({str(pid_file)!r}).write_text(str(os.getpid()));time.sleep(60)'
    parent_code = ('from tools import jetson_m1 as m;import sys;'
                   f'm.run_guarded([sys.executable,"-c",{child_code!r}],lambda:None,sys.stdout.buffer,poll=0.01)')
    supervisor = subprocess.Popen([sys.executable, '-B', '-c', parent_code], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    child_pid = None
    try:
        deadline = time.monotonic() + 5
        while not pid_file.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        assert pid_file.exists()
        child_pid = int(pid_file.read_text())
        supervisor.send_signal(getattr(signal, signal_name))
        supervisor.wait(timeout=5)
        with pytest.raises(ProcessLookupError):
            os.kill(child_pid, 0)
        child_pid = None
    finally:
        if child_pid is not None:
            try: os.kill(child_pid, signal.SIGKILL)
            except ProcessLookupError: pass
        if supervisor.poll() is None:
            supervisor.kill()
        supervisor.wait()


def test_import_disables_bytecode_before_later_dependencies():
    result = subprocess.run([sys.executable, '-B', '-c',
        'import sys;sys.dont_write_bytecode=False;from tools import jetson_m1;assert sys.dont_write_bytecode'], capture_output=True)
    assert result.returncode == 0, result.stderr.decode()


def test_marker_is_bound_to_private_owned_root_and_not_symlink(tmp_path):
    import os
    dev = tmp_path / 'dev'
    dev.mkdir(mode=0o700)
    marker = dev / '.m1-isolated.json'
    def write(root):
        marker.write_text(json.dumps({'schema': 1, 'development_root': str(root), 'identity': m1.V3_IDENTITY, 'do_not_install': True}))
        marker.chmod(0o600)
    write(dev)
    m1.validate_marker(dev)
    write(tmp_path / 'another')
    with pytest.raises(m1.GateError, match='ISOLATION'):
        m1.validate_marker(dev)
    write(dev)
    external = tmp_path / 'external-marker'
    marker.rename(external)
    marker.symlink_to(external)
    with pytest.raises(m1.GateError, match='ISOLATION'):
        m1.validate_marker(dev)


@pytest.mark.parametrize('message,stage,expected', [
    ('out of memory', 'build', 'OUT_OF_MEMORY'),
    ('CUDA_ERROR_ILLEGAL_ADDRESS', 'precheck', 'CUDA_ERROR'),
    ('onnx parse failed: unsupported operator', 'build', 'PARSER_UNSUPPORTED'),
    ('no space left on device', 'build', 'STORAGE_ERROR'),
    ('v3 patch: unexpected Cast', 'patch', 'ONNX_PATCH_ERROR'),
    ('TensorRT internal error', 'build', 'TRT_INTERNAL_ERROR'),
    ('unexpected exception', 'build', 'UNKNOWN'),
])
def test_build_errors_are_classified_without_retry(message, stage, expected):
    assert m1.classify_error(message, stage) == expected
