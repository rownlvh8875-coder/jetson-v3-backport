#!/usr/bin/env python3
"""Build and compare the identified Cinque V3 model.

TRT build/verification requires compatible local CUDA/TRT hardware; never tested
on a real Jetson here. CPU ONNX comparison: --onnx-only --out patched.onnx.
Both comparison modes check all four outputs and exact backend I/O contracts.
Frame 0 is zero smoke; frames 1+ vary seeded images and desire with 0/255 pixels.
--comparison-mode recurrent follows independent backend states; same-state uses
identical zero states for each step. ORT is explicitly CPU and runs sequential
sessions for ONNX parity to limit memory. No default tolerance is established.

Exit codes: 0 requested gate passed (or build-only completed), 1 failed,
2 invalid CLI arguments, 3 comparison incomplete or measured without a tolerance.
A build alone is not numerical validation. The engine-hash-bound retype record
is consumed by this verifier; production server integration remains stage 3.
Timing distinguishes enqueue, CUDA events, and completed transfer/inference;
none is the comma-to-Jetson path latency. See docs/PROJECT_STATE.md for evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

V3_RETYPES = dict.fromkeys(('new_img', 'state_img_q', 'next_state_img_q'), 'float16')


class VerificationIncomplete(RuntimeError):
  """Measurements or comparison are incomplete; never a parity PASS."""


def file_identity(path: Path) -> dict:
  import hashlib
  h, size = hashlib.sha256(), 0
  with Path(path).open('rb') as f:
    while chunk := f.read(1 << 20):
      h.update(chunk)
      size += len(chunk)
  return dict(sha256=h.hexdigest(), nbytes=size)


def build_record_path(engine_path, digest):
  return engine_path.with_name(engine_path.name + '.' + digest + '.retypes.json')


def load_build_record(engine_path, source):
  identity = file_identity(engine_path)
  record = json.loads(build_record_path(engine_path, identity['sha256']).read_text())
  if record['engine'] != identity or record['source'] != source:
    raise ValueError('engine/source identity does not match build record')
  if file_identity(Path(record['patched_path'])) != record['patched']:
    raise ValueError('parsed ONNX identity does not match build record')
  transforms = record['dtype_transforms']
  if transforms not in ({}, V3_RETYPES):
    raise ValueError('undeclared dtype transforms in build record')
  return record


def onnx_contract(model):
  import onnx
  result = {}
  for kind, values in (('inputs', model.graph.input), ('outputs', model.graph.output)):
    result[kind] = {}
    for vi in values:
      tensor = vi.type.tensor_type
      if any(not d.HasField('dim_value') or d.dim_value <= 0 for d in tensor.shape.dim):
        raise ValueError(f'dynamic/invalid ONNX shape: {vi.name}')
      result[kind][vi.name] = dict(shape=[d.dim_value for d in tensor.shape.dim],
          dtype=str(np.dtype(onnx.helper.tensor_dtype_to_np_dtype(tensor.elem_type))))
  return result


def spec_contract(spec, transforms=None):
  transforms = transforms or {}
  return {kind: {n: dict(shape=list(shape), dtype=transforms.get(n, spec[prefix+'_dtypes'][n]))
                 for n, shape in spec[prefix+'_shapes'].items()}
          for kind, prefix in (('inputs', 'input'), ('outputs', 'output'))}


def validate_contract(actual, expected):
  if actual != expected:
    raise ValueError(f'I/O contract mismatch: actual={actual}, expected={expected}')


def ort_contract(session):
  types = {'tensor(uint8)': 'uint8', 'tensor(float)': 'float32', 'tensor(float16)': 'float16'}
  return {kind: {v.name: dict(shape=list(v.shape), dtype=types[v.type]) for v in values}
          for kind, values in (('inputs', session.get_inputs()), ('outputs', session.get_outputs()))}


def validate_arguments(frames, threshold, mode='recurrent'):
  if not isinstance(frames, int) or frames <= 0:
    raise ValueError('frames must be a positive integer')
  if threshold is not None and (not np.isfinite(threshold) or threshold < 0):
    raise ValueError('threshold must be finite and nonnegative (0 means exact)')
  if mode not in ('recurrent', 'same-state'):
    raise ValueError('unknown comparison mode')


def frame_inputs(inputs, frame, seed):
  """Frame 0 is zero smoke; subsequent frames vary pixels/desire, with 0/255 edges."""
  rng = np.random.default_rng(seed + frame)
  feeds = {n: np.zeros(v['shape'], v['dtype']) for n, v in inputs.items()}
  if frame:
    image = rng.integers(0, 256, size=inputs['new_img']['shape'], dtype=np.uint8)
    image.flat[0], image.flat[-1] = 0, 255
    # Only the intentional V3 image retype crosses backend dtypes.
    if feeds['new_img'].dtype not in (np.dtype('uint8'), np.dtype('float16')):
      raise ValueError('unexpected image dtype')
    np.copyto(feeds['new_img'], image, casting='safe')
    feeds['desire'].flat[frame % feeds['desire'].size] = 1
    feeds['traffic_convention'].flat[0] = 1
    feeds['action_t'].fill(frame / 20)
  return feeds


def validate_outputs(outputs, contract):
  if set(outputs) != set(contract):
    raise ValueError('output names mismatch')
  for n, v in contract.items():
    x = outputs[n]
    if not isinstance(x, np.ndarray) or x.shape != tuple(v['shape']) or x.dtype != np.dtype(v['dtype']):
      raise ValueError(f'output shape/dtype mismatch: {n}')
    if not np.all(np.isfinite(x)):
      raise ValueError(f'non-finite output: {n}')


def compare_outputs(left, right, threshold):
  if set(left) != set(right):
    raise ValueError('comparison output names mismatch')
  stats = {}
  for n in left:
    if left[n].shape != right[n].shape:
      raise ValueError(f'comparison shape mismatch: {n}')
    # Explicit float64 error arithmetic avoids uint8 wrap and fp16 overflow.
    with np.errstate(over='ignore', invalid='ignore'):
      err = np.abs(left[n].astype(np.float64) - right[n].astype(np.float64))
      maximum, mean = float(err.max()), float(err.mean())
    if not np.isfinite(maximum) or not np.isfinite(mean):
      raise ValueError(f'non-finite comparison error: {n}')
    stats[n] = dict(max_abs=maximum, mean_abs=mean)
    if threshold is not None and maximum > threshold:
      raise ValueError(f'threshold exceeded: {n} max_abs={maximum} > {threshold}')
  return stats


def advance_state(feeds, outputs):
  pending = {}
  for n, target in feeds.items():
    if n.startswith('state_'):
      value = outputs['next_' + n]
      if value.shape != target.shape or value.dtype != target.dtype or not np.all(np.isfinite(value)):
        raise ValueError(f'invalid state feedback: {n}')
      pending[n] = value
  for n, value in pending.items():
    np.copyto(feeds[n], value, casting='no')


def require_ort(compare_onnx):
  if compare_onnx is None:
    raise VerificationIncomplete('comparison not requested; parity not performed')
  try:
    import onnxruntime as ort
  except ImportError as e:
    raise VerificationIncomplete('onnxruntime unavailable; parity not performed') from e
  return ort


def ort_session(ort, path):
  options = ort.SessionOptions()
  options.intra_op_num_threads = 2
  options.inter_op_num_threads = 1
  options.enable_cpu_mem_arena = False
  options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
  # CPU is explicit for reproducibility and to avoid a second CUDA allocator/context.
  session = ort.InferenceSession(str(path), sess_options=options, providers=['CPUExecutionProvider'])
  print('ORT registered providers:', session.get_providers(), '(CPU requested; per-op GPU placement not asserted)', flush=True)
  return session


def finish_verification(threshold):
  if threshold is None:
    raise VerificationIncomplete('MEASURED: tolerance basis absent; acceptance UNDETERMINED')
  print('parity PASS for the requested threshold; synthetic inputs only')


def verify_onnx_pair(original, patched, spec, frames=5, require_max_abs_err=None,
                     mode='recurrent', seed=73):
  """Sequential ORT sessions and on-disk reference outputs keep memory bounded."""
  import gc
  import tempfile
  validate_arguments(frames, require_max_abs_err, mode)
  ort = require_ort(original)
  check_onnx_identity(Path(original), spec)
  with tempfile.TemporaryDirectory(prefix='v3-parity-') as td:
    for index, (path, transforms) in enumerate(((original, {}), (patched, V3_RETYPES))):
      session = ort_session(ort, path)
      contract = ort_contract(session)
      validate_contract(contract, spec_contract(spec, transforms))
      state = None
      names = list(contract['outputs'])
      for frame in range(frames):
        feeds = frame_inputs(contract['inputs'], frame, seed)
        if mode == 'recurrent' and state is not None:
          for n, value in state.items(): np.copyto(feeds[n], value, casting='no')
        outputs = dict(zip(names, session.run(names, feeds)))
        validate_outputs(outputs, contract['outputs'])
        if index == 0:
          for n, value in outputs.items(): np.save(Path(td)/f'{frame}-{n}.npy', value)
        else:
          reference = {n: np.load(Path(td)/f'{frame}-{n}.npy', mmap_mode='r') for n in names}
          stats = compare_outputs(reference, outputs, require_max_abs_err)
          print(json.dumps(dict(comparison='original-patched-onnx', mode=mode, frame=frame, tensors=stats)), flush=True)
          del reference
        advance_state(feeds, outputs)
        state = {n: value.copy() for n, value in feeds.items() if n.startswith('state_')}
      del session, outputs, feeds, state
      gc.collect()
  finish_verification(require_max_abs_err)


def build_engine(onnx_path: Path, engine_path: Path, workspace_mib: int,
                 fp16: bool = True, patch: str = "auto") -> Path | None:
  """Patch (like production), parse and build. Returns the retype record
  path when a patch was applied, else None.

  Follows production's patch -> parse -> build ordering. The pinned production
  builder does not yet invoke this V3 patch or consume this build record.
  patch="auto" leaves non-V3 graphs on their existing raw parse path.
  """
  import tensorrt as trt

  logger = trt.Logger(trt.Logger.INFO)
  builder = trt.Builder(logger)

  def configure_precision(config, want_fp16: bool) -> str:
    """Ask for fp16 the way this TensorRT allows.

    Mirrors production jetlink/server/backends/trt/build.py::configure_precision:
    TensorRT 10.x wants trt.BuilderFlag.FP16. (trt.Flag does not exist in the
    10.x Python API; the old spelling would raise AttributeError at build
    time, so this was a build blocker.)
    """
    if want_fp16:
      if not builder.platform_has_fast_fp16:
        print("WARNING: platform reports no fast FP16; building FP16 anyway",
              file=sys.stderr)
      config.set_flag(trt.BuilderFlag.FP16)
      return 'fp16 enabled'
    return 'fp32'

  import os
  import tempfile
  import onnx
  from patch_v3_uint8 import needs_patch_v3, patch_file_v3
  if onnx_path.resolve() == engine_path.resolve():
    raise ValueError('engine output would overwrite original ONNX')
  source = file_identity(onnx_path)
  model = onnx.load(str(onnx_path))
  original_io = onnx_contract(model)
  needs_patch = patch == 'v3-uint8' or (patch == 'auto' and needs_patch_v3(model))
  del model
  engine_path.parent.mkdir(parents=True, exist_ok=True)
  with tempfile.TemporaryDirectory(prefix=engine_path.name + '.build-', dir=engine_path.parent) as td:
    stage = Path(td)
    parse_path, retypes = onnx_path, {}
    if needs_patch:
      parse_path = stage / 'patched.onnx'
      retypes = patch_file_v3(onnx_path, parse_path)
    network = builder.create_network(1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
    parser = trt.OnnxParser(network, logger)
    if not parser.parse_from_file(str(parse_path)):
      for i in range(parser.num_errors):
        print(f'parser error {i}: {parser.get_error(i)}', file=sys.stderr)
      raise RuntimeError(f'ONNX parsing failed for {parse_path}')
    config = builder.create_builder_config()
    config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_mib << 20)
    print(f'precision: {configure_precision(config, fp16)}', flush=True)
    inputs = [network.get_input(i) for i in range(network.num_inputs)]
    print(f'inputs : {[(i.name, tuple(i.shape), str(i.dtype)) for i in inputs]}', flush=True)
    t0 = time.monotonic()
    serialized = builder.build_serialized_network(network, config)
    if serialized is None:
      raise RuntimeError('TensorRT engine build returned None')
    staged_engine = stage / 'engine.plan'
    staged_engine.write_bytes(bytes(serialized))
    engine_id = file_identity(staged_engine)
    record_path = build_record_path(engine_path, engine_id['sha256'])
    patched_id = file_identity(parse_path)
    saved_patch = engine_path.with_name(engine_path.name + '.' + engine_id['sha256'] + '.patched.onnx')
    record = dict(schema=1, source=source, original_io=original_io,
                  patched=patched_id, patched_path=str(saved_patch.resolve()) if retypes else str(onnx_path.resolve()),
                  engine=engine_id, dtype_transforms=retypes,
                  patch='v3-uint8' if retypes else 'none', fp16=fp16, workspace_mib=workspace_mib,
                  tensorrt_version=getattr(trt, '__version__', 'unknown'),
                  patcher=file_identity(Path(__file__).with_name('patch_v3_uint8.py')) if retypes else None)
    if record_path.exists() and json.loads(record_path.read_text()) != record:
      raise ValueError('engine metadata collision; preserve previous build')
    if retypes:
      if saved_patch.exists() and file_identity(saved_patch) != patched_id:
        raise ValueError('patched artifact collision')
      if not saved_patch.exists(): os.replace(parse_path, saved_patch)
    staged_record = stage / 'record.json'
    staged_record.write_text(json.dumps(record, indent=2, sort_keys=True), encoding='utf-8')
    if not record_path.exists(): os.replace(staged_record, record_path)
    # Engine publication is the commit point. Failed staging preserves the old engine.
    os.replace(staged_engine, engine_path)
    print(f'built {engine_path} in {time.monotonic()-t0:.2f}s; build record: {record_path}')
    return record_path if retypes else None


def check_onnx_identity(onnx_path: Path, spec: dict) -> None:
  """Refuse to build unless the ONNX file is exactly the one the spec
  describes. A wrong ONNX + right JSON combination must never build."""
  import hashlib
  if not onnx_path.is_file():
    raise SystemExit(f"ONNX file missing: {onnx_path}; refusing to build")
  h = hashlib.sha256()
  n = 0
  with open(onnx_path, "rb") as f:
    while chunk := f.read(1 << 20):
      h.update(chunk)
      n += len(chunk)
  digest, want_digest = h.hexdigest(), spec.get("sha256", "")
  if digest != want_digest:
    raise SystemExit(
      f"ONNX sha256 mismatch:\n  actual {digest}\n  spec   {want_digest}\n"
      f"refusing to build")
  if n != spec.get("nbytes"):
    raise SystemExit(
      f"ONNX size mismatch: actual {n} != spec nbytes {spec.get('nbytes')}; "
      f"refusing to build")
  print(f"ONNX identity ok: sha256 {digest[:16]}… size {n}")


def _trt_dtype(trt, dtype) -> np.dtype:
  return {
    trt.float32: np.float32, trt.float16: np.float16, trt.int32: np.int32,
    trt.int64: np.int64, trt.uint8: np.uint8, trt.bool: np.bool_,
  }[dtype]


def engine_contract(engine, trt):
  actual = {'inputs': {}, 'outputs': {}}
  seen = set()
  for i in range(engine.num_io_tensors):
    name = engine.get_tensor_name(i)
    mode = engine.get_tensor_mode(name)
    if name in seen or mode not in (trt.TensorIOMode.INPUT, trt.TensorIOMode.OUTPUT):
      raise ValueError('invalid engine tensor name/mode')
    seen.add(name)
    kind = 'inputs' if mode == trt.TensorIOMode.INPUT else 'outputs'
    shape = list(engine.get_tensor_shape(name))
    if any(d <= 0 for d in shape): raise ValueError(f'invalid engine shape: {name}')
    actual[kind][name] = dict(shape=shape, dtype=str(np.dtype(_trt_dtype(trt, engine.get_tensor_dtype(name)))))
  return actual


from contextlib import contextmanager


@contextmanager
def trt_runner(engine_path, expected):
  """Private verifier only. Primary context and pinned arrays live through sync."""
  import tensorrt as trt
  import pycuda.driver as cuda
  cuda.init()
  primary = cuda.Device(0).retain_primary_context()
  primary.push()
  runtime = engine = context = stream = start = end = None
  buffers = {}
  try:
    logger = trt.Logger(trt.Logger.WARNING)
    runtime = trt.Runtime(logger)
    engine = runtime.deserialize_cuda_engine(engine_path.read_bytes())
    if engine is None: raise RuntimeError('engine deserialize failed')
    actual = engine_contract(engine, trt)
    validate_contract(actual, expected)  # Before ANY buffer allocation or execution.
    context = engine.create_execution_context()
    if context is None: raise RuntimeError('execution context creation failed')
    stream, start, end = cuda.Stream(), cuda.Event(), cuda.Event()
    for kind in ('inputs', 'outputs'):
      for name, info in actual[kind].items():
        host = cuda.pagelocked_empty(tuple(info['shape']), np.dtype(info['dtype']))
        buffers[name] = [host, None]
        dev = cuda.mem_alloc(host.nbytes)
        buffers[name][1] = dev
        if not context.set_tensor_address(name, int(dev)):
          raise RuntimeError(f'set_tensor_address failed: {name}')

    def run(feeds):
      validate_outputs(feeds, actual['inputs'])
      t0 = time.monotonic()
      for name in actual['inputs']:
        host, dev = buffers[name]
        np.copyto(host, feeds[name], casting='no')
        cuda.memcpy_htod_async(dev, host, stream)
      start.record(stream)
      enqueue_start = time.monotonic()
      ok = context.execute_async_v3(stream.handle)
      enqueue_ms = (time.monotonic()-enqueue_start)*1e3
      end.record(stream)
      if not ok: raise RuntimeError('execute_async_v3 failed')
      for name in actual['outputs']:
        host, dev = buffers[name]
        cuda.memcpy_dtoh_async(host, dev, stream)
      stream.synchronize()
      print(f'TRT enqueue_ms={enqueue_ms:.3f} gpu_ms={start.time_till(end):.3f} '
            f'completed_h2d_execute_d2h_ms={(time.monotonic()-t0)*1e3:.3f}', flush=True)
      return {n: buffers[n][0].copy() for n in actual['outputs']}
    yield run
  finally:
    # Also synchronize on a failed enqueue/address path before releasing pages.
    try:
      if stream is not None: stream.synchronize()
    finally:
      context = None
      cleanup_error = None
      for host, dev in buffers.values():
        for allocation in (dev, host.base):
          try:
            if allocation is not None: allocation.free()
          except Exception as e:
            cleanup_error = cleanup_error or e
      buffers.clear()
      engine = runtime = start = end = stream = None
      try:
        primary.pop()
      finally:
        primary.detach()
      if cleanup_error is not None: raise cleanup_error


def verify_engine(engine_path, spec, compare_onnx, frames=5,
                  require_max_abs_err=None, mode='recurrent', seed=73):
  validate_arguments(frames, require_max_abs_err, mode)
  ort = require_ort(compare_onnx)
  check_onnx_identity(Path(compare_onnx), spec)
  record = load_build_record(engine_path, {k: spec[k] for k in ('sha256', 'nbytes')})
  validate_contract(record['original_io'], spec_contract(spec))
  session = ort_session(ort, compare_onnx)
  raw = ort_contract(session)
  validate_contract(raw, spec_contract(spec))
  patched = spec_contract(spec, record['dtype_transforms'])
  state_left = state_right = None
  with trt_runner(engine_path, patched) as run:
    for frame in range(frames):
      left = frame_inputs(raw['inputs'], frame, seed)
      right = frame_inputs(patched['inputs'], frame, seed)
      if mode == 'recurrent' and state_left is not None:
        for n in state_left:
          np.copyto(left[n], state_left[n], casting='no')
          np.copyto(right[n], state_right[n], casting='no')
      left_out = dict(zip(raw['outputs'], session.run(list(raw['outputs']), left)))
      right_out = run(right)
      validate_outputs(left_out, raw['outputs'])
      validate_outputs(right_out, patched['outputs'])
      stats = compare_outputs(left_out, right_out, require_max_abs_err)
      print(json.dumps(dict(comparison='original-TRT', mode=mode, frame=frame, tensors=stats)), flush=True)
      advance_state(left, left_out)
      advance_state(right, right_out)
      state_left = {n: v.copy() for n, v in left.items() if n.startswith('state_')}
      state_right = {n: v.copy() for n, v in right.items() if n.startswith('state_')}
  finish_verification(require_max_abs_err)


def main():
  ap = argparse.ArgumentParser(description='Build/compare the identified Cinque V3 model')
  ap.add_argument('--onnx', required=True, type=Path)
  ap.add_argument('--spec', required=True, type=Path)
  ap.add_argument('--out', required=True, type=Path)
  ap.add_argument('--workspace', type=int, default=1536)
  ap.add_argument('--no-fp16', action='store_true')
  ap.add_argument('--patch', choices=['auto', 'v3-uint8', 'none'], default='auto')
  ap.add_argument('--verify', action='store_true')
  ap.add_argument('--onnx-only', action='store_true', help='patch to --out and compare sequential ORT CPU sessions; no TRT')
  ap.add_argument('--compare-onnx', type=Path)
  ap.add_argument('--frames', type=int, default=5)
  ap.add_argument('--require-max-abs-err', type=float)
  ap.add_argument('--comparison-mode', choices=['recurrent', 'same-state'], default='recurrent')
  a = ap.parse_args()
  try:
    validate_arguments(a.frames, a.require_max_abs_err, a.comparison_mode)
    if a.workspace <= 0: raise ValueError('workspace must be positive')
    if not (a.verify or a.onnx_only) and (a.require_max_abs_err is not None or a.compare_onnx is not None):
      raise ValueError('comparison/gate requires --verify or --onnx-only')
  except ValueError as e:
    ap.error(str(e))
  spec = json.loads(a.spec.read_text())
  if 'new_img' not in spec['input_shapes']:
    raise SystemExit('spec is not V3 stateful; refusing to build')
  check_onnx_identity(a.onnx, spec)
  try:
    if a.onnx_only:
      from patch_v3_uint8 import patch_file_v3
      patch_file_v3(a.onnx, a.out)
      verify_onnx_pair(a.onnx, a.out, spec, a.frames, a.require_max_abs_err, a.comparison_mode)
    else:
      record = build_engine(a.onnx, a.out, a.workspace, not a.no_fp16, a.patch)
      if record: print('verifier dtype record (production consumer NOT integrated):', record)
      if a.verify:
        verify_engine(a.out, spec, a.compare_onnx or a.onnx, a.frames,
                      a.require_max_abs_err, a.comparison_mode)
  except VerificationIncomplete as e:
    print(f'INCOMPLETE: {e}', file=sys.stderr)
    raise SystemExit(3)
  except (ValueError, RuntimeError, ImportError, OSError) as e:
    print(f'FAIL: {e}', file=sys.stderr)
    raise SystemExit(1)


if __name__ == '__main__':
  main()
