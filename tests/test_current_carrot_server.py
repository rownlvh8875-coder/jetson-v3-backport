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
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip'))
    assert reference.is_dir(), 'current upstream reference is required; no silent skip'
    path = tmp_path_factory.mktemp('current-carrot-server')
    shutil.copytree(reference / 'third_party/jetlink', path / 'third_party/jetlink')
    for name, data in server_files(reference).items():
        target = path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
    contract = 'openpilot/selfdrive/modeld/jetlink/jetson_model.json'
    if (reference / contract).is_file():
        (path / contract).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(reference / contract, path / contract)
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


def test_native_n16_cannot_be_adopted_by_unsupported_protocol3(candidate):
    if (candidate / 'third_party/jetlink/jetlink/server/backends/trt/managed_engine.py').exists():
        assert run_peer(candidate, 'native-protocol3')['passed']


def test_upstream_body_change_requires_review(tmp_path):
    from adapters.carrot.server import PREFIX, server_files
    reference = tmp_path / 'reference'
    baseline = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip'))
    shutil.copytree(baseline / 'third_party/jetlink', reference / 'third_party/jetlink')
    target = reference / PREFIX / 'server/session.py'
    target.write_text(target.read_text() + "\nraise RuntimeError('unreviewed source body')\n")
    with pytest.raises(ValueError, match='source body changed'):
        server_files(reference)


def test_reviewed_current_server_preserves_native_paths():
    """Current source must build; upstream N16 implementations remain available."""
    import ast
    from adapters.carrot.server import PREFIX, server_files
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip'))
    files = server_files(reference)
    original = (reference / PREFIX / 'server/session.py').read_text()
    generated = files[PREFIX + 'server/session.py'].decode()
    if 'def _decode_cached_spec' in original:
        before = ast.parse(original)
        after = ast.parse(generated)
        for name in ('_warm', '_infer'):
            native = next(n for n in ast.walk(before) if isinstance(n, ast.FunctionDef) and n.name == name)
            retained = next(n for n in ast.walk(after) if isinstance(n, ast.FunctionDef) and n.name == name + '_native')
            assert ast.dump(ast.Module(body=native.body, type_ignores=[])) == ast.dump(ast.Module(body=retained.body, type_ignores=[]))
        assert 'carrot_n16_driving_output_v1' not in generated  # capability comes from upstream module
    assert 'resident_only' in generated
    assert 'loaded.valid = False' in generated


def test_current_native_dependencies_remain_isolated_from_experiments():
    from adapters.carrot.server import PREFIX, server_files
    from experimental.jetson_optimizations.device_adapter import device_optimization_files
    from experimental.jetson_optimizations.fastpath_adapter import fastpath_optimization_files
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip'))
    standard = server_files(reference)
    combined = standard | device_optimization_files(standard)
    combined |= fastpath_optimization_files(combined)
    for name, body in standard.items():
        if '/native_' in name:
            assert combined[name] == body
    if PREFIX + 'server/backends/trt/managed_engine.py' in standard:
        assert standard[PREFIX + 'server/backends/trt/engine.py'] == (reference / PREFIX / 'server/backends/trt/engine.py').read_bytes()
        assert combined[PREFIX + 'server/backends/trt/engine.py'] == standard[PREFIX + 'server/backends/trt/engine.py']
        assert PREFIX + 'managed_input_cast.py' in combined
        assert PREFIX + 'input_cast.py' not in combined


@pytest.mark.parametrize('name', ['server/backends/trt/device_state.py', 'finite.c', 'input_cast.c'])
def test_current_dependency_drift_cannot_bypass_body_review(tmp_path, name):
    from adapters.carrot.server import PREFIX, server_files
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip'))
    changed = tmp_path / 'reference'
    shutil.copytree(reference / 'third_party/jetlink', changed / 'third_party/jetlink')
    dependency = changed / PREFIX / name
    if dependency.exists():
        dependency.write_text(dependency.read_text() + '\n# unreviewed native change\n')
    else:
        dependency = changed / PREFIX / 'queues.py'
        dependency.write_text(dependency.read_text() + '\n# unreviewed queue change\n')
    with pytest.raises(ValueError, match='source body changed'):
        server_files(changed)
