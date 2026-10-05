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
 - one bad state mid-update -> validation failure leaves all states
   unchanged (E; validation-level atomicity, not transactional rollback)
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

# --- Test G: real EngineHost._warm() regression test --------------------------
# Calls the actual _warm() (not just reset/step_into) with a fake engine,
# so a future warm-order regression is caught. The fake's warm() asserts
# the three states are zero AT WARM TIME; after _warm returns they must be
# zero again (post-warm reset).
bufs = make_state(spec)
for n, _ in spec.state_pairs:
  bufs[n][...] = 13  # simulate garbage left in pinned buffers

from collections import namedtuple as _nt2
_WarmIO = _nt2("WarmIO", ["shape", "dtype"])


class _FakeWarmEngine:
  def __init__(self, spec, bufs):
    self._bufs = bufs
    self.inputs = {n: _WarmIO(s, np.dtype(spec.input_dtypes.get(n, "float32")))
                   for n, s in spec.input_shapes.items()}
    self.outputs = {n: _WarmIO(s, np.dtype(spec.output_dtypes.get(n, "float32")))
                    for n, s in spec.output_shapes.items()}
    self.warm_saw_zero = None

  def host_input(self, n):
    return self._bufs[n]

  def warm(self):
    self.warm_saw_zero = all(not self._bufs[n].any()
                             for n, _ in spec.state_pairs)
    return "warmed"


_fake_self = types.SimpleNamespace(
  backend=None,
  _backend_dtype_transforms=lambda: None)  # no dtype retypes declared
_feng = _FakeWarmEngine(spec, bufs)
_loaded = _sess.EngineHost._warm(_fake_self, _feng, spec)
check("G: engine.warm ran with zeroed states", _feng.warm_saw_zero is True)
check("G: states zero after _warm (post-warm reset)",
      all(not bufs[n].any() for n, _ in spec.state_pairs))
check("G: _warm returns Loaded for this spec",
      _loaded.spec.sha256 == spec.sha256)

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

# --- Test B: Inf in next_state_feat_q (float) -> reject, no commit ---------
# NOTE (review item 7): the finite gate must be exercised on a FLOAT state.
# next_state_img_q is uint8 and cannot hold Inf; injecting Inf there via a
# float32 cast trips the dtype gate first, so it would not test finiteness.
bufs = make_state(spec)
st = StatefulState(spec, bufs)
for n in sentinel:
  bufs[n][...] = sentinel[n]
outs = good_outputs(spec, rng)
outs["next_state_feat_q"][0, 0, 0] = np.inf  # float32: exercises the finite gate
before = snapshot(bufs, spec)
try:
  st.after_run(outs)
  check("B: Inf state raises", False, "no exception")
except StateValidationError:
  check("B: Inf state raises", True)
check("B: state untouched on Inf", states_equal(before, snapshot(bufs, spec), spec))

# --- dtype mismatch is a SEPARATE gate (dedicated test, not Test B) ---------
# Documents the current same_kind boundary: a genuinely incompatible dtype
# (complex) is refused; same-kind narrowing (float64->float32) is allowed
# pending the Jetson engine-dtype measurement (review item 5).
bufs = make_state(spec)
st = StatefulState(spec, bufs)
outs = good_outputs(spec, rng)
outs["next_state_feat_q"] = np.zeros_like(outs["next_state_feat_q"],
                                          dtype=np.complex64)
try:
  st.validate_next_states(outs)
  check("dtype: complex64 state output refused", False, "no exception")
except StateValidationError as e:
  check("dtype: complex64 state output refused", "dtype" in str(e), str(e))

# --- Test E: validation failure leaves all states unchanged ------------------
# (review item 8: renamed from "atomic commit". This proves validation-level
# atomicity -- a failed validation never starts the commit phase -- not a
# transactional rollback of the copy phase itself.)
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
check("E: validation failure leaves all states unchanged",
      states_equal(before, snapshot(bufs, spec), spec))

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

# --- Item 3: v3 uint8 patch -- ORT parity patched vs original ----------------
# tools/patch_v3_uint8.py retypes new_img/state_img_q to fp16. The queue ops
# are pure data movement and 0..255 is exactly representable in fp16, so the
# patched model must be BIT-IDENTICAL to the original across recurrent
# frames. Verified here by measurement, not claimed from the range alone.
# Skipped (not failed) without onnx+onnxruntime or the local v3 ONNX.
try:
    import onnx as _onnx  # noqa: F401
    from importlib.machinery import SourceFileLoader as _SFL
    _patch_mod = _SFL("patch_v3_uint8",
                      str(ROOT / "tools" / "patch_v3_uint8.py")).load_module()
    _have_patch_deps = True
except ImportError:
    _have_patch_deps = False

if _have_ort and _have_patch_deps and V3_ONNX.exists():
    import tempfile as _tf2
    _td2 = _tf2.mkdtemp(dir=str(ROOT / "artifacts"))
    try:
        _patched_path = str(Path(_td2) / "v3_patched.onnx")
        _retypes = _patch_mod.patch_file_v3(str(V3_ONNX), _patched_path)
        check("3: patch returns retype record",
              _retypes == {"new_img": "float16", "state_img_q": "float16",
                           "next_state_img_q": "float16"}, str(_retypes))
        _r = np.random.default_rng(11)
        _img = _r.integers(0, 256, size=spec.input_shapes["new_img"]).astype(np.uint8)
        _des = _r.standard_normal(spec.input_shapes["desire"]).astype(np.float32)

        def _run(p, as_fp16, n=3):
            s, onames = ort.InferenceSession(p, providers=["CPUExecutionProvider"]), None
            s, onames = s, [o.name for o in s.get_outputs()]
            st = {}
            for n_ in spec.input_shapes:
                if n_.startswith("state_"):
                    dt = np.float16 if (as_fp16 and "img" in n_) else np.dtype(spec.input_dtypes[n_])
                    st[n_] = np.zeros(spec.input_shapes[n_], dt)
            outs_all = []
            for _f in range(n):
                feeds = {"new_img": _img.astype(np.float16) if as_fp16 else _img,
                         "desire": _des,
                         "traffic_convention": np.zeros(spec.input_shapes["traffic_convention"], np.float32),
                         "action_t": np.zeros(spec.input_shapes["action_t"], np.float32),
                         **st}
                outs = dict(zip(onames, s.run(None, feeds)))
                outs_all.append({k: np.asarray(v) for k, v in outs.items()})
                for s_in, s_out in spec.state_pairs:
                    st[s_in] = np.asarray(outs[s_out]).reshape(
                        spec.input_shapes[s_in]).astype(st[s_in].dtype)
            return outs_all, onames

        _orig_outs, _onames = _run(str(V3_ONNX), False)
        _patched_outs, _pnames = _run(_patched_path, True)
        _exact = all(
            np.array_equal(_orig_outs[f][n].astype(np.float32),
                           _patched_outs[f][n].astype(np.float32))
            for f in range(3) for n in _onames)
        _finite = all(bool(np.all(np.isfinite(o.astype(np.float32))))
                      for fr in _patched_outs for o in fr.values())
        check("3: patched vs original bit-exact (3 recurrent frames)", _exact)
        check("3: patched outputs all finite", _finite)
    finally:
        import shutil as _sh
        _sh.rmtree(_td2, ignore_errors=True)
else:
    print("SKIP item-3 patch parity test (need onnx+onnxruntime + local v3 ONNX)")


# --- Item 4: v2 fresh-build dtype regression --------------------------------
# Production onnx_patch.py retypes v2's img/big_img uint8->fp16 at build
# time. The old _check_shapes compared the engine's fp16 directly against
# the spec's ONNX uint8 and would REJECT a legitimately rebuilt v2 engine.
# The fix: the backend declares its intentional transforms; the engine must
# match THOSE exactly. Undeclared/wrong retypes still fail (nothing loosened).
_v2d = json.loads((ROOT / "tests" / "cinque_v2.json").read_text())
# v2 ONNX dtypes: img/big_img are uint8 (this is WHY production's patcher
# exists); the scalar/feature inputs and outputs are float32.
_v2d["input_dtypes"] = {"img": "uint8", "big_img": "uint8",
                        "desire_pulse": "float32", "traffic_convention": "float32",
                        "action_t": "float32", "features_buffer": "float32"}
_v2d["output_dtypes"] = {"outputs": "float32"}
v2spec = ModelSpec.from_dict(_v2d)

# fake engine as production's patch would leave it: img/big_img fp16
_v2eng = fake_engine(v2spec, {})
for _n in ("img", "big_img"):
    _v2eng.inputs[_n] = _v2eng.inputs[_n]._replace(dtype=np.dtype("float16"))

# without declared transforms: the regression -- legit engine rejected
expect_raise("4: v2 fresh-build rejected without declared transforms",
             lambda: _check_shapes(_v2eng, v2spec))
# with the backend's declared transforms: passes
try:
    _check_shapes(_v2eng, v2spec,
                  dtype_transforms={"img": "float16", "big_img": "float16"})
    check("4: v2 fresh-build passes with declared transforms", True)
except ValueError as e:
    check("4: v2 fresh-build passes with declared transforms", False, str(e)[:80])
# a wrongly-declared transform still fails (check not loosened)
expect_raise("4: wrong transform declaration refused",
             lambda: _check_shapes(
                 _v2eng, v2spec,
                 dtype_transforms={"img": "int32", "big_img": "float16"}))
# an undeclared retype on another tensor still fails
_v2eng2 = fake_engine(v2spec, {})
_v2eng2.inputs["desire_pulse"] = _v2eng2.inputs["desire_pulse"]._replace(
    dtype=np.dtype("float16"))
expect_raise("4: undeclared retype refused",
             lambda: _check_shapes(
                 _v2eng2, v2spec,
                 dtype_transforms={"img": "float16", "big_img": "float16"}))
# legacy dtype-less spec (tests/cinque_v2.json as-is): dtype checks skipped,
# shapes/names still enforced -- backward compatible
_v2legacy = ModelSpec.from_dict(json.loads((ROOT / "tests" / "cinque_v2.json").read_text()))
try:
    _check_shapes(fake_engine(_v2legacy), _v2legacy)
    check("4: legacy dtype-less v2 spec still loads and passes", True)
except ValueError as e:
    check("4: legacy dtype-less v2 spec still loads and passes", False, str(e)[:80])


# --- Item 10: ONNX identity gate negative tests -------------------------------
# tools/build_trt_v3.py imports only numpy at module scope (tensorrt is
# function-local), so it loads on this VM.
_build_mod = SourceFileLoader("build_trt_v3",
                              str(ROOT / "tools" / "build_trt_v3.py")).load_module()

_identity_spec = {
  "sha256": "0" * 64,
  "nbytes": 12345,
  "input_shapes": {"new_img": [2, 6, 128, 256]},
}
_dummy_onnx = ROOT / "artifacts" / "big_driving_supercombo_v3.onnx"

try:
  _build_mod.check_onnx_identity(_dummy_onnx, _identity_spec)
  check("10: bad sha256 refused", False, "no SystemExit")
except SystemExit as e:
  check("10: bad sha256 refused", "mismatch" in str(e), str(e)[:80])

_bad_size_spec = dict(json.loads((ROOT / "artifacts" / "cinque_v3.json").read_text()))
_bad_size_spec["nbytes"] = 1  # sha matches, size does not
try:
  _build_mod.check_onnx_identity(_dummy_onnx, _bad_size_spec)
  check("10: bad nbytes refused", False, "no SystemExit")
except SystemExit as e:
  check("10: bad nbytes refused", "size" in str(e), str(e)[:80])

# main() flow: a bad identity must exit BEFORE build_engine is reached.
import tempfile as _tf
_calls = []
_build_mod.build_engine = lambda *a, **k: _calls.append((a, k))
with _tf.TemporaryDirectory() as _td:
  _spec_path = Path(_td) / "spec.json"
  _spec_path.write_text(json.dumps(_identity_spec))
  _argv = ["build_trt_v3.py", "--onnx", str(_dummy_onnx),
           "--spec", str(_spec_path), "--out", str(Path(_td) / "o.engine")]
  _old_argv = sys.argv
  sys.argv = _argv
  try:
    _build_mod.main()
    check("10: main() exits on bad identity", False, "no SystemExit")
  except SystemExit:
    check("10: main() exits on bad identity", True)
  finally:
    sys.argv = _old_argv
check("10: build_engine never reached on bad identity", _calls == [])


print(f"\n{len(PASS)} passed, {len(FAIL)} failed")
sys.exit(1 if FAIL else 0)
