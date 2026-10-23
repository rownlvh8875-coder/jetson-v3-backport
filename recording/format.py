"""Fixed little-endian V3 nonstate capture format; no model/device imports."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import re
import struct
import numpy as np

BASE_SHA='366d6eae9aa9962104391e1d997fe956dea8f64d'
TARGET_SHA='404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4'
SPEC_DIGEST='6905b3d4efd18caf3df8c02898e9f3003a5adb11813a277f627b1decea8304e0'
INPUTS={'new_img':((2,6,128,256),'|u1'),'desire':((8,),'<f4'),
        'traffic_convention':((1,2),'<f4'),'action_t':((1,2),'<f4')}
RECORD_DTYPE=np.dtype([(n,'<u8') for n in ('index','main_frame_id','extra_frame_id','model_timestamp_ns','monotonic_ns','main_sof_ns','extra_sof_ns')]+
    [('flags','<u4'),('selection','u1',(2,)),('reserved','<u2'),('transforms','<f4',(2,3,3)),('expected_interval_ns','<u8')]+
    [(n,d,s) for n,(s,d) in INPUTS.items()],align=False)
RECORD_BYTES=RECORD_DTYPE.itemsize
HEADER_BYTES=4096
MAGIC=b'JLV3CAP1'
MAX_FRAMES=1024
EXPECTED_INTERVAL_NS=50_000_000
PROVENANCE_KEYS={'carrot_head','recorder_source_sha','source_model_sha','source_spec_sha','source_kind','capture_id','source_files'}


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def validate_provenance(value):
    if not isinstance(value,dict) or set(value)!=PROVENANCE_KEYS:raise ValueError('provenance allowlist')
    if value['carrot_head']!=BASE_SHA or value['source_kind']!='existing_jetlink_nonstate':raise ValueError('source pin/kind')
    for n in ('recorder_source_sha','source_model_sha','source_spec_sha'):
        if not isinstance(value[n],str) or re.fullmatch('[0-9a-f]{64}',value[n]) is None:raise ValueError('source SHA')
    if not isinstance(value['capture_id'],str) or re.fullmatch('[0-9a-f]{32}',value['capture_id']) is None:raise ValueError('anonymous capture ID')
    if not isinstance(value['source_files'],dict) or not value['source_files']:raise ValueError('source files')
    for name,sha in value['source_files'].items():
        if name not in ('__init__.py','format.py','recorder.py','dataset.py','hook.py') or not isinstance(sha,str) or re.fullmatch('[0-9a-f]{64}',sha) is None:
            raise ValueError('source file identity')
    if hashlib.sha256(canonical(value['source_files'])).hexdigest()!=value['recorder_source_sha']:
        raise ValueError('recorder source digest mismatch')
    return value


def expected_size(capacity):
    if type(capacity) is not int or not 1<=capacity<=MAX_FRAMES:raise ValueError('frame cap')
    return HEADER_BYTES+RECORD_BYTES*capacity


def header_bytes(provenance,capacity):
    expected_size(capacity);validate_provenance(provenance)
    body=canonical({'schema':1,'format':'jetlink-v3-input-v1','capacity':capacity,'record_bytes':RECORD_BYTES,
                    'spec_digest':SPEC_DIGEST,'target_sha256':TARGET_SHA,'provenance':provenance})
    prefix=MAGIC+struct.pack('<I',len(body))
    if len(prefix)+len(body)>HEADER_BYTES:raise ValueError('oversized header')
    return prefix+body+bytes(HEADER_BYTES-len(prefix)-len(body))


def parse_header(raw):
    if len(raw)!=HEADER_BYTES or raw[:8]!=MAGIC:raise ValueError('header magic/length')
    size=struct.unpack('<I',raw[8:12])[0]
    if not 0<size<=HEADER_BYTES-12 or any(raw[12+size:]):raise ValueError('header size/padding')
    value=json.loads(raw[12:12+size]);expected=header_bytes(value['provenance'],value['capacity'])
    if expected!=raw:raise ValueError('header contract/canonical mismatch')
    return value


def validate_record(record,previous=None):
    if record.dtype!=RECORD_DTYPE or record.shape not in ((),):raise ValueError('record dtype/shape')
    if int(record['reserved']) or int(record['flags']) & ~1:raise ValueError('invalid/gap flags')
    if list(record['selection']) not in ([0,0],[0,1]):raise ValueError('camera roles')
    if int(record['expected_interval_ns'])!=EXPECTED_INTERVAL_NS:raise ValueError('expected cadence')
    for name in ('model_timestamp_ns','monotonic_ns','main_sof_ns','extra_sof_ns'):
        if int(record[name])<=0:raise ValueError('missing timestamp')
    for name in ('desire','traffic_convention','action_t','transforms'):
        if not np.all(np.isfinite(record[name])):raise ValueError('nonfinite '+name)
    if previous is None:
        if int(record['index'])!=0:raise ValueError('initial frame index')
    else:
        if int(record['flags']) & 1:raise ValueError('CONTINUITY reset')
        for name in ('index','main_frame_id','extra_frame_id'):
            if int(record[name])!=int(previous[name])+1:raise ValueError('CONTINUITY '+name)
        for name in ('model_timestamp_ns','monotonic_ns','main_sof_ns','extra_sof_ns'):
            if int(record[name])<=int(previous[name]):raise ValueError('CONTINUITY timestamp')
        if not np.array_equal(record['selection'],previous['selection']):raise ValueError('CONTINUITY camera selection')


def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1<<20),b''):h.update(block)
    return h.hexdigest()


def dataset_digest(manifest):
    return hashlib.sha256(canonical({k:v for k,v in manifest.items() if k!='dataset_digest'})).hexdigest()
