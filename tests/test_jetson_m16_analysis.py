"""CPU-only analysis boundaries, independent of actual device measurements."""
from pathlib import Path
import sys
import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
import jetson_m16_analysis as a


def test_region_boundaries_keep_preview_interpolation_node18_and_mpc_tail():
    left=np.zeros((1,33,15),np.float32);right=left.copy()
    right[0,16,0]=1;right[0,18,0]=2;right[0,19,0]=3
    rows=a.region_metrics(left,right)
    assert rows['near_control_nodes_0_16']['POSITION[0]']['max_abs']==1
    assert rows['mid_preview_support_17_18']['POSITION[0]']['max_abs']==2
    assert rows['far_MPC_tail_19_32']['POSITION[0]']['max_abs']==3
    with pytest.raises(ValueError):a.region_metrics(left[:,:32],right[:,:32])


def test_attribution_reports_difference_of_differences_without_causal_percentage():
    ort=np.array([1.,2.],np.float32);ind=np.array([3.,4.],np.float32);teacher=np.array([2.,2.],np.float32)
    rows=a.attribution(ort,ind,teacher)
    assert rows['independent_error']['mean_abs']==2
    assert rows['teacher_error']['mean_abs']==.5
    assert rows['feedback_associated_difference']['max_abs']==2
    assert rows['interpretation']=='PAIRED_DIAGNOSTIC_NOT_ADDITIVE_CAUSAL_DECOMPOSITION'


def test_zoom_diagnostic_rejects_shape_truncation_before_loading_source(tmp_path):
    with pytest.raises(ValueError,match='shape'):
        a.zoom_diagnostic(tmp_path/'absent.py',{},[np.zeros(2)],[np.zeros(3)])


def test_desire_detail_keeps_unnamed_class_and_slot_without_invented_seconds():
    spec={'output_slices':{'desire_pred':[0,32],'desire_state':[32,40]}}
    raw=np.zeros((1,40),np.float32);raw[0,7]=2
    parsed={'desire_pred':np.full((1,4,8),.125,np.float32),'desire_state':np.full((1,8),.125,np.float32)}
    parsed['desire_pred'][0,0]=[0,0,0,0,0,0,0,1]
    value=a.desire_detail(raw,parsed,spec)
    assert value['prediction_slots'][0]['top1']['class']=='UNNAMED_SCHEMA_SLOT_7'
    assert value['prediction_slots'][0]['ranking'][0]['logit']==2
    assert value['prediction_time_mapping']=='NOT_DEFINED_IN_PINNED_NAV_SOURCE'


def test_reference_and_result_frame_counts_cannot_silently_truncate():
    ref={'frames':257,'files':[{}]*257}
    report={'frames':257,'files':[{}]*257,'per_frame':[{}]*257}
    a.require_complete_frames(ref,report)
    with pytest.raises(ValueError,match='complete'):
        a.require_complete_frames({**ref,'files':ref['files'][:-1]},report)
    with pytest.raises(ValueError,match='complete'):
        a.require_complete_frames(ref,{**report,'per_frame':report['per_frame'][:-1]})


def test_queue_accounting_distinguishes_filled_history_from_teacher_single_slot():
    rows=[{'frame':0,'mean_abs':1.,'rmse':np.sqrt(3.),'max_abs':3.,'instantaneous_hidden':{'mean_abs':3.,'rmse':3.,'max_abs':3.}},
          {'frame':1,'mean_abs':3.,'rmse':np.sqrt(15.),'max_abs':6.,'instantaneous_hidden':{'mean_abs':6.,'rmse':6.,'max_abs':6.}}]
    value=a.queue_accounting(rows,depth=3)
    assert value['max_mean_abs_residual']==0 and value['max_max_abs_residual']==0
    assert value['max_rmse_residual']<1e-14
    teacher=[{**rows[1],'frame':0,'mean_abs':2.,'rmse':np.sqrt(12.)}]
    result=a.queue_accounting(teacher,depth=3,teacher=True)
    assert result['max_mean_abs_residual']==0 and result['mode']=='ONE_CHANGED_SLOT_WITH_ORT_HISTORY'
