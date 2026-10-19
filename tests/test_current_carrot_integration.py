"""FIXTURE: candidate provenance, protected source and patch roundtrip."""
import hashlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from adapters.carrot.integration import build_candidate, comma_files

REPO = Path(__file__).resolve().parents[1]


def candidate():
    root = Path(os.environ.get('CARROT_CANDIDATE_ROOT', REPO / '.candidate/current')).resolve()
    assert (root / '.jetlink-candidate/manifest.json').is_file(), 'build candidate first'
    return root


def test_manifest_hashes_patch_apply_and_rollback_restore_every_file(tmp_path):
    root = candidate()
    manifest = json.loads((root / '.jetlink-candidate/manifest.json').read_text())
    patch = root / '.jetlink-candidate/candidate.patch'
    assert hashlib.sha256(patch.read_bytes()).hexdigest() == manifest['patch_sha256']
    assert len(manifest['base_sha']) == 40
    # Reverse from the actual candidate bytes, then apply again and check every
    # hash. No clone/reference/installed runtime is modified by this test.
    for entry in manifest['touched_files']:
        source = root / entry['path']
        assert hashlib.sha256(source.read_bytes()).hexdigest() == entry['after_sha256']
        target = tmp_path / entry['path']
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    for args in [('apply', '--reverse', '--check'), ('apply', '--reverse')]:
        subprocess.run(['git', *args, str(patch)], cwd=tmp_path, check=True, capture_output=True)
    for entry in manifest['touched_files']:
        path = tmp_path / entry['path']
        if entry['before_sha256'] is None:
            assert not path.exists()
        else:
            assert hashlib.sha256(path.read_bytes()).hexdigest() == entry['before_sha256']
    for args in [('apply', '--check'), ('apply',)]:
        subprocess.run(['git', *args, str(patch)], cwd=tmp_path, check=True, capture_output=True)
    for entry in manifest['touched_files']:
        assert hashlib.sha256((tmp_path / entry['path']).read_bytes()).hexdigest() == entry['after_sha256']


def test_protected_model_link_parser_and_current_client_not_in_patch():
    root = candidate()
    manifest = json.loads((root / '.jetlink-candidate/manifest.json').read_text())
    paths = {entry['path'] for entry in manifest['touched_files']}
    assert not paths.intersection({
        'openpilot/selfdrive/modeld/jetlink/model.py',
        'openpilot/selfdrive/modeld/jetlink/link.py',
        'openpilot/selfdrive/modeld/parse_model_outputs.py',
        'third_party/jetlink/jetlink/client.py',
    })
    assert not (root / '.git').exists()


def test_builder_refuses_existing_destination_without_overwrite(tmp_path):
    (tmp_path / 'sentinel').write_text('preserve')
    with pytest.raises(ValueError, match='must not exist'):
        build_candidate(Path('unused'), tmp_path)
    assert (tmp_path / 'sentinel').read_text() == 'preserve'


def test_changed_mac_prepare_signature_is_incompatible(tmp_path):
    peer = tmp_path / 'openpilot/common/jetlink_peer.py'
    mac = tmp_path / 'openpilot/selfdrive/modeld/jetlink/mac.py'
    peer.parent.mkdir(parents=True)
    mac.parent.mkdir(parents=True)
    peer.write_text('import re\n')
    mac.write_text('def prepare(client, renamed):\n  pass\n')
    with pytest.raises(ValueError, match='mac.prepare signature'):
        comma_files(tmp_path)
