"""Stateful safety tests: fail-closed behavior of the v3 backport.

Covers review items 13A-13G (negative/fault-injection) and item 12
(multi-frame recurrent parity against the real ONNX via onnxruntime).

Run: python3 tests/test_stateful_safety.py
The multi-frame section needs onnxruntime and artifacts/big_driving_supercombo_v3.onnx;
it is skipped (not failed) when either is absent. The 766 MB ONNX is never committed.

What is verified here (software, this VM):
 - next_state NaN/Inf -> StateValidationError, state buffers untouched (A, B)
 - transposed-but-same-nelem shape -> engine load refused (C)
 - missing next_state_* -> validation refused (D)
 - one bad state mid-update -> all three states unchanged, atomic (E)
 - reset() zeroes all three states (F)
 - warm pre-condition: reset + step_into leaves states at zero (G)
 - 5-frame recurrent loop on the REAL v3 ONNX: every frame finite,
   state actually evolves, validate+commit path matches direct feedback (12)

What is NOT verified here (needs the Jetson):
 - TensorRT engine build and TRT<->ORT numerical parity
 - on-vehicle behavior
"""
import json
import sys
import types
from importlib.machinery import SourceFileLoader
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from jetlink.spec import ModelSpec  # noqa: E402
from jetlink.queues import StatefulState, StateValidationError  # noqa: E402

PASS = []
FAIL = []


def check(name, cond, detail=""):
  (PASS if cond else FAIL).append(name)
  print(("PASS " if cond else "FAIL ") + name + (f" [{detail}]" if detail and not cond else ""))


def load_v3():
  d = json.loads((ROOT / "artifacts" / "cinque_v3.json").read_text())
  return ModelSpec.from_dict(d)


def make_state(spec, dtype_map=None):
  """Host input buffers like the engine's pinned staging arrays."""
  bufs = {}
  for n, s in spec.input_shapes.items():
    dt = np.dtype(dtype_map[n]) if dtype_map and n in dtype_map else None
    if dt is None:
      dt = np.dtype(spec.input_dtypes[n]) if n in spec.input_dtypes else np.float32
    bufs[n] = np.zeros(s, dt)
  return bufs


def good_outputs(spec, rng):
  out = {}
  for n, s in spec.output_shapes.items():
    dt = np.dtype(spec.output_dtypes.get(n, "float32"))
    if dt == np.dtype("uint8"):
      out[n] = rng.integers(0, 256, size=s).astype(np.uint8)
    else:
      out[n] = rng.standard_normal(s).astype(np.float32)
  return out


def snapshot(bufs, spec):
  return {n: bufs[n].copy() for n, _ in spec.state_pairs}


def states_equal(a, b, spec):
  return all(np.array_equal(a[n], b[n]) for n, _ in spec.state_pairs)


spec = load_v3()
rng = np.random.default_rng(42)

# --- Test F: reset zeroes all three states ----------------------------------
bufs = make_state(spec)
st = StatefulState(spec, bufs)
for n, _ in spec.state_pairs:
  bufs[n][...] = 7  # poison
st.reset()
check("F: reset zeroes state_img_q", not bufs["state_img_q"].any())
check("F: reset zeroes state_desire_q", not bufs["state_desire_q"].any())
check("F: reset zeroes state_feat_q", not bufs["state_feat_q"].any())

# --- Test G: warm pre-condition (reset -> step_into leaves states at zero) --
bufs = make_state(spec)
st = StatefulState(spec, bufs)
for n, _ in spec.state_pairs:
  bufs[n][...] = 13  # simulate garbage left in pinned buffers
st.reset()  # the item-5 fix: warm() must start from here
warped = np.zeros(spec.warped_shape, np.uint8)
packed = np.zeros(spec.packed_nelem, np.float32)
st.step_into(warped, packed, bufs)  # must not touch state_* inputs
check("G: states zero before warm", all(not bufs[n].any() for n, _ in spec.state_pairs))

# --- Test A: NaN in next_state_feat_q -> reject, no commit -------------------
bufs = make_state(spec)
st = StatefulState(spec, bufs)
sentinel = {n: np.full(bufs[n].shape, 3, dtype=bufs[n].dtype) for n, _ in spec.state_pairs}
for n in sentinel:
  bufs[n][...] = sentinel[n]
outs = good_outputs(spec, rng)
outs["next_state_feat_q"][0, 0, 0] = np.nan
before = snapshot(bufs, spec)
try:
  st.after_run(outs)
  check("A: NaN state raises", False, "no exception")
except StateValidationError:
  check("A: NaN state raises", True)
check("A: state untouched on NaN", states_equal(before, snapshot(bufs, spec), spec))

# --- Test B: Inf in next_state_img_q -> reject, no commit --------------------
# (uint8 cannot hold Inf; inject via float32 to exercise the finite gate
# the same way a misbehaving engine output would.)
bufs = make_state(spec)
st = StatefulState(spec, bufs)
for n in sentinel:
  bufs[n][...] = sentinel[n]
outs = good_outputs(spec, rng)
bad = outs["next_state_img_q"].astype(np.float32)
bad.flat[0] = np.inf
outs["next_state_img_q"] = bad
before = snapshot(bufs, spec)
try:
  st.after_run(outs)
  check("B: Inf state raises", False, "no exception")
except StateValidationError:
  check("B: Inf state raises", True)
check("B: state untouched on Inf", states_equal(before, snapshot(bufs, spec), spec))

# --- Test E: one invalid state mid-update -> ALL states unchanged (atomic) ---
bufs = make_state(spec)
st = StatefulState(spec, bufs)
for n in sentinel:
  bufs[n][...] = sentinel[n]
outs = good_outputs(spec, rng)
# poison the SECOND pair's output only; the first would already be staged
_, second_out = spec.state_pairs[1]
o = outs[second_out].astype(np.float32)
o.flat[0] = np.nan
outs[second_out] = o.astype(outs[second_out].dtype)
before = snapshot(bufs, spec)
try:
  st.after_run(outs)
  check("E: mid-update invalid raises", False, "no exception")
except StateValidationError:
  check("E: mid-update invalid raises", True)
check("E: all three states unchanged (atomic)", states_equal(before, snapshot(bufs, spec), spec))

# --- validate/commit split: good outputs commit all three -------------------
bufs = make_state(spec)
st = StatefulState(spec, bufs)
outs = good_outputs(spec, rng)
staged = st.validate_next_states(outs)
check("validate returns 3 staged", len(staged) == 3, str(len(staged)))
st.commit_next_states(staged)
ok = all(np.array_equal(bufs[i], np.asarray(outs[o]).reshape(bufs[i].shape))
         for i, o, _ in staged)
check("commit writes all three states", ok)

# --- Test D: missing next_state_desire_q -> validation refuses --------------
bufs = make_state(spec)
st = StatefulState(spec, bufs)
outs = good_outputs(spec, rng)
del outs["next_state_desire_q"]
try:
  st.validate_next_states(outs)
  check("D: missing state output raises", False, "no exception")
except StateValidationError as e:
  check("D: missing state output raises", "missing" in str(e), str(e))

# --- Test C + D via _check_shapes (engine load contract) --------------------
# session.py.new is not importable directly (server deps); load the module
# with light stubs, like the production backend provides IO.shape/.dtype.
_stub_defs = {
  "jetlink.server": [],
  "jetlink.server.backends": [],
  "jetlink.server.backends.base": ["ArtifactInvalid"],
  "jetlink.server.cache": ["CacheEntry", "EngineCache"],
  "jetlink.server.telemetry": ["CachedTelemetry", "NoTelemetry"],
  "jetlink.transport": [],
  "jetlink.transport.base": ["LinkError", "LinkTimeout", "Message", "Transport"],
  "jetlink.server.power": ["request_poweroff"],
}
for _name, _attrs in _stub_defs.items():
  _m = types.ModuleType(_name)
  for _a in _attrs:
    setattr(_m, _a, type(_a, (Exception,), {}) if ("Error" in _a or "Timeout" in _a) else type(_a, (), {}))
  sys.modules[_name] = _m
_sess = SourceFileLoader("sessnew", str(ROOT / "patches" / "session.py.new")).load_module()
_check_shapes = _sess._check_shapes


def fake_engine(spec, overrides=None):
  from collections import namedtuple
  IO = namedtuple("IO", ["shape", "dtype"])
  ov = overrides or {}
  return types.SimpleNamespace(
    inputs={n: IO(ov.get(("in", n), s), np.dtype(spec.input_dtypes.get(n, "float32")))
            for n, s in spec.input_shapes.items()},
    outputs={n: IO(ov.get(("out", n), s), np.dtype(spec.output_dtypes.get(n, "float32")))
             for n, s in spec.output_shapes.items()})


def expect_raise(label, fn):
  try:
    fn()
    check(label, False, "no exception")
  except ValueError:
    check(label, True)


_check_shapes(fake_engine(spec), spec)
check("C/D: exact contract passes", True)
# Test C: same element count, transposed dims -> must fail
expect_raise("C: transposed (128,16384,1) refused",
             lambda: _check_shapes(
               fake_engine(spec, {("out", "next_state_feat_q"): (128, 16384, 1)}), spec))
# Test D: missing output tensor -> must fail
eng = fake_engine(spec)
del eng.outputs["next_state_desire_q"]
expect_raise("D: missing output refused", lambda: _check_shapes(eng, spec))
# unexpected extra tensor -> must fail
eng = fake_engine(spec)
from collections import namedtuple as _nt
_IO = _nt("IO", ["shape", "dtype"])
eng.inputs["bogus"] = _IO((1,), np.dtype("float32"))
expect_raise("unexpected input refused", lambda: _check_shapes(eng, spec))
# dtype mismatch -> must fail
def _dtype_mismatch_case():
  from collections import namedtuple as _nt
  IO = _nt("IO", ["shape", "dtype"])
  eng = types.SimpleNamespace(
    inputs={n: IO(s, np.dtype("int32")) for n, s in spec.input_shapes.items()},
    outputs={n: IO(s, np.dtype(spec.output_dtypes.get(n, "float32")))
             for n, s in spec.output_shapes.items()})
  _check_shapes(eng, spec)


expect_raise("dtype mismatch refused", _dtype_mismatch_case)


# --- Item 3: validate_stateful strictness ------------------------------------
# v3 passes the strict contract
try:
  pairs = spec.validate_stateful()
  check("3: v3 validate_stateful passes", len(pairs) == 3)
except ValueError as e:
  check("3: v3 validate_stateful passes", False, str(e))

# orphan state_* input (no next_ output) -> must fail, not be ignored
import copy as _copy
d = json.loads((ROOT / "artifacts" / "cinque_v3.json").read_text())
d["input_shapes"]["state_bogus"] = [4]
d["input_dtypes"]["state_bogus"] = "float32"
try:
  ModelSpec.from_dict(d).validate_stateful()
  check("3: orphan state_* input refused", False, "no exception")
except ValueError:
  check("3: orphan state_* input refused", True)

# shape-mismatched pair -> must fail (not silently admitted)
d = json.loads((ROOT / "artifacts" / "cinque_v3.json").read_text())
d["output_shapes"]["next_state_feat_q"] = [128, 16384, 1]  # same nelem, wrong order
try:
  ModelSpec.from_dict(d).validate_stateful()
  check("3: shape-mismatched pair refused", False, "no exception")
except ValueError:
  check("3: shape-mismatched pair refused", True)

# dtype-mismatched pair -> must fail
d = json.loads((ROOT / "artifacts" / "cinque_v3.json").read_text())
d["output_dtypes"]["next_state_feat_q"] = "float16"
try:
  ModelSpec.from_dict(d).validate_stateful()
  check("3: dtype-mismatched pair refused", False, "no exception")
except ValueError:
  check("3: dtype-mismatched pair refused", True)

# --- Item 12: multi-frame recurrent parity on the REAL v3 ONNX ---------------
V3_ONNX = ROOT / "artifacts" / "big_driving_supercombo_v3.onnx"
try:
  import onnxruntime as ort  # noqa: E402
  _have_ort = True
except ImportError:
  _have_ort = False

if _have_ort and V3_ONNX.exists():
  sess = ort.InferenceSession(str(V3_ONNX), providers=["CPUExecutionProvider"])
  out_names = [o.name for o in sess.get_outputs()]
  bufs = make_state(spec)
  st = StatefulState(spec, bufs)
  st.reset()
  r = np.random.default_rng(7)
  n_frames = 5
  frames_ok = True
  evolved = False
  prev_feat = None
  for f in range(n_frames):
    feeds = {
      "new_img": r.integers(0, 256, size=spec.input_shapes["new_img"]).astype(np.uint8),
      "desire": r.standard_normal(spec.input_shapes["desire"]).astype(np.float32),
      "traffic_convention": np.zeros(spec.input_shapes["traffic_convention"], np.float32),
      "action_t": np.zeros(spec.input_shapes["action_t"], np.float32),
      "state_img_q": bufs["state_img_q"],
      "state_desire_q": bufs["state_desire_q"],
      "state_feat_q": bufs["state_feat_q"],
    }
    outs = dict(zip(out_names, sess.run(None, feeds)))
    # every output incl. all three next_state_* finite, like the server gate
    if not all(bool(np.all(np.isfinite(np.asarray(o, dtype=np.float32)))) for o in outs.values()):
      frames_ok = False
      break
    # commit through the real validate+commit path (what session.py does)
    staged = st.validate_next_states(outs)
    st.commit_next_states(staged)
    # the committed state must equal the model's own next_state (feedback)
    for state_in, state_out, _ in staged:
      if not np.array_equal(bufs[state_in], np.asarray(outs[state_out]).reshape(bufs[state_in].shape)):
        frames_ok = False
    cur_feat = bufs["state_feat_q"].copy()
    if prev_feat is not None and not np.array_equal(cur_feat, prev_feat):
      evolved = True
    prev_feat = cur_feat
  check("12: 5-frame recurrent loop all finite", frames_ok)
  check("12: state evolves frame to frame", evolved)
  check("12: committed state == model next_state", frames_ok)
else:
  print("SKIP item-12 multi-frame test (need onnxruntime + local v3 ONNX)")

print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
