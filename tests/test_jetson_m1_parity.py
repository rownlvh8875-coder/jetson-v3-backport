"""CPU-only tests for reference exchange and independent recurrent measurement."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace as NS

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]


def module():
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        spec = importlib.util.spec_from_file_location('m1_parity', ROOT / 'tools/jetson_m1_parity.py')
        loaded = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(loaded)
        return loaded
    finally:
        sys.path.pop(0)


def test_help_does_not_require_cuda_trt_or_ort():
    result = subprocess.run([sys.executable, str(ROOT / 'tools/jetson_m1_parity.py'), '--help'],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert 'export-ort' in result.stdout and 'measure-trt' in result.stdout


@pytest.fixture
def parity():
    sys.path.insert(0, str(ROOT / 'tools'))
    try:
        yield module()
    finally:
        sys.path.pop(0)


@pytest.fixture
def contracts():
    inputs = {'new_img': {'shape': [2], 'dtype': 'uint8'},
              'desire': {'shape': [8], 'dtype': 'float32'},
              'traffic_convention': {'shape': [1, 2], 'dtype': 'float32'},
              'action_t': {'shape': [1, 2], 'dtype': 'float32'},
              'state_img_q': {'shape': [2], 'dtype': 'uint8'},
              'state_desire_q': {'shape': [2], 'dtype': 'float32'},
              'state_feat_q': {'shape': [2], 'dtype': 'float32'}}
    outputs = {'outputs': {'shape': [2], 'dtype': 'float32'},
               'next_state_img_q': {'shape': [2], 'dtype': 'uint8'},
               'next_state_desire_q': {'shape': [2], 'dtype': 'float32'},
               'next_state_feat_q': {'shape': [2], 'dtype': 'float32'}}
    raw = {'inputs': inputs, 'outputs': outputs}
    physical = copy.deepcopy(raw)
    physical['inputs']['new_img']['dtype'] = 'float16'
    physical['inputs']['state_img_q']['dtype'] = 'float16'
    physical['outputs']['next_state_img_q']['dtype'] = 'float16'
    return raw, physical


class Backend:
    def __init__(self, contract, increment=1):
        self.contract, self.increment = contract, increment
        self.seen, self.closed = [], False
        self.last_timing = {'gpu_execute_ms': 1.}

    def run(self, feeds):
        self.seen.append(float(feeds['state_feat_q'][0]))
        result = {n: np.zeros(v['shape'], v['dtype']) for n, v in self.contract['outputs'].items()}
        for n in ('state_img_q', 'state_desire_q', 'state_feat_q'):
            result['next_' + n] = feeds[n] + np.array(self.increment, dtype=feeds[n].dtype)
        result['outputs'].fill(feeds['state_feat_q'][0])
        return result

    def close(self): self.closed = True


def make_reference(parity, tmp_path, contracts):
    raw, _ = contracts
    backend = Backend(raw)
    manifest = parity.export_sequence(backend.run, raw, tmp_path / 'reference', 'fake-ort', ['CPUExecutionProvider'])
    assert backend.seen == [0., 1., 2., 3., 4.]
    return tmp_path / 'reference', manifest


def test_reference_roundtrip_is_no_pickle_and_binds_each_file(parity, tmp_path, contracts):
    reference, manifest = make_reference(parity, tmp_path, contracts)
    checked = parity.validate_reference(reference, contracts[0])
    assert checked['frames'] == 5 and checked['seed'] == 73
    assert checked['files'] == manifest['files']
    assert len(list(reference.glob('*.npz'))) == 5
    for entry in manifest['files']:
        with np.load(reference / entry['name'], allow_pickle=False) as arrays:
            assert arrays['next_state_feat_q'].dtype == np.float32
            assert arrays['next_state_img_q'].dtype == np.uint8
    with pytest.raises(FileExistsError):
        parity.export_sequence(Backend(contracts[0]).run, contracts[0], reference, 'fake', ['CPUExecutionProvider'])


@pytest.mark.parametrize('fault', ['bytes', 'path', 'dtype', 'shape', 'nonfinite', 'pickle', 'missing'])
def test_corrupt_reference_is_rejected_before_trt_session(parity, tmp_path, contracts, fault):
    reference, manifest = make_reference(parity, tmp_path, contracts)
    entry = manifest['files'][0]
    file = reference / entry['name']
    if fault == 'bytes': file.write_bytes(b'corrupt')
    elif fault == 'path': entry['name'] = '../escape.npz'
    else:
        with np.load(file, allow_pickle=False) as source:
            arrays = {n: source[n].copy() for n in source.files}
        if fault == 'dtype': arrays['next_state_feat_q'] = arrays['next_state_feat_q'].astype(np.float16)
        elif fault == 'shape': arrays['outputs'] = arrays['outputs'].reshape(1, 2)
        elif fault == 'nonfinite': arrays['outputs'][0] = np.nan
        elif fault == 'pickle': arrays['outputs'] = np.array([{'forbidden': 1}], dtype=object)
        else: arrays.pop('next_state_feat_q')
        np.savez(file, **arrays)
        entry.update(parity.verify.file_identity(file))
    (reference / 'manifest.json').write_text(json.dumps(manifest))
    with pytest.raises((ValueError, OSError)):
        parity.validate_reference(reference, contracts[0])


def test_recurrent_measurement_keeps_independent_states_and_no_threshold(parity, tmp_path, contracts):
    reference, manifest = make_reference(parity, tmp_path, contracts)
    backend = Backend(contracts[1], increment=2)
    report = parity.measure_sequence(lambda: backend, contracts[1], reference, manifest)
    assert backend.seen == [0., 2., 4., 6., 8.]
    assert backend.closed
    assert report['status'] == 'MEASURED_NO_ACCEPTANCE'
    assert report['exit_status'] == 3
    assert report['acceptance'] == 'UNDETERMINED: no established tolerance'
    assert report['frames'][0]['tensors']['next_state_feat_q']['max_abs'] == 1.
    assert report['frames'][4]['tensors']['next_state_feat_q']['max_abs'] == 5.
    assert report['frames'][4]['tensors']['next_state_feat_q']['max_abs_minus_first_frame'] == 4.
    assert report['frames'][4]['tensors']['outputs']['max_abs'] == 4.


def test_exact_measurement_still_has_no_acceptance(parity, tmp_path, contracts):
    reference, manifest = make_reference(parity, tmp_path, contracts)
    backend = Backend(contracts[1])
    report = parity.measure_sequence(lambda: backend, contracts[1], reference, manifest)
    assert report['exit_status'] == 3
    assert report['aggregate']['next_state_feat_q']['maximum_max_abs'] == 0.


def test_failed_trt_output_closes_generation(parity, tmp_path, contracts):
    reference, manifest = make_reference(parity, tmp_path, contracts)
    backend = Backend(contracts[1])
    plain = backend.run
    def bad(feeds):
        result = plain(feeds)
        result['outputs'][0] = np.inf
        return result
    backend.run = bad
    with pytest.raises(ValueError):
        parity.measure_sequence(lambda: backend, contracts[1], reference, manifest)
    assert backend.closed


@pytest.mark.parametrize('fault', ['status', 'engine', 'source', 'finite', 'reset', 'reload', 'contract', 'evidence', 'mode'])
def test_base_pass_must_belong_to_same_engine_and_contract(parity, tmp_path, contracts, fault):
    engine = {'sha256': 'a' * 64, 'nbytes': 1}
    report = {'status': 'PASS', 'evidence': 'TRT_REAL/SYNTHETIC', 'engine': engine,
              'mode': 'BASE/all-state-host-roundtrip/no-CUDA-graph',
              'source': parity.isolation.V3_IDENTITY, 'contract': contracts[1],
              'all_outputs_exact_contract_and_finite': True, 'reset_first_frame_exact': True,
              'reload_first_frame_exact': True, 'stress': {'frames': 1000}, 'smoke': {'frames': 10}}
    if fault == 'status': report['status'] = 'FAIL'
    elif fault == 'engine': report['engine'] = {'sha256': 'b' * 64, 'nbytes': 1}
    elif fault == 'source': report['source'] = {}
    elif fault == 'finite': report['all_outputs_exact_contract_and_finite'] = False
    elif fault == 'reset': report['reset_first_frame_exact'] = False
    elif fault == 'reload': report['reload_first_frame_exact'] = False
    elif fault == 'contract': report['contract'] = {}
    elif fault == 'evidence': report['evidence'] = 'CPU_FAKE'
    else: report['mode'] = 'DeviceState/optimized'
    file = tmp_path / 'base.json'
    file.write_text(json.dumps(report))
    with pytest.raises(ValueError): parity.validate_base_report(file, engine, contracts[1])


def test_valid_base_pass_is_accepted(parity, tmp_path, contracts):
    engine = {'sha256': 'a' * 64, 'nbytes': 1}
    report = {'status': 'PASS', 'evidence': 'TRT_REAL/SYNTHETIC', 'engine': engine,
              'mode': 'BASE/all-state-host-roundtrip/no-CUDA-graph',
              'source': parity.isolation.V3_IDENTITY, 'contract': contracts[1],
              'all_outputs_exact_contract_and_finite': True, 'reset_first_frame_exact': True,
              'reload_first_frame_exact': True, 'stress': {'frames': 1000}, 'smoke': {'frames': 10}}
    path = tmp_path / 'base.json'
    path.write_text(json.dumps(report))
    assert parity.validate_base_report(path, engine, contracts[1])['stress']['frames'] == 1000


def test_export_full_source_identity_is_checked_before_ort_import(parity, tmp_path, monkeypatch):
    from jetlink import cinque_v3 as v3
    source, spec = tmp_path / 'wrong.onnx', tmp_path / 'spec.json'
    source.write_bytes(b'not the approved 766MB graph')
    spec.write_text(json.dumps(v3.CANONICAL_SPEC))
    def forbid_import(name): pytest.fail('wrong source must fail before ORT import')
    monkeypatch.setattr(parity.importlib, 'import_module', forbid_import)
    with pytest.raises(ValueError, match='hash/size'):
        parity.export_ort(source, spec, tmp_path / 'reference')
    assert not (tmp_path / 'reference').exists()


def test_measure_mode_does_not_import_ort(parity, tmp_path, contracts, monkeypatch):
    reference, manifest = make_reference(parity, tmp_path, contracts)
    monkeypatch.setitem(sys.modules, 'onnxruntime', None)
    report = parity.measure_sequence(lambda: Backend(contracts[1]), contracts[1], reference, manifest)
    assert report['exit_status'] == 3
