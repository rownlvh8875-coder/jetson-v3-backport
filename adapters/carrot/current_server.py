"""Reviewed 604bc server seams; retain native protocol2/N16 behavior.

The shared adapter still owns managed protocol3 validation. These helpers only
bridge the two exact reviewed source layouts, never arbitrary upstream bodies.
"""
CURRENT_SOURCES = {'spec.py': 'ec844ccaf13ffc1d7c03ad683b0e3f2ce6a1d78f4088067739aaa419af422170',
 'queues.py': 'c251eecc45e38704c15b2a10f0969c270cd9fa11603ebdaae88c1b1187112ea8',
 'server/session.py': '975e36a680fe57a1ed6e865c3bba119903508a0ed21032d83b77295580998591',
 'onnx_patch.py': '742fa6080ee81d8c5f61c9ee3d4616d6d28fee7f99e691463561e71121bf9c1c',
 'onnx_meta.py': '17eabd7f663020c857f6c426c78aa021e7853fd9b761f3cb1f3d481ea584db94',
 'server/backends/trt/build.py': '45d7080bf85c897e0cf92980ae1006e4db9205b27ae2e335244f3a4ec657c8c1',
 'server/backends/trt/__init__.py': 'dd604510a62aa8b8d2ee7b44b5bd91ab9386666805b5eef9b656e3af6ba2d009',
 'server/backends/trt/engine.py': '44cfa18fa841bf83c70dfeab0e53debf07675c9c7d5ff23838d86eb509762c6e',
 'server/control.py': 'f69345e416faf74e11ddee7bd89e69f570504b1ffa730f6c416db01ed28918f4',
 'server/main.py': 'db09427220eae1eb5346ea4ebb9b5dc286dea491dd34e3baac7ac3e2f31f5813'}

NATIVE_SOURCES = {'input_cast.c': 'd14dc4b88fa5af1e30e8fbc74d2830a1537d6d1e75dbeded1dd08b6b9ca4188f',
 'finite.c': '04196af6ea6c6823f9d6b2dbeeb3c94f8ac3f77ece74e9aeec983b74e2a663b0',
 'output_projection.py': 'd76547e3426c488c6f8ab341a2b1f0613c183a02c6b6710c9871af8a94d3a534',
 'packed_codec.py': '8d67a94951e6188d811c8ad7072e5db1b40ff9ef24ec28049634b07cb26c9004',
 'block_codec.py': 'a42299bd1fccdf53022afd50066909caa5740f4790cec1a88eec9665f8e7ad5e',
 'direct_map.py': 'bc2e9be99ffc36fa9e39eb5a68f241d1fa3a11a77a30212e35df04a185210161',
 'finite.py': '94b7a40d8b00a89d480075cf4763d827ac75e27ba95b194fba8d138507131f6c',
 'input_cast.py': '8f115c4a2c52f60d9ff339b1111184a29c69874a99223fe61af7f3afe66c47a0',
 'server/backends/trt/state_buffers.py': '0942c00bf24e00eb030607648a35ae69efbda3ebce631647c1d17cbf0c8f6519',
 'server/backends/trt/device_state.py': '80cd6159dc6ab9ec3559f4556986752d49dd670ef6d6f6c5d8ab863fa84dfa4b',
 'server/backends/trt/cudart.py': 'd4079ec3bebb889b4b2b7dce3bd5629f64e357733d75d35e2cf3fa7eb5836db1',
 'server/cache.py': '259d5abc99609f866f091ed0e1d0a9d9846849cc082bbf1475d2b9b5f048aeeb'}

LEGACY_INFER = '''  def _infer(self, loaded: Loaded, msg: Message) -> None:
    t0 = time.perf_counter()
    spec = loaded.spec
    if msg.payload.nbytes != spec.infer_req_nbytes:
      # The offsets below come from the spec, not the wire: a client on another
      # model would have its scalars read out of the image, and the result would
      # look perfectly finite.
      self._send(P.Msg.INFER_RESP, msg.seq,
                 (P.pack_infer_resp(0, P.Status.BAD_SHAPE, 0, 0, 0),))
      return
    frame_id, flags = P.unpack_infer_req(msg.payload)
    if flags & P.Flag.RESET_QUEUES:
      loaded.queues.reset()

    off = P.INFER_REQ_SIZE
    warped = np.frombuffer(msg.payload, np.uint8, spec.warped_nbytes, off).reshape(spec.warped_shape)
    off += spec.warped_nbytes
    packed = np.frombuffer(msg.payload, np.float32, spec.packed_nelem, off)

    # Gathers land straight in TensorRT's pinned input buffers: between the
    # wire and the GPU there is exactly one copy.
    loaded.queues.step_into(warped, packed, loaded.host_inputs)
    queue_us = int((time.perf_counter() - t0) * 1e6)

    outputs = loaded.engine.run()
    out = next(iter(outputs.values())).reshape(-1)

    # asarray, not astype: a no-op when the engine already outputs float32.
    # isfinite is ~7x faster on float32 and the non-finites map across exactly.
    # openpilot drops to the small model on a non-finite output either way, so
    # checking here saves the comma rescanning 18452 floats to find out.
    out32 = np.asarray(out, dtype=np.float32)
    status = P.Status.OK if np.all(np.isfinite(out32)) else P.Status.NOT_FINITE

    total_us = int((time.perf_counter() - t0) * 1e6)
    parts = [P.pack_infer_resp(frame_id, status, loaded.engine.last_gpu_us, queue_us, total_us),
             out32]
    if flags & P.Flag.WANT_STATE:
      parts.append(json.dumps(self.telemetry.read()).encode())
    send_started = time.perf_counter()
    self._send(P.Msg.INFER_RESP, msg.seq, parts)
    send_us = int((time.perf_counter() - send_started) * 1e6)
    self.frames += 1
    if total_us > SLOW_FRAME_US or send_us > 10_000:
      # After the reply, so the log never delays it. The comma logs the same
      # frame by its own stages; together they place a slow frame.
      log.warning("slow frame %d: gpu %.1f queue %.1f total %.1f send %.1f ms", frame_id,
                  loaded.engine.last_gpu_us / 1e3, queue_us / 1e3, total_us / 1e3, send_us / 1e3)
    self.host.frame_stats.record(total_us, loaded.engine.last_gpu_us)

'''

def split_native_session(source):
    start = source.index('  def _warm(self,')
    end = source.index('  def unload(self)', start)
    warm = source[start:end].replace('def _warm(', 'def _warm_native(', 1)
    start = source.index('  def _infer(self,')
    end = source.index('  def on_shutdown(', start)
    native = source[start:end].replace('def _infer(', 'def _infer_native(', 1)
    shapes_start = source.index('def _check_shapes(')
    shapes_end = source.index('\n\nclass Session:', shapes_start)
    checks = source[shapes_start:shapes_end].replace('def _check_shapes(', 'def _check_shapes_native(', 1)
    hello_start = source.index('  def on_hello(')
    hello_end = source.index('  def on_engine_req(', hello_start)
    hello = source[hello_start:hello_end].replace('def on_hello(', 'def on_hello_native(', 1)
    return source[:start] + LEGACY_INFER + source[end:], warm, native, checks, hello


def retain_native_session(source, warm, infer, checks, hello):
    # N16 is the reviewed native protocol2 contract, not a managed protocol3
    # model. Refuse adoption before ready and do not reset its live recurrence
    # merely because a protocol3 peer sent HELLO.
    source = source.replace("      if resp['protocol'] == 3 and loaded is not None and loaded.valid:\n",
        "      if (resp['protocol'] == 3 and loaded is not None and loaded.valid\n"
        "          and not projection.eligible(loaded.spec)):\n", 1)
    source = source.replace('or loaded.spec.to_dict() != self._hello_spec or loaded.sha256 != req.sha256\n',
        'or projection.eligible(loaded.spec)\n'
        '            or loaded.spec.to_dict() != self._hello_spec or loaded.sha256 != req.sha256\n', 1)
    start, end = source.index('  def _respond_engine('), source.index('  def on_upload_chunk(')
    source = source[:start] + RESPOND_ENGINE + source[end:]
    source = source.replace('  def _warm(self, engine, spec: ModelSpec) -> Loaded:\n',
        '  def _warm(self, engine, spec: ModelSpec) -> Loaded:\n'
        '    from jetlink.output_projection import eligible\n'
        '    if eligible(spec):\n'
        '      return EngineHost._warm_native(self, engine, spec)\n', 1)
    source = source.replace('    t0 = time.perf_counter()\n    spec = loaded.spec\n',
        '    if (getattr(self.t, "protocol_version", P.VERSION) == 2\n'
        '        and projection.eligible(loaded.spec)):\n'
        '      return self._infer_native(loaded, msg)\n'
        '    t0 = time.perf_counter()\n    spec = loaded.spec\n', 1)
    # Both native methods remain source-equivalent. They use Loaded defaults;
    # managed models never select them because their dtype contract is explicit.
    source = source.replace('def _check_shapes(engine, spec: ModelSpec) -> None:\n', 'def _check_shapes(engine, spec: ModelSpec) -> None:\n  from jetlink.output_projection import eligible\n  if eligible(spec):\n    return _check_shapes_native(engine, spec)\n', 1)
    source = source.replace('  def on_hello(self, msg: Message) -> None:\n', '  def on_hello(self, msg: Message) -> None:\n    if getattr(self.t, \"protocol_version\", P.VERSION) == 2:\n      return Session.on_hello_native(self, msg)\n', 1)
    source = source.replace('\n\nclass Session:', '\n\n' + checks + '\n\nclass Session:', 1)
    return source.replace('  def unload(self)', warm + '  def unload(self)', 1) + '\n' + infer + hello


RESPOND_ENGINE = '''  def _respond_engine(self, seq: int) -> None:
    response = self.host.status(*self._wanted())
    with self.host.lock:
      if response.get('state') == 'ready':
        loaded = self.host.loaded
        if (getattr(self.t, 'protocol_version', P.VERSION) == 3
            and (loaded is None or not loaded.valid or loaded is not self._prepared_loaded
                 or loaded is not self._hello_loaded or projection.eligible(loaded.spec)
                 or loaded.spec.to_dict() != self._hello_spec
                 or response.get('spec') != self._prepared_spec)):
          self._prepared_loaded = self._prepared_spec = None
          response = {'state': 'failed', 'detail': 'resident generation/contract not adopted; repeat HELLO and ENGINE_REQ'}
        else:
          self._prepared_loaded = loaded
          self._prepared_spec = json.loads(json.dumps(response['spec']))
    self._send_json(P.Msg.ENGINE_RESP, seq, response)

'''


# Frozen pre-native engine used only by the separately guarded managed V3 path.
MANAGED_ENGINE = '''"""
Copyright (c) 2026-, Zeph Leggett.

This file is part of jetlink and is licensed under the MIT License.
See the LICENSE file in the root directory for more details.

TensorRT execution.

Device buffers, pinned host buffers and the stream are all preallocated at load
time, so the steady state never allocates: the 50 ms frame budget is broken by
the tail, not the mean. Callers write into the pinned arrays `host_input()`
hands out, which saves a copy on the way to the GPU.
"""
from __future__ import annotations

import ctypes
import time
from dataclasses import dataclass

import numpy as np
import tensorrt as trt

from jetlink.server.backends.trt import cudart

TRT_TO_NP = {
  trt.DataType.FLOAT: np.float32,
  trt.DataType.HALF: np.float16,
  trt.DataType.INT8: np.int8,
  trt.DataType.INT32: np.int32,
  trt.DataType.INT64: np.int64,
  trt.DataType.BOOL: np.bool_,
  trt.DataType.UINT8: np.uint8,
}


@dataclass
class Binding:
  name: str
  shape: tuple[int, ...]
  dtype: np.dtype
  nbytes: int
  device_ptr: int
  host_ptr: int
  host: np.ndarray
  is_input: bool


def _np_from_ptr(ptr: int, shape, dtype) -> np.ndarray:
  """Writable numpy view over pinned host memory, so writes need no further copy.

  Through a raw byte buffer, because np.ctypeslib.as_ctypes_type cannot
  represent float16, which is most of this model.
  """
  dtype = np.dtype(dtype)
  nbytes = int(np.prod(shape)) * dtype.itemsize
  buf = (ctypes.c_char * nbytes).from_address(ptr)
  return np.frombuffer(buf, dtype=dtype).reshape(shape)


class TrtEngine:
  def __init__(self, plan_path: str, log_severity=trt.Logger.WARNING, device: int | None = None):
    self.logger = trt.Logger(log_severity)
    # Absent on a TensorRT that dropped the V2 plugin family; the driving
    # models use no plugins either way.
    init_plugins = getattr(trt, 'init_libnvinfer_plugins', None)
    if init_plugins is not None:
      init_plugins(self.logger, '')
    if device is not None:
      cudart.set_device(device)
    self.runtime = trt.Runtime(self.logger)
    with open(plan_path, 'rb') as f:
      self.engine = self.runtime.deserialize_cuda_engine(f.read())
    if self.engine is None:
      raise RuntimeError(f"failed to deserialize engine {plan_path}")
    self.context = self.engine.create_execution_context()
    self.stream = cudart.stream_create()

    self.bindings: dict[str, Binding] = {}
    for i in range(self.engine.num_io_tensors):
      name = self.engine.get_tensor_name(i)
      is_input = self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT
      shape = tuple(self.engine.get_tensor_shape(name))
      if any(d < 0 for d in shape):
        raise RuntimeError(f"tensor {name} has a dynamic shape {shape}; "
                           "jetlink builds fixed-shape engines")
      dtype = np.dtype(TRT_TO_NP[self.engine.get_tensor_dtype(name)])
      nbytes = int(np.prod(shape)) * dtype.itemsize
      dev = cudart.malloc(nbytes)
      host = cudart.host_alloc(nbytes)
      self.bindings[name] = Binding(name, shape, dtype, nbytes, int(dev), int(host),
                                    _np_from_ptr(int(host), shape, dtype), is_input)
      self.context.set_tensor_address(name, int(dev))

    self.inputs = {n: b for n, b in self.bindings.items() if b.is_input}
    self.outputs = {n: b for n, b in self.bindings.items() if not b.is_input}
    self.last_gpu_us = 0
    self.graph_exec = None

  # -- introspection --------------------------------------------------------

  @property
  def input_shapes(self) -> dict[str, tuple[int, ...]]:
    return {n: b.shape for n, b in self.inputs.items()}

  @property
  def output_shapes(self) -> dict[str, tuple[int, ...]]:
    return {n: b.shape for n, b in self.outputs.items()}

  def host_input(self, name: str) -> np.ndarray:
    """Pinned array for an input. Write into it, then call run()."""
    return self.inputs[name].host

  # -- execution ------------------------------------------------------------

  def load_inputs(self, values: dict[str, np.ndarray]) -> None:
    from jetlink.server.backends.base import load_inputs
    load_inputs(self, values)

  def _enqueue(self) -> None:
    for b in self.inputs.values():
      cudart.memcpy_h2d_async(b.device_ptr, b.host_ptr, b.nbytes, self.stream)
    if not self.context.execute_async_v3(self.stream):
      raise RuntimeError("execute_async_v3 failed")
    for b in self.outputs.values():
      cudart.memcpy_d2h_async(b.host_ptr, b.device_ptr, b.nbytes, self.stream)

  def capture_graph(self) -> bool:
    """Capture the per-frame sequence into a CUDA graph.

    A replay skips the per-launch CPU work, worth a couple of ms and most of the
    launch jitter. Valid only because no buffer ever moves. Call after at least
    one warm run.
    """
    if self.graph_exec is not None:
      return True
    try:
      cudart.stream_begin_capture(self.stream)
      self._enqueue()
      graph = cudart.stream_end_capture(self.stream)
      self.graph_exec = cudart.graph_instantiate(graph)
      cudart.graph_destroy(graph)
      return True
    except Exception:
      # Not fatal: fall back to enqueueing each frame.
      self.graph_exec = None
      return False

  def warm(self) -> str:
    """One plain run so lazy CUDA state is paid for, then the graph, then one
    replay so the steady state is never the first thing a frame does."""
    self.run()
    if self.capture_graph():
      self.run()
      return 'cuda graph captured'
    return 'cuda graph unavailable, enqueueing per frame'

  def run(self) -> dict[str, np.ndarray]:
    """Run one frame. Returns views over pinned output memory, valid until the next run."""
    t0 = time.perf_counter()
    if self.graph_exec is not None:
      cudart.graph_launch(self.graph_exec, self.stream)
    else:
      self._enqueue()
    cudart.stream_sync(self.stream)
    self.last_gpu_us = int((time.perf_counter() - t0) * 1e6)
    return {n: b.host for n, b in self.outputs.items()}

  def infer(self, values: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    self.load_inputs(values)
    return self.run()

  # No __del__: host_input() hands out views over cudaHostAlloc memory with no
  # reference back here, so a GC-driven close would free pages someone is still
  # writing into. Whoever swaps an engine out closes it.
  def close(self) -> None:
    for b in self.bindings.values():
      try:
        cudart.free(b.device_ptr)
        cudart.host_free(b.host_ptr)
      except Exception:
        pass
    self.bindings.clear()
    if self.graph_exec is not None:
      cudart.graph_exec_destroy(self.graph_exec)
      self.graph_exec = None
    try:
      cudart.stream_destroy(self.stream)
    except Exception:
      pass
'''
