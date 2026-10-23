"""FIXTURE/CPU checks for provenance gates, not recorded model parity."""
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import recorded_driving_gate as gate


@pytest.mark.parametrize('flags', [None, {}, {'IsOffroad':'0','IsOnroad':'1'},
                                  {'IsOffroad':1,'IsOnroad':0}, {'IsOffroad':'1','IsOnroad':'unknown'}])
def test_unknown_or_nonexact_offroad_refuses(flags):
    with pytest.raises(ValueError):
        gate.require_offroad(flags)


def test_exact_offroad_accepts_only_read_only_precondition():
    gate.require_offroad({'IsOffroad':'1','IsOnroad':'0'})


def test_qcamera_driver_and_lock_files_are_not_paired_model_cameras():
    result=gate.camera_availability(['qcamera.ts','dcamera.hevc','fcamera.hevc.lock'])
    assert result=={'full_road':False,'full_wide':False,'qcamera':True,'driver_camera':True}
    assert gate.camera_availability(['fcamera.hevc','ecamera.hevc'])['full_wide']


def test_missing_pixels_do_not_turn_telemetry_into_recorded_inputs():
    evidence={name:True for name in gate.INPUT_PROOFS}
    evidence['paired_recorded_pixels']=False
    result=gate.reconstruction_gate(evidence)
    assert result['status']=='BLOCKED_RECORDED_INPUT_RECONSTRUCTION'
    assert result['missing']==['paired_recorded_pixels'] and result['reconstructed_frames']==0
    evidence['paired_recorded_pixels']=True
    evidence['exact_action_t_history']='inferred default'
    assert 'exact_action_t_history' in gate.reconstruction_gate(evidence)['missing']


def test_complete_proofs_are_preflight_only_not_parity_approval():
    result=gate.reconstruction_gate({name:True for name in gate.INPUT_PROOFS})
    assert result['status']=='READY_FOR_DATASET_VALIDATION'
    assert result['numerical_decision']=='PARITY_UNDETERMINED'


def test_stop_to_motion_survives_zero_speed_release_gap():
    observed=gate.MotionObservations()
    for speed,standstill in [(1.,False),(0.,True),(0.,False),(-0.001,False),(0.01,False),(1.,False),(0.,True)]:
        observed.update(speed,standstill)
    assert observed.stop_to_motion==1 and observed.standstill_samples==2
    with pytest.raises(ValueError):observed.update(float('nan'),False)


def test_public_candidate_rejects_raw_route_fields_and_validates_content_identity():
    record={'label':'REC_CANDIDATE_01','filename':'rlog.zst','bytes':12,'sha256':'a'*64,'camera_metadata_frames':1200}
    assert gate.public_candidate(record)==record
    for extra in ('route','gps','latitude','timestamp','directory'):
        with pytest.raises(ValueError):gate.public_candidate({**record,extra:'private'})
    with pytest.raises(ValueError):gate.public_candidate({**record,'label':'actual-route--14'})
    with pytest.raises(ValueError):gate.public_candidate({**record,'sha256':'short'})


def test_exclusive_output_and_no_nan(tmp_path):
    path=tmp_path/'result.json'
    gate.write_exclusive(path,{'status':'BLOCKED','frames':0})
    before=path.read_bytes()
    with pytest.raises(FileExistsError):gate.write_exclusive(path,{'frames':1})
    assert path.read_bytes()==before
    with pytest.raises(ValueError):gate.write_exclusive(tmp_path/'nan.json',{'metric':float('nan')})
    assert not (tmp_path/'nan.json').exists()
