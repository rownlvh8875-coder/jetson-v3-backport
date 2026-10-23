#!/usr/bin/env python3
"""Offline analysis of M16 exact paired outputs, after the GPU process closes."""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse
import contextlib
import importlib.util
import io
import json
from pathlib import Path
from types import SimpleNamespace
import numpy as np
import jetson_m16_acceptance as m

REGIONS={'near_control_nodes_0_16':slice(0,17),'mid_preview_support_17_18':slice(17,19),'far_MPC_tail_19_32':slice(19,33)}


def region_metrics(left,right):
    if left.shape!=(1,33,15) or right.shape!=left.shape:raise ValueError('plan region shape')
    return {name:{f'{field}[{c-at.start}]':m.semantic.metrics(left[:,sl,c],right[:,sl,c])
                  for field,at in m.semantic.PLAN_AXES.items() for c in range(at.start,at.stop)} for name,sl in REGIONS.items()}


def attribution(ort,independent,teacher):
    return {'independent_error':m.semantic.metrics(ort,independent),'teacher_error':m.semantic.metrics(ort,teacher),
            'feedback_associated_difference':m.semantic.metrics(teacher,independent),
            'interpretation':'PAIRED_DIAGNOSTIC_NOT_ADDITIVE_CAUSAL_DECOMPOSITION'}


def desire_detail(raw,parsed,spec):
    views=m.semantic.slice_outputs(raw,spec) if set(spec['output_slices'])!={'desire_pred','desire_state'} else {
        n:raw[:,start:stop] for n,(start,stop) in spec['output_slices'].items()}
    logits=views['desire_pred'].reshape(1,4,8)
    return {'prediction_slots':[m.rankings(logits[0,i],parsed['desire_pred'][0,i],m.DESIRE_CLASSES) for i in range(4)],
            'state':m.rankings(views['desire_state'][0],parsed['desire_state'][0],m.DESIRE_CLASSES),
            'prediction_time_mapping':'NOT_DEFINED_IN_PINNED_NAV_SOURCE'}


def zoom_diagnostic(source,spec,left,right):
    if len(left)!=len(right) or not left or any(a.shape!=b.shape for a,b in zip(left,right)):
        raise ValueError('exact frame/shape equality required; upstream truncation forbidden')
    if m.verify.file_identity(source)['sha256']!=m.BOUNDED_SOURCE['sha256']:raise ValueError('pinned verifier source drift')
    spec_source=source.with_name('jetlink_spec.py')
    spec_identity=m.verify.file_identity(spec_source)
    if spec_identity['sha256']!='a8b9323ba86d28b32c40353f4730efd67b2e61293049524c4bebe4dd3880a9f9':raise ValueError('pinned verifier ModelSpec source drift')
    module_spec=importlib.util.spec_from_file_location('_m16_pinned_zoompilot',source)
    module=importlib.util.module_from_spec(module_spec)
    # The current host's spec predates DRIVING_OUTPUT. Load the verifier's exact
    # matching pure spec source, then immediately restore the caller namespace.
    # No production source is edited, and no engine/client entrypoint is called.
    key='jetlink.spec';sentinel=object();previous=sys.modules.get(key,sentinel)
    parent=sys.modules.get('jetlink');previous_attribute=getattr(parent,'spec',sentinel)
    pinned_key='_m16_zoompilot_spec';prior_pinned=sys.modules.get(pinned_key,sentinel)
    try:
        importlib.import_module('jetlink.protocol')
        definition=importlib.util.spec_from_file_location(pinned_key,spec_source)
        pinned=importlib.util.module_from_spec(definition);sys.modules[pinned_key]=pinned
        definition.loader.exec_module(pinned)
        sys.modules[key]=pinned;module_spec.loader.exec_module(module)
    finally:
        if previous is sentinel:sys.modules.pop(key,None)
        else:sys.modules[key]=previous
        if prior_pinned is sentinel:sys.modules.pop(pinned_key,None)
        else:sys.modules[pinned_key]=prior_pinned
        package=sys.modules.get('jetlink')
        if package is not None:
            if previous_attribute is sentinel:package.__dict__.pop('spec',None)
            else:setattr(package,'spec',previous_attribute)
    mapping=SimpleNamespace(output_slices={n:slice(*bounds) for n,bounds in spec['output_slices'].items()})
    left=[a.reshape(-1).astype(np.float32) for a in left];right=[b.reshape(-1).astype(np.float32) for b in right]
    # left=ORT reference; actual upstream API takes links first, references second.
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream):pooled=module.report_slices(mapping,right,left)
    rows={};frame_fail={}
    for name,sl in mapping.output_slices.items():
        correlations=[module._corr(b[sl],a[sl]) for a,b in zip(left,right)]
        n=left[0][sl].size
        if n>=module.MIN_SAMPLES:
            failed=[i for i,c in enumerate(correlations) if c<module.MIN_CORR]
            if failed:frame_fail[name]=failed
        aa=np.concatenate([a[sl] for a in left]);bb=np.concatenate([b[sl] for b in right])
        quiet_columns=[];column_details={};spread=float(aa.std())
        lc=[module.columns(name,a[sl]) for a in left];rc=[module.columns(name,b[sl]) for b in right]
        if lc[0]:
            for key in lc[0]:
                ref=np.concatenate([c[key] for c in lc]);actual=np.concatenate([c[key] for c in rc])
                passed,why=module.judge(actual,ref,lc[0][key].size,spread)
                quiet=bool(ref.std()<module.QUIET_FRACTION*spread)
                if quiet:quiet_columns.append(key)
                column_details[key]={'passed':bool(passed),'actual_upstream_judgment':why,'quiet':quiet,
                                      'max_abs':float(np.max(np.abs(actual-ref))),
                                      'small_value_bound':float(module.tolerance(ref,spread))}
        _,why=module.judge(bb,aa,n)
        rows[name]={'pooled_PASS':bool(pooled[name]),'pooled_correlation':module._corr(bb,aa),
                    'minimum_frame_correlation':min(correlations),'per_frame_gated':n>=module.MIN_SAMPLES,
                    'failed_frames':frame_fail.get(name,[]),'small_slice':n<module.MIN_SAMPLES,
                    'actual_upstream_judgment':why,'quiet_columns':quiet_columns,'columns':column_details,
                    'quiet_column_fraction':len(quiet_columns)/len(column_details) if column_details else None}
    return {'status':'PASS' if all(pooled.values()) and not frame_fail else 'FAIL',
            'meaning':'ZOOMPILOT_HEURISTIC_ONLY_NOT_APPLICATION_APPROVAL','frames':len(left),
            'source':m.BOUNDED_SOURCE,'spec_source':spec_identity,'criteria':{n:float(getattr(module,n)) for n in ('MIN_CORR','MIN_SAMPLES','QUIET_FRACTION','TINY_TOLERANCE','CONSTANT_FRACTION')},
            'slices':rows,'console':stream.getvalue()}


def load_constants(directory):
    # The unchanged M15 loader verifies both exact files before any execution.
    m.semantic.load_parser(directory)
    spec=importlib.util.spec_from_file_location('_m16_nav_constants',directory/'constants.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module.ModelConstants


def finish(accumulators):
    return {name:a.finish() for name,a in accumulators.items()}


def accumulate(target,values_left,values_right):
    for name,left in values_left.items():
        target.setdefault(name,m.semantic.Accumulator()).add(left,values_right[name])


def require_complete_frames(reference,report):
    n=reference.get('frames')
    if (type(n) is not int or n not in (257,512) or report.get('frames')!=n
            or len(reference.get('files',[]))!=n or len(report.get('files',[]))!=n
            or len(report.get('per_frame',[]))!=n):raise ValueError('complete equal reference/result frame lists required')


def queue_accounting(rows,depth=128,teacher=False):
    errors=[]
    for i,row in enumerate(rows):
        history=[row['instantaneous_hidden']] if teacher else [r['instantaneous_hidden'] for r in rows[max(0,i-depth+1):i+1]]
        expected={'max_abs':max(r['max_abs'] for r in history),
                  'mean_abs':sum(r['mean_abs'] for r in history)/depth,
                  'rmse':float(np.sqrt(sum(r['rmse']**2 for r in history)/depth))}
        errors.append({k:abs(row[k]-expected[k]) for k in expected})
    return {'mode':'ONE_CHANGED_SLOT_WITH_ORT_HISTORY' if teacher else 'ROLLING_SHIFT_QUEUE_WITH_ZERO_INITIALIZATION',
            'depth':depth,'frames':len(rows),**{'max_'+k+'_residual':max(r[k] for r in errors) for k in ('mean_abs','rmse','max_abs')},
            'interpretation':'moment reconstruction, not a universal bound or feature-feedback causality proof'}


def analyze(args):
    spec=json.loads(args.spec.read_text());report=json.loads((args.result_dir/'report.json').read_text())
    reference=json.loads((args.reference_dir/'manifest.json').read_text())
    require_complete_frames(reference,report)
    m.validate_result_header(report,args.sequence,reference['frames'])
    if report['reference_manifest']!=m.verify.file_identity(args.reference_dir/'manifest.json'):raise ValueError('reference binding changed')
    if reference['spec']!=spec or reference['source']!=m.isolation.V3_IDENTITY:raise ValueError('source/spec changed')
    if not report.get('all_contracts_finite') or report['input_digest_matches']!=report['frames']:raise ValueError('strict gates not passed')
    if len(report['files'])!=report['frames'] or len(report['per_frame'])!=report['frames']:raise ValueError('incomplete measurement')
    parser,provenance=m.semantic.load_parser(args.parser_source);constants=load_constants(args.parser_source)
    if provenance!=report['parser_source'] or provenance!=reference['parser']:raise ValueError('parser binding changed')
    output=m.prior.new_directory(args.out_dir)
    accum={v:{'raw':{},'parsed':{},'regions':{},'feedback_associated':{}} for v in m.VARIANTS}
    worst={v:{} for v in m.VARIANTS};interest={v:{} for v in m.VARIANTS};desire_changes={v:[] for v in m.VARIANTS}
    focus={v:[] for v in m.VARIANTS};neighbors={v:[] for v in m.VARIANTS};lefts=[];rights={v:[] for v in m.VARIANTS}
    old_acc={n:m.semantic.Accumulator() for n in ('outputs','plan','lead','desire_pred','action','hidden_state')}
    for frame,(ref_entry,entry,row) in enumerate(zip(reference['files'],report['files'],report['per_frame'],strict=True)):
        if (entry['frame']!=frame or ref_entry['frame']!=frame or row['frame']!=frame
                or not row['input_digest_match'] or row['teacher_state_input_exact'] is not True):raise ValueError('measurement frame/proof mismatch')
        ref_path=args.reference_dir/ref_entry['name'];path=args.result_dir/entry['name']
        if ref_entry['name']!=f'frame-{frame:04d}.npz' or entry['name']!=ref_entry['name']:raise ValueError('unsafe frame name')
        if m.verify.file_identity(ref_path)!={k:ref_entry[k] for k in ('sha256','nbytes')} or m.verify.file_identity(path)!={k:entry[k] for k in ('sha256','nbytes')}:raise ValueError('paired arrays changed')
        left=m.prior.read_arrays(ref_path,m.compact_contract(spec))['outputs']
        physical=m.prior.read_arrays(path,{v:m.verify.spec_contract(spec)['outputs']['outputs'] for v in m.VARIANTS})
        lviews={'outputs':left,**m.semantic.slice_outputs(left,spec)};lp=m.semantic.parsed_outputs(parser,left,spec)
        lefts.append(left)
        for variant,right in physical.items():
            rights[variant].append(right)
            rviews={'outputs':right,**m.semantic.slice_outputs(right,spec)};rp=m.semantic.parsed_outputs(parser,right,spec)
            m.semantic.compare_parsed(lp,rp)
            accumulate(accum[variant]['raw'],lviews,rviews);accumulate(accum[variant]['parsed'],lp,rp)
            for region,sl in REGIONS.items():
                for field,at in m.semantic.PLAN_AXES.items():
                    for column in range(at.start,at.stop):
                        key=f'{region}.{field}[{column-at.start}]'
                        accum[variant]['regions'].setdefault(key,m.semantic.Accumulator()).add(lp['plan'][:,sl,column],rp['plan'][:,sl,column])
            pc=m.plan_case(lp['plan'],rp['plan'],constants.T_IDXS)
            lc=m.lead_case(lp,rp,constants.LEAD_T_IDXS,['X','Y','V','A'])
            for name,case in (('plan',pc),('lead',lc)):
                case['frame']=frame
                if name not in worst[variant] or case['abs_error']>worst[variant][name]['abs_error']:worst[variant][name]=case
            if frame in (14,45,46):
                interest[variant][str(frame)]={'plan':pc,'lead':lc,'desire':{'ort':desire_detail(left,lp,spec),'trt':desire_detail(right,rp,spec)}}
            if 10<=frame<=18:
                feeds=m.frame_inputs(reference['contract']['inputs'],frame,args.sequence)
                neighbors[variant].append({'frame':frame,'input_desire':feeds['desire'].tolist(),'action_t':feeds['action_t'].tolist(),
                         'ort':desire_detail(left,lp,spec),'trt':desire_detail(right,rp,spec),
                         'probability_abs_differences':np.abs(lp['desire_pred']-rp['desire_pred']).tolist()})
            if 14<=frame<=20:
                focus[variant].append({'frame':frame,'raw':{n:m.semantic.metrics(lviews[n],rviews[n]) for n in ('plan','lead','action','desire_state','desire_pred','hidden_state')},
                                      'parsed_plan':m.semantic.metrics(lp['plan'],rp['plan']),'parsed_lead':m.semantic.metrics(lp['lead'],rp['lead']),
                                      'action_values':{'ort':lp['action'].tolist(),'trt':rp['action'].tolist()}})
            for name in ('desire_pred','desire_state'):
                changed=np.argwhere(np.argmax(lp[name],axis=-1)!=np.argmax(rp[name],axis=-1))
                if changed.size:
                    desire_changes[variant].append({'frame':frame,'field':name,'changed_slots':changed.tolist(),
                                                    'ort':desire_detail(left,lp,spec),'trt':desire_detail(right,rp,spec)})
            if variant=='independent' and frame<101:
                for name,acc in old_acc.items():acc.add(lviews[name],rviews[name])
        # Difference between two TRT evaluations at different states is a paired
        # feedback-associated diagnostic, not a linear causal allocation.
        iv=m.semantic.slice_outputs(physical['independent'],spec);tv=m.semantic.slice_outputs(physical['teacher_forced'],spec)
        accumulate(accum['independent']['feedback_associated'],iv,tv)
        if frame%128==0:print(json.dumps({'analysis':args.sequence,'frame':frame}),flush=True)
    numerical={v:{name:finish(collection) for name,collection in groups.items() if collection} for v,groups in accum.items()}
    states={v:{name:m.turnover([{'frame':r['frame'],**r['variants'][v]['state'][name],
                               'instantaneous_hidden':r['variants'][v]['hidden']} for r in report['per_frame']])
               for name in ('next_state_img_q','next_state_desire_q','next_state_feat_q')} for v in m.VARIANTS}
    accounting={v:queue_accounting([{'frame':r['frame'],**r['variants'][v]['state']['next_state_feat_q'],
                                    'instantaneous_hidden':r['variants'][v]['hidden']} for r in report['per_frame']],teacher=v=='teacher_forced') for v in m.VARIANTS}
    zoom={}
    for variant in m.VARIANTS:
        result=zoom_diagnostic(args.zoompilot_source,spec,lefts,rights[variant])
        (output/(variant+'-zoompilot-console.txt')).write_text(result.pop('console'))
        zoom[variant]=result
    result={'schema':1,'sequence':args.sequence,'frames':report['frames'],'variants':m.VARIANTS,
            'source':m.isolation.V3_IDENTITY,'engine':m.semantic.M1_PLAN,'measurement_report':m.verify.file_identity(args.result_dir/'report.json'),
            'reference_manifest':report['reference_manifest'],'parser':provenance,'numerical':numerical,
            'worst':worst,'interest_frames':interest,'desire_neighbors':neighbors,'desire_changes':desire_changes,
            'frame14_20':focus,'turnover':states,'feature_queue_accounting':accounting,'first101':finish(old_acc),'zoompilot':zoom,
            'actual_time_indices':constants.T_IDXS,'lead_time_indices':constants.LEAD_T_IDXS,
            'plan_regions':{n:{'indices':[sl.start,sl.stop],'first_seconds':constants.T_IDXS[sl.start],'last_seconds':constants.T_IDXS[sl.stop-1]} for n,sl in REGIONS.items()},
            'region_interpretation':'report-only disjoint CONTROL_N/preview support/remainder; ALL33 nodes can affect MPC, no universal near/mid/far acceptance',
            'attribution_interpretation':'PAIRED_DIAGNOSTIC_NOT_ADDITIVE_CAUSAL_DECOMPOSITION',
            'evidence':report['evidence'],'numerical_decision':'PARITY_UNDETERMINED','representative':'BLOCKED_REPRESENTATIVE_INPUT',
            'comma_replay':'NOT_RUN: no aligned recorded CapnProto replay messages or camera preprocessing provenance',
            'installation':'DO_NOT_INSTALL'}
    m.write_public(output/'analysis.json',result)
    return {'status':'ANALYZED_NO_APPROVAL','sequence':args.sequence,'frames':report['frames'],
            'analysis':m.verify.file_identity(output/'analysis.json'),'exit_status':3}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('reference-dir','result-dir','parser-source','spec','zoompilot-source','out-dir'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--sequence',choices=('historical','bounded'),required=True)
    args=p.parse_args(argv)
    try:result=analyze(args)
    except Exception as e:result={'status':'FAIL','error_type':type(e).__name__,'error':str(e),'exit_status':1}
    print(json.dumps(result),flush=True)
    return result['exit_status']


if __name__=='__main__':raise SystemExit(main())
