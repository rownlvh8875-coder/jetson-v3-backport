"""Backport verification: stateful (Cinque Terre V3) support.

Run: python3 tests/test_backport.py  (network needed for the lfs test)

What is verified here:
 1. spec.py: stateful detection, state pairs, packed layout, wire sizes,
    for both layouts, against upstream's fixtures and the real v2 spec.
 2. queues.py StatefulState: input building, state feedback, reset,
    with synthetic data (layout-agnostic logic).
 3. registry/lfs.py: export-pointer fallback resolves the real V3 commit
    to its real ONNX oid/size via the live HuggingFace API.

What is NOT verified here (needs the Jetson + the real 766 MB ONNX):
 - spec_from_onnx on the real v3 ONNX (tensor names/shapes ground truth)
 - TensorRT 10.3 engine build of the v3 ONNX
 - session.py/model.py patches (specified, not executed here)
 - on-vehicle behavior
"""
import json
import math
import sys
import urllib.request
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# The backport tree carries only the files under test plus their stdlib-only
# deps; keep the registry package __init__ (which pulls the server runtime)
# out of the import.
import types  # noqa: E402

_stub = types.ModuleType("jetlink.registry")
_stub.__path__ = [str(ROOT / "jetlink" / "registry")]
sys.modules["jetlink.registry"] = _stub

from jetlink.spec import ModelSpec, STATEFUL_FRAME  # noqa: E402
from jetlink.queues import PolicyQueues, StatefulState  # noqa: E402
from jetlink.registry.lfs import fetch_pointer  # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
  (PASS if cond else FAIL).append(name)
  print(("PASS " if cond else "FAIL ") + name + (f" [{detail}]" if detail and not cond else ""))


def load_spec(name):
  return ModelSpec.from_dict(json.loads((ROOT / "tests" / name).read_text()))


# --- 1. spec.py -------------------------------------------------------------
v2 = load_spec("cinque_v2.json")          # real Cinque v2, queued
tq = load_spec("tiny_queued.spec.json")   # upstream queued fixture
ts = load_spec("tiny_stateful.spec.json")  # upstream stateful fixture

check("v2 not stateful", not v2.stateful)
check("v2 state_pairs empty", v2.state_pairs == [])
check("v2 packed has prev_feat", "prev_feat" in v2.packed_shapes)
check("v2 wire sizes sane", v2.infer_req_nbytes > 0 and v2.infer_resp_nbytes > 0)

check("tiny queued not stateful", not tq.stateful)
check("tiny stateful detected", ts.stateful)
pairs = dict(ts.state_pairs)
check("state pairs", pairs == {
  "state_img_q": "next_state_img_q",
  "state_desire_q": "next_state_desire_q",
  "state_feat_q": "next_state_feat_q",
}, str(pairs))
check("stateful packed has no prev_feat", "prev_feat" not in ts.packed_shapes)
check("stateful packed keys", set(ts.packed_shapes) == {"desire", "traffic_convention", "action_t"})
check("stateful model_hw", ts.model_hw == (8, 16), str(ts.model_hw))
check("stateful warped_shape", ts.warped_shape == (2, 6, 8, 16))
check("roundtrip to_dict/from_dict", ModelSpec.from_dict(ts.to_dict()).to_dict() == ts.to_dict())
# queued spec must be untouched by the backport
check("queued packed layout", set(tq.packed_shapes) == {"desire", "traffic_convention", "action_t", "prev_feat"})

# --- 2. queues.py StatefulState ----------------------------------------------
spec = ts
rng = np.random.default_rng(0)

# fake pinned buffers like the TRT engine's host_input()
dest = {n: np.zeros(s, np.float16) for n, s in spec.input_shapes.items()}
st = StatefulState(spec, dest)
st.reset()
check("reset zeros states", all(not dest[i].any() for i, _ in spec.state_pairs))

warped = rng.integers(0, 256, size=spec.warped_shape).astype(np.uint8)
packed = rng.standard_normal(spec.packed_nelem).astype(np.float32)
st.step_into(warped, packed, dest)
check("new_img written", dest[STATEFUL_FRAME].shape == spec.input_shapes[STATEFUL_FRAME]
      and dest[STATEFUL_FRAME].any())
check("desire written", dest["desire"].shape == spec.input_shapes["desire"])
# states untouched by step_into (still zeros)
check("states preserved across step", all(not dest[i].any() for i, _ in spec.state_pairs))

# fake engine outputs; after_run must feed next_* back into state_*
# (tolerant: the pinned state buffers are float16, outputs float32)
outputs = {n: rng.standard_normal(s).astype(np.float32) for n, s in spec.output_shapes.items()}
st.after_run(outputs)
ok = True
for state_in, state_out in spec.state_pairs:
  if not np.allclose(dest[state_in].astype(np.float32), outputs[state_out].reshape(dest[state_in].shape),
                     rtol=1e-2, atol=1e-2):
    ok = False
check("after_run feeds states back", ok)

# second frame: states are now non-zero and carried forward
warped2 = rng.integers(0, 256, size=spec.warped_shape).astype(np.uint8)
st.step_into(warped2, packed, dest)
check("states persist to next frame", all(dest[i].any() for i, _ in spec.state_pairs))
st.reset()
check("reset clears again", all(not dest[i].any() for i, _ in spec.state_pairs))

# PolicyQueues still constructs for queued (regression)
pq = PolicyQueues(tq)
check("PolicyQueues queued ok", pq is not None)

# --- 3. registry/lfs.py: live V3 resolution ----------------------------------
V3_REF = "bf3e3631b3f91d92a1020a5e0dd4298b93ff4244"  # "Use f78ed37d for the precompiled eGPU driving model"
V3_OID = "404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4"
V3_SIZE = 766354845
try:
  p = fetch_pointer(V3_REF, opener=urllib.request.urlopen)
  check("v3 export fallback oid", p.oid == V3_OID, p.oid[:16])
  check("v3 export fallback size", p.size == V3_SIZE, str(p.size))
except Exception as e:  # noqa: BLE001
  check("v3 export fallback (network)", False, f"{type(e).__name__}: {e}")

# v2 ref must still resolve through the normal in-tree path (regression)
try:
  p2 = fetch_pointer("37bfa1413edcdc2e8844984b83727c33f81d8f46", opener=urllib.request.urlopen)
  check("v2 in-tree pointer", p2.oid == "09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec"
        and p2.size == 766040736, p2.oid[:16])
except Exception as e:  # noqa: BLE001
  check("v2 in-tree pointer (network)", False, f"{type(e).__name__}: {e}")

print(f"\n{PASS.__len__()} passed, {FAIL.__len__()} failed")
sys.exit(1 if FAIL else 0)
