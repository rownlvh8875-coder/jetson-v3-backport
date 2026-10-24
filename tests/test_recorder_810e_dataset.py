"""810e logical dataset, CPU_FAKE/FIXTURE only; writer is a real CPU subprocess."""
import importlib
import json
import numpy as np
import pytest
from adapters.carrot import recorder_810e as r
from recorder_810e_support import package, ticket, REFERENCE
from test_v3_input_recorder import inputs, metadata, ready, finish


def test_strict_reader_distinct_profile_and_exact_feed(tmp_path,monkeypatch,capsys):
    h=package(tmp_path,monkeypatch)
    module=importlib.import_module('capture810.recorder')
    rec=module.Recorder(tmp_path/'dataset',h._provenance(ticket(h,tmp_path)),frames=3)
    assert ready(rec)
    data=inputs()
    for i in range(3):
        assert rec.observe(**data,metadata=metadata(i))
        import time;time.sleep(.02)
    finish(rec)
    Dataset=r.dataset_class(REFERENCE)
    with Dataset(tmp_path/'dataset') as dataset:
        assert len(dataset)==3
        for i in range(3):
            feed=dataset.ort_feeds(i)
            assert set(feed)=={'new_img','desire','traffic_convention','action_t'}
            for key,value in feed.items(): assert value.tobytes()==data[key].tobytes()
        assert dataset.manifest['provenance']['carrot_head']==r.BASE_SHA
    # An old366 reader must not reinterpret this as its own source profile.
    from recording.dataset import Dataset as Historical
    with pytest.raises(ValueError): Historical(tmp_path/'dataset')
    from tools.v3_input_dataset_810e import main
    assert main(['validate',str(tmp_path/'dataset'),'--reference',str(REFERENCE)])==0
    assert json.loads(capsys.readouterr().out)['profile']==r.PROFILE


@pytest.mark.parametrize('fault',['short_write','fsync','manifest','exception','crash','low_space'])
def test_reused_writer_failure_never_complete(tmp_path,monkeypatch,fault):
    h=package(tmp_path,monkeypatch); Recorder=importlib.import_module('capture810.recorder').Recorder
    rec=Recorder(tmp_path/'dataset',h._provenance(ticket(h,tmp_path)),frames=1,fault={fault:True})
    if ready(rec):rec.observe(**inputs(),metadata=metadata(0))
    finish(rec)
    assert rec.reason is not None
    assert not (tmp_path/'dataset/COMPLETE').exists()
    with pytest.raises((ValueError,OSError)):r.dataset_class(REFERENCE)(tmp_path/'dataset')


@pytest.mark.parametrize('field',['source_model_sha','source_spec_sha'])
def test_profile_rejects_other_source_identity(tmp_path,monkeypatch,field):
    h=package(tmp_path,monkeypatch)
    provenance=h._provenance(ticket(h,tmp_path));provenance[field]='0'*64
    with pytest.raises(ValueError):h.validate_provenance(provenance)
