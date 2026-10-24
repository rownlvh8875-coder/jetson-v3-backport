"""Fixed generated hook through exact5bb source/transport/host; CPU_FAKE only."""
import itertools
import json

import pytest

from adapters.carrot import recorder_5bb as profile
from recorder_810e_support import REFERENCE
import test_recorder_5bb_wire as historical_fixture


def run_fixed(tmp_path,monkeypatch,shared,chunks,compact,overlap,nav,quantum,deferred):
    # Reuse the frozen C03 harness only. The package now contains the actual
    # fixed hook; hook_mode=fixed cannot enter its manual boundary_probe branch.
    monkeypatch.setattr(historical_fixture,'r',profile)
    historical_fixture.run_case(tmp_path,shared,chunks,compact,overlap,nav,quantum,deferred,'fixed')
    receipt=json.loads((tmp_path/'wire-5bb-receipt.json').read_text())
    assert receipt['hook_mode']=='fixed'
    assert receipt['client']['frames']==receipt['server']['executions']==5
    with profile.dataset_class(REFERENCE)(tmp_path/'capture') as saved:
        assert saved.manifest['provenance']['carrot_head']==profile.BASE_SHA
        assert set(saved.manifest['inputs'])=={'new_img','desire','traffic_convention','action_t'}
        assert saved.manifest['state_tensors_stored'] is False
        assert 'nav_metadata' not in json.dumps(saved.manifest)
        expected=('index','main_frame_id','extra_frame_id','model_timestamp_ns','monotonic_ns',
                  'main_sof_ns','extra_sof_ns','flags','selection','reserved','transforms',
                  'expected_interval_ns','new_img','desire','traffic_convention','action_t')
        assert saved.record(0).dtype.names==expected
        for frame in range(5):
            assert set(saved.ort_feeds(frame))=={'new_img','desire','traffic_convention','action_t'}


@pytest.mark.parametrize('shared,chunks,compact,overlap,nav',
    list(itertools.product((False,True),repeat=5)))
def test_fixed_wrapper_real_pipeline_all_switches(tmp_path,monkeypatch,shared,chunks,compact,overlap,nav):
    run_fixed(tmp_path,monkeypatch,shared,chunks,compact,overlap,nav,8192,True)


@pytest.mark.parametrize('quantum,deferred',[(32768,True),(32768,False)])
@pytest.mark.parametrize('shared,nav',[(True,True),(False,False)])
def test_fixed_wrapper_supported_writer_partitions(tmp_path,monkeypatch,shared,nav,quantum,deferred):
    run_fixed(tmp_path,monkeypatch,shared,True,True,True,nav,quantum,deferred)
