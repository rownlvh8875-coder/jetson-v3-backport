"""Current exact24c metadata/map/error behavior paired against the unwrapped source."""
import json

import pytest

from recorder_24c_paired import SCENARIOS, check_case


@pytest.mark.parametrize('case_id,label,scenario',SCENARIOS,ids=[r[0] for r in SCENARIOS])
def test_exact24c_wrapped_unwrapped_metadata_map_and_error_equivalence(case_id,label,scenario,tmp_path):
    receipt=check_case(case_id,label,scenario)
    assert receipt['status']=='PASS' and receipt['source_traces_equal']
    assert receipt['source_commit']=='24c1ba5e4b3428f56fa0e402f5a10097e2e94c32'
    assert len(receipt['source_pins'])==41
    (tmp_path/(case_id+'.json')).write_text(json.dumps(receipt,indent=2)+'\n')
