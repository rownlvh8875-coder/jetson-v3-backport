"""DEFAULT-OFF device feedback overlay: CPU_FAKE/FIXTURE, no GPU evidence."""
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
def device_candidate(tmp_path_factory):
    configured = os.environ.get('CARROT_OPTIMIZATION_ROOT')
    if configured:
        candidate = Path(configured)
        assert (candidate / 'third_party/jetlink/jetlink/server/backends/trt/device_state.py').is_file()
        assert (candidate / 'third_party/jetlink/jetlink/direct_inputs.py').is_file()
        return candidate
    from adapters.carrot.server import server_files
    from experimental.jetson_optimizations.device_adapter import device_optimization_files
    requested_reference = os.environ.get('CARROT_REFERENCE_ROOT')
    reference = Path(requested_reference) if requested_reference else ROOT / '.reference/carrot-wip-ba186'
    if requested_reference:
        assert reference.is_dir(), 'configured current-source reference is required'
    elif not reference.is_dir():
        reference = ROOT / '.reference/carrot-wip'
    standard = server_files(reference)
    before = standard.copy()
    optional = device_optimization_files(standard)
    assert standard == before, 'overlay must not mutate the baseline files'
    modern = 'third_party/jetlink/jetlink/server/backends/trt/managed_engine.py' in standard
    assert set(optional) == {
        'third_party/jetlink/jetlink/server/session.py',
        'third_party/jetlink/jetlink/server/backends/trt/' + ('managed_engine.py' if modern else 'engine.py'),
        'third_party/jetlink/jetlink/server/backends/trt/' + ('managed_device_state.py' if modern else 'device_state.py'),
    }
    from experimental.jetson_optimizations.fastpath_adapter import fastpath_optimization_files
    base = {**standard, **optional}
    combined = {**base, **fastpath_optimization_files(base)}
    candidate = tmp_path_factory.mktemp('device-state-candidate')
    shutil.copytree(reference / 'third_party/jetlink', candidate / 'third_party/jetlink')
    for name, data in combined.items():
        target = candidate / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    return candidate


@pytest.mark.parametrize('scenario', ['off', 'contracts', 'bindings', 'runtime', 'faults', 'drain', 'capture', 'combined'])
def test_device_state_candidate(device_candidate, scenario):
    environment = {**os.environ, 'PYTHONPATH': str(device_candidate / 'third_party/jetlink')}
    environment.pop('CARROT_TRT_DEVICE_STATE', None)
    result = subprocess.run([sys.executable, str(ROOT / 'tests/jetson_device_state_peer.py'), scenario],
                            env=environment, capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report['evidence'] == 'CPU_FAKE/FIXTURE' and report['cases'] > 0
