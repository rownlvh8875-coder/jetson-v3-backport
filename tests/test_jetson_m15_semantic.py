"""CPU_FAKE/FIXTURE mathematical and source boundary evidence only."""
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import jetson_m15_semantic as m


def test_float64_errors_quantiles_rmse_and_resolution_denominator():
    ref=np.array([0.,1.,-2.,3.],np.float32)
    got=np.array([1.,2.,-4.,3.],np.float32)
    out=m.metrics(ref,got)
    assert out['max_abs']==2 and out['mean_abs']==1
    assert out['rmse']==pytest.approx(np.sqrt(1.5))
    assert out['p95_abs']==pytest.approx(np.percentile([1,1,2,0],95))
    assert out['p99_abs']==pytest.approx(np.percentile([1,1,2,0],99))
    assert out['reference_min']==-2 and out['reference_max']==3 and out['elements']==4
    assert out['relative_denominator_epsilon']==3*np.finfo(np.float32).eps
    assert out['max_relative']==1/out['relative_denominator_epsilon']


def test_integer_difference_does_not_wrap_and_unit_quantum_is_diagnostic_only():
    out=m.metrics(np.array([255,0],np.uint8),np.array([0,255],np.uint8))
    assert out['max_abs']==255 and out['relative_denominator_epsilon']==1
    assert out['max_relative']==255


@pytest.mark.parametrize('ref,got',[(np.zeros(2),np.zeros(3)),(np.array([np.nan]),np.zeros(1)),(np.zeros(1),np.array([np.inf]))])
def test_invalid_metrics_fail(ref,got):
    with pytest.raises(ValueError):m.metrics(ref,got)


def test_slice_coverage_uses_every_actual_spec_name_and_rejects_gaps_overlap():
    spec=json.loads((ROOT/'artifacts/cinque_v3.json').read_text())
    values=np.zeros((1,18452),np.float32)
    views=m.slice_outputs(values,spec)
    assert set(views)==set(spec['output_slices']) and sum(v.size for v in views.values())==18452
    spec['output_slices']['plan'][0]+=1
    with pytest.raises(ValueError):m.slice_outputs(values,spec)


def test_sequence_input_identity_normalizes_only_exact_image_retype():
    raw={'new_img':np.array([0,255],np.uint8),'action_t':np.ones(2,np.float32),'state_feat_q':np.zeros(2,np.float32)}
    physical={**raw,'new_img':raw['new_img'].astype(np.float16),'state_feat_q':np.ones(2,np.float32)}
    assert m.input_digest(raw)==m.input_digest(physical)
    physical['new_img'][0]=.5
    with pytest.raises(ValueError):m.input_digest(physical)
    physical['new_img'][0]=0;physical['action_t']=np.zeros(2,np.float32)
    assert m.input_digest(raw)!=m.input_digest(physical)


def test_pooled_quantiles_are_over_all_elements_not_mean_frame_percentiles():
    acc=m.Accumulator()
    acc.add(np.zeros(1,np.float32),np.array([100],np.float32))
    acc.add(np.zeros(99,np.float32),np.zeros(99,np.float32))
    out=acc.finish()
    assert out['elements']==100 and out['mean_abs']==1 and out['p95_abs']==0
    assert out['rmse']==10


def test_drift_observation_never_claims_infinite_bound_or_acceptance():
    rows=[{'frame':i,'max_abs':min(i,.2),'mean_abs':min(i*.01,.02),'rmse':min(i*.02,.04)} for i in range(101)]
    out=m.drift_summary(rows)
    assert out['frames']==101 and out['last']['frame']==100
    assert out['max_abs_nondecreasing'] is True
    assert out['infinite_boundedness']=='NOT_ESTABLISHED'
    assert out['acceptance']=='UNDETERMINED'


def test_actual_parser_source_is_hashed_and_does_not_mutate_raw_outputs():
    reference=ROOT/'.reference/m05-carrot-nav-366d6eae/openpilot/selfdrive/modeld'
    assert reference.is_dir(),'exact source reference required for this fixture test'
    parser,provenance=m.load_parser(reference)
    spec=json.loads((ROOT/'artifacts/cinque_v3.json').read_text())
    raw=np.linspace(-.1,.1,18452,dtype=np.float32).reshape(1,-1)
    before=raw.copy()
    parsed=m.parsed_outputs(parser,raw,spec)
    assert np.array_equal(raw,before)
    assert parsed['plan'].shape==(1,33,15) and parsed['lead'].shape==(1,3,6,4)
    assert len(parsed)==22 and all(np.all(np.isfinite(v)) for v in parsed.values())
    assert all(len(v['sha256'])==64 for v in provenance.values())


def test_parsed_shape_and_probability_decisions_are_checked():
    left={'desire_state':np.array([[.1,.9]],np.float32),'plan':np.zeros((1,2),np.float32)}
    right={'desire_state':np.array([[.9,.1]],np.float32),'plan':np.zeros((1,2),np.float32)}
    assert m.decision_changes(left,right)['desire_state_argmax_changes']==1
    with pytest.raises(ValueError):m.compare_parsed(left,{'plan':np.zeros((1,2),np.float32)})


def test_measurement_completion_never_returns_parity_pass_without_approval():
    out=m.decision_report({'max_abs':0})
    assert out['numerical_decision']=='PARITY_UNDETERMINED' and out['exit_status']==3
    assert out['parser_parity']=='UNDETERMINED: measured without approved tolerance'


def test_reference_rejects_incomplete_sequence_before_runtime(tmp_path):
    spec=json.loads((ROOT/'artifacts/cinque_v3.json').read_text())
    (tmp_path/'manifest.json').write_text(json.dumps({'schema':1,'frames':5}))
    with pytest.raises(ValueError,match='reference source'):m.validate_reference(tmp_path,spec)


def test_actual_parser_source_drift_is_rejected_before_execution(tmp_path):
    (tmp_path/'constants.py').write_text('raise RuntimeError("must not execute")')
    (tmp_path/'parse_model_outputs.py').write_text('raise RuntimeError("must not execute")')
    with pytest.raises(ValueError,match='source drift'):m.load_parser(tmp_path)


def test_parser_dtype_drift_is_rejected():
    with pytest.raises(ValueError,match='dtype'):
        m.compare_parsed({'plan':np.zeros(2,np.float32)},{'plan':np.zeros(2,np.float64)})
