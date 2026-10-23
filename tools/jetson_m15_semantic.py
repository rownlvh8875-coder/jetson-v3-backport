#!/usr/bin/env python3
"""101-frame, independent recurrent M1 extension. Measurement only; exit3.

Original ORT CPU export and BASE TRT consumer never install/build/use USB.
Use the M1 owned-worker live offroad guardian for actual device execution.
The unmodified actual Nav parser/constants are hash-pinned before execution.
"""
from __future__ import annotations
import sys
sys.dont_write_bytecode=True
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import stat
import numpy as np
import build_trt_v3 as verify
import jetson_m1 as isolation
import jetson_m1_recurrent as recurrent
import jetson_m1_parity as prior

FRAMES,SEED=101,73
PARSER_HASHES={'parse_model_outputs.py':'45b38da9f929bd59ca28ff9e19f64e8718286ae3ccbeccddb7868ffbcd88fc85',
               'constants.py':'5d597d287df626d08b234a17db05e884302fead646ff4e7f0153079547c8010c'}
PLAN_AXES={'POSITION':slice(0,3),'VELOCITY':slice(3,6),'ACCELERATION':slice(6,9),
           'T_FROM_CURRENT_EULER':slice(9,12),'ORIENTATION_RATE':slice(12,15)}
M1_PLAN={'sha256':'8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa','nbytes':768580676}


def cache_memory():
    return {k:int(line.split()[1])*1024 for line in Path('/proc/meminfo').read_text().splitlines()
            if (k:=line.split(':',1)[0]) in ('MemFree','MemAvailable','Cached','SwapFree')}


def release_private_cache(root,entries):
    """Explicit Linux-only own-file advice; never global cache/config changes.

    Hash each allowlisted file on the SAME pinned read-only FD before advice.
    Metadata is checked after advice; no subsequent content read re-caches it.
    Advisory success does not assert CUDA memory availability.
    """
    root=recurrent.guarded_root(root);isolation.validate_marker(root)
    if not hasattr(os,'posix_fadvise'):raise ValueError('private cache advice unavailable')
    before=cache_memory();count=total=0
    def fingerprint(s):
        return (s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    for name,expected in entries.items():
        allowed=re.fullmatch(r'm15/ort-reference-101/frame-(?:00[0-9][0-9]|0100)\.npz',name)
        if name=='models/big_driving_supercombo_v3.onnx':allowed=expected==isolation.V3_IDENTITY
        if name=='build/cinque-v3.plan':allowed=expected==M1_PLAN
        if not allowed:raise ValueError('private cache target not in exact allowlist')
        p=isolation.inside(root,root/name);info=p.lstat()
        if not stat.S_ISREG(info.st_mode):raise ValueError('private cache target is not a regular file')
        descriptors=[]
        try:
            directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW);descriptors.append(directory)
            device=os.fstat(directory).st_dev
            for part in Path(name).parts[:-1]:
                directory=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory);descriptors.append(directory)
                entry=os.fstat(directory)
                if entry.st_dev!=device or entry.st_uid!=os.getuid() or entry.st_mode&0o022:raise ValueError('private parent ownership/mount mismatch')
            fd=os.open(Path(name).name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory);descriptors.append(fd)
            original=os.fstat(fd)
            if (not stat.S_ISREG(original.st_mode) or original.st_dev!=device or original.st_uid!=os.getuid()
                    or original.st_nlink!=1 or original.st_mode&0o022 or fingerprint(original)!=fingerprint(info)):
                raise ValueError('private file owner/link/mode/inode mismatch')
            digest=hashlib.sha256()
            while block:=os.read(fd,1<<20):digest.update(block)
            if {'sha256':digest.hexdigest(),'nbytes':original.st_size}!=expected:raise ValueError('private file hash/size mismatch')
            if fingerprint(os.fstat(fd))!=fingerprint(original):raise ValueError('private file changed while hashing')
            os.posix_fadvise(fd,0,0,os.POSIX_FADV_DONTNEED)
            if fingerprint(os.fstat(fd))!=fingerprint(original) or fingerprint(p.lstat())!=fingerprint(original):raise ValueError('private file changed during advice')
            count+=1;total+=original.st_size
        finally:
            for fd in reversed(descriptors):os.close(fd)
    return {'advised_files':count,'advised_bytes':total,'memory_before':before,'memory_after':cache_memory(),
            'meaning':'advisory own-file cache release only; not CUDA availability or numerical acceptance'}


def epsilon(reference):
    # One reference-dtype resolution at max(1,maxabs) scale, not an approval bound.
    dtype=reference.dtype
    return (float(np.finfo(dtype).eps)*max(1.,float(np.max(np.abs(reference.astype(np.float64)))))
            if np.issubdtype(dtype,np.floating) else 1.)


def metrics(reference,actual):
    if (not isinstance(reference,np.ndarray) or not isinstance(actual,np.ndarray)
            or reference.shape!=actual.shape or reference.size==0
            or not np.all(np.isfinite(reference)) or not np.all(np.isfinite(actual))):
        raise ValueError('nonfinite, empty or mismatched comparison')
    left,right=reference.astype(np.float64),actual.astype(np.float64)
    error=np.abs(left-right);eps=epsilon(reference)
    result={'reference_dtype':str(reference.dtype),'actual_dtype':str(actual.dtype),'elements':reference.size,
            'reference_min':float(left.min()),'reference_max':float(left.max()),
            'max_abs':float(error.max()),'mean_abs':float(error.mean()),
            'rmse':float(np.sqrt(np.mean(np.square(error)))),
            'p95_abs':float(np.percentile(error,95)),'p99_abs':float(np.percentile(error,99)),
            'relative_denominator_epsilon':eps,'max_relative':float(np.max(error/np.maximum(np.abs(left),eps)))}
    if not all(np.isfinite(v) for v in result.values() if isinstance(v,(float,int))):
        raise ValueError('comparison overflow')
    return result


class Accumulator:
    def __init__(self):self.errors=[];self.rows=[]
    def add(self,left,right):
        row=metrics(left,right);self.rows.append(row)
        self.errors.append(np.abs(left.astype(np.float64)-right.astype(np.float64)).ravel())
        return row
    def finish(self):
        if not self.rows:raise ValueError('empty accumulator')
        error=np.concatenate(self.errors)
        return {'frames':len(self.rows),'elements':int(error.size),
                'reference_dtype':self.rows[0]['reference_dtype'],'actual_dtype':self.rows[0]['actual_dtype'],
                'reference_min':min(r['reference_min'] for r in self.rows),'reference_max':max(r['reference_max'] for r in self.rows),
                'max_abs':float(error.max()),'mean_abs':float(error.mean()),'rmse':float(np.sqrt(np.mean(error*error))),
                'p95_abs':float(np.percentile(error,95)),'p99_abs':float(np.percentile(error,99)),
                'max_relative':max(r['max_relative'] for r in self.rows),
                'epsilon_min':min(r['relative_denominator_epsilon'] for r in self.rows),
                'epsilon_max':max(r['relative_denominator_epsilon'] for r in self.rows)}


def slice_outputs(raw,spec):
    if raw.shape!=(1,spec['output_shapes']['outputs'][1]):raise ValueError('driving shape mismatch')
    result={};expected=0
    for name,(start,stop) in sorted(spec['output_slices'].items(),key=lambda x:x[1]):
        if type(start) is not int or type(stop) is not int or start!=expected or stop<=start:
            raise ValueError('noncontiguous or overlapping semantic slices')
        result[name]=raw[:,start:stop];expected=stop
    if expected!=raw.size:raise ValueError('semantic slices do not cover full output')
    return result


def input_digest(feeds):
    h=hashlib.sha256()
    for name,value in sorted(feeds.items()):
        if name.startswith('state_'):continue
        if name=='new_img':
            if not np.all(np.isfinite(value)) or np.any(value<0) or np.any(value>255) or np.any(value!=value.astype(np.uint8)):
                raise ValueError('non-exact image representation')
            value=value.astype(np.uint8)
        h.update(name.encode()+b'\0'+str(value.shape).encode()+b'\0'+str(value.dtype).encode()+b'\0')
        h.update(np.ascontiguousarray(value).tobytes())
    return h.hexdigest()


def load_parser(directory):
    directory=prior.plain_path(directory);provenance={}
    for name,digest in PARSER_HASHES.items():
        p=prior.plain_path(directory/name);identity=verify.file_identity(p)
        if identity['sha256']!=digest:raise ValueError('actual Nav parser source drift: '+name)
        provenance[name]=identity
    def load(name,filename):
        module_spec=importlib.util.spec_from_file_location(name,directory/filename)
        module=importlib.util.module_from_spec(module_spec);module_spec.loader.exec_module(module)
        return module
    constants=load('_m15_actual_nav_constants','constants.py')
    if any(getattr(constants.Plan,n)!=at for n,at in PLAN_AXES.items()):raise ValueError('plan channel contract drift')
    key='openpilot.selfdrive.modeld.constants';previous=sys.modules.get(key)
    try:
        sys.modules[key]=constants
        module=load('_m15_actual_nav_parser','parse_model_outputs.py')
    finally:
        if previous is None:sys.modules.pop(key,None)
        else:sys.modules[key]=previous
    return module.Parser(),provenance


def parsed_outputs(parser,raw,spec):
    out=parser.parse_outputs({n:v.copy() for n,v in slice_outputs(raw,spec).items()})
    if any(not isinstance(v,np.ndarray) or not np.all(np.isfinite(v)) for v in out.values()):
        raise ValueError('invalid actual parser output')
    return out


def compare_parsed(left,right):
    if set(left)!=set(right):raise ValueError('parser field names mismatch')
    if any(left[n].dtype!=right[n].dtype for n in left):raise ValueError('parser dtype mismatch')
    return {n:metrics(left[n],right[n]) for n in left}


def decision_changes(left,right):
    out={}
    for name in ('desire_state','desire_pred'):
        if name in left:
            out[name+'_argmax_changes']=int(np.count_nonzero(np.argmax(left[name],axis=-1)!=np.argmax(right[name],axis=-1)))
    return out


def drift_summary(rows):
    if not rows:raise ValueError('empty drift series')
    return {'frames':len(rows),'first':rows[0],'last':rows[-1],
            'checkpoints':[r for r in rows if r['frame'] in (0,1,5,10,25,50,100)],
            'max_abs_nondecreasing':all(a['max_abs']<=b['max_abs'] for a,b in zip(rows,rows[1:])),
            'mean_abs_nondecreasing':all(a['mean_abs']<=b['mean_abs'] for a,b in zip(rows,rows[1:])),
            'observed_max_abs':max(r['max_abs'] for r in rows),'observed_max_rmse':max(r['rmse'] for r in rows),
            'infinite_boundedness':'NOT_ESTABLISHED','plateau':'NOT_ESTABLISHED: finite sequence/horizon128',
            'acceptance':'UNDETERMINED'}


def decision_report(_measurements):
    return {'numerical_decision':'PARITY_UNDETERMINED','exit_status':3,
            'parser_parity':'UNDETERMINED: measured without approved tolerance',
            'installation':'DO_NOT_INSTALL','thresholds':'NO_APPROVED_TOLERANCE'}


def export_ort(args):
    from jetlink import cinque_v3 as v3
    from onnx_meta_light import check_meta_against_spec
    spec=json.loads(args.spec.read_text());v3.validate_spec(spec)
    if verify.file_identity(args.onnx)!=isolation.V3_IDENTITY:raise ValueError('original model identity mismatch')
    check_meta_against_spec(args.onnx,spec)
    parser,provenance=load_parser(args.parser_source)
    import onnxruntime as ort
    session=verify.ort_session(ort,args.onnx);contract=verify.ort_contract(session)
    verify.validate_contract(contract,verify.spec_contract(spec))
    output=prior.new_directory(args.out_dir);names=list(contract['outputs']);state={};files=[]
    for frame in range(FRAMES):
        feeds=verify.frame_inputs(contract['inputs'],frame,SEED)
        for n,value in state.items():np.copyto(feeds[n],value,casting='no')
        digest=input_digest(feeds)
        values=dict(zip(names,session.run(names,feeds)));verify.validate_outputs(values,contract['outputs'])
        parsed_outputs(parser,values['outputs'],spec)
        verify.advance_state(feeds,values);state={n:v for n,v in feeds.items() if n.startswith('state_')}
        path=output/f'frame-{frame:04d}.npz'
        with path.open('xb') as f:np.savez(f,**values)
        files.append({'frame':frame,'name':path.name,**verify.file_identity(path),'input_digest':digest})
    manifest={'schema':1,'kind':'m15-cinque-v3-ort-cpu','frames':FRAMES,'seed':SEED,
              'source':isolation.V3_IDENTITY,'spec':spec,'contract':contract,'files':files,
              'input_generator':verify.file_identity(Path(verify.__file__)),'parser':provenance,
              'runtime':{'ort':ort.__version__,'providers':session.get_providers(),'numpy':np.__version__},
              'sequence_limit':'M1 random-noise stress; action_t=frame/20 reaches5s, not vehicle input'}
    (output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return {'status':'ORT_REFERENCE_COMPLETE','frames':FRAMES,'manifest':verify.file_identity(output/'manifest.json'),'exit_status':0}


def validate_reference(directory,spec):
    directory=prior.plain_path(directory);manifest=json.loads((directory/'manifest.json').read_text())
    if (manifest.get('schema')!=1 or manifest.get('kind')!='m15-cinque-v3-ort-cpu'
            or manifest.get('frames')!=FRAMES or manifest.get('seed')!=SEED
            or manifest.get('source')!=isolation.V3_IDENTITY or manifest.get('spec')!=spec
            or manifest.get('input_generator')!=verify.file_identity(Path(verify.__file__))
            or manifest.get('contract')!=verify.spec_contract(spec)
            or manifest.get('runtime',{}).get('providers')!=['CPUExecutionProvider']
            or len(manifest.get('files',[]))!=FRAMES):raise ValueError('reference source/sequence/contract mismatch')
    for frame,entry in enumerate(manifest['files']):
        if entry.get('frame')!=frame or entry.get('name')!=f'frame-{frame:04d}.npz':raise ValueError('reference frame mismatch')
        path=prior.plain_path(directory/entry['name'])
        if verify.file_identity(path)!={n:entry[n] for n in ('sha256','nbytes')}:raise ValueError('reference file changed')
        feeds=verify.frame_inputs(manifest['contract']['inputs'],frame,SEED)
        if input_digest(feeds)!=entry['input_digest']:raise ValueError('nonstate input sequence mismatch')
        prior.read_arrays(path,manifest['contract']['outputs'])
    return manifest


def measure_trt(args):
    root=recurrent.guarded_root(args.development_root);isolation.validate_marker(root)
    engine,spec_path,reference,base,parser_dir=[isolation.inside(root,p) for p in (args.engine,args.spec,args.reference_dir,args.base_report,args.parser_source)]
    spec=json.loads(spec_path.read_text());metadata=recurrent.validate_artifact(engine,spec)
    physical=verify.spec_contract(spec,verify.V3_RETYPES)
    prior.validate_base_report(base,metadata['cinque_v3_record']['engine'],physical)
    manifest=validate_reference(reference,spec);parser,provenance=load_parser(parser_dir)
    if manifest['parser']!=provenance:raise ValueError('parser differs from ORT export')
    output=recurrent.create_output(root,args.out_dir);recurrent.prepare_environment(output)
    cache_preparation=None
    if args.release_private_file_cache:
        entries={'m15/ort-reference-101/'+e['name']:{n:e[n] for n in ('sha256','nbytes')} for e in manifest['files']}
        entries.update({'build/cinque-v3.plan':M1_PLAN,'models/big_driving_supercombo_v3.onnx':isolation.V3_IDENTITY})
        cache_preparation=release_private_cache(root,entries)
        (output/'cache-preparation.json').write_text(json.dumps(cache_preparation,indent=2)+'\n')
        if cache_preparation['memory_after']['MemFree']-cache_preparation['memory_before']['MemFree']<735338624:
            raise ValueError('BLOCKED_MEMORY: no measured recovery of the failed allocation size; no CUDA retry')
    generation=recurrent.Generation(recurrent.CudaTrtSession(engine,physical,metadata),physical)
    raw_acc={n:Accumulator() for n in ['outputs',*spec['output_slices']]};parsed_acc={};channel_acc={}
    rows=[];state_rows={n:[] for n in spec['output_shapes'] if n.startswith('next_state_')}
    try:
        for frame,entry in enumerate(manifest['files']):
            path=prior.plain_path(reference/entry['name'])
            if verify.file_identity(path)!={n:entry[n] for n in ('sha256','nbytes')}:raise ValueError('reference changed during measurement')
            left=prior.read_arrays(path,manifest['contract']['outputs'])
            # Prove actual physical frame generation normalizes to the same raw input.
            if input_digest(verify.frame_inputs(physical['inputs'],frame,SEED))!=entry['input_digest']:raise ValueError('physical frame input mismatch')
            right,timing=generation.step(frame,SEED)
            raw_metrics={'outputs':raw_acc['outputs'].add(left['outputs'],right['outputs'])}
            lviews,rviews=slice_outputs(left['outputs'],spec),slice_outputs(right['outputs'],spec)
            for name in lviews:raw_metrics[name]=raw_acc[name].add(lviews[name],rviews[name])
            lp,rp=parsed_outputs(parser,left['outputs'],spec),parsed_outputs(parser,right['outputs'],spec)
            compare_parsed(lp,rp)
            for name in lp:parsed_acc.setdefault(name,Accumulator()).add(lp[name],rp[name])
            for name in ('plan','plan_stds'):
                for field,at in PLAN_AXES.items():
                    for column in range(at.start,at.stop):
                        key=f'{name}.{field}[{column-at.start}]'
                        channel_acc.setdefault(key,Accumulator()).add(lp[name][...,column],rp[name][...,column])
            for name in state_rows:
                metric=metrics(left[name],right[name])
                state_rows[name].append({'frame':frame,**{k:metric[k] for k in ('max_abs','mean_abs','rmse')}})
            rows.append({'frame':frame,'input_digest_match':True,'raw':raw_metrics,'decisions':decision_changes(lp,rp),'timing':timing})
        result={'schema':1,'status':'MEASURED','frames':FRAMES,'seed':SEED,
                'evidence':['ORT_REAL_MODEL','TRT_REAL','JETSON_REAL','SYNTHETIC_INPUT'],
                'source':isolation.V3_IDENTITY,'engine':metadata['cinque_v3_record']['engine'],
                'trt_version':metadata['trt_version'],'ort_runtime':manifest['runtime'],'parser_source':provenance,
                'relative_policy':'max(abs(reference), dtype_eps*max(1,maxabs(reference per tensor/frame))); integer quantum1; diagnostic not tolerance',
                'raw':{n:a.finish() for n,a in raw_acc.items()},'parsed':{n:a.finish() for n,a in parsed_acc.items()},
                'parsed_plan_channels':{n:a.finish() for n,a in channel_acc.items()},
                'state_drift':{n:{'summary':drift_summary(values),'frames':values} for n,values in state_rows.items()},
                'per_frame':rows,'input_digest_matches':FRAMES,'reference_manifest':verify.file_identity(reference/'manifest.json'),
                'sequence_limit':manifest['sequence_limit'],'all_contracts_finite':True,'optimizations':'OFF',
                'private_file_cache_preparation':cache_preparation,
                **decision_report({})}
    finally:generation.close()
    (output/'report.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    export=sub.add_parser('export-ort');measure=sub.add_parser('measure-trt')
    for name in ('onnx','spec','out-dir','parser-source'):export.add_argument('--'+name,type=Path,required=True)
    for name in ('development-root','engine','spec','reference-dir','base-report','out-dir','parser-source'):measure.add_argument('--'+name,type=Path,required=True)
    measure.add_argument('--release-private-file-cache',action='store_true',help='After a diagnosed own-file-cache pressure failure only: advise exact private files, no global caches/configuration')
    args=p.parse_args(argv)
    try:result=export_ort(args) if args.mode=='export-ort' else measure_trt(args)
    except Exception as e:result={'status':'FAIL','error_type':type(e).__name__,'error':str(e),'exit_status':1,'installation':'DO_NOT_INSTALL'}
    print(json.dumps({k:v for k,v in result.items() if k not in ('per_frame','raw','parsed','parsed_plan_channels','state_drift')}),flush=True)
    return result['exit_status']


if __name__=='__main__':raise SystemExit(main())
