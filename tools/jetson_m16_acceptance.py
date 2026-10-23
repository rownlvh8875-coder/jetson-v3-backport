#!/usr/bin/env python3
"""Exact BASE-plan numerical diagnostics; no install, rebuild or USB path.

Use the existing M1 owned-worker/offroad guardian for every device invocation.
References are compact, but feature reconstruction is byte-proven against real
ORT outputs at every exported frame and rechecked before CUDA. Exit3 means
measurement without application approval, never a hidden passing tolerance.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse
import hashlib
import ipaddress
import json
from pathlib import Path
import re
import time
import numpy as np
import jetson_m15_semantic as semantic
import jetson_m1 as isolation
import jetson_m1_recurrent as recurrent
import jetson_m1_parity as prior
import build_trt_v3 as verify

SEED=73
VARIANTS=['independent','teacher_forced']
CHECKPOINTS=(0,1,5,10,25,50,100,127,128,129,192,255,256,384,511)
DESIRE_CLASSES=['none','turnLeft','turnRight','laneChangeLeft','laneChangeRight','keepLeft','keepRight','UNNAMED_SCHEMA_SLOT_7']
BOUNDED_SOURCE={'sha':'d24328d849b0e5154b55f149dc18c5dfe8bd79cc',
 'path':'scripts/verify_parity.py','sha256':'89a4c8b5c96904a091c713a9d82ce753149e4c5af80c13eaf7ecb306d4b6ff84',
 'formula':'[.25+.1*sin(.5*frame), .35+.1*cos(.5*frame)] cast float32',
 'analytic_envelopes':[[.15,.35],[.25,.45]]}


def array_sha(value):
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def worst(left,right):
    metric=semantic.metrics(left,right)
    error=np.abs(right.astype(np.float64)-left.astype(np.float64))
    index=tuple(int(i) for i in np.unravel_index(int(np.argmax(error)),left.shape))
    a,b=float(left[index]),float(right[index])
    return {'index':list(index),'ort':a,'trt':b,'signed_trt_minus_ort':b-a,
            'abs_error':abs(b-a),'reference_magnitude':abs(a),
            'relative_error':abs(b-a)/max(abs(a),semantic.epsilon(left)),
            'relative_denominator_epsilon':semantic.epsilon(left),'metrics':metric}


def plan_case(left,right,times):
    if left.shape!=(1,33,15) or right.shape!=left.shape or len(times)!=33:
        raise ValueError('actual plan/time contract mismatch')
    out=worst(left,right);_,at,column=out['index']
    field=next(f'{name}[{column-view.start}]' for name,view in semantic.PLAN_AXES.items() if view.start<=column<view.stop)
    out.update(field=field,timestep=at,time_seconds=float(times[at]),
               hypothesis='SINGLE_DIRECT_OUTPUT_NO_MDN_SELECTION',
               raw_mean_index=917+15*at+column,raw_logstd_index=1412+15*at+column,
               profile=[{'timestep':i,'time_seconds':float(t),'ort':float(left[0,i,column]),
                         'trt':float(right[0,i,column]),'signed_trt_minus_ort':float(right[0,i,column])-float(left[0,i,column]),
                         'abs_error':abs(float(right[0,i,column])-float(left[0,i,column]))} for i,t in enumerate(times)])
    return out


def lead_case(left,right,times,fields):
    if left['lead'].shape!=(1,3,6,4) or len(times)!=6 or len(fields)!=4:
        raise ValueError('actual direct lead/time contract mismatch')
    out=worst(left['lead'],right['lead']);_,head,at,column=out['index']
    out.update(head=head,timestep=at,time_seconds=float(times[at]),field=fields[column],
               head_probability_offset_seconds=float([0,2,4][head]),
               hypothesis='DIRECT_HEAD_NO_MDN_ALTERNATIVES',
               raw_mean_index=1907+head*24+at*4+column,
               raw_logstd_index=1979+head*24+at*4+column,
               ort_probability=float(left['lead_prob'][0,head]),trt_probability=float(right['lead_prob'][0,head]),
               ort_std=float(left['lead_stds'][0,head,at,column]),trt_std=float(right['lead_stds'][0,head,at,column]),
               all_ort_head_probabilities=left['lead_prob'][0].tolist(),all_trt_head_probabilities=right['lead_prob'][0].tolist())
    return out


def rankings(logits,probabilities,classes):
    if logits.ndim!=1 or logits.shape!=probabilities.shape or len(classes)!=len(logits):
        raise ValueError('categorical shape mismatch')
    if not np.all(np.isfinite(logits)) or not np.all(np.isfinite(probabilities)):
        raise ValueError('categorical nonfinite')
    if np.any(probabilities<0) or np.any(probabilities>1):raise ValueError('invalid probability')
    order=np.argsort(-probabilities,kind='stable')
    rows=[{'index':int(i),'class':classes[i],'probability':float(probabilities[i]),'logit':float(logits[i])} for i in order]
    return {'top1':rows[0],'top2':rows[1],'margin':float(probabilities[order[0]])-float(probabilities[order[1]]),'ranking':rows}


def frame_inputs(inputs,frame,sequence):
    if sequence not in ('historical','bounded'):raise ValueError('unknown sequence')
    out=verify.frame_inputs(inputs,frame,SEED)
    if sequence=='bounded':
        out['action_t'][0]=np.asarray([.25+.1*np.sin(.5*frame),.35+.1*np.cos(.5*frame)],np.float32)
    return out


def replace_states(feeds,states,physical):
    expected={n:v for n,v in physical['inputs'].items() if n.startswith('state_')}
    if set(states)!=set(expected):raise ValueError('incomplete recurrent replacement')
    pending={}
    for name,info in expected.items():
        value=states[name];dtype=np.dtype(info['dtype'])
        if not isinstance(value,np.ndarray) or value.shape!=tuple(info['shape']) or not np.all(np.isfinite(value)):
            raise ValueError('state shape/finite mismatch')
        if name=='state_img_q' and value.dtype==np.uint8 and dtype==np.float16:
            converted=value.astype(dtype)
            if not np.array_equal(converted.astype(np.uint8),value):raise ValueError('non-exact state image conversion')
            value=converted
        if value.dtype!=dtype:raise ValueError('state dtype mismatch')
        pending[name]=value
    for name,value in pending.items():np.copyto(feeds[name],value,casting='no')


def state_feeds(base,states,physical):
    out={n:v.copy() for n,v in base.items()}
    replace_states(out,states,physical)
    return out


def state_digest(states):
    digest=hashlib.sha256()
    for name,value in sorted(states.items()):
        if not name.startswith('state_'):continue
        if name=='state_img_q':
            if not np.all(np.isfinite(value)) or np.any(value<0) or np.any(value>255) or np.any(value!=value.astype(np.uint8)):
                raise ValueError('non-exact state image representation')
            value=value.astype(np.uint8)
        digest.update(name.encode()+b'\0'+str(value.shape).encode()+b'\0'+str(value.dtype).encode()+b'\0')
        digest.update(np.ascontiguousarray(value).tobytes())
    return digest.hexdigest()


def paired_step(session,base,state,ort_state,left,physical,parser,spec):
    payload={};row={'variants':{},'teacher_state_input_exact':False};pending=None
    lp=semantic.parsed_outputs(parser,left['outputs'],spec)
    for variant,source_state in (('independent',state),('teacher_forced',ort_state)):
        feeds=state_feeds(base,source_state,physical)
        if variant=='teacher_forced':
            if state_digest(feeds)!=state_digest(ort_state):raise ValueError('teacher recurrent input differs')
            row['teacher_state_input_exact']=True
        right=session.run(feeds);verify.validate_outputs(right,physical['outputs'])
        verify.advance_state(feeds,right)
        if variant=='independent':pending=next_states(right)
        rp=semantic.parsed_outputs(parser,right['outputs'],spec);semantic.compare_parsed(lp,rp)
        drift={n:{k:v for k,v in semantic.metrics(left[n],right[n]).items() if k in ('max_abs','mean_abs','rmse')}
               for n in left if n.startswith('next_state_')}
        row['variants'][variant]={'state':drift,'hidden':{k:v for k,v in semantic.metrics(hidden(left,spec),hidden(right,spec)).items() if k in ('max_abs','mean_abs','rmse')},
                                 'timing':dict(session.last_timing),'decisions':semantic.decision_changes(lp,rp)}
        payload[variant]=right['outputs']
    return payload,row,pending


def feature_next(previous,hidden):
    if previous.ndim!=3 or previous.shape[1:]!=hidden.shape or previous.dtype!=np.float32 or hidden.dtype!=np.float32:
        raise ValueError('feature feedback shape/dtype mismatch')
    return np.concatenate((previous[1:],hidden[None]),axis=0)


def prove_feature(previous,hidden,actual):
    expected=feature_next(previous,hidden)
    if expected.shape!=actual.shape or expected.dtype!=actual.dtype or array_sha(expected)!=array_sha(actual):
        raise ValueError('actual ORT feature feedback is not byte-exact shift+hidden')


def turnover(rows):
    if not rows or [r['frame'] for r in rows]!=list(range(len(rows))):raise ValueError('noncontiguous drift frames')
    out={'frames':len(rows),'queue_turnover':'PASS' if len(rows)>=129 else 'NOT_REACHED',
         'checkpoints':[r for r in rows if r['frame'] in CHECKPOINTS],
         'infinite_boundedness':'NOT_ESTABLISHED','acceptance':'DIAGNOSTIC_ONLY','classification':'INCONCLUSIVE'}
    if len(rows)>128:
        selected=rows[128:];x=np.array([r['frame'] for r in selected],np.float64)
        width=max(1,len(rows)//4);quarters=[rows[-2*width:-width],rows[-width:]]
        out['window']={'first_frame':128,'last_frame':rows[-1]['frame'],
             **{key+'_slope_per_frame':float(np.polyfit(x,[r[key] for r in selected],1)[0]) if len(x)>1 else None for key in ('mean_abs','rmse')},
             'rolling128':[{'frame':i,'max_abs':max(r['max_abs'] for r in rows[max(0,i-127):i+1]),
                            'p95_frame_mean_abs':float(np.percentile([r['mean_abs'] for r in rows[max(0,i-127):i+1]],95))} for i in range(128,len(rows))],
             'previous_last_quarters':[{k:float(np.mean([r[k] for r in q])) for k in ('max_abs','mean_abs','rmse')} for q in quarters]}
    return out


def validate_recorded_provenance(value):
    if (value.get('evidence')!='RECORDED_INPUT' or not re.fullmatch('[0-9a-f]{64}',value.get('source_sha256',''))
            or type(value.get('frames')) is not int or value['frames']<1
            or not value.get('exact_model_input_reconstruction') or not value.get('authorized_project_source')):
        raise ValueError('recorded provenance/reconstruction/authorization missing')


def write_public(path,value):
    def check(x):
        if isinstance(x,dict):
            for k,v in x.items():
                if re.search(r'(?i)password|passphrase|private_key|credential',k):raise ValueError('private artifact key')
                check(v)
        elif isinstance(x,list):
            for v in x:check(v)
        elif isinstance(x,str):
            if re.search(r'(?i)[a-z]:[/\\]Users[/\\]|/home/[^/]+/|-----BEGIN.*PRIVATE',x):raise ValueError('private artifact path')
            for v in re.findall(r'(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])',x):
                try:a=ipaddress.ip_address(v)
                except ValueError:continue
                if a.is_private and not a.is_loopback and v!='10.3.0.30':raise ValueError('private artifact address')
    check(value);data=json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n'
    with Path(path).open('x',encoding='utf-8') as stream:stream.write(data)


def validate_result_header(value,sequence,frames):
    if (value.get('sequence')!=sequence or value.get('frames')!=frames or value.get('variants')!=VARIANTS
            or value.get('source')!=isolation.V3_IDENTITY or value.get('engine')!=semantic.M1_PLAN):
        raise ValueError('result source/engine/sequence/variant mismatch')


def compact_contract(spec):
    return {n:v for n,v in verify.spec_contract(spec)['outputs'].items() if n!='next_state_feat_q'}


def hidden(values,spec):
    start,stop=spec['output_slices']['hidden_state']
    return values['outputs'][:,start:stop]


def raw_states(contract):
    return {n:np.zeros(v['shape'],v['dtype']) for n,v in contract['inputs'].items() if n.startswith('state_')}


def reference_values(path,entry,state,spec):
    if verify.file_identity(path)!={k:entry[k] for k in ('sha256','nbytes')}:raise ValueError('reference changed')
    values=prior.read_arrays(path,compact_contract(spec))
    values['next_state_feat_q']=feature_next(state['state_feat_q'],hidden(values,spec))
    if array_sha(values['next_state_feat_q'])!=entry['feature_sha256']:raise ValueError('feature reconstruction proof changed')
    verify.validate_outputs(values,verify.spec_contract(spec)['outputs'])
    return values


def next_states(values):
    return {n.replace('next_','',1):v for n,v in values.items() if n.startswith('next_state_')}


def export_ort(args):
    from jetlink import cinque_v3 as v3
    from onnx_meta_light import check_meta_against_spec
    spec=json.loads(args.spec.read_text());v3.validate_spec(spec)
    if verify.file_identity(args.onnx)!=isolation.V3_IDENTITY:raise ValueError('original model identity mismatch')
    check_meta_against_spec(args.onnx,spec)
    parser,provenance=semantic.load_parser(args.parser_source)
    if args.frames not in (257,512):raise ValueError('turnover export must be257 or512 frames')
    if args.out_dir.exists():raise FileExistsError('reference output exists')
    import onnxruntime as ort
    session=verify.ort_session(ort,args.onnx);contract=verify.ort_contract(session)
    verify.validate_contract(contract,verify.spec_contract(spec))
    output=prior.new_directory(args.out_dir);state=raw_states(contract);files=[];names=list(contract['outputs']);start=time.monotonic()
    for frame in range(args.frames):
        feeds=state_feeds(frame_inputs(contract['inputs'],frame,args.sequence),state,contract)
        values=dict(zip(names,session.run(names,feeds)));verify.validate_outputs(values,contract['outputs'])
        prove_feature(state['state_feat_q'],hidden(values,spec),values['next_state_feat_q'])
        semantic.parsed_outputs(parser,values['outputs'],spec)
        p=output/f'frame-{frame:04d}.npz'
        with p.open('xb') as stream:np.savez(stream,**{n:values[n] for n in compact_contract(spec)})
        files.append({'frame':frame,'name':p.name,**verify.file_identity(p),
                      'input_digest':semantic.input_digest(feeds),'feature_sha256':array_sha(values['next_state_feat_q'])})
        state=next_states(values)
        if frame%64==0:print(json.dumps({'progress':'ORT','sequence':args.sequence,'frame':frame}),flush=True)
    manifest={'schema':1,'kind':'m16-compact-exact-ORT','frames':args.frames,'sequence':args.sequence,'seed':SEED,
              'source':isolation.V3_IDENTITY,'spec':spec,'contract':contract,'parser':provenance,'files':files,
              'input_generator':verify.file_identity(Path(verify.__file__)),'bounded_source':BOUNDED_SOURCE,
              'feature_reconstruction':'byte-proven against actual full ORT outputs on every frame',
              'runtime':{'ort':ort.__version__,'providers':session.get_providers(),'numpy':np.__version__},
              'evidence':['ORT_REAL_MODEL','SYNTHETIC_INPUT'],'elapsed_seconds':time.monotonic()-start}
    with (output/'manifest.json').open('x') as stream:json.dump(manifest,stream,indent=2)
    return {'status':'ORT_REFERENCE_COMPLETE','sequence':args.sequence,'frames':args.frames,
            'manifest':verify.file_identity(output/'manifest.json'),'exit_status':0}


def validate_reference(directory,spec,sequence):
    directory=prior.plain_path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    if (manifest.get('schema')!=1 or manifest.get('kind')!='m16-compact-exact-ORT' or manifest.get('sequence')!=sequence
            or manifest.get('frames') not in (257,512) or manifest.get('source')!=isolation.V3_IDENTITY
            or manifest.get('spec')!=spec or manifest.get('contract')!=verify.spec_contract(spec)
            or manifest.get('seed')!=SEED or manifest.get('bounded_source')!=BOUNDED_SOURCE
            or manifest.get('runtime',{}).get('providers')!=['CPUExecutionProvider']
            or manifest.get('input_generator')!=verify.file_identity(Path(verify.__file__))
            or len(manifest.get('files',[]))!=manifest['frames']):raise ValueError('reference metadata mismatch')
    state=raw_states(manifest['contract'])
    for frame,entry in enumerate(manifest['files']):
        if entry.get('frame')!=frame or entry.get('name')!=f'frame-{frame:04d}.npz':raise ValueError('reference ordering mismatch')
        if semantic.input_digest(frame_inputs(manifest['contract']['inputs'],frame,sequence))!=entry['input_digest']:raise ValueError('input sequence changed')
        values=reference_values(prior.plain_path(directory/entry['name']),entry,state,spec);state=next_states(values)
    return manifest


def measure_trt(args):
    root=recurrent.guarded_root(args.development_root);isolation.validate_marker(root)
    engine,spec_path,reference,base,parser_dir=[isolation.inside(root,p) for p in (args.engine,args.spec,args.reference_dir,args.base_report,args.parser_source)]
    if verify.file_identity(engine)!=semantic.M1_PLAN:raise ValueError('exact M1 plan required')
    spec=json.loads(spec_path.read_text());metadata=recurrent.validate_artifact(engine,spec)
    physical=verify.spec_contract(spec,verify.V3_RETYPES)
    prior.validate_base_report(base,semantic.M1_PLAN,physical)
    manifest=validate_reference(reference,spec,args.sequence);parser,provenance=semantic.load_parser(parser_dir)
    if provenance!=manifest['parser']:raise ValueError('parser differs from reference')
    output=recurrent.create_output(root,args.out_dir);recurrent.prepare_environment(output)
    cache=None
    if args.release_private_file_cache:
        # EXACT existing reviewed M15 allowlist and implementation. New reference
        # files are never advised; no expansion or new memory workaround.
        previous=semantic.validate_reference(root/'m15/ort-reference-101',spec)
        entries={'m15/ort-reference-101/'+e['name']:{k:e[k] for k in ('sha256','nbytes')} for e in previous['files']}
        entries.update({'build/cinque-v3.plan':semantic.M1_PLAN,'models/big_driving_supercombo_v3.onnx':isolation.V3_IDENTITY})
        cache=semantic.release_private_cache(root,entries)
        with (output/'cache-preparation.json').open('x') as stream:json.dump(cache,stream,indent=2)
        if cache['memory_after']['MemFree']-cache['memory_before']['MemFree']<735338624:raise ValueError('BLOCKED_MEMORY: original measured-recovery gate')
    state=raw_states(physical);ort_state=raw_states(manifest['contract']);rows=[];files=[]
    session=recurrent.CudaTrtSession(engine,physical,metadata);start=time.monotonic()
    try:
        for frame,entry in enumerate(manifest['files']):
            left=reference_values(prior.plain_path(reference/entry['name']),entry,ort_state,spec)
            base_feeds=frame_inputs(physical['inputs'],frame,args.sequence)
            if semantic.input_digest(base_feeds)!=entry['input_digest']:raise ValueError('physical nonstate inputs differ')
            payload,row,state=paired_step(session,base_feeds,state,ort_state,left,physical,parser,spec)
            row.update(frame=frame,input_digest_match=True)
            p=output/f'frame-{frame:04d}.npz'
            with p.open('xb') as stream:np.savez(stream,**payload)
            files.append({'frame':frame,'name':p.name,**verify.file_identity(p)});rows.append(row)
            ort_state=next_states(left)
            if frame%64==0:print(json.dumps({'progress':'TRT','sequence':args.sequence,'frame':frame}),flush=True)
    finally:session.close()
    report={'schema':1,'status':'MEASURED','exit_status':3,'numerical_decision':'PARITY_UNDETERMINED',
            'sequence':args.sequence,'frames':manifest['frames'],'variants':VARIANTS,'source':isolation.V3_IDENTITY,
            'engine':semantic.M1_PLAN,'trt_version':metadata['trt_version'],'device':metadata['device'],
            'reference_manifest':verify.file_identity(reference/'manifest.json'),'parser_source':provenance,
            'evidence':['ORT_REAL_MODEL','TRT_REAL','JETSON_REAL','SYNTHETIC_INPUT','TEACHER_FORCED_DIAGNOSTIC'],
            'ort_runtime':manifest['runtime'],'input_digest_matches':len(rows),'all_contracts_finite':True,
            'teacher_state_conversion':'all pairs exact; uint8 image->FP16 only; feature/desire float32 unchanged',
            'optimizations':'OFF','installation':'DO_NOT_INSTALL','cache_preparation':cache,
            'elapsed_seconds':time.monotonic()-start,'per_frame':rows,'files':files}
    with (output/'report.json').open('x') as stream:json.dump(report,stream,indent=2)
    return {k:v for k,v in report.items() if k not in ('per_frame','files')}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    export=sub.add_parser('export-ort');measure=sub.add_parser('measure-trt')
    for name in ('onnx','spec','out-dir','parser-source'):export.add_argument('--'+name,type=Path,required=True)
    export.add_argument('--frames',type=int,default=512)
    for name in ('development-root','engine','spec','reference-dir','base-report','out-dir','parser-source'):measure.add_argument('--'+name,type=Path,required=True)
    for command in (export,measure):command.add_argument('--sequence',choices=('historical','bounded'),required=True)
    measure.add_argument('--release-private-file-cache',action='store_true')
    args=p.parse_args(argv)
    try:result=export_ort(args) if args.mode=='export-ort' else measure_trt(args)
    except Exception as e:result={'status':'FAIL','error_type':type(e).__name__,'error':str(e),'exit_status':1,'installation':'DO_NOT_INSTALL'}
    print(json.dumps(result,sort_keys=True),flush=True)
    return result['exit_status']


if __name__=='__main__':raise SystemExit(main())
