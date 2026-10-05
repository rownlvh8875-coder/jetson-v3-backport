#!/usr/bin/env python3
"""Generate artifacts/cinque_v3.json from the real v3 ONNX.

Reads ONLY tensor metadata (names/shapes/dtypes) plus metadata_props;
the 766 MB of weights are never loaded (see tools/onnx_meta_light.py).

Nothing here is fabricated: every field comes from the downloaded file,
whose sha256/size are checked against the known-good values first.

Usage:
  /tmp/onnxenv/bin/python tools/gen_cinque_v3_json.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tools"))

from onnx_meta_light import parse_meta_light  # noqa: E402
from jetlink.onnx_meta import OnnxMeta  # noqa: E402
from jetlink.spec import spec_from_meta, sha256_file  # noqa: E402

# Known-good values (REPORT.md: measured against HuggingFace)
EXPECT_SHA256 = "404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4"
EXPECT_NBYTES = 766354845
EXPECT_OUTPUT_NELEM = 18452

ONNX_PATH = ROOT / "artifacts" / "big_driving_supercombo_v3.onnx"
OUT_PATH = ROOT / "artifacts" / "cinque_v3.json"


def main() -> None:
  if not ONNX_PATH.exists():
    raise SystemExit(f"missing {ONNX_PATH}; download it first")

  sha, nbytes = sha256_file(str(ONNX_PATH))
  print(f"sha256: {sha}\nsize:   {nbytes}")
  if sha != EXPECT_SHA256:
    raise SystemExit(f"SHA256 MISMATCH: expected {EXPECT_SHA256}")
  if nbytes != EXPECT_NBYTES:
    raise SystemExit(f"SIZE MISMATCH: expected {EXPECT_NBYTES}")

  raw = parse_meta_light(str(ONNX_PATH))
  meta = OnnxMeta(
    inputs={n: s for n, (s, _) in raw["inputs"].items()},
    outputs={n: s for n, (s, _) in raw["outputs"].items()},
    input_types={n: t for n, (_, t) in raw["inputs"].items()},
    output_types={n: t for n, (_, t) in raw["outputs"].items()},
    props=raw["props"],
  )
  spec = spec_from_meta(meta, sha, nbytes)

  # --- sanity checks (fail loudly, never fabricate) ---
  assert spec.stateful, "v3 spec is not stateful (no new_img input)"
  pairs = spec.state_pairs
  assert len(pairs) == 3, f"expected 3 state pairs, got {pairs}"
  assert spec.output_shapes.get("outputs") is not None, "no 'outputs' output"
  assert spec.output_nelem == EXPECT_OUTPUT_NELEM, (
    f"outputs nelem {spec.output_nelem} != {EXPECT_OUTPUT_NELEM}")
  assert "desire" in spec.input_shapes, "no 'desire' input"
  assert "prev_feat" not in spec.packed_shapes, "stateful packed must not have prev_feat"
  assert set(spec.packed_shapes) == {"desire", "traffic_convention", "action_t"}, (
    f"unexpected packed keys: {set(spec.packed_shapes)}")
  # output_slices must come from the file's own metadata_props.
  # Note: v3 keeps the same outputs slice layout as v2 (hidden_state
  # 2066..18450 included); the difference is the comma no longer feeds
  # it back, the graph keeps its own state. Slices are ground truth here.
  assert "output_slices" in raw["props"], "model has no output_slices metadata"

  print("stateful:", spec.stateful)
  print("state_pairs:", pairs)
  print("model_hw:", spec.model_hw)
  print("checkpoint:", spec.checkpoint)
  print("packed:", {k: v for k, v in spec.packed_shapes.items()})

  OUT_PATH.write_text(json.dumps(spec.to_dict(), indent=2) + "\n")
  print(f"wrote {OUT_PATH}")


if __name__ == "__main__":
  main()
