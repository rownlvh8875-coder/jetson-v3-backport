#!/usr/bin/env python3
"""CPU_HOST_BENCH: incremental observer vs real810e shared-slot bookkeeping.

Synthetic host bytes only. No QCOM, camera, USB, model, device or acceptance
threshold. Both baseline and observed cases include begin/copy/token/read/reply
completion; the observed case additionally copies into the bounded recorder.
"""
from __future__ import annotations
import argparse
import ast
from dataclasses import dataclass
import importlib
import json
import math
import os
from pathlib import Path
import platform
import socket
import sys
import tempfile
import time
import types
import numpy as np

if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
sys.dont_write_bytecode=True
from adapters.carrot import recorder_810e as r
from tools.benchmark_v3_input_recorder import percentile_ns, rss_kib


def run(reference, root, frames=512):
    source=r.sources(reference);files=r.recorder_files(reference)
    folder=root/'bench810';folder.mkdir()
    for name in r.PACKAGE_FILES:(folder/name).write_bytes(files[r.PACKAGE+'/'+name])
    sys.path.insert(0,str(root))
    try:
        hook=importlib.import_module('bench810.hook')
        runtime=importlib.import_module('bench810.recorder')
        f=importlib.import_module('bench810.format')
        shared=types.ModuleType('bench_shared')
        exec(compile(source['openpilot/selfdrive/modeld/jetlink/shared_input.py'],'<exact810-shared>','exec'),shared.__dict__)
        # size/shape interface exactly matches reviewed N16; no runtime behavior
        # is replaced in Reader/Writer. Spec audit and wire tests use ModelSpec.
        spec=types.SimpleNamespace(warped_nbytes=393216,packed_nbytes=262380,
                                   warped_shape=(2,6,128,256),packed_nelem=65595)
        a,b=socket.socketpair()
        reader=shared.Reader.offer(a,spec);a.sendall(reader.nonce)
        writer=shared.Writer.receive(b,spec,lambda sock,deadline:sock.recv(16),time.monotonic()+.15)
        a.close();b.close()
        value=dict(capture_id='c'*32,source_model_sha=r.NAV_MODEL_SHA,source_spec_sha=r.NAV_SPEC_SHA)
        rec=runtime.Recorder(root/'dataset',hook._provenance(value),frames=frames,depth=4,measure=True)
        sm=types.ModuleType('_bench810_spec');sys.modules[sm.__name__]=sm
        sm.__dict__.update(dataclass=dataclass,math=math,STATEFUL_FRAME='new_img',DEFAULT_FRAME_SKIP=4)
        node=next(n for n in ast.parse(source['third_party/jetlink/jetlink/spec.py']).body
                  if isinstance(n,ast.ClassDef) and n.name=='ModelSpec')
        exec(compile(ast.Module(body=[node],type_ignores=[]),'<exact810-ModelSpec>','exec',flags=__import__('__future__').annotations.compiler_flag),sm.__dict__)
        nav=sm.ModelSpec.from_dict(json.loads(source[r.SPEC_FILE]))
        client=types.SimpleNamespace(spec=nav,_v3_capture_contract=hook._contract(nav,value))
        capture=hook._Capture(rec,dict(value,frames=frames))
        try:
            deadline=time.monotonic()+8
            while not rec.ready and rec.reason is None and time.monotonic()<deadline:
                rec.poll();time.sleep(.001)
            if not rec.ready:raise RuntimeError('writer startup')
            pixels=np.zeros((2,6,128,256),np.uint8);packed=np.zeros(65595,np.float32)
            baseline=[];observed=[];observer=[];peak_rss=0
            start=time.perf_counter()
            for index in range(frames):
                # Benchmark pacing never occurs inside the production observer.
                time.sleep(max(0,start+index/20-time.perf_counter()))
                pixels[:]=index%256;packed[:12]=index
                for enabled,results in ((False,baseline),(True,observed)):
                    stamp=1_000_000_000+index*50_000_000
                    meta=dict(main_frame_id=index,extra_frame_id=index,model_timestamp_ns=stamp,
                        monotonic_ns=stamp+1,main_sof_ns=stamp,extra_sof_ns=stamp,selection=(0,0),
                        transforms=(np.eye(3,dtype=np.float32),np.eye(3,dtype=np.float32)),flags=int(index==0))
                    begin=time.perf_counter_ns()
                    image=writer.begin();np.copyto(image,pixels)
                    if enabled:
                        frame=types.SimpleNamespace(frame_id=index,timestamp_sof=stamp)
                        capture.pair=(frame,frame,(0,0));capture.transforms=meta['transforms'];capture.warped=image
                        before=time.perf_counter_ns()
                        capture.observe(client,image,packed,index==0)
                        if rec.count!=index+1 or rec.reason is not None:
                            raise RuntimeError('observer stopped: '+str(rec.reason))
                        observer.append(time.perf_counter_ns()-before)
                    token=writer.token(image,packed,index,0,stamp)
                    reader.read(token);writer.complete()
                    results.append(time.perf_counter_ns()-begin)
                peak_rss=max(peak_rss,rss_kib(rec.process.pid))
            rec.close(timeout=10)
            if rec.reason is not None:raise RuntimeError(rec.reason)
            with r.dataset_class(reference)(root/'dataset') as dataset:
                if len(dataset)!=frames:raise RuntimeError('incomplete benchmark')
                digest=dataset.manifest['dataset_digest']
            stats=lambda values:dict(percentile_ns(values),max_us=max(values)/1000,mean_us=float(np.mean(values)/1000))
            return dict(classification='CPU_HOST_BENCH',input='SYNTHETIC_FIXTURE',frames=frames,target_hz=20,
                shared_baseline=stats(baseline),shared_plus_observer=stats(observed),observer_only=stats(observer),
                paired_increment=stats(np.array(observed)-baseline),copy=stats(rec.copy_ns),queue=stats(rec.put_ns),
                high_water=rec.high_water,depth=4,ring_bytes=runtime.CONTROL_BYTES+4*f.RECORD_BYTES,
                dataset_bytes=f.expected_size(frames),writer_sampled_rss_kib=peak_rss,
                elapsed_s=time.perf_counter()-start,dataset_digest=digest,strict_reader='PASS',
                caveat='Paired baseline always runs first; host scheduling/cache diagnostic, not device realtime acceptance',
                measured_observer='Full generated _Capture.observe including spec snapshots, metadata, copy and queue; excludes receive/Warp wrapper bookkeeping',
                comma_real_performance='NOT_MEASURED',python=platform.python_version(),numpy=np.__version__)
        finally:
            rec.close(timeout=10);writer.close();reader.close()
    finally:sys.path.remove(str(root))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():parser.error('output collision')
    with tempfile.TemporaryDirectory(prefix='recorder810-host-') as temporary:
        result=run(args.reference,Path(temporary))
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
