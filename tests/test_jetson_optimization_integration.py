"""Composition/provenance tests for an explicitly requested experimental copy."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from adapters.carrot.integration import build_candidate

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope='module')
def copies(tmp_path_factory):
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip-ba186'))
    assert reference.is_dir(), 'provide freshly verified reference; no silent skip'
    directory = tmp_path_factory.mktemp('optimization-composition')
    standard = directory/'standard'
    experiment = directory/'experiment'
    before = subprocess.check_output(['git','-C',str(reference),'status','--porcelain'])
    base = build_candidate(reference, standard)
    opt = build_candidate(reference, experiment, experimental_optimizations=True)
    assert subprocess.check_output(['git','-C',str(reference),'status','--porcelain']) == before
    return standard, experiment, base, opt


def test_standard_candidate_has_no_optimization_code_or_env_imports(copies):
    standard, experiment, base, opt = copies
    assert 'experimental_optimizations' not in base or base['experimental_optimizations'] is False
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip-ba186'))
    for name in ('third_party/jetlink/jetlink/server/backends/trt/device_state.py',
                 'third_party/jetlink/jetlink/input_cast.py'):
        # Upstream now ships native N16 implementations at these paths. Their
        # presence is not evidence that our V3 experiment was activated.
        if (reference/name).exists():
            assert (standard/name).read_bytes() == (reference/name).read_bytes()
        else:
            assert not (standard/name).exists()
    for entry in base['touched_files']:
        assert hashlib.sha256((standard/entry['path']).read_bytes()).hexdigest() == entry['after_sha256']


def test_experimental_overlay_preserves_protected_comma_and_wire_files(copies):
    standard, experiment, base, opt = copies
    assert opt['experimental_optimizations'] is True
    for name in ('openpilot/selfdrive/modeld/jetlink/daemon.py',
                 'openpilot/selfdrive/modeld/jetlink/model.py',
                 'openpilot/selfdrive/modeld/jetlink/link.py',
                 'openpilot/selfdrive/modeld/parse_model_outputs.py',
                 'third_party/jetlink/jetlink/client.py',
                 'third_party/jetlink/jetlink/protocol.py',
                 'third_party/jetlink/jetlink/protocol_v3.py',
                 'third_party/jetlink/jetlink/transport/ffs.py'):
        assert (standard/name).read_bytes() == (experiment/name).read_bytes(), name
    assert not (experiment/'third_party/jetlink/jetlink/transport/ffs_aio.py').exists()


def test_optional_overlay_patch_can_reverse_and_apply_without_losing_standard(copies,tmp_path):
    _, experiment, _, manifest = copies
    for item in manifest['touched_files']:
        target = tmp_path/item['path']
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((experiment/item['path']).read_bytes())
    patch = experiment/'.jetlink-candidate/candidate.patch'
    subprocess.run(['git','apply','--reverse','--check',str(patch)],cwd=tmp_path,check=True,capture_output=True)
    subprocess.run(['git','apply','--reverse',str(patch)],cwd=tmp_path,check=True,capture_output=True)
    for item in manifest['touched_files']:
        path = tmp_path/item['path']
        if item['before_sha256'] is None:
            assert not path.exists()
        else:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == item['before_sha256']
    subprocess.run(['git','apply',str(patch)],cwd=tmp_path,check=True,capture_output=True)
    for item in manifest['touched_files']:
        assert hashlib.sha256((tmp_path/item['path']).read_bytes()).hexdigest() == item['after_sha256']
