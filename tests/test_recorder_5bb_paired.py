"""25 paired wrapped/unwrapped regressions; all source is offline exact33-pinned."""
import json

import pytest

from recorder_5bb_paired import SCENARIOS, check_case


@pytest.mark.parametrize('case_id,label,scenario', SCENARIOS, ids=[row[0] for row in SCENARIOS])
def test_exact5bb_paired_source(case_id, label, scenario, tmp_path):
    receipt = check_case(case_id, label, scenario)
    # pytest's caller-selected basetemp controls retention; no fixed private path.
    (tmp_path / (case_id + '.json')).write_text(json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    assert receipt['status'] == 'PASS'
