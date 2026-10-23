"""FIXTURE: on-disk contract, never actual capture evidence."""
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest
from recording import format as f


def provenance():
    sources={'recorder.py':'a'*64}
    return {'carrot_head':f.BASE_SHA,'recorder_source_sha':hashlib.sha256(f.canonical(sources)).hexdigest(),'source_model_sha':'b'*64,
            'source_spec_sha':'c'*64,'source_kind':'existing_jetlink_nonstate',
            'capture_id':'d'*32,'source_files':{'recorder.py':'a'*64}}


def test_recorder_source_digest_binds_source_file_hashes():
    value=provenance();value['recorder_source_sha']='f'*64
    with pytest.raises(ValueError,match='source digest'):f.validate_provenance(value)


def record(index=0):
    r=np.zeros((),f.RECORD_DTYPE)
    for name,value in {'index':index,'main_frame_id':100+index,'extra_frame_id':200+index,
                       'model_timestamp_ns':1_000_000_000+index*50_000_000,'monotonic_ns':2_000_000_000+index*50_000_000,
                       'main_sof_ns':1_000_000_000+index*50_000_000,'extra_sof_ns':1_001_000_000+index*50_000_000,
                       'expected_interval_ns':50_000_000}.items():r[name]=value
    r['selection']=[0,1];r['transforms'][:]=np.eye(3,dtype=np.float32)
    r['traffic_convention'][:]=[1,0]
    return r


def test_contract_matches_authoritative_spec_and_fixed_sizes():
    spec=json.loads((Path(__file__).resolve().parents[1]/'artifacts/cinque_v3.json').read_text())
    assert hashlib.sha256(f.canonical(spec)).hexdigest()==f.SPEC_DIGEST
    for name,(shape,dtype) in f.INPUTS.items():
        assert tuple(spec['input_shapes'][name])==shape and np.dtype(spec['input_dtypes'][name])==np.dtype(dtype)
    assert f.RECORD_BYTES==393408 and f.RECORD_DTYPE.fields['new_img'][1]==144
    assert f.expected_size(512)==201428992
    assert f.expected_size(256)==100716544


def test_header_is_exact_little_endian_and_rejects_private_provenance():
    value=f.header_bytes(provenance(),512)
    assert len(value)==4096 and f.parse_header(value)['capacity']==512
    with pytest.raises(ValueError):f.header_bytes({**provenance(),'route':'private'},256)
    with pytest.raises(ValueError):f.parse_header(b'bad'+value[3:])
    with pytest.raises(ValueError):f.header_bytes(provenance(),1025)


def test_record_preserves_bits_and_complete_continuity():
    a=record();a['new_img'].flat[:256]=np.arange(256,dtype=np.uint8)
    a['action_t'][:]=np.array([[-0.,np.nextafter(np.float32(.2),np.float32(1))]],np.float32)
    b=np.frombuffer(a.tobytes(),f.RECORD_DTYPE)[0]
    f.validate_record(b,None);f.validate_record(record(1),b)
    for name in f.INPUTS:assert a[name].tobytes()==b[name].tobytes()
    bad=record(1);bad['main_frame_id']+=1
    with pytest.raises(ValueError,match='CONTINUITY'):f.validate_record(bad,b)


@pytest.mark.parametrize('change',[('action_t',float('nan')),('desire',float('inf')),('flags',2),('reserved',1)])
def test_invalid_record_cannot_be_approved(change):
    r=record();r[change[0]]=change[1]
    with pytest.raises(ValueError):f.validate_record(r,None)
