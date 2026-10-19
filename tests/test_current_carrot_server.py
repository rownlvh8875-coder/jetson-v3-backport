"""CPU_FAKE/FIXTURE checks of the CURRENT vendored host, never Jetson evidence."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def candidate(tmp_path_factory):
    configured = os.environ.get('CARROT_CANDIDATE_ROOT')
    if configured:
        path = Path(configured)
        assert (path / 'third_party/jetlink/jetlink/server/session.py').is_file()
        return path
    from adapters.carrot.server import server_files
    reference = ROOT / '.reference/carrot-wip'
    assert reference.is_dir(), 'current upstream reference is required; no silent skip'
    path = tmp_path_factory.mktemp('current-carrot-server')
    shutil.copytree(reference / 'third_party/jetlink', path / 'third_party/jetlink')
    for name, data in server_files(reference).items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return path


def run_peer(candidate, *args):
    env = {**os.environ, 'PYTHONPATH': str(candidate / 'third_party/jetlink')}
    result = subprocess.run([sys.executable, str(ROOT / 'tests/current_carrot_server_peer.py'), *args],
                            env=env, text=True, capture_output=True, timeout=40)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize('version,model', [(2, 'v2'), (3, 'v2'), (3, 'v3')])
def test_current_server_loopback(candidate, version, model):
    report = run_peer(candidate, 'loopback', str(version), model)
    assert report['evidence'] == 'CPU_FAKE/FIXTURE'
    assert report['protocol'] == version
    assert report['model'] == model
    assert report['passed']


def test_all_outputs_fail_closed_and_reload(candidate):
    report = run_peer(candidate, 'faults')
    assert report['cases'] >= 18


def test_exact_contracts_and_physical_warm(candidate):
    report = run_peer(candidate, 'contracts')
    assert report['cases'] >= 10


def test_managed_request_generation_identity(candidate):
    report = run_peer(candidate, 'identity')
    assert report['passed']


def test_current_trt_build_load_fixture(candidate):
    report = run_peer(candidate, 'trt')
    assert report['cases'] >= 20


def test_managed_offroad_control_default_deny(candidate):
    report = run_peer(candidate, 'offroad')
    assert report['cases'] >= 10


def test_upstream_body_change_requires_review(tmp_path):
    from adapters.carrot.server import PREFIX, server_files
    reference = tmp_path / 'reference'
    baseline = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip'))
    shutil.copytree(baseline / 'third_party/jetlink', reference / 'third_party/jetlink')
    target = reference / PREFIX / 'server/session.py'
    target.write_text(target.read_text().replace('    queues = PolicyQueues(spec)',
                                               "    log.info('new upstream behavior')\n    queues = PolicyQueues(spec)"))
    with pytest.raises(ValueError, match='source body changed'):
        server_files(reference)
