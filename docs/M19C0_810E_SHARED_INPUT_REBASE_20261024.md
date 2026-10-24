# M19-C0 — exact810e shared-input recorder, offline only

**PASS — CPU_FAKE/FIXTURE,415 unique tests (339 historical+76 new),0FAIL/0SKIP.**
Shared input, exact N16 contract, input identity, socket fallback, Strategy B and
both reversible deployment layouts pass offline. Candidate is ready for a
separately approved fresh OFF deployment gate; **M19-B2 capture is NO**.

Target: `carrot-nav@810e14aaf51176f1a50a113939dc2e70907b394b`.
Profile: `RECORDER_810E_SHARED_INPUT_V1`. Development start:
`58bdcbc0fc36abda1051fc054fe7f2a5e875f555`, feature branch, initially clean and
equal to origin. Historical366 templates, patches, evidence and numerical/managed
model adapters remain unchanged. Actual comma and Jetson were **not accessed**.
Candidate status and fresh test totals are recorded in the accompanying artifact.

## Baseline and incompatibility

The user reports that the updater reset/fast-forwarded to810e at
2026-10-24 12:28:40+0900. The current tracked `jetlink/model.py` is pure810e,
SHA256 `103dc0c7eb1b4998ddbf0a498be55ffd02fd51b195ce20cb7ea44ba3dbce6c42`;
the five untracked366 recorder modules survived. The supplied live observation
was OFF/ON0/1, started=true and999 stationary samples over10.001s, Park/canValid.
Those are historical user-supplied observations, **not a fresh device preflight**.

The old recorder is **INCOMPATIBLE** for two separate reasons: its Warp wrapper
rejects `output_buffer=`, and its contract rejects `spec.stateful` and requires
`prev_feat`. Changing expected SHAs alone cannot fix either. The old package must
not be activated against810e. It was not imported, changed or removed on device.

Immutable Git objects were read by `git archive`/`git show` without checkout,
reset, source update or modifying the reference HEAD. Comparing366 to810e:

| Source | Change |810e responsibility |
|---|---|---|
| `jetlink/model.py` | changed | Warp `output_buffer`, one `image_buffer()` reservation |
| `jetlink/link.py` | changed | shared negotiation and connection retirement |
| `jetlink/shared_input.py` | new | size-sealed memfd/SCM_RIGHTS, nonce/generation/token |
| `jetlink/contracts.py` | changed | projected output compatibility |
| `jetlink/daemon.py` | changed | shared setup/read and unchanged inference forwarding |
| `jetlink/inputs.py`, `prepare.py`, N16 sidecar | unchanged | actual scalars, helper actor and model contract |
| `camera_gap.py`, `camera_sync.py` | unchanged | camera pairing and provenance |
| vendored `spec.py` | unchanged | N16 stateful classification/packed ordering |
| `modeld.py`, manager `process.py`/config/manager | unchanged | lazy main import, fork and onroad policy |
| launch scripts/restart | unchanged | restart.sh still performs git pull; unsuitable |

Full before/after source hashes are in the artifact. The five relevant changed
files do not imply all other openpilot changes are safe for vehicle use.

## N16 contract: a stateful graph with nonstate transport payload

Source model SHA is
`01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`,
814591107bytes. Canonical `ModelSpec.to_dict()` SHA is
`63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`.
`spec.stateful=True`, with five input/output pairs:
img, desire, feat, map_features and navigation_features queues. Actual
`EngineHost._warm -> make_queues -> StatefulQueues`, and `Session._infer ->
feedback` maintain these on the server. They are not client `prev_feat` payloads.

| Packed field, in exact order | Shape | Float offset |
|---|---|---|
| desire |8 |0..8 |
| traffic_convention |1×2 |8..10 |
| action_t |1×2 |10..12 |
| nav_map |1×1×256×256 |12..65548 |
| navigation |1×47 |65548..65595 |

The new contract verifies the exact model/spec, stateful graph, all five pairs,
ordered packed fields, total65595 and warped shape2×6×128×256. It does **not**
loosen the historical366 nonstate gate. Unsupported source models disable only
recording; normal inference and fallback remain unchanged.

Capture remains logical V3 parity input: `new_img uint8`393216bytes and actual
same-frame `desire/traffic_convention/action_t float32`48bytes. The new distinct
provenance kind is `existing_jetlink_n16_nonstate_payload`. Nav map/navigation,
all recurrent state, raw camera, GPS and routes are excluded. `fill_inputs` is
unchanged: desire is the actual rising-edge pulse, not published meta.desire;
traffic/action are copied from the call and nav fields are independently filled.
No scalar is reconstructed from logs. V3 target/spec digest and binary layout
remain the same as M18. N16 is a source of inputs, **not the V3 model**.

## Image identity and slot lifetime

1. `Client.image_buffer()` calls `Writer.begin()` once. It sets busy and returns
   the connection-owned writable ndarray over the sealed memfd.
2. Original `Warp.__call__(..., prepare=None, output_buffer=None)` runs once,
   preserves the prepare callback and GPU completion fence. `read_result` copies
   directly into the destination and returns **that same Python object**. With
   None it returns the original ndarray path.
3. The wrapper forwards both keyword arguments exactly once and returns the
   original result. It never calls image_buffer, begin/token/complete/release.
4. Immediately before the unchanged original `Client.infer`, the observer checks
   that the image **is the borrowed Warp result**, copies it and the first12
   packed floats into its separate bounded ring, and clears the borrowed lease.
   On failure it clears borrowed metadata and stops only the recorder.
5. Original infer creates the token, copies packed data into the shared mapping,
   advances generation and sends it. Recorder observation has not changed busy,
   nonce, generation, packed context or ownership.
6. Daemon `Reader.read` checks nonce, next generation and unchanged150ms token
   age. Its readonly ndarray is a **different Python object/virtual mapping of
   the same memfd**, not a claim of Python identity across processes. The daemon
   forwards these exact bytes through actual JetlinkClient to actual Session.
   The engine receives serialized/staged copies with byte-equal logical inputs.
7. Only the matching finite inference reply calls Writer.complete. Timeout,
   disconnect or bad reply closes/retires the whole connection. An exported old
   mapping can remain alive as a lease; a new session allocates a new mapping and
   nonce. Recorder failure cannot release or hold the input slot busy.

Socket fallback is supported when RAM input is disabled/unavailable: no second
Warp/reservation is introduced, and original request framing carries the same
image/scalars. Tests execute both paths, including real memfd/SCM_RIGHTS and
UNIX sockets on the CPU host. Separate comma/server subprocesses execute actual
810e `Client`, `_serve_local`, vendored `JetlinkClient`, `Session`,
`EngineHost._warm` and five-state queues. Only GPU/QCOM execution and native
Params/logging/diagnostic boundaries are substituted. Three records per mode
are read back through the strict reader; each of four input hashes equals the
fake engine's received logical tensor hash. This is CPU_FAKE/FIXTURE, not USB or
real N16/V3 execution.

Invalid destination dtype/shape/read-only/noncontiguous arrays retain the
original ValueError and GPU-drain behavior. The prepare exception object is
preserved. Warp does not know whether an otherwise-valid ndarray is retired;
original Client/Writer ownership checks reject its use for a closed session.
The observer does not invent a different Warp error for that case.

Recording is of **inference input attempts**, not an inference-success receipt.
The timeout tests show intact copied bytes and retired ownership; they do not
claim that an uncertain remote attempt was consumed. Dataset COMPLETE validates
capture integrity/continuity, not remote execution or numerical acceptance.

Copying adds CPU time before original infer creates its deadline/token. It does
not change ordering or token ownership, but it can affect camera age/latency.
Actual timing acceptance remains a future on-device measurement; no timeout,
finite, shape or identity gate was increased or relaxed.

## Activation and update resilience

Strategy B is retained: one lstat at lazy model import for the fixed volatile
ticket. With no ticket, no recorder package import, writer/ring/copy or frame
work is added. Legacy capture environment selectors cannot activate this
profile. No manager/process/launcher changes or restart mechanism are added.

Exact810e `modeld.main` is the lazy JoiningModel import; prepare.main separately
imports Warp. Manager prepare imports modeld, not jetlink.model. Source-backed
fork fixtures use the actual PythonProcess/launcher and prepare loop, reduced
modeld.main/native stubs, and the real role guard. They show manager preimport
does not consume, preparation helper does not consume, first proper child does,
and second child stays OFF after COMPLETE or recorder failure. Context drift is
denied. This is a source-backed CPU fixture, not a real manager run.

Existing ticket schema/security is reused: genuine OFF assertion at external
arming, boot ID, monotonic expiry1..300s, fixed tmpfs/root1777 parent, private
owner/group/mode700 directory, regular single-link mode600 ticket, O_EXCL,
no-symlink handling, path/source/spec binding, exclusive capture ID and retained
consumed marker. No automatic rearm or cleanup is introduced. Expired/wrong boot/
malformed/moved/source/spec tickets terminate recording only; unsafe symlink/FIFO
entries remain untouched. Arming verifies exact HEAD and full model-with-footer
plus pinned transport/actor/spec/server sources **before creating a ticket**.
The hook pins the other four package modules; the model footer binds the full
hook SHA. Verification requires that exact footer template and the original810e
model body hash. This avoids a circular self-hash and rejects any one package
member's change/removal before the discovery directory is touched. All six
absolute after hashes are also independently pinned in the deployment artifact;
the coupling is an integrity gate, not authentication against an attacker who
can rewrite both program and attestation.

Updater reset may remove the tracked footer again. That is accepted fail-closed
behavior for this temporary diagnostic: pure810e no longer matches the patched
model SHA, so pre-arm verification refuses it. If the footer is absent no import
consumer runs. There is no updater disable, auto-repatch, saved Param or service
configuration. A separately approved deployment must verify **all six package
hashes** from this artifact immediately before arming; runtime source checks
are not a substitute for that complete private attestation.

## Deployment profiles and rollback — not executed on device

The main patch targets **pure810e model plus the exact surviving366/B1 package**.
It changes three files: model.py, hook.py and format.py. The other three module
bytes are reused unchanged. The separate `-clean` patch targets a clean810e tree:
one existing model file and five added modules. All six before/after hashes and
both forward/reverse hashes are in the artifact; deployment must compare each
path, not infer layout from a status label or anonymous U-number ordering.

Both forward/reverse roundtrips execute `git apply --check` then `git apply` on
fresh disposable copies and restore exact before bytes/absence. No blanket
delete/recreate, source reset, Git index write or original48 operation occurs.
Historical M18/B1 patches are not reapplied to810e. Candidate construction refuses
an existing output directory.

Future deployment requires a **new** approved OFF safety/source/runtime audit,
including an810e private inventory of original runtime overlays, models/routes,
process state, no ticket/writer and exact old-package hashes. Previous366 digest
and readiness are historical, not a fresh810e attestation. The supplied current
ON state is not authorization for deployment. After an approved exact transition,
verify POST hashes/default OFF; any subsequent arming/capture needs its own scope.

## Reproduction and limitations

Use a local reference containing the810e Git object; no checkout is needed:

```sh
PYTHONPATH=. python -B -c "from adapters.carrot.recorder_810e import build_candidate; build_candidate('.reference/m15-carrot-nav-366d6eae', '.candidate/fresh-recorder810', layout='surviving366')"
PYTHONPATH=. python -B tools/v3_input_dataset_810e.py validate PRIVATE_DATASET --reference .reference/m15-carrot-nav-366d6eae
PYTHONPATH=. python -B tools/benchmark_recorder_810e.py --reference .reference/m15-carrot-nav-366d6eae --output PRIVATE_NEW_BENCH_JSON
```

The first command is offline preparation, not installation. Reader validates the
distinct810e provenance and exact N16 identity; `ort_feeds()` returns only the
four logical tensors. `trt_into()` reuses existing validated conversion. Neither
creates recurrent state. Dataset code is loaded from trusted generated templates,
never from recorded files. No pickle execution or model run is involved.

Fresh scoped regression includes historical310, deployment receipt29 and the
new810e tests, once each. Root bare pytest is unsupported: legacy
`tests/test_backport.py` exits during collection (`SystemExit:0`, no tests run).
This runner problem is recorded separately from the final scoped green suite;
it was not hidden by modifying historical tests. Private RED/setup failures and
final JUnit remain ignored local evidence.

The512-frame20Hz host benchmark reports shared baseline, full pre-infer observer,
copy/send costs, incremental paired differences, queue high-water and RSS. It
excludes receive/Warp wrapper bookkeeping and all GPU/camera/USB costs. Baseline
always runs first in each pair; host cache/scheduling affect this diagnostic.
See artifact for final measurements and exact measured profile. It is not comma
real-time acceptance.

Final512-frame host run: full observer p50/p95/p99/max
205.331/393.347/521.116/618.624us, baseline shared p99 131.307us, paired
incremental p99 509.616us. Queue high-water1/4, ring1577728bytes,
dataset201428992bytes, sampled writer RSS35612KiB, strict reader PASS. The
10000-iteration missing-ticket footer diagnostic used one real host lstat
redirected to a fresh absent temporary path: p50/p95/p99
1.745/2.758/5.010us, no package import. These are host fixture measurements.

Upstream Nav/WIP moved during this work; start/end full refs are recorded in the
artifact. Target stays810e. No compatibility with later HEADs is asserted.
One final independent review found the missing package-profile arming check.
Ten changed/missing-module RED cases reproduced it; the single fix pass added
the binding above and regenerated both profiles/reverse patches. No minors were
deferred. The fresh final regression after this fix is the authoritative count.
Numerical parity remains **PARITY_UNDETERMINED**, M2 **NO**. Actual deployment,
ticket, capture, restart, GPU/USB/vehicle/road tests: **NOT_RUN**. Candidate
readiness is for a separately approved OFF deployment only, not M19-B2 capture.
