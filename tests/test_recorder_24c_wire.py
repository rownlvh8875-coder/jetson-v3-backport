"""Exact24c generated hook and source through real POSIX/native transport fixture."""
import itertools
import json
from pathlib import Path

import pytest

from adapters.carrot import recorder_24c as profile
from recorder_810e_support import REFERENCE
import test_recorder_5bb_wire as source_fixture


def run_24c_case(tmp_path,monkeypatch,*,shared,chunks,compact,overlap,nav,quantum=8192,deferred=True):
    monkeypatch.setattr(source_fixture,'r',profile)
    monkeypatch.setattr(source_fixture,'TARGET',profile.BASE_SHA)
    source_fixture.run_case(tmp_path,shared,chunks,compact,overlap,nav,quantum,deferred,'fixed')
    receipt=json.loads((tmp_path/'wire-5bb-receipt.json').read_text())
    assert receipt['client']['recorded_hashes']==receipt['client']['submitted_hashes']==receipt['server']['engine_hashes']
    assert receipt['client']['frames']==receipt['server']['executions']==5
    assert len(set(receipt['client']['scalar_hashes']))==5
    assert receipt['client']['desire_pulses']==[0.,1.,0.,0.,1.]
    with profile.dataset_class(REFERENCE)(tmp_path/'capture') as saved:
        assert saved.manifest['provenance']['carrot_head']==profile.BASE_SHA
        assert set(saved.manifest['inputs'])=={'new_img','desire','traffic_convention','action_t'}
        assert not saved.manifest['state_tensors_stored']
        assert 'nav_metadata' not in json.dumps(saved.manifest)
        receipt['observer_monotonic_ns']=[int(saved.record(i)['monotonic_ns']) for i in range(5)]
    receipt.update(source_commit=profile.BASE_SHA,profile=profile.PROFILE,source_pins=profile.SOURCE_PINS)
    (tmp_path/'wire-24c-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt


@pytest.mark.parametrize('shared,chunks,compact,overlap,nav',list(itertools.product((False,True),repeat=5)))
def test_exact24c_all32_source_execution_switches(tmp_path,monkeypatch,shared,chunks,compact,overlap,nav):
    run_24c_case(tmp_path,monkeypatch,shared=shared,chunks=chunks,compact=compact,overlap=overlap,nav=nav)


@pytest.mark.parametrize('quantum,deferred',[(32768,True),(32768,False)])
@pytest.mark.parametrize('shared,nav',[(True,True),(False,False)])
def test_exact24c_supported_native_writer_partitions(tmp_path,monkeypatch,quantum,deferred,shared,nav):
    run_24c_case(tmp_path,monkeypatch,shared=shared,chunks=True,compact=True,overlap=True,nav=nav,quantum=quantum,deferred=deferred)
