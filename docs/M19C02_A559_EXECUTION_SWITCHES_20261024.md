# M19-C0.2 — a559 input overlap / execution switches

**RECORDER_LOGIC_REUSABLE.** The060 infer-wrapper observation point remains exact
under both CPU preparation orders. Separate profile:
`RECORDER_A559_EXECUTION_SWITCHES_V1`, pinned exclusively to
`a559fcd971ccaa5a87befb8ec080f59a2966325b`.

**627 unique CPU_FAKE/FIXTURE PASS /0FAIL/0SKIP:**533 specified project cases
(449 historical once +84 new a559) and94 disjoint exact-a559 upstream transport
cases. No comma/Jetson access, actual deployment, ticket, recorder activation,
capture, restart, Params write, USB operation or updater manipulation occurred.
All datasets below are synthetic fixture outputs. Prior actual OFF evidence is
historical; it is not refreshed or used as deployment permission here.

The complete source comparison,30 pins, six before/after hashes, migration hashes,
16 matrix receipts, test commands and JUnit digests are in
`artifacts/m19c02_a559_execution_switches_20261024.json`.
Implementation commit: `f79ae3beb9d160a3acaf48ce7e1e3c37bfce4458`.

## Exact source range

Immutable Git objects were read without checkout. Development started on the
required feature branch at2744d6ffbf784cee6892594566f41fe33be03f67,
CLEAN/local=remote. Main2519ad0b and old feature26c9c06a are protected.
Reference checkout HEAD366 and its existing submodule status were preserved.

060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c..a559 contains exactly six commits:

| Commit | Subject |
|---|---|
|3032c4c6 |Add independent Jetson regression comparison switches |
|c62f35c5 |Report actual Jetson execution options during regression trials |
|710da0d2 |Release camera EGL imports before UI shutdown |
|c3e8be79 |Correlate Jetson transport phases for the slowest frame |
|ef90615e |Run correlated timing checks with the updated diagnostics fixture |
|a559fcd9 |Install existing diagnostics test dependency in integration CI |

All14 changed files are enumerated with full before/after hashes in the artifact.
Only model.py/link.py/daemon.py changed among the prior28 source pins. Inputs,
Warp implementation, shared input, contracts, CameraGapTrace/camera sync, modeld,
manager process, N16 sidecar, spec/queues/Session and request transport are byte
identical. Two additional pins bind RuntimeDiagnostics and output_projection.py.
UI EGL shutdown changes do not change the recorder input or actor import sites.
The CI dependency addition is zstandard; it does not change input preparation.

## Exact observation and the two preparation orders

Actual source-backed `JoiningModel.run`, `fill_inputs`, `Warp.__call__` and
`Client.infer` execute in the matrix. Native QCOM execution is a deterministic
CPU fixture; the original source functions are not replaced with copied logic.

| JETLINK_CPU_OVERLAP | Observed order |
|---|---|
|1 (default) |image_buffer reservation → Warp submit → fill_inputs → read/output → Warp return → recorder observe → original infer |
|0 |fill_inputs → image_buffer reservation → Warp submit → read/output → Warp return → recorder observe → original infer |

`fill_inputs` executes exactly once for each inference attempt. For0,
`prepare=None` is the intended runtime call; the existing recorder wrapper forwards
both prepare and output_buffer once without requiring a callback. Warp returns
the same object received by the recorder and original infer. Shared mode returns
the actual offered ndarray; socket mode returns Warp's ndarray. The recorder
does not reserve, complete, release or retain a shared slot after observation.
One reservation occurs per frame, and the original infer completes ownership.

The wrapper reads **the actual final packed ndarray** immediately before the
original infer. Desire/traffic/action are views of its first12 float32 values;
no scalar value is reconstructed from the callback, previous frame, logs or
outputs. Capture.warped borrows the actual Warp return, and its copied image
bytes equal original infer's argument before infer changes transport ownership.
The060 hook function/class AST, recorder.py, dataset.py and __init__.py are reused
unchanged. Only source/provenance constants and the hash-bound footer differ.

Five sequential attempts use distinct action values `[[i/4,(4-i)/4]]`, alternating
traffic one-hot values, different image bytes, camera IDs100+i/200+i,50ms SOF
steps,3ms camera offset and distinct transforms. Requested desire is
`[0,1,1,0,1]` for class1. Actual packed pulse is `[0,1,0,0,1]`, exercising no
desire, rise, hold, fall and another rise under both modes. All five scalar hashes
are distinct, and each saved frame hash equals that same original-infer attempt.
There is no one-frame lag. Metadata/reset flags remain attached to the same
camera-pair/inference attempt. Camera receive is a named fixture boundary; its
unchanged production source is separately pinned and covered by retained tests.

## Sixteen execution combinations and transport

CPU overlap0/1 × request chunks0/1 × compact reply0/1 × shared input0/1 all pass.
For each of80 attempts, four saved logical-input hashes equal the original
infer arguments and the engine's host input buffers. Full packed hashes also
match Session/EngineHost. Across all16 cases, the five ordered input/scalar/packed
hash lists are identical. Observation timestamps/provenance can differ between
separate datasets; equality here is the four logical input payloads, not a whole
manifest digest that contains capture-time metadata.

Chunk opt-in is evaluated from the actual daemon.main keyword expression.
When1, the actual FfsTransport request writer sends bounded packets; a native
Linux AIO Writer writes a private regular file, then exact completed bytes relay
over a local socket to ReadAheadTransport, Receiver, CarrotSession, Session and
EngineHost. When0, legacy P2 framing goes through the same host path. Reassembled
logical requests equal the pre-framing request bytes in each case. Every bounded
packet is duplicated and each completed whole request is replayed: five engine
executions remain five. Protocol remains2; no Protocol3 promotion is claimed.

Compact reply uses the actual link.Client projection selector, eligible exact
N16 descriptor and real host projection. Replies contain2066 float32 values
when enabled and18580 when disabled. Only the output representation changes;
input payloads remain identical. SEND_RAW_PRED and capability/spec gates remain
unchanged. The matrix uses canonical zero Nav-map compact input encoding; the
retained060 scope also exercises full-float/noncanonical Nav input. Request
framing/projection/diagnostics introduce no second fill_inputs or alternate infer.

Physical FunctionFS/USB, real QCOM Warp, GPU/ONNX inference, numerical parity,
latency and on-vehicle behavior are **NOT_RUN**. The parser at the output boundary
is a fixture, so this is input correctness evidence, not numerical acceptance.

## Diagnostics and failure preservation

RuntimeDiagnostics receives numeric sizes/timings plus frame_id/usb_seq after
the inference reply. It receives neither input ndarray nor packed buffer. It
owns one peak context/metric snapshot, reads scheduler telemetry, and records
`usb_exchange_ms`; it does not mutate sequence numbers or retry that inference.
All16 wire cases exercise the exact class and daemon source with a fixture
interval0 factory, producing five correlated events each.

Logging exceptions in emit are suppressed. An internal programming error, such
as a nonnumeric metric, can still raise TypeError before that guard. The dedicated
test confirms this boundary. _serve_local catches ConnectionError/BrokenPipeError/
ValueError, closes its shared mapping in finally; TypeError reaches main's outer
Exception handler, resource cleanup and later session reconnect. The reply was
already sent before diagnostics. A later setup/warm-up session may run; there is
no same-request inference retry in diagnostics. This existing behavior is
characterized, not changed or described as unconditionally non-interfering.

Source-backed paired wrapped/unwrapped tests compare successful call order,
preparation failure, GPU read failure, original infer failure and recorder-only
observer failure for both overlap modes. Original direct exceptions retain object
identity. Overlap1 drains a submitted Warp before preparation failure reaches
fallback; overlap0 fails before GPU submission. Recorder failure still allows
the original infer exactly once. Existing invalid-shape/finite/identity/timeouts
and local fallback gates are not relaxed.

## Separate binding and reversible migration

Historical366/810/060 generators, patches, tests and evidence remain immutable.
New generator: `adapters/carrot/recorder_a559.py`; strict reader:
`tools/v3_input_dataset_a559.py`. Reader rejects datasets from another source
profile. Thirty source drifts, wrong HEAD, absent footer and altered hook deny
arming before touching a ticket namespace. No-ticket footer imports no capture
package. Lazy model import, manager/helper fork guard, completion/failure and
second-child one-shot behavior pass with the generated a559 package. Broader
unchanged activation/security behavior remains in the449 historical project cases.

The approved future before layout is **pure exact-a559 model.py + exact surviving
366/B1 recorder package**. The surviving migration changes only model.py,
format.py and hook.py. The clean-layout alternative creates the five package
files plus footer. Both were applied forward/reverse in disposable local trees,
and all bytes matched the exact before/after maps. A clean-layout patch must
never be substituted for a surviving-package migration.

| Layout | Forward SHA256 | Reverse SHA256 |
|---|---|---|
|surviving366 |aa983f2bc477f011da46d55b0b3305c77c7540e1e0d0619e200bf26bdcb6164e |147888f44973025c56d35bc9cdd6dd3f2c50a88d561b8270666ef0299b114230 |
|cleana559 |afbc80858ea5592a943ef9571153a930773c4d3158c9c63dfdff4c16e908fae6 |e65289f690698b95add5d1641c42b623032a68c1a4c7313e2ccd68eab56b943c |

Public files: `patches/carrot-nav-a559-v3-input-recorder.patch`, corresponding
`.reverse.patch`, `-clean.patch` and `-clean.reverse.patch`. Candidate manifests
in the artifact contain all six exact hashes, including unchanged files.
After model.py SHA256 is1e12806606823d09ff57bb65879810e73f50eb9dd45c85aec555d0b0777c74cb;
hook SHA256 is1e82abdfc93ab23f7add69c8f248677538ec2c20b47868b7bc06cb0195a18256.

N16 source model SHA remains
`01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`,814591107bytes.
The supplied repeated spec text is malformed, not a SHA256. Independent canonical
hashing of exact-source ModelSpec JSON yields
`63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`, agreeing with
the frozen060 contract and output-projection descriptor. No model download/load.
Packed65595float32 and uint8 image2×6×128×256 remain unchanged; recurrent state
stays host-owned and is not saved by this four-input recorder.

## Verification and next gate

| Scope | PASS | FAIL | SKIP |
|---|---:|---:|---:|
|Historical project once |449 |0 |0 |
|a559 binding/migration8 + source/reader38 + actor5 + matrix16 + order/diagnostics17 |84 |0 |0 |
|Exact a559 upstream transport |94 |0 |0 |
|Unique total |627 |0 |0 |

Linux Python3.12.3 / NumPy2.5.4, existing WSL venv;533 cases229.41s and94 cases
7.70s, exit0 each. JUnit IDs are unique/disjoint. Full commands are in the artifact;
use PYTHONDONTWRITEBYTECODE=1, PYTHONPATH=.:tests, OPENBLAS_NUM_THREADS=1,
pytest -q -p no:cacheprovider and a short private /tmp basetemp for AF_UNIX tests.
Initial fixture issues were corrected without production changes: long mounted
socket path, missing parser fixture and the actual API name infer_end. The reply
size expectation was corrected to the exact source constant2066.

The supplemental upstream diagnostics4 module could not collect because the
existing environment lacks zstandard. No package installation was performed and
those four are not counted. Exact RuntimeDiagnostics was exercised by the new
dedicated test and matrix. Full-root pytest is not claimed: the documented
tests/test_backport.py:192 SystemExit0/pytest3 collection blocker was not rerun.

Next is a **separate exact-a559 genuine-OFF preflight and current overlay/package
attestation** before proposing migration. Fresh OFF1/ON0, startedfalse, both
ignition bitsfalse, normal OFF processes, actual carrot-nav exact-a559, exact old
six hashes, source pins, N16 source identity, ticket absent, writer0, operating
preservation and POST attestation are required. If HEAD moved, STOP. Do not
auto-retarget, restart, create a ticket or capture in this stage.

Status: offline candidate PASS; actual install NOT_RUN. Ready for vehicle10 NO;
M2 readiness NO; numerical decision PARITY_UNDETERMINED. Result commit resolves
with `git log -1 --format=%H -- artifacts/m19c02_a559_execution_switches_20261024.json`.

Independent read-only final review of2744d6f..0665c3a: PASS, zero critical,
important or minor findings. Source pins, canonical spec, frozen behavior,
migration bytes,16 receipts and627 unique test/log evidence were independently
checked. Real QCOM/GPU/USB, actual deployment, numerical parity, latency and
vehicle readiness were deliberately left unjudged within the offline-only scope.

Decisions carried forward: use the explicitly requested feature checkout (any
unexpected shared development change would require isolation/reconciliation);
use only exact-source canonical spec hash for the malformed supplied text
(a mismatch would block the profile); retain previous OFF as historical only
(fresh actual gates are still required); leave the review's real-device and
numerical exclusions NOT_RUN (vehicle readiness cannot follow from this review).
