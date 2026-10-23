#!/usr/bin/env python3
"""Offline CPU_HOST_BENCH only; writes temporary synthetic tensors, never devices."""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import resource
import tempfile
import time
import numpy as np
from recording import format as f
from recording.dataset import Dataset
from recording.recorder import Recorder, CONTROL_BYTES


def percentile_ns(values):
    return {f'p{p}_us':float(np.percentile(values,p)/1000) for p in (50,95,99)}


def rss_kib(pid):
    try:
        for line in Path(f'/proc/{pid}/status').read_text().splitlines():
            if line.startswith('VmRSS:'):return int(line.split()[1])
    except (OSError,ValueError):pass
    return 0


def run(root,frames,depth,hz):
    provenance=dict(carrot_head=f.BASE_SHA,recorder_source_sha=hashlib.sha256(f.canonical({'recorder.py':'4'*64})).hexdigest(),source_model_sha='2'*64,
                    source_spec_sha='3'*64,source_kind='existing_jetlink_nonstate',
                    capture_id=f'{depth:032x}',source_files={'recorder.py':'4'*64})
    recorder=Recorder(root/f'depth{depth}-{hz}',provenance,frames=frames,depth=depth,measure=True)
    deadline=time.monotonic()+15
    while not recorder.ready and recorder.reason is None and time.monotonic()<deadline:
        recorder.poll();time.sleep(.001)
    if not recorder.ready:raise RuntimeError('writer startup')
    tensors={n:np.zeros(s,dtype=d) for n,(s,d) in f.INPUTS.items()}
    observer=[];start=time.perf_counter();high_water=0
    writer_rss=rss_kib(recorder.process.pid)
    for index in range(frames):
        if hz:
            time.sleep(max(0,start+index/hz-time.perf_counter()))
        else:
            # Throughput-only producer pacing is outside observer, never in model hook.
            while not recorder.free and recorder.reason is None:
                recorder.poll();time.sleep(.0001)
        tensors['new_img'].fill(index%256)
        ns=1_000_000_000+index*f.EXPECTED_INTERVAL_NS
        metadata=dict(main_frame_id=index,extra_frame_id=index,model_timestamp_ns=ns,
            monotonic_ns=ns+1,main_sof_ns=ns,extra_sof_ns=ns,flags=int(index==0),
            selection=(0,0),transforms=(np.eye(3,dtype=np.float32),np.eye(3,dtype=np.float32)))
        before=time.perf_counter_ns()
        accepted=recorder.observe(**tensors,metadata=metadata)
        observer.append(time.perf_counter_ns()-before)
        high_water=max(high_water,recorder.high_water)
        if not accepted:raise RuntimeError('recording failed: '+str(recorder.reason))
        # Benchmark instrumentation only, outside the measured observer call.
        writer_rss=max(writer_rss,rss_kib(recorder.process.pid))
    recorder.close(timeout=15);elapsed=time.perf_counter()-start
    if recorder.reason is not None:raise RuntimeError('writer failed: '+str(recorder.reason))
    with Dataset(root/f'depth{depth}-{hz}') as dataset:
        if len(dataset)!=frames:raise RuntimeError('frame count')
        digest=dataset.manifest['dataset_digest']
    return dict(frames=frames,depth=depth,target_hz=hz,elapsed_s=elapsed,high_water=high_water,
        ring_bytes=CONTROL_BYTES+depth*f.RECORD_BYTES,dataset_bytes=f.expected_size(frames),
        copy=percentile_ns(recorder.copy_ns),queue_send=percentile_ns(recorder.put_ns),
        observe=percentile_ns(observer),effective_payload_mib_s=frames*f.RECORD_BYTES/elapsed/2**20,
        writer_sampled_peak_rss_kib=writer_rss,dataset_digest=digest,exact_validation='PASS')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('refusing output collision')
    with tempfile.TemporaryDirectory(prefix='v3-recorder-host-bench-') as temporary:
        root=Path(temporary)
        sustained=run(root,512,4,20)
        throughput=[run(root,128,depth,0) for depth in (4,8,16)]
    result=dict(classification='CPU_HOST_BENCH',input='SYNTHETIC_FIXTURE',
        python=platform.python_version(),numpy=np.__version__,architecture=platform.machine(),
        os=platform.system(),sustained_20hz=sustained,writer_throughput=throughput,
        parent_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        children_lifetime_peak_rss_kib=resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        rss_note='Lifetime peaks include reader mappings and pre-exec inheritance; per-run writer RSS is sampled after exec.',
        comma_real_performance='NOT_MEASURED')
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
