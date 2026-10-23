"""Offline synthetic FIXTURE checks; these are never real capture evidence."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
import pytest

from recording import format as f


def fixture_record(index, interval=50_000_000):
    value = np.zeros((), f.RECORD_DTYPE)
    for name, item in {
        'index': index, 'main_frame_id': 100 + index, 'extra_frame_id': 200 + index,
        'model_timestamp_ns': 1_000_000_000 + index * interval,
        'monotonic_ns': 2_000_000_000 + index * interval,
        'main_sof_ns': 1_000_000_000 + index * interval,
        'extra_sof_ns': 1_001_000_000 + index * interval,
        'expected_interval_ns': 50_000_000,
    }.items():
        value[name] = item
    value['selection'] = [0, 1]
    value['transforms'] = np.eye(3, dtype=np.float32)
    value['new_img'].flat[:] = np.arange(value['new_img'].size, dtype=np.uint32) % 256
    value['desire'] = np.array([-0., 0., 1., 0., 0., 0., 0., 0.], '<f4')
    value['traffic_convention'] = [[1., -0.]]
    value['action_t'] = [[-0., np.nextafter(np.float32(.2), np.float32(1))]]
    return value


def fixture_provenance():
    return {'carrot_head': f.BASE_SHA, 'recorder_source_sha': hashlib.sha256(f.canonical({'recorder.py':'a'*64})).hexdigest(),
            'source_model_sha': 'b' * 64, 'source_spec_sha': 'c' * 64,
            'source_kind': 'existing_jetlink_nonstate', 'capture_id': 'd' * 32,
            'source_files': {'recorder.py': 'a' * 64}}


def publish_manifest(path, manifest):
    manifest['dataset_digest'] = f.dataset_digest(manifest)
    encoded = f.canonical(manifest)
    (path / 'manifest.json').write_bytes(encoded)
    marker = path / 'COMPLETE'
    if marker.exists():
        marker.unlink()
    os.link(path / 'manifest.json', marker)


def fixture_dataset(tmp_path, count=3, interval=50_000_000):
    path = tmp_path / 'synthetic-fixture'
    path.mkdir()
    records = [fixture_record(i, interval) for i in range(count)]
    provenance = fixture_provenance()
    (path / 'frames.bin').write_bytes(f.header_bytes(provenance, count) + b''.join(r.tobytes() for r in records))
    diagnostic = interval if count > 1 else 0
    manifest = {'schema': 1, 'kind': 'v3-logical-input-dataset', 'status': 'COMPLETE',
                'expected_frames': count, 'frames': count, 'continuity': 'CONTIGUOUS',
                'spec_digest': f.SPEC_DIGEST, 'target_sha256': f.TARGET_SHA,
                'provenance': provenance,
                'inputs': {name: {'shape': list(shape), 'dtype': dtype} for name, (shape, dtype) in f.INPUTS.items()},
                'files': {'frames.bin': {'bytes': f.expected_size(count), 'sha256': f.file_sha(path / 'frames.bin')}},
                'capture_start_ns': int(records[0]['monotonic_ns']),
                'capture_end_ns': int(records[-1]['monotonic_ns']),
                'interval_diagnostic': {'expected_ns': 50_000_000, 'min_ns': diagnostic, 'max_ns': diagnostic,
                                        'p50_ns': float(diagnostic), 'p95_ns': float(diagnostic), 'p99_ns': float(diagnostic)},
                'no_gps_raw_camera': True, 'state_tensors_stored': False}
    publish_manifest(path, manifest)
    return path, manifest, records


def rewrite_records(path, manifest, records):
    (path / 'frames.bin').write_bytes(f.header_bytes(manifest['provenance'], len(records)) + b''.join(r.tobytes() for r in records))
    manifest['files']['frames.bin']['bytes'] = (path / 'frames.bin').stat().st_size
    manifest['files']['frames.bin']['sha256'] = f.file_sha(path / 'frames.bin')
    publish_manifest(path, manifest)


def test_complete_fixture_readonly_random_access_exact_logical_bits(tmp_path):
    from recording.dataset import Dataset
    path, manifest, records = fixture_dataset(tmp_path)
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    with Dataset(path) as dataset:
        assert len(dataset) == 3
        assert dataset.manifest == manifest
        assert [int(r['index']) for r in dataset] == [0, 1, 2]
        assert dataset.record(2).tobytes() == records[2].tobytes()
        feeds = dataset.ort_feeds(1)
        assert set(feeds) == {'new_img', 'desire', 'traffic_convention', 'action_t'}
        for name in feeds:
            assert feeds[name].tobytes() == records[1][name].tobytes()
            assert feeds[name].shape == f.INPUTS[name][0]
            assert feeds[name].dtype == np.dtype(f.INPUTS[name][1])
            assert not feeds[name].flags.writeable
            with pytest.raises(ValueError):
                feeds[name].flat[0] = 1
        for bad in (-1, 3, True, 0.0, '0'):
            with pytest.raises((IndexError, TypeError)):
                dataset.record(bad)
    assert {p.name: p.read_bytes() for p in path.iterdir()} == before
    with pytest.raises(ValueError):
        dataset.ort_feeds(0)


@pytest.mark.parametrize('change', ['missing', 'wrong', 'partial', 'extra', 'truncated', 'tamper', 'header'])
def test_reject_incomplete_colliding_or_tampered_fixture(tmp_path, change):
    from recording.dataset import Dataset
    path, manifest, records = fixture_dataset(tmp_path)
    if change == 'missing':
        (path / 'COMPLETE').unlink()
    elif change == 'wrong':
        (path / 'COMPLETE').unlink()
        (path / 'COMPLETE').write_bytes(b'COMPLETE')
    elif change in ('partial', 'extra'):
        (path / ('frames.bin.partial' if change == 'partial' else 'gps.json')).write_bytes(b'')
    elif change == 'truncated':
        (path / 'frames.bin').write_bytes((path / 'frames.bin').read_bytes()[:-1])
    elif change == 'tamper':
        data = bytearray((path / 'frames.bin').read_bytes())
        data[-1] ^= 1
        (path / 'frames.bin').write_bytes(data)
    elif change == 'header':
        data = bytearray((path / 'frames.bin').read_bytes())
        data[0] ^= 1
        (path / 'frames.bin').write_bytes(data)
        manifest['files']['frames.bin']['sha256'] = f.file_sha(path / 'frames.bin')
        publish_manifest(path, manifest)
    with pytest.raises(ValueError):
        Dataset(path)


@pytest.mark.parametrize('field,value', [
    ('schema', True), ('frames', True), ('frames', 2), ('expected_frames', 4),
    ('status', 'INCOMPLETE'), ('continuity', 'GAPPED'), ('spec_digest', 'e' * 64),
    ('target_sha256', 'e' * 64), ('no_gps_raw_camera', False), ('state_tensors_stored', True),
    ('gps', 'private'), ('capture_start_ns', 0), ('capture_end_ns', 9),
    ('inputs', {}), ('files', {}), ('interval_diagnostic', {}),
])
def test_reject_schema_privacy_identity_and_metadata_mismatch(tmp_path, field, value):
    from recording.dataset import Dataset
    path, manifest, _ = fixture_dataset(tmp_path)
    manifest[field] = value
    publish_manifest(path, manifest)
    with pytest.raises(ValueError):
        Dataset(path)


@pytest.mark.parametrize('variant', ['duplicate', 'nan', 'list', 'bad_digest', 'privacy_provenance', 'provenance_mismatch', 'file_extra', 'file_hash', 'input_dtype', 'diagnostic'])
def test_reject_nested_and_json_manifest_attacks(tmp_path, variant):
    from recording.dataset import Dataset
    path, manifest, _ = fixture_dataset(tmp_path)
    if variant in ('duplicate', 'nan', 'list'):
        encoded = f.canonical(manifest)
        if variant == 'duplicate':
            encoded = encoded[:-1] + b',"schema":1}'
        elif variant == 'nan':
            encoded = encoded.replace(b'"schema":1', b'"schema":NaN')
        else:
            encoded = b'[]'
        (path / 'manifest.json').write_bytes(encoded)
    else:
        if variant == 'bad_digest':
            manifest['dataset_digest'] = '0' * 64
            (path / 'manifest.json').write_bytes(f.canonical(manifest))
        else:
            if variant == 'privacy_provenance':
                manifest['provenance']['route'] = 'private'
            elif variant == 'provenance_mismatch':
                manifest['provenance']['source_model_sha'] = 'e' * 64
            elif variant == 'file_extra':
                manifest['files']['frames.bin']['path'] = '/private'
            elif variant == 'file_hash':
                manifest['files']['frames.bin']['sha256'] = 'e' * 64
            elif variant == 'input_dtype':
                manifest['inputs']['desire']['dtype'] = 'object'
            elif variant == 'diagnostic':
                manifest['interval_diagnostic']['p95_ns'] = 12.0
            publish_manifest(path, manifest)
    with pytest.raises(ValueError):
        Dataset(path)


@pytest.mark.parametrize('field,index,value', [
    ('index', 0, 1), ('index', 1, 4), ('main_frame_id', 1, 104),
    ('extra_frame_id', 1, 207), ('model_timestamp_ns', 1, 1_000_000_000),
    ('monotonic_ns', 1, 2_000_000_000), ('main_sof_ns', 1, 1_000_000_000),
    ('extra_sof_ns', 1, 1_001_000_000), ('flags', 1, 1), ('flags', 0, 2),
    ('selection', 1, [0, 0]), ('reserved', 0, 1), ('expected_interval_ns', 0, 1),
    ('desire', 0, float('nan')), ('traffic_convention', 0, float('inf')),
    ('action_t', 0, float('-inf')), ('transforms', 0, float('nan')),
])
def test_reject_rehashed_corrupt_fixture_records(tmp_path, field, index, value):
    from recording.dataset import Dataset
    path, manifest, records = fixture_dataset(tmp_path)
    records[index][field] = value
    rewrite_records(path, manifest, records)
    with pytest.raises(ValueError):
        Dataset(path)


@pytest.mark.parametrize('target', ['root', 'parent', 'frames.bin', 'manifest.json', 'COMPLETE'])
def test_reject_symlink_paths_including_ancestors(tmp_path, target):
    from recording.dataset import Dataset
    path, _, _ = fixture_dataset(tmp_path)
    if target in ('root', 'parent'):
        link = tmp_path / 'linked'
        link.symlink_to(path if target == 'root' else tmp_path, target_is_directory=True)
        path = link if target == 'root' else link / path.name
    else:
        original = path / target
        moved = tmp_path / ('moved-' + target)
        original.rename(moved)
        original.symlink_to(moved)
    with pytest.raises(ValueError):
        Dataset(path)


@pytest.mark.parametrize('count,interval', [(1, 50_000_000), (3, 23_000_000), (3, 77_000_000)])
def test_camera_cadence_is_diagnostic_not_a_jitter_gate(tmp_path, count, interval):
    from recording.dataset import Dataset
    path, _, _ = fixture_dataset(tmp_path, count, interval)
    with Dataset(path) as dataset:
        assert len(dataset) == count


def test_changed_file_after_validation_cannot_supply_feeds(tmp_path):
    from recording.dataset import Dataset
    path, _, _ = fixture_dataset(tmp_path)
    with Dataset(path) as dataset:
        with (path / 'frames.bin').open('r+b') as stream:
            stream.seek(-1, os.SEEK_END)
            stream.write(b'\x01')
        with pytest.raises(ValueError):
            dataset.ort_feeds(0)


def test_nonregular_dataset_member_rejects_without_blocking(tmp_path):
    path, _, _ = fixture_dataset(tmp_path)
    (path / 'frames.bin').unlink()
    os.mkfifo(path / 'frames.bin')
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(root / 'tools/v3_input_dataset.py'), 'validate', str(path)],
                            capture_output=True, text=True, timeout=2)
    assert result.returncode == 1
    assert json.loads(result.stdout)['status'] == 'FAIL'


def test_published_readonly_snapshot_survives_close(tmp_path):
    from recording.dataset import Dataset
    path, _, records = fixture_dataset(tmp_path)
    with Dataset(path) as dataset:
        feeds = dataset.ort_feeds(0)
    for name in feeds:
        assert feeds[name].tobytes() == records[0][name].tobytes()
        with pytest.raises(ValueError):
            feeds[name].flags.writeable = True


def load_spec():
    from jetlink.spec import ModelSpec
    return ModelSpec.from_dict(json.loads((Path(__file__).resolve().parents[1] / 'artifacts/cinque_v3.json').read_text()))


def trt_buffers(spec):
    return {name: np.full(shape, 7, np.float16 if name in ('new_img', 'state_img_q') else np.float32)
            for name, shape in spec.input_shapes.items()}


def test_trt_reuses_existing_conversion_all_256_values_without_touching_state(tmp_path):
    from recording.dataset import Dataset
    from jetlink.queues import StatefulState
    path, _, records = fixture_dataset(tmp_path)
    spec = load_spec()
    dest, reference = trt_buffers(spec), trt_buffers(spec)
    state_before = {name: arr.tobytes() for name, arr in dest.items() if name.startswith('state_')}
    packed = np.concatenate([records[1][n].reshape(-1) for n in ('desire', 'traffic_convention', 'action_t')])
    StatefulState(spec).step_into(records[1]['new_img'], packed, reference)
    with Dataset(path) as dataset:
        assert dataset.trt_into(1, dest) is None
    for name in dest:
        assert dest[name].tobytes() == reference[name].tobytes()
    assert np.array_equal(dest['new_img'].reshape(-1)[:256].view(np.uint16), np.arange(256).astype(np.float16).view(np.uint16))
    for name, before in state_before.items():
        assert dest[name].tobytes() == before
    for name in ('desire', 'traffic_convention', 'action_t'):
        assert dest[name].view(np.uint32).tobytes() == records[1][name].view(np.uint32).tobytes()


def test_trt_can_fill_with_all_recurrent_arrays_readonly(tmp_path):
    from recording.dataset import Dataset
    path, _, records = fixture_dataset(tmp_path)
    spec = load_spec()
    dest = trt_buffers(spec)
    for name, array in dest.items():
        if name.startswith('state_'):
            array.flags.writeable = False
    with Dataset(path, spec=spec.to_dict()) as dataset:
        dataset.trt_into(0, dest)
    assert dest['action_t'].tobytes() == records[0]['action_t'].tobytes()
    assert np.all(dest['state_img_q'] == 7)


@pytest.mark.parametrize('variant', ['spec', 'missing', 'shape', 'dtype', 'scalar_dtype', 'readonly', 'state_alias'])
def test_trt_rejects_bad_spec_or_destination_before_any_write(tmp_path, variant):
    from recording.dataset import Dataset
    path, _, _ = fixture_dataset(tmp_path)
    spec = load_spec()
    dest = trt_buffers(spec)
    supplied_spec = spec
    if variant == 'spec':
        supplied_spec = copy.deepcopy(spec.to_dict())
        supplied_spec['frame_skip'] = 8
    elif variant == 'missing':
        del dest['action_t']
    elif variant == 'shape':
        dest['action_t'] = np.empty((2,), np.float32)
    elif variant == 'dtype':
        dest['new_img'] = np.empty(f.INPUTS['new_img'][0], np.float32)
    elif variant == 'scalar_dtype':
        dest['desire'] = np.empty((8,), np.float16)
    elif variant == 'readonly':
        dest['action_t'].flags.writeable = False
    elif variant == 'state_alias':
        dest['desire'] = dest['state_desire_q'].reshape(-1)[:8]
    before = {name: arr.tobytes() for name, arr in dest.items()}
    with Dataset(path, spec=supplied_spec) as dataset:
        with pytest.raises(ValueError):
            dataset.trt_into(0, dest)
    assert {name: arr.tobytes() for name, arr in dest.items()} == before


def test_reader_default_and_cli_validate_inspect_have_no_model_device_imports(tmp_path):
    path, _, _ = fixture_dataset(tmp_path)
    result = subprocess.run([sys.executable, '-c',
        'import sys; from recording.dataset import Dataset; d=Dataset(sys.argv[1]); d.ort_feeds(0); '
        'assert not any(n.startswith(("jetlink", "tensorrt", "pycuda", "onnxruntime", "cuda")) for n in sys.modules)',
        str(path)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    root = Path(__file__).resolve().parents[1]
    for command in ('validate', 'inspect'):
        result = subprocess.run([sys.executable, str(root / 'tools/v3_input_dataset.py'), command, str(path)], capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        report = json.loads(result.stdout)
        assert report['status'] == 'PASS' and report['frames'] == 3
        assert report['evidence'] == 'OFFLINE_DATASET_VALIDATION'
    (path / 'COMPLETE').unlink()
    result = subprocess.run([sys.executable, str(root / 'tools/v3_input_dataset.py'), 'validate', str(path)], capture_output=True, text=True)
    assert result.returncode == 1
    assert json.loads(result.stdout)['status'] == 'FAIL'


def test_real_writer_process_to_reader_exact_synthetic_fixture_crosscontract(tmp_path):
    """Real local writer process, synthetic arrays; no camera/device capture."""
    from recording.dataset import Dataset
    from recording.recorder import Recorder
    path = tmp_path / 'local-process-fixture'
    records = [fixture_record(i) for i in range(3)]
    # Source cadence permits 23/77 ms while recurrence still stays contiguous.
    records[1]['model_timestamp_ns'] = 1_023_000_000
    records[1]['main_sof_ns'] = 1_023_000_000
    records[1]['extra_sof_ns'] = 1_024_000_000
    records[1]['monotonic_ns'] = 2_023_000_000
    records[0]['flags'] = 1
    source_before = [record.tobytes() for record in records]
    recorder = Recorder(path, fixture_provenance(), frames=3)
    try:
        deadline = time.monotonic() + 8
        while not recorder.ready and recorder.reason is None and time.monotonic() < deadline:
            recorder.poll()
            time.sleep(.005)
        assert recorder.ready, recorder.reason
        for record in records:
            metadata = {name: int(record[name]) for name in (
                'main_frame_id', 'extra_frame_id', 'model_timestamp_ns',
                'monotonic_ns', 'main_sof_ns', 'extra_sof_ns', 'flags')}
            metadata['selection'] = tuple(int(v) for v in record['selection'])
            metadata['transforms'] = tuple(record['transforms'])
            assert recorder.observe(**{name: record[name] for name in f.INPUTS}, metadata=metadata)
    finally:
        recorder.close(timeout=10)
    assert recorder.reason is None
    assert [record.tobytes() for record in records] == source_before
    with Dataset(path) as dataset:
        assert len(dataset) == 3
        assert dataset.manifest['interval_diagnostic']['min_ns'] == 23_000_000
        assert dataset.manifest['interval_diagnostic']['max_ns'] == 77_000_000
        for index, record in enumerate(records):
            assert dataset.record(index).tobytes() == record.tobytes()
            for name, value in dataset.ort_feeds(index).items():
                assert value.tobytes() == record[name].tobytes()


def test_reader_imports_under_actual_candidate_nested_namespace(tmp_path):
    path, _, _ = fixture_dataset(tmp_path)
    root = Path(__file__).resolve().parents[1]
    package = tmp_path
    for name in ('openpilot', 'selfdrive', 'modeld', 'jetlink', 'input_recording'):
        package /= name
        package.mkdir()
        (package / '__init__.py').write_bytes(b'')
    for name in ('format.py', 'dataset.py'):
        shutil.copyfile(root / 'recording' / name, package / name)
    environment = dict(os.environ, PYTHONPATH=str(tmp_path), PYTHONDONTWRITEBYTECODE='1')
    result = subprocess.run([sys.executable, '-c',
        'from openpilot.selfdrive.modeld.jetlink.input_recording.dataset import Dataset; '
        'import sys; d=Dataset(sys.argv[1]); assert len(d)==3; assert len(d.ort_feeds(0))==4; d.close()',
        str(path)], cwd=tmp_path, env=environment, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
