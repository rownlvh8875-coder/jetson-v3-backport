#!/usr/bin/env python3
"""Build a TensorRT engine from the Cinque v3 ONNX on the Jetson.

================================================================
JETSON ONLY. Run this ON the Jetson Orin Nano Super (L4T 36.4.7,
TensorRT 10.3.0) as the `jetlink` user. It was written and reviewed
on a dev VM but NEVER executed there: there is no GPU or TensorRT
in this environment, so any claim of a VM test run would be false.
================================================================

Usage (on the Jetson):
  python3 tools/build_trt_v3.py \
    --onnx artifacts/big_driving_supercombo_v3.onnx \
    --spec artifacts/cinque_v3.json \
    --out  artifacts/cinque_v3_fp16.engine

  # with output verification against ONNX Runtime (needs onnxruntime):
  python3 tools/build_trt_v3.py --onnx ... --spec ... --out ... --verify

What it does:
  0. Refuses to build unless the ONNX sha256/size match the spec (identity gate).
  1. Parses the v3 ONNX with TensorRT's OnnxParser (opset must parse
     under TRT 10.3; if parsing fails the log names the unsupported op).
  2. Builds an FP16 engine. Workspace is capped for the Orin Nano
     Super's 8 GB unified memory (default 1536 MiB; tune with --workspace).
  3. Saves the serialized engine.
  4. --verify: runs frame(s) through the TRT engine via the TRT 10.x
     named-tensor API (set_tensor_address + execute_async_v3 on an
     explicit CUDA stream; H2D -> execute -> D2H -> synchronize) and
     checks every output is finite every frame. --frames N feeds
     next_state_* back as state_* to exercise the recurrent loop.
     With onnxruntime installed, also runs the ONNX and reports
     max/mean abs err per output; --require-max-abs-err turns the
     report into a pass/fail gate (no verified default threshold
     exists, so without it the gate is reported UNDETERMINED).

Expected cost (from the v2 experience): ~160 s build, ~1.7 GB engine
resident. Keep v2 as the default model (fail-closed); this engine is
only loaded when CARROT_JETLINK_MODEL_JSON=cinque_v3.json is set.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np


def build_engine(onnx_path: Path, engine_path: Path, workspace_mib: int,
                 fp16: bool = True) -> None:
  import tensorrt as trt

  logger = trt.Logger(trt.Logger.INFO)
  builder = trt.Builder(logger)
  network = builder.create_network(
    1 << int(trt.NetworkDefinitionCreationFlag.EXPLICIT_BATCH))
  parser = trt.OnnxParser(network, logger)
  ok = parser.parse_from_file(str(onnx_path))
  if not ok:
    for i in range(parser.num_errors):
      print(f"parser error {i}: {parser.get_error(i)}", file=sys.stderr)
    raise RuntimeError(f"ONNX parsing failed for {onnx_path}")

  config = builder.create_builder_config()
  config.set_memory_pool_limit(trt.MemoryPoolType.WORKSPACE, workspace_mib << 20)
  if fp16:
    if not builder.platform_has_fast_fp16:
      print("WARNING: platform reports no fast FP16; building FP16 anyway",
            file=sys.stderr)
    config.set_flag(trt.Flag.FP16)

  # The v3 graph is stateful: every input shape is static, no profiles needed.
  print(f"inputs : {[(i.name, tuple(i.shape), str(i.dtype)) for i in network]}",
        flush=True)
  t0 = time.monotonic()
  serialized = builder.build_serialized_network(network, config)
  dt = time.monotonic() - t0
  if serialized is None:
    raise RuntimeError("TensorRT engine build returned None")
  engine_path.write_bytes(bytes(serialized))
  print(f"built {engine_path} ({len(serialized)/2**20:.0f} MiB) in {dt:.0f}s")


def check_onnx_identity(onnx_path: Path, spec: dict) -> None:
  """Refuse to build unless the ONNX file is exactly the one the spec
  describes. A wrong ONNX + right JSON combination must never build."""
  import hashlib
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


def verify_engine(engine_path: Path, spec: dict,
                  compare_onnx: Path | None, frames: int = 1,
                  require_max_abs_err: float | None = None) -> None:
  """Run the built engine and gate on numerical behavior.

  Per frame, every output (driving outputs + all next_state_*) must be
  finite. With frames > 1 the next_state_* outputs are fed back as the
  next frame's state_* inputs, exercising the recurrent loop the server
  depends on.

  Parity vs onnxruntime (frame 0) reports max/mean abs err per output.
  require_max_abs_err turns the report into a pass/fail gate; without it
  the measurements are reported and the gate is marked UNDETERMINED --
  no arbitrary threshold is declared a verified acceptance criterion.
  """
  import tensorrt as trt

  logger = trt.Logger(trt.Logger.WARNING)
  runtime = trt.Runtime(logger)
  engine = runtime.deserialize_cuda_engine(bytes(engine_path.read_bytes()))
  context = engine.create_execution_context()

  import pycuda.driver as cuda  # noqa: E402
  import pycuda.autoinit  # noqa: E402,F401

  stream = cuda.Stream()
  host_bufs, dev_bufs = {}, {}
  for name in spec["input_shapes"]:
    dtype = _trt_dtype(trt, engine.get_tensor_dtype(name))
    shape = tuple(spec["input_shapes"][name])
    host = np.zeros(shape, dtype)
    dev = cuda.mem_alloc(host.nbytes)
    host_bufs[name], dev_bufs[name] = host, dev
    # TRT 10.x named-tensor API: no positional bindings list.
    context.set_tensor_address(name, int(dev))
  out_bufs = {}
  for name in spec["output_shapes"]:
    dtype = _trt_dtype(trt, engine.get_tensor_dtype(name))
    shape = tuple(spec["output_shapes"][name])
    host = np.empty(shape, dtype)
    dev = cuda.mem_alloc(host.nbytes)
    out_bufs[name] = (host, dev)
    context.set_tensor_address(name, int(dev))

  state_ins = [n for n in spec["input_shapes"] if n.startswith("state_")]
  state_outs = {"next_" + n: n for n in state_ins}

  def run_frame() -> dict[str, np.ndarray]:
    for name, dev in dev_bufs.items():  # H2D
      cuda.memcpy_htod_async(dev, host_bufs[name], stream)
    t0 = time.monotonic()
    ok = context.execute_async_v3(stream.handle)
    dt = (time.monotonic() - t0) * 1e3
    if not ok:
      raise RuntimeError("execute_async_v3 failed")
    for _host, dev in out_bufs.values():  # D2H
      cuda.memcpy_dtoh_async(_host, dev, stream)
    stream.synchronize()
    return ({n: host.copy() for n, (host, _dev) in out_bufs.items()}, dt)

  first_outs = None
  for f in range(frames):
    outs, ms = run_frame()
    if f == 0:
      first_outs = outs
    bad = [n for n, o in outs.items()
           if not bool(np.all(np.isfinite(o.astype(np.float32))))]
    if bad:
      raise RuntimeError(f"frame {f}: non-finite TRT outputs: {bad}")
    # recurrent feedback for the next frame
    for out_n, in_n in state_outs.items():
      np.copyto(host_bufs[in_n],
                outs[out_n].reshape(host_bufs[in_n].shape).astype(host_bufs[in_n].dtype))
    print(f"TRT frame {f}: {ms:.1f} ms, all {len(outs)} outputs finite")

  gate_failed = False
  if compare_onnx is not None:
    try:
      import onnxruntime as ort
    except ImportError:
      print("onnxruntime not installed; skipping ONNX comparison")
      compare_onnx = None
  if compare_onnx is not None:
    sess = ort.InferenceSession(str(compare_onnx),
                                providers=["CUDAExecutionProvider"])
    feeds = {n: host_bufs[n] for n in spec["input_shapes"]}
    # NOTE: feeds hold the last frame's state after the loop; reset to the
    # zero-state first frame for a like-for-like comparison with first_outs.
    for n in state_ins:
      feeds[n] = np.zeros_like(feeds[n])
    ref = dict(zip([o.name for o in sess.get_outputs()], sess.run(None, feeds)))
    for name in first_outs:
      t = first_outs[name].astype(np.float32)
      r = np.asarray(ref[name], dtype=np.float32)
      max_err = float(np.max(np.abs(t - r)))
      mean_err = float(np.mean(np.abs(t - r)))
      finite = bool(np.all(np.isfinite(t)))
      print(f"  parity {name:<22} max|err|={max_err:.3e} mean|err|={mean_err:.3e} finite={finite}")
      if require_max_abs_err is not None and max_err > require_max_abs_err:
        print(f"  GATE FAIL: {name} max err {max_err:.3e} > {require_max_abs_err:.3e}")
        gate_failed = True
    if require_max_abs_err is None:
      print("  허용오차 기준 미확정: parity gate not enforced "
            "(pass --require-max-abs-err with a documented basis to enforce)")
  if gate_failed:
    raise SystemExit("parity gate FAILED")


def main() -> None:
  ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
  ap.add_argument("--onnx", required=True, type=Path)
  ap.add_argument("--spec", required=True, type=Path,
                  help="cinque_v3.json (from spec_from_onnx)")
  ap.add_argument("--out", required=True, type=Path)
  ap.add_argument("--workspace", type=int, default=1536,
                  help="TRT workspace MiB (default 1536)")
  ap.add_argument("--no-fp16", action="store_true")
  ap.add_argument("--verify", action="store_true",
                  help="TRT run + optional ORT comparison")
  ap.add_argument("--frames", type=int, default=1,
                  help="recurrent frames for --verify (default 1; "
                       "next_state_* is fed back as state_* each frame)")
  ap.add_argument("--compare-onnx", type=Path, default=None,
                  help="with --verify, also run this ONNX in onnxruntime")
  ap.add_argument("--require-max-abs-err", type=float, default=None,
                  help="enforce the parity report as a pass/fail gate at this "
                       "max abs err; only pass a value with a documented basis "
                       "(no verified default exists: without it the gate is "
                       "reported as UNDETERMINED)")
  a = ap.parse_args()

  spec = json.loads(a.spec.read_text())
  if "new_img" not in spec["input_shapes"]:
    raise SystemExit("spec is not stateful (no new_img); refusing to build v3 engine")
  check_onnx_identity(a.onnx, spec)
  build_engine(a.onnx, a.out, a.workspace, fp16=not a.no_fp16)
  if a.verify:
    verify_engine(a.out, spec, a.compare_onnx or a.onnx,
                  frames=a.frames, require_max_abs_err=a.require_max_abs_err)


if __name__ == "__main__":
  main()
