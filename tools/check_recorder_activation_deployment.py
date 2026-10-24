"""Validate sanitized M19-B1 metadata receipts offline, without device I/O.

This checks receipt consistency, not the truth of an untrusted observation. The
private collector's path/hash/metadata commitments and bounded live health reads
remain the deployment evidence. No source patching, importing or arming occurs.
"""
from __future__ import annotations

from tools.check_comma_dirty_baseline import AFTER as M19A, BASE_SHA

MODEL = 'openpilot/selfdrive/modeld/jetlink/model.py'
HOOK = 'openpilot/selfdrive/modeld/jetlink/input_recording/hook.py'
V2 = {**M19A,
      MODEL: '0fbcba80a84fa6ffd22a6463cb75f111c95cd939697ce357e44ec45909109c91',
      HOOK: '9e688299d4fcefeea3a5ebc1460ee8fd72afd1c15c9f2d1a1fd3f58b1a5ca7de'}
CONTEXT = {
    'openpilot/system/manager/process.py': 'fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752',
    'openpilot/selfdrive/modeld/modeld.py': '008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594',
}
BASELINE = '8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5'
M19A_POST = '6857b161fe10363ae9bb58b505195a40a031872e3ef1746917d7e7f89fba50ba'


def validate(receipt):
    """Pure fail-closed comparison; never relabel old M19A as activation-v2."""
    checks = {}
    try:
        a, pre, post = receipt['actual'], receipt['pre'], receipt['post']
        original, off, preservation = receipt['original48'], receipt['off'], receipt['preservation']
        checks['schema'] = receipt['schema'] == 1 and receipt['stage'] == 'M19-B1'
        checks['identity'] = a == {'branch': 'carrot-nav', 'head': BASE_SHA, 'flags': ['1', '0']}
        checks['pre_M19A'] = (pre['digest'] == M19A_POST and pre['entries'] == 49
                             and pre['files'] == 2011 and pre['bytes'] == 417259473
                             and pre['six_hashes'] == M19A)
        checks['post_v2'] = (post['entries'] == 49 and post['files'] == 2011
                             and post['bytes'] == 417266269 and post['six_hashes'] == V2)
        checks['context'] = post['context_pins'] == CONTEXT
        checks['post_exact'] = (post['all_collector_checks'] is True and post['mode_owner_preserved'] is True
                                and post['index_unchanged'] is True and post['unexpected_entries'] == 0)
        paths = original['path_tree_checks']
        checks['original48'] = (original['digest'] == BASELINE and original['files'] == 2006
                                and original['bytes'] == 417208589
                                and set(paths) == {f'U{i:02d}' for i in range(1, 49)}
                                and all(v is True for v in paths.values()))
        checks['OFF'] = (off['detached_windows'] == 3 and off['all_health_checks'] is True
                         and off['namespace'] == 'ABSENT' and off['env_present'] is False
                         and off['writer_count'] == 0 and off['capture_memfds'] == 0
                         and off['output_present'] is False and off['ticket_created'] is False
                         and off['activation'] is False and off['restart'] is False and off['frames'] == 0)
        checks['preservation'] = (set(preservation) == {'models', 'routes', 'processes', 'U32', 'U46'}
                                   and all(v is True for v in preservation.values()))
    except (KeyError, TypeError, AttributeError, ValueError):
        checks['valid_evidence'] = False
    return {'status': 'PASS' if checks and all(checks.values()) else 'FAIL', 'checks': checks,
            'scope': 'OFFLINE_RECEIPT_VALIDATION_ONLY'}
