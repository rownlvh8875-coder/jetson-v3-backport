"""FIXTURE: opt-in CPU staging/native C, never CUDA/TRT/Jetson evidence."""
import copy
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import warnings

import numpy as np
import pytest


ROOT = Path(__file__).resolve().parents[1]
PACKAGE = 'experimental.jetson_optimizations'
LENGTHS = (0, 1, 7, 8, 15, 16, 17, 31, 32, 33, 255, 256, 257)


def reference_root():
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip-ba186'))
    assert reference.is_dir(), 'provide the freshly verified reference; configured paths must not silently skip'
    return reference


def module(name):
    return importlib.import_module(f'{PACKAGE}.{name}')


def test_native_converter_is_available_for_explicit_cpu_preparation():
    assert (ROOT / 'experimental/jetson_optimizations/input_cast.py').is_file(), 'native converter is not implemented'
    convert = module('input_cast').native_u8_to_f16()
    source, target = np.array([0, 127, 255], np.uint8), np.empty(3, np.float16)
    convert(source, target)
    assert target.view(np.uint16).tolist() == [0, 22512, 23544]


@pytest.fixture(scope='module')
def converter():
    return module('input_cast').native_u8_to_f16()


@pytest.mark.parametrize('length', LENGTHS)
def test_native_lut_exact_binary16_for_all_bytes_and_vector_tails(converter, length):
    source = np.arange(length, dtype=np.uint8)
    source.flags.writeable = False
    target = np.full(length, -123, np.float16)
    converter(source, target)
    assert target.tobytes() == source.astype(np.float16).tobytes()


def test_native_lut_random_full_camera_pair_bit_exact(converter):
    source = np.random.default_rng(431).integers(0, 256, (2, 6, 128, 256), dtype=np.uint8)
    target = np.empty(source.shape, np.float16)
    converter(source, target)
    assert target.view(np.uint16).tobytes() == source.astype(np.float16).view(np.uint16).tobytes()


@pytest.mark.parametrize('fault', ['dtype_source', 'dtype_dest', 'shape', 'noncontig_source',
                                  'noncontig_dest', 'readonly_dest', 'misaligned_dest', 'overlap'])
def test_native_converter_rejects_unsafe_buffers_before_write(converter, fault):
    source = np.arange(8, dtype=np.uint8)
    target = np.full(8, -123, np.float16)
    if fault == 'dtype_source':
        source = source.astype(np.int8)
    elif fault == 'dtype_dest':
        target = target.astype(np.float32)
    elif fault == 'shape':
        source = source.reshape(2, 4)
    elif fault == 'noncontig_source':
        source = np.arange(16, dtype=np.uint8)[::2]
    elif fault == 'noncontig_dest':
        target = np.full(16, -123, np.float16)[::2]
    elif fault == 'readonly_dest':
        target.flags.writeable = False
    elif fault == 'misaligned_dest':
        target = np.ndarray((8,), np.float16, buffer=bytearray(17), offset=1)
    elif fault == 'overlap':
        storage = bytearray(16)
        source = np.ndarray((8,), np.uint8, buffer=storage)
        target = np.ndarray((8,), np.float16, buffer=storage)
    before = target.tobytes()
    with pytest.raises(ValueError):
        converter(source, target)
    assert target.tobytes() == before


def make_spec_and_buffers():
    from jetlink.spec import ModelSpec
    raw = json.loads((ROOT / 'artifacts/cinque_v3.json').read_text())
    spec = ModelSpec.from_dict(raw)
    buffers = {name: np.full(shape, 7, np.float16 if name in ('new_img', 'state_img_q') else raw['input_dtypes'][name])
               for name, shape in spec.input_shapes.items()}
    return spec, buffers


def test_direct_inputs_exact_images_scalars_preserve_all_recurrent_bytes():
    spec, buffers = make_spec_and_buffers()
    direct = module('direct_inputs').DirectInputs(spec, buffers)
    source = np.random.default_rng(98).integers(0, 256, spec.warped_shape, dtype=np.uint8)
    source.flags.writeable = False
    packed = np.linspace(-.5, .5, 12, dtype=np.float32)
    original = {name: value.tobytes() for name, value in buffers.items() if name.startswith('state_')}
    direct.stage(source, packed, buffers)
    assert buffers['new_img'].tobytes() == source.astype(np.float16).tobytes()
    np.testing.assert_array_equal(buffers['desire'], packed[:8])
    np.testing.assert_array_equal(buffers['traffic_convention'], packed[8:10].reshape(1, 2))
    np.testing.assert_array_equal(buffers['action_t'], packed[10:12].reshape(1, 2))
    assert all(buffers[name].tobytes() == value for name, value in original.items())


@pytest.mark.parametrize('fault', ['readonly', 'misaligned', 'scalar_narrowing', 'noncontig', 'overlap'])
def test_direct_inputs_rejects_invalid_binding_at_load(fault):
    spec, buffers = make_spec_and_buffers()
    if fault == 'readonly':
        buffers['new_img'].flags.writeable = False
    elif fault == 'misaligned':
        buffers['new_img'] = np.ndarray(spec.warped_shape, np.float16,
            buffer=bytearray(buffers['new_img'].nbytes + 1), offset=1)
    elif fault == 'scalar_narrowing':
        buffers['action_t'] = buffers['action_t'].astype(np.float16)
    elif fault == 'noncontig':
        buffers['new_img'] = buffers['new_img'][..., ::-1]
    else:
        buffers['traffic_convention'] = buffers['action_t']
    with pytest.raises(ValueError):
        module('direct_inputs').DirectInputs(spec, buffers)


@pytest.mark.parametrize('fault', ['replacement', 'pointer', 'shape', 'dtype', 'strides', 'readonly', 'unaligned', 'container'])
def test_direct_inputs_revalidates_binding_at_every_use(fault):
    spec, buffers = make_spec_and_buffers()
    direct = module('direct_inputs').DirectInputs(spec, buffers)
    if fault == 'replacement':
        buffers['new_img'] = buffers['new_img'].copy()
    elif fault == 'pointer':
        value = buffers['new_img']
        original_pointer = value.ctypes.data
        # ndarray.data is read-only in NumPy 2; setstate is a public way to
        # replace storage on the same ndarray object without replacing identity.
        value.__setstate__((1, value.shape, value.dtype, False, bytes(value.nbytes)))
        assert value.ctypes.data != original_pointer
    elif fault in ('shape', 'dtype', 'strides'):
        # Deliberately exercise prohibited in-place metadata mutation; NumPy
        # still exposes these setters but has deprecated ordinary use.
        with warnings.catch_warnings():
            warnings.simplefilter('ignore', DeprecationWarning)
            if fault == 'shape':
                buffers['new_img'].shape = (-1,)
            elif fault == 'dtype':
                buffers['new_img'].dtype = np.uint16
            else:
                buffers['new_img'].strides = (0,) + buffers['new_img'].strides[1:]
    elif fault == 'readonly':
        buffers['new_img'].flags.writeable = False
    elif fault == 'unaligned':
        buffers['new_img'].flags.aligned = False
    else:
        buffers = dict(buffers)
    before = {name: value.tobytes() for name, value in buffers.items()}
    with pytest.raises(ValueError):
        direct.stage(np.zeros(spec.warped_shape, np.uint8), np.zeros(12, np.float32), buffers)
    assert all(value.tobytes() == before[name] for name, value in buffers.items())


@pytest.mark.parametrize('fault', ['image_dtype', 'image_shape', 'image_size', 'image_noncontig',
                                  'scalar_nan', 'scalar_inf', 'scalar_dtype', 'scalar_size', 'source_alias', 'scalar_alias'])
def test_direct_inputs_rejects_invalid_sources_before_any_staging(fault):
    spec, buffers = make_spec_and_buffers()
    direct = module('direct_inputs').DirectInputs(spec, buffers)
    source = np.zeros(spec.warped_shape, np.uint8)
    packed = np.zeros(12, np.float32)
    if fault == 'image_dtype':
        source = source.astype(np.float16)
    elif fault == 'image_shape':
        source = source.reshape(-1)
    elif fault == 'image_size':
        source = source[..., :-1]
    elif fault == 'image_noncontig':
        source = source[..., ::-1]
    elif fault in ('scalar_nan', 'scalar_inf'):
        packed[-1] = np.nan if fault == 'scalar_nan' else np.inf
    elif fault == 'scalar_dtype':
        packed = packed.astype(np.float64)
    elif fault == 'scalar_size':
        packed = packed[:-1]
    elif fault == 'source_alias':
        source = buffers['new_img'].view(np.uint8).reshape(-1)[:source.size].reshape(source.shape)
    else:
        packed = buffers['state_feat_q'].reshape(-1)[:12]
    before = {name: value.tobytes() for name, value in buffers.items()}
    with pytest.raises(ValueError):
        direct.stage(source, packed, buffers)
    assert all(value.tobytes() == before[name] for name, value in buffers.items())


def test_direct_inputs_rejects_nav_map_contract_and_compact_payload():
    spec, buffers = make_spec_and_buffers()
    raw = copy.deepcopy(spec.to_dict())
    raw['input_shapes']['nav_map'] = [1, 256, 256]
    raw['input_dtypes']['nav_map'] = 'float32'
    from jetlink.spec import ModelSpec
    with pytest.raises(ValueError):
        module('direct_inputs').DirectInputs(ModelSpec.from_dict(raw), buffers)
    direct = module('direct_inputs').DirectInputs(spec, buffers)
    with pytest.raises(ValueError):
        direct.stage(np.zeros(spec.warped_shape, np.uint8), bytes(48), buffers)


@pytest.fixture(scope='module')
def overlay(tmp_path_factory):
    from adapters.carrot.server import server_files
    reference = reference_root()
    files = server_files(reference)
    before = files.copy()
    changed = module('fastpath_adapter').fastpath_optimization_files(files)
    assert files == before
    modern = 'third_party/jetlink/jetlink/server/backends/trt/managed_engine.py' in files
    names = ('queues.py', 'managed_input_cast.c', 'managed_input_cast.py', 'direct_inputs.py') if modern else (
        'queues.py', 'input_cast.c', 'input_cast.py', 'direct_inputs.py')
    assert set(changed) == {'third_party/jetlink/jetlink/' + name for name in names}
    target = tmp_path_factory.mktemp('input-fastpath-candidate')
    # These are the actual current candidate modules, in a separate namespace.
    import shutil
    shutil.copytree(reference / 'third_party/jetlink', target / 'third_party/jetlink')
    for name, value in (files | changed).items():
        destination = target / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(value)
    return target


def run_candidate(overlay, flag):
    env = dict(os.environ, PYTHONPATH=str(overlay / 'third_party/jetlink'))
    if flag is None:
        env.pop('CARROT_TRT_INPUT_FASTPATH', None)
    else:
        env['CARROT_TRT_INPUT_FASTPATH'] = flag
    process = subprocess.run([sys.executable, str(ROOT / 'tests/jetson_input_fastpath_peer.py')],
                             env=env, text=True, capture_output=True, timeout=40)
    assert process.returncode == 0, process.stdout + process.stderr
    return json.loads(process.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize('flag', [None, '0', '1'])
def test_actual_candidate_warm_and_stateful_steps_default_off_and_opt_in(overlay, flag):
    report = run_candidate(overlay, flag)
    assert report['v2_unchanged'] and report['state_untouched'] and report['exact_images']
    assert report['native_loaded'] is (flag == '1')
    assert report['evidence'] == 'FIXTURE_NATIVE_CPU'


@pytest.mark.parametrize('flag', ['', 'true', '01', ' 1', '2'])
def test_actual_candidate_rejects_invalid_runtime_flag(overlay, flag):
    report = run_candidate(overlay, flag)
    assert report['flag_rejected'] is True


def test_overlay_rejects_changed_stateful_source_without_mutating_input():
    files = {'third_party/jetlink/jetlink/queues.py': b'class StatefulState: pass\n'}
    before = copy.deepcopy(files)
    with pytest.raises(ValueError):
        module('fastpath_adapter').fastpath_optimization_files(files)
    assert files == before


def test_overlay_rejects_changed_validation_inside_otherwise_matching_class():
    from adapters.carrot.server import server_files
    files = server_files(reference_root())
    name = 'third_party/jetlink/jetlink/queues.py'
    files[name] = files[name].replace(b"np.copyto(dest[STATEFUL_FRAME], warped, casting='safe')",
                                    b"np.copyto(dest[STATEFUL_FRAME], warped, casting='unsafe')")
    with pytest.raises(ValueError):
        module('fastpath_adapter').fastpath_optimization_files(files)
