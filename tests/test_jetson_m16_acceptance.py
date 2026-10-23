"""CPU_FAKE/FIXTURE diagnostics; no CUDA or numerical approval implied."""
import json
import ipaddress
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import jetson_m16_acceptance as m


def test_worst_index_preserves_signed_value_and_near_zero_denominator():
    a=np.array([[0.,20.],[-3.,4.]],np.float32);b=a.copy();b[1,0]=1.25
    r=m.worst(a,b)
    assert r['index']==[1,0] and r['ort']==-3 and r['trt']==1.25
    assert r['signed_trt_minus_ort']==r['abs_error']==4.25
    assert r['reference_magnitude']==3 and r['relative_error']==pytest.approx(4.25/3)
    with pytest.raises(ValueError):m.worst(a,np.zeros(4,np.float32))


def test_plan_localizes_nonlinear_time_and_complete_channel_profile():
    a=np.zeros((1,33,15),np.float32);b=a.copy();a[0,32,0]=500;b[0,32,0]=504.25
    times=[10*(i/32)**2 for i in range(33)]
    r=m.plan_case(a,b,times)
    assert r['timestep']==32 and r['time_seconds']==10 and r['field']=='POSITION[0]'
    assert r['hypothesis']=='SINGLE_DIRECT_OUTPUT_NO_MDN_SELECTION'
    assert len(r['profile'])==33 and r['profile'][16]['time_seconds']==2.5
    assert r['profile'][-1]['abs_error']==4.25 and r['profile'][0]['abs_error']==0
    with pytest.raises(ValueError):m.plan_case(a,b,times[:-1])


def test_lead_localizes_direct_head_field_probability_and_std():
    a=np.zeros((1,3,6,4),np.float32);b=a.copy();a[0,2,5,2]=100;b[0,2,5,2]=104
    left={'lead':a,'lead_stds':np.ones_like(a),'lead_prob':np.array([[.9,.7,.2]],np.float32)}
    right={**left,'lead':b}
    r=m.lead_case(left,right,[0,2,4,6,8,10],['X','Y','V','A'])
    assert (r['head'],r['timestep'],r['field'],r['time_seconds'])==(2,5,'V',10)
    assert r['ort_probability']==pytest.approx(.2) and r['ort_std']==1
    assert r['hypothesis']=='DIRECT_HEAD_NO_MDN_ALTERNATIVES'


def test_rankings_report_all_logits_probabilities_and_exact_margin():
    logits=np.array([0.,2.,1.],np.float32);p=np.array([.1,.4501,.4499],np.float32)
    r=m.rankings(logits,p,['none','left','right'])
    assert r['top1']['class']=='left' and r['top2']['class']=='right'
    assert r['margin']==pytest.approx(float(p[1]-p[2]),abs=1e-8)
    assert [x['index'] for x in r['ranking']]==[1,2,0]
    assert r['ranking'][0]['logit']==2
    with pytest.raises(ValueError):m.rankings(logits,np.array([0.,np.nan,1.]),['a','b','c'])


def test_state_replacement_uses_all_pairs_and_only_exact_image_retype():
    physical={'inputs':{'state_img_q':{'shape':[2],'dtype':'float16'},'state_feat_q':{'shape':[2],'dtype':'float32'},'state_desire_q':{'shape':[2],'dtype':'float32'}}}
    state={'state_img_q':np.array([0,255],np.uint8),'state_feat_q':np.array([.5,1],np.float32),'state_desire_q':np.zeros(2,np.float32)}
    feeds={k:np.ones(v['shape'],v['dtype']) for k,v in physical['inputs'].items()}
    m.replace_states(feeds,state,physical)
    assert feeds['state_img_q'].tolist()==[0,255] and feeds['state_img_q'].dtype==np.float16
    assert feeds['state_feat_q'].tolist()==[.5,1]
    with pytest.raises(ValueError):m.replace_states(feeds,{**state,'state_feat_q':np.zeros(2,np.float16)},physical)
    with pytest.raises(ValueError):m.replace_states(feeds,{k:v for k,v in state.items() if k!='state_desire_q'},physical)


def test_feature_reconstruction_shift_is_byte_exact_and_proof_rejects_bad_state():
    prev=np.arange(12,dtype=np.float32).reshape(3,1,4);hidden=np.array([[50,60,70,80]],np.float32)
    expected=np.array([[[4,5,6,7]],[[8,9,10,11]],[[50,60,70,80]]],np.float32)
    assert np.array_equal(m.feature_next(prev,hidden),expected)
    m.prove_feature(prev,hidden,expected)
    with pytest.raises(ValueError):m.prove_feature(prev,hidden,prev)


def test_post_turnover_slopes_and_checkpoints_are_diagnostics_not_acceptance():
    rows=[{'frame':i,'max_abs':float(i),'mean_abs':2.*i,'rmse':3.*i} for i in range(512)]
    r=m.turnover(rows)
    assert r['queue_turnover']=='PASS' and r['window']['first_frame']==128 and r['window']['last_frame']==511
    assert r['window']['mean_abs_slope_per_frame']==pytest.approx(2)
    assert r['window']['rmse_slope_per_frame']==pytest.approx(3)
    assert [x['frame'] for x in r['checkpoints']]==[0,1,5,10,25,50,100,127,128,129,192,255,256,384,511]
    assert r['infinite_boundedness']=='NOT_ESTABLISHED' and r['acceptance']=='DIAGNOSTIC_ONLY'
    assert m.turnover(rows[:101])['queue_turnover']=='NOT_REACHED'
    with pytest.raises(ValueError):m.turnover([rows[0],rows[2]])


def test_bounded_action_uses_exact_pinned_formula_and_historical_unchanged():
    contract=json.loads((ROOT/'artifacts/cinque_v3.json').read_text())
    inputs=m.verify.spec_contract(contract)['inputs']
    a=m.frame_inputs(inputs,100,'historical');b=m.frame_inputs(inputs,100,'bounded')
    assert a['action_t'].tolist()==[[5.,5.]]
    assert np.array_equal(a['new_img'],b['new_img'])
    assert b['action_t'][0,0]==np.float32(.25+.1*np.sin(50))
    assert b['action_t'][0,1]==np.float32(.35+.1*np.cos(50))
    with pytest.raises(ValueError):m.frame_inputs(inputs,0,'unknown')


def test_teacher_and_independent_feeds_do_not_alias_or_cross_contaminate():
    p={'inputs':{'state_feat_q':{'shape':[1],'dtype':'float32'}}}
    base={'state_feat_q':np.zeros(1,np.float32)}
    a=m.state_feeds(base,{'state_feat_q':np.array([10],np.float32)},p)
    b=m.state_feeds(base,{'state_feat_q':np.array([20],np.float32)},p)
    a['state_feat_q'][0]=99
    assert b['state_feat_q'][0]==20 and base['state_feat_q'][0]==0


def test_recorded_provenance_rejects_synthetic_or_missing_input_reconstruction():
    with pytest.raises(ValueError):m.validate_recorded_provenance({'evidence':'SYNTHETIC_INPUT'})
    with pytest.raises(ValueError):m.validate_recorded_provenance({'evidence':'RECORDED_INPUT','source_sha256':'a'*64,'frames':10})


def test_public_serialization_rejects_private_info_nonfinite_and_overwrite(tmp_path):
    p=tmp_path/'safe.json';m.write_public(p,{'status':'PARITY_UNDETERMINED','frames':512})
    assert json.loads(p.read_text())['frames']==512
    with pytest.raises(FileExistsError):m.write_public(p,{'frames':0})
    for value in ({'address':str(ipaddress.ip_address(167838211))},{'private_key':'fixture-only'},{'value':float('nan')},{'file':'C:'+ '/Users/'+'fixture/model.onnx'}):
        with pytest.raises(ValueError):m.write_public(tmp_path/'bad.json',value)
    assert not (tmp_path/'bad.json').exists()


def test_variant_manifest_cannot_silently_mix_sequences_or_frame_counts():
    good={'sequence':'historical','frames':512,'variants':['independent','teacher_forced'],'source':m.isolation.V3_IDENTITY,'engine':m.semantic.M1_PLAN}
    m.validate_result_header(good,'historical',512)
    for k,v in [('sequence','bounded'),('frames',511),('variants',['independent']),('engine',{'sha256':'0'*64,'nbytes':1})]:
        with pytest.raises(ValueError):m.validate_result_header({**good,k:v},'historical',512)


def test_teacher_input_proof_normalizes_only_validated_image_representation():
    a={'state_img_q':np.array([0,255],np.uint8),'state_feat_q':np.array([.25],np.float32)}
    b={**a,'state_img_q':a['state_img_q'].astype(np.float16)}
    assert m.state_digest(a)==m.state_digest(b)
    assert m.state_digest(a)!=m.state_digest({**b,'state_feat_q':np.array([.5],np.float32)})
    with pytest.raises(ValueError):m.state_digest({**b,'state_img_q':np.array([.5,255],np.float16)})


@pytest.mark.parametrize('fault',[None,'nan','shape','dtype'])
def test_real_paired_step_separates_histories_and_fails_closed(fault):
    spec=json.loads((ROOT/'artifacts/cinque_v3.json').read_text())
    physical=m.verify.spec_contract(spec,m.verify.V3_RETYPES);raw=m.verify.spec_contract(spec)
    parser,_=m.semantic.load_parser(ROOT/'.reference/m15-carrot-nav-366d6eae/openpilot/selfdrive/modeld')
    independent=m.raw_states(physical);teacher=m.raw_states(raw)
    independent['state_feat_q'].fill(2);teacher['state_feat_q'].fill(3)
    left={n:np.zeros(v['shape'],v['dtype']) for n,v in raw['outputs'].items()}
    class Engine:
        last_timing={}
        def __init__(self):self.seen=[]
        def run(self,feeds):
            self.seen.append(float(feeds['state_feat_q'][0,0,0]))
            out={n:np.zeros(v['shape'],v['dtype']) for n,v in physical['outputs'].items()}
            out['outputs'][0,0]=feeds['state_feat_q'][0,0,0]
            if fault=='nan':out['next_state_feat_q'][0,0,0]=np.nan
            if fault=='shape':out['outputs']=out['outputs'][:,:-1]
            if fault=='dtype':out['next_state_desire_q']=out['next_state_desire_q'].astype(np.float16)
            return out
    engine=Engine();base=m.frame_inputs(physical['inputs'],0,'historical')
    if fault:
        with pytest.raises(ValueError):m.paired_step(engine,base,independent,teacher,left,physical,parser,spec)
        assert engine.seen==[2] and independent['state_feat_q'][0,0,0]==2
    else:
        payload,row,state=m.paired_step(engine,base,independent,teacher,left,physical,parser,spec)
        assert engine.seen==[2,3] and payload['independent'][0,0]==2 and payload['teacher_forced'][0,0]==3
        assert row['teacher_state_input_exact'] is True and np.count_nonzero(state['state_feat_q'])==0
        assert independent['state_feat_q'][0,0,0]==2 and teacher['state_feat_q'][0,0,0]==3
