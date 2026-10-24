"""Sanitized M19-B1 POST receipt fixtures; no device, import or deployment I/O."""
import copy
import json
from pathlib import Path

import pytest

from tools.check_recorder_activation_deployment import validate

REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def receipt():
    v = json.loads((REPO / 'artifacts/m19b0_activation_v2_validation_20261024.json').read_text(encoding='utf-8'))
    return {
        'schema': 1, 'stage': 'M19-B1',
        'actual': {'branch': 'carrot-nav', 'head': '366d6eae9aa9962104391e1d997fe956dea8f64d', 'flags': ['1', '0']},
        'pre': {'digest': '6857b161fe10363ae9bb58b505195a40a031872e3ef1746917d7e7f89fba50ba',
                'entries': 49, 'files': 2011, 'bytes': 417259473, 'six_hashes': v['before_profile']},
        'post': {'entries': 49, 'files': 2011, 'bytes': 417266269, 'six_hashes': v['after_profile'],
                 'context_pins': {
                     'openpilot/system/manager/process.py': 'fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752',
                     'openpilot/selfdrive/modeld/modeld.py': '008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594'},
                 'all_collector_checks': True, 'mode_owner_preserved': True, 'index_unchanged': True,
                 'unexpected_entries': 0},
        'original48': {'digest': '8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5',
                       'files': 2006, 'bytes': 417208589,
                       'path_tree_checks': {f'U{i:02d}': True for i in range(1, 49)}},
        'off': {'detached_windows': 3, 'all_health_checks': True, 'namespace': 'ABSENT', 'env_present': False,
                'writer_count': 0, 'capture_memfds': 0, 'output_present': False, 'ticket_created': False,
                'activation': False, 'restart': False, 'frames': 0},
        'preservation': {'models': True, 'routes': True, 'processes': True, 'U32': True, 'U46': True},
    }


def test_exact_v2_post_fixture_passes_without_mutation(receipt):
    before = copy.deepcopy(receipt)
    assert validate(receipt)['status'] == 'PASS'
    assert receipt == before


@pytest.mark.parametrize(('section', 'key', 'bad'), [
    ('actual', 'head', '0' * 40), ('actual', 'branch', 'carrot-wip'), ('actual', 'flags', ['0', '1']),
    ('pre', 'digest', '0' * 64), ('post', 'files', 2012), ('post', 'bytes', 417259473),
    ('post', 'unexpected_entries', 1), ('post', 'all_collector_checks', False),
    ('post', 'mode_owner_preserved', False), ('post', 'index_unchanged', False),
    ('off', 'namespace', 'PRESENT'), ('off', 'writer_count', 1), ('off', 'env_present', True),
    ('off', 'ticket_created', True), ('off', 'capture_memfds', 1), ('off', 'restart', True),
    ('off', 'activation', True), ('off', 'frames', 10), ('off', 'all_health_checks', False),
    ('off', 'detached_windows', 2), ('preservation', 'processes', False),
])
def test_fail_closed_metadata_or_lifecycle_drift(receipt, section, key, bad):
    receipt[section][key] = bad
    assert validate(receipt)['status'] == 'FAIL'


@pytest.mark.parametrize('section', ['pre', 'post'])
def test_wrong_six_profile_rejected(receipt, section):
    receipt[section]['six_hashes']['openpilot/selfdrive/modeld/jetlink/model.py'] = '0' * 64
    assert validate(receipt)['status'] == 'FAIL'


def test_context_source_drift_rejected(receipt):
    receipt['post']['context_pins']['openpilot/system/manager/process.py'] = '0' * 64
    assert validate(receipt)['status'] == 'FAIL'


@pytest.mark.parametrize('change', ['missing', 'extra', 'drift'])
def test_original_private_identity_commitments_not_remapped(receipt, change):
    items = receipt['original48']['path_tree_checks']
    if change == 'missing': items.pop('U32')
    elif change == 'extra': items['U49'] = True
    else: items['U32'] = False
    assert validate(receipt)['status'] == 'FAIL'


def test_missing_evidence_fails(receipt):
    del receipt['off']
    assert validate(receipt)['status'] == 'FAIL'
