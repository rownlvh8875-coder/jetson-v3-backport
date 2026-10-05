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
  1. Parses the v3 ONNX with TensorRT's OnnxParser (opset must parse
     under TRT 10.3; if parsing fails the log names the unsupported op).
  2. Builds an FP16 engine. Workspace is capped for the Orin Nano
     Super's 8 GB unified memory (default 1536 MiB; tune with --workspace).
  3. Saves the serialized engine.
  4. --verify: runs one zero-input frame through the TRT engine and
     checks every output is finite; if onnxruntime is installed, also
     runs the ONNX and reports max abs diff per output.

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


def _trt_dtype(trt, dtype) -> np.dtype:
  return {
    trt.float32: np.float32, trt.float16: np.float16, trt.int32: np.int32,
    trt.int64: np.int64, trt.uint8: np.uint8, trt.bool: np.bool_,
  }[dtype]


def verify_engine(engine_path: Path, spec: dict,
                  compare_onnx: Path | None) -> None:
  import tensorrt as trt

  logger = trt.Logger(trt.Logger.WARNING)
  runtime = trt.Runtime(logger)
  engine = runtime.deserialize_cuda_engine(bytes(engine_path.read_bytes()))
  context = engine.create_execution_context()

  import pycuda.driver as cuda  # noqa: E402
  import pycuda.autoinit  # noqa: E402,F401

  bindings = []
  host_bufs, dev_bufs = {}, {}
  for name in spec["input_shapes"]:
    dtype = _trt_dtype(trt, engine.get_tensor_dtype(name))
    shape = tuple(spec["input_shapes"][name])
    host = np.zeros(shape, dtype)
    dev = cuda.mem_alloc(host.nbytes)
    host_bufs[name], dev_bufs[name] = host, dev
    bindings.append(int(dev))
    context.set_tensor_address(name, int(dev))
  out_bufs = {}
  for name in spec["output_shapes"]:
    dtype = _trt_dtype(trt, engine.get_tensor_dtype(name))
    shape = tuple(spec["output_shapes"][name])
    host = np.empty(shape, dtype)
    dev = cuda.mem_alloc(host.nbytes)
    out_bufs[name] = (host, dev)
    bindings.append(int(dev))
    context.set_tensor_address(name, int(dev))

  for name, dev in dev_bufs.items():  # zero state = first frame
    cuda.memcpy_htod(dev, host_bufs[name])
  t0 = time.monotonic()
  ok = context.execute_v3(bindings)
  dt = (time.monotonic() - t0) * 1e3
  assert ok, "execute_v3 failed"
  print(f"TRT infer: {dt:.1f} ms")
  all_finite = True
  for name, (host, dev) in out_bufs.items():
    cuda.memcpy_dtoh(host, dev)
    finite = bool(np.all(np.isfinite(host.astype(np.float32))))
    all_finite &= finite
    print(f"  out {name:<22} shape={host.shape} finite={finite}")
  if not all_finite:
    raise RuntimeError("non-finite TRT outputs on zero input")

  if compare_onnx is not None:
    try:
      import onnxruntime as ort
    except ImportError:
      print("onnxruntime not installed; skipping ONNX comparison")
      return
    sess = ort.InferenceSession(str(compare_onnx),
                                providers=["CUDAExecutionProvider"])
    feeds = {n: host_bufs[n] for n in spec["input_shapes"]}
    ref = sess.run(None, feeds)
    for (name, _), r in zip(out_bufs.items(), ref):
      host, _ = out_bufs[name]
      diff = float(np.max(np.abs(host.astype(np.float32)
                                - r.astype(np.float32))))
      print(f"  diff {name:<22} max|trt-ort| = {diff:.3e}")


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
                  help="zero-input TRT run + optional ORT comparison")
  ap.add_argument("--compare-onnx", type=Path, default=None,
                  help="with --verify, also run this ONNX in onnxruntime")
  a = ap.parse_args()

  spec = json.loads(a.spec.read_text())
  if "new_img" not in spec["input_shapes"]:
    raise SystemExit("spec is not stateful (no new_img); refusing to build v3 engine")
  build_engine(a.onnx, a.out, a.workspace, fp16=not a.no_fp16)
  if a.verify:
    verify_engine(a.out, spec, a.compare_onnx or a.onnx)


if __name__ == "__main__":
  main()
