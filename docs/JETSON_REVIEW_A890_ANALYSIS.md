# External Jetson inference review — 2026-10-20

Purpose: prepare later performance A/B tests without changing the validated
baseline V3 implementation or enabling an optimization by default.

## Scope and source identity

Project start: feature/jetlink-multimodel-carrot at
`8bf5e1e3379a37575a3420ef074bd74e96f06ff0`, clean working tree.
Latest freshly queried carrot-wip:
`ba186915179816a9b0476cec52bf321e73d2d4b0`.
Its relevant Jetlink Git blobs are identical to the last validated
`5032afca77a96e31a077a5e9ac738d9ac08a99df`; no source-adapter rewrite is needed.

External read-only source: tjdgus200/openpilot codex/jetson-review,
`a890f6df1bd3eb0478754c68d8b5f92f15e8b722` (branch HEAD freshly confirmed).
Inference commit parent: `de75c056712fbe19943892919f19960f3e6d565b`.
Base: carrot-nav `74955c98560435895df28a8ae6f9af4d3d414d5f`.
Review full a890 diff (15 files, +1199/-24), never merge/cherry-pick the branch.

## Decisions made before implementation

- Existing V3/multi-model/parser/approval/fallback is preserved.
- Standard candidate generation stays byte-identical. Experimental overlays
  require an explicit build option, then runtime flags absent/0 remain OFF.
- DeviceState candidate retains every state D2H and CPU validation. It saves
  state H2D only; D2D commit is allowed after validation, not before it. Full
  external D2H elimination is not adopted without an equivalent trusted gate.
- InputFastpath reuses the exact native byte→binary16 lookup, with stricter
  repeated binding checks; Cinque V3 scalar contract only. Navigation compact
  map/spec/wire changes are not imported.
- AIO stays isolated experimental review/test code; no production FunctionFS or
  daemon hook. Default-off is necessary but does not prove USB lifecycle safety.
- de75 direct Wi-Fi/HUD code remains OUT_OF_SCOPE and is not ported.
- No device, operating-image, service, Params, engine/cache or deployment action.

## Source comparison

“Current” below means our source-generated current carrot-wip candidate,
not the historical protocol-2 V3 force-fit patch. Source hashes for **all 15**
a890 changed files, including tools and documentation, are recorded in
`artifacts/jetson_review_a890_sources.json`.

| Feature | Current candidate | External a890 | Decision / prepared candidate |
|---|---|---|---|
| StatefulState | Validated host state pairs, staging + commit | DeviceStateQueues uses GPU-managed pairs | Retain our class and CPU validation/commit |
| DeviceState | No GPU recurrence controller | Distinct input/output device buffers + D2D | Adapt optional controller; H2D savings only |
| PolicyQueues | Existing V2 queue/prev_feat path | Separate device-state queue for stateful models | Leave V2 implementation unchanged |
| EngineHost._warm | Shape/spec validation, stateful selection, warm/reset, authorization recheck | Configures device state and optional direct input staging | Configure only requested stateful TRT; retain current gates |
| Session._infer | Validate every driving/state output before commit; invalidate failed generation | Device-state path receives driving only, GPU status validates state finiteness | Preserve every output and CPU gate; D2D only after host commit |
| TensorRT engine.run | H2D all inputs, execute, D2H all outputs, stream synchronization | Skips state H2D/D2H; reply event + trailing D2D | Skip only steady-state state H2D; retain all D2H + stream sync |
| State reset | Host zero, HELLO/reset/warm zero state | Synchronize then reset GPU recurrence | Drain pending feedback before host zero; next run uploads zeros |
| next_state validation | Presence, exact shape/dtype, finite, all-pair atomic validation | GPU finite scan, binding/pair setup validation; outputs omitted from CPU result | Keep all existing checks; GPU scan is an additional gate |
| Finite validation | CPU all-output checks | NVRTC FP16/FP32 exponent-bit scanner | Reuse scanner lazily; unsupported dtype rejects; real execution BLOCKED |
| CUDA graph | Current capture, fixed bindings, fallback | Graph includes scan/status; reply event separates tail | Retain existing full-sync boundary; fake capture success/failure tests |
| Host pinned memory | Existing TRT binding allocations | Maintains host buffers, direct input writes | Reuse current allocator; no pinned-memory claim from CPU fake |
| State H2D | Every frame | Initial/reset upload, then omitted | Optional omission after initial/reset upload |
| State D2H | Every frame, needed for CPU validation | Omitted | Retained; external full-transfer elimination not adopted |
| D2D feedback | None | Scheduled after reply event, before CPU reads scan status | Schedule only after all CPU validation + host commit |
| Reply event | Stream sync covers all output copies | Response can precede trailing D2D | Event optimization not ported; post-validation D2D alone can trail response |
| USB write | Existing synchronous FunctionFS | Bounded AIO submission/reaping | Isolated experimental controller only, no transport hookup |
| Input staging | Validated NumPy conversion/copy | LUT conversion + direct pinned writes + nav compact decode | V3-only direct staging and exact LUT; no nav format import |
| Failure handling | Invalid loaded generation until reload, fallback contract | Local queue reset on feedback failure | Preserve invalidation; partial D2D never reusable |
| Cleanup | Existing engine/transport cleanup | Drain/reply-event/AIO cleanup guards | Device drain before any free; AIO uncertain ownership refuses cleanup/rebind |
| Fallback | Existing daemon/parser/JoiningModel local small model | Existing modeld path plus daemon AIO selection | No modeld/daemon changes; baseline fallback regression retained |
| Model identity / approval | V2 preserved, managed P3 exact SHA/spec and offroad approval | Based on carrot-nav with different input contracts | Keep current policy, wire and model selection unchanged |

Already present and reused: current protocol 2/3, stateful ModelSpec,
PolicyQueues/StatefulState, host pinned allocations, CUDA graph support,
all-output validation, offroad approval and local model fallback. These were
not reimplemented from the external branch.

External ideas worth adapting: distinct-buffer recurrence, exact byte→binary16
conversion and bounded AIO ownership. Device recurrence and direct staging are
software-prepared A/B candidates, not validated device performance features.

## DeviceState: retained validation and ordering

The external `ModelSpec.state_pairs` dictionary API matches current carrot-wip.
Our StatefulState validates that dictionary and stores internal tuple pairs;
the optional controller consumes the validated spec dictionary, not those
tuples. It does not replace StatefulState or authorize a model.

External engine `_enqueue` records its reply event after GPU finite scan/status
D2H, then enqueues D2D before CPU `validate()` reads status. The scan is a finite
check; it does not make D2D conditional on success. External DeviceStateQueues
cannot provide our CPU validation of every returned next_state because those
outputs are omitted from its return dictionary. This is a source-level reason
to reject a wholesale port, not a real-device failure measurement.

Prepared sequence:

1. First/reset frame uploads zero host state outside graph capture.
2. Same stream executes non-state H2D → inference → **all** output D2H → GPU
   finite scan/status D2H → existing full stream synchronization.
3. Session validates driving output and every next_state for existence, exact
   shape/dtype and finite values; then commits all validated host state.
4. Only after successful host commit does DeviceState enqueue all D2D feedback.
5. A subsequent same-stream frame observes feedback before execution. Reset,
   HELLO and close drain trailing feedback before host zero or buffer free.

This deliberately retains state D2H and CPU checking, so it cannot claim the
external implementation's full transfer savings. GPU finite validation is an
extra check. No reply-event wrapper is imported. Failed validation schedules no
D2D and preserves the previous valid host state. Failure after host commit or
partial D2D invalidates the loaded generation; reload is required. A failed
drain retains allocations and refuses cleanup rather than freeing live buffers.

Unsupported pair/dtype/shape/alias/binding contracts reject preparation. Graph
capture failure may use the current non-graph execution path only after a
successful drain; CUDA drain failure invalidates the generation. Fake execution
tests these control decisions, not NVRTC compilation or CUDA scheduling.

## InputFastpath: exact values, narrow contract

The original ONNX image contract is uint8. Our existing TRT10.3 ONNX patch makes
physical `new_img`, `state_img_q` and `next_state_img_q` FP16, with the remaining
physical tensors FP32. This is the **candidate** physical contract; installed
engine bindings must still be checked on the real Jetson. No builder or ONNX
patch changes are made in this optimization work.

The external DirectInputs imports carrot-nav compact map decoding. Our V3
contract has 12 scalar fields and no navigation map, so that codec/protocol path
is not imported. The candidate converts only uint8 `new_img` into its exact FP16
destination, copies exact FP32 scalar fields, and leaves recurrent inputs to
StatefulState/DeviceState.

The C lookup implements all 256 exactly representable uint8→binary16 values.
It compiles and self-tests only when explicitly requested during preparation.
Missing compiler/native conversion refuses requested preparation; there is no
silent pretend-fastpath success. Conversion tests compare raw bits against
NumPy, including tails and full random images. These are native **CPU** tests.

All binding objects, dictionaries, pointers, shapes, dtypes, strides,
contiguity/alignment and writeability are checked again before writing. Source
image/scalar contracts and overlaps are all checked before the first write.
External FP16 conversion itself does check destination alignment/contiguity;
its enclosing repeated binding contract is less complete for scalar/other
NumPy paths. This review does not claim an observed external native memory
corruption. The stricter contract prevents such storage changes in our candidate.

## AIO: ownership review only, no activation

Source uses the existing framed byte parts, 32 KiB requests, depth 32 and at
most 1 MiB outstanding. It preserves serial submission order. Short/error/
unknown/late completion must fail the connection; no synchronous retransmission
after a partial send is permissible.

CPU characterization reproduced three lifecycle defects in the inspected
source: a late final completion can bypass the deadline check, context clearing
before a failed `io_destroy` loses the handle, and holding the condition while
submitting can defeat a close deadline. Source also removes completions before
validation and assumes FunctionFS copies payload/iocb data by submit return;
that kernel-specific ownership assumption is unverified on this target.
The isolated candidate retains immutable payload
owners and per-request native slots, validates a whole completion batch before
release, avoids the lock around submission, joins/observes the active submitter,
and quarantines unresolved ownership. Native syscall tests inject the syscall
boundary; they do not invoke FunctionFS or Linux kernel AIO.

The module is explicitly disabled unless constructed with `enabled=True`.
`CARROT_JETLINK_AIO_WRITE` is **not connected** to any generated transport. No
FfsTransport subclass, daemon import, automatic fallback or endpoint rebind is
added. A future integration must propagate unsafe-cleanup refusal through the
actual daemon and prove kernel ownership, ordering, framing and endpoint reopen
on real USB before this can advance beyond a deferred candidate.

## Excluded code and performance evidence

de75 Wi-Fi/authenticated HUD is independent of the inference mechanisms, but
both commits edit `daemon.py`; applying either patch blindly can cause context
conflicts. A later separately authorized Wi-Fi port is possible after its own
source/security review. No Wi-Fi/HUD/power/credential changes are imported here.

The external benchmark assumes a navigation model and a named installed service;
the actual runtime/service is unknown until M0. The synthetic pipeline simulator
uses durations/latest-pending work, not an executed V3 recurrence contract.
Neither tool nor daemon scheduling changes are ported.

External reported input staging 0.938→0.448 ms and earlier synthetic cruise
mean 43.159 / p99 54.362 / max 62.628 ms are author/prior-system observations.
They are **not** performance of this repository, our candidate or the user's
Orin. External reported test counts (258/319) are not added to our test totals.

| Optimization | Classification | Conditions |
|---|---|---|
| DeviceState | READY_FOR_JETSON_AB | Prepared H2D-only variant; base recurrent V3 + USB + latency gates first |
| InputFastpath | READY_FOR_JETSON_AB | Exact CPU bits checked; real engine/pinned-memory/performance still required |
| AIO | DEFER_UNTIL_LATENCY_PROBLEM | Isolated tests only; no production transport adapter |
| Direct Wi-Fi / HUD | OUT_OF_SCOPE | No port |
| Wholesale external branch merge / full D2H bypass | REJECT | Wrong baseline and bypasses our CPU state validation contract |
| Read-only runtime inventory | READY_FOR_M0 | Existing inventory tool; no optimization enabled |

## Verification and continuation

Generate review copies only, never an installed runtime:

```sh
python -m adapters.carrot.integration <clean-reference> <new-standard-copy>
python -m adapters.carrot.integration <clean-reference> <new-experimental-copy> --experimental-optimizations
```

The second copy includes DeviceState and InputFastpath hooks, independently OFF
unless their exact flags equal `1`. AIO is absent from both copies. Missing flags
and `0` use the existing execution/staging bodies; invalid flags reject explicit
preparation. The default standard copy contains none of the optional modules or
hooks and retains the previous patch bytes. No supplied command installs,
enables, builds an engine or restarts a service.

Final command results, candidate hashes and development commit are recorded
below and in `docs/CODEX_CONTINUATION.md`. Evidence classes
are CPU_FAKE / FIXTURE only for this work. Prior ORT_REAL_MODEL evidence remains
historical and is not rerun or relabeled as optimization validation.

Verified implementation HEAD: `fcecd9c31f2e29c741f2e5bf161a6e318d63ed88`.
Environment: WSL Ubuntu24.04, Python3.12.3 isolated
`~/.venvs/cinque-v3-stage3/bin/python` (`$PY`), NumPy/pytest/ONNX and Linux C
compiler. No CUDA/TRT import is required by the default experimental package.

| Executed command / scope | Final result |
|---|---|
| `$PY tools/check_latest_carrot_compat.py --work-dir .candidate/rolling-a890-fcecd9c --report .reports/carrot-compat-a890-final.json --update-baseline` | ONLINE PASS288, FAIL0, SKIP0; fresh three heads equal before/after, baseline updated |
| `$PY -m pytest tests --ignore=tests/test_backport.py --ignore=tests/test_stateful_safety.py -q --junitxml=.reports/a890-all-final.xml` with historical C/J, current standard and LF reference environments | PASS368 +6 subtests; FAIL0, SKIP0 |
| `$PY -m pytest -q tests/test_jetson_device_state.py tests/test_jetson_input_fastpath.py tests/test_jetson_aio_candidate.py tests/test_jetson_optimization_integration.py tests/test_latest_carrot_compat.py` | PASS123, FAIL0, SKIP0; final independent review also123, source hashes stable |
| `CARROT_CANDIDATE_ROOT=$PWD/.candidate/rolling-a890-fcecd9c/optimization-candidate CARROT_TRT_DEVICE_STATE=0 CARROT_TRT_INPUT_FASTPATH=0 $PY -m pytest -q tests/test_current_carrot_server.py` | PASS9, FAIL0, SKIP0; repeat, not added to unique total |
| `$PY tests/test_backport.py` | PASS36 assertion checks, FAIL0, optional ONNX section SKIP1 |
| `$PY tests/test_stateful_safety.py` | PASS40 assertion checks, FAIL0, optional ONNX sections SKIP2 |

Unique pytest accounting: prior local265 +4 new checker cases +99 optimization
cases +101 additional upstream cases = **469 PASS /0 FAIL /0 pytest SKIP**.
Existing regression366 is preserved. New103 comprises DeviceState8 scenarios,
InputFastpath58, AIO30, composition3, checker4. Internal assertions and repeated
runs are not inflated into new test counts. The two previous ORT acceptance
gates remain unrerun/deferred, so the earlier five optional/deferred sections
remain distinct from zero pytest skips. Portable totals are in
`artifacts/jetson_review_a890_validation.json`.

The start ONLINE run also passed the pre-existing189 required cases. An initial
native Windows checker attempt failed to collect because that interpreter has
no pytest; it was rerun with the existing WSL test environment. RED failures
for source seams, EOL, pointer/name/owner/None handling were fixed and retested;
they are not hidden hardware skips or remaining final failures.

BLOCKED: real GPU finite/NVRTC, CUDA graph/order/drain/pinned memory and TRT10.3
binding/recurrence (TRT_REAL / JETSON_REAL); Orin timing/thermal/sustained20Hz
(JETSON_REAL); FunctionFS AIO/USB lifecycle (USB_REAL); actual comma fallback
(COMMA_REAL). Existing device/vehicle gates in continuation remain blocked.

Seven optimization acceptance gates remain BLOCKED, independently of CPU tests:

| Gate | Required evidence |
|---|---|
| NVRTC compilation and GPU finite scanner correctness | JETSON_REAL / TRT_REAL |
| Graph capture/replay, stream ordering and pending-feedback drain/failure | JETSON_REAL |
| Real recurrent parity, reset/reload and omitted H2D correctness | TRT_REAL / JETSON_REAL |
| Actual pinned destinations and aarch64 native fastpath integration | JETSON_REAL |
| Orin latency/20 Hz, power/thermal A/B | JETSON_REAL |
| FunctionFS kernel ownership, deadline, unplug/rebind and cleanup | USB_REAL |
| Actual comma stationary inference/fallback with each option | COMMA_REAL / VEHICLE_PARKED |

## Candidate manifests and rollback

The standard patch remains `patches/current-carrot-multimodel.patch` with SHA256
`04c7b08fd1fbcd21efddb103bdb0b336fe0ef92bffe0837b7fe2eb7344bffcf3`.
Its manifest advances only the validated upstream observation to ba1869151;
all generated source after-hashes remain unchanged.

The experimental patch and manifest are separate:
`patches/experimental-jetson-optimizations-a890.patch` and
`artifacts/experimental_jetson_optimizations_manifest.json`. They describe a
**complete patch from clean carrot-wip**, including the standard candidate.
Do not stack that patch on an already-patched standard copy. All touched files
have exact before/after hashes; patch SHA is in the manifest. AIO/Wi-Fi are absent.

Experimental full patch SHA256:
`c67cef9dac197ee8254dc928d72fdccdc30b840266ff3f9a78a7931cf8169776`.
Standard16 and experimental20 touched files are listed with before/after hashes.
Rolling baseline freezes813 relevant upstream blobs and44 local source/helper/
test/provenance files; optional adapter drift is a required FAIL, never auto-fix.

Apply/check/reverse were tested only in disposable development copies. Check
every after-hash, use `git apply --reverse --check <patch>` before reversing,
then check every before-hash (new files must disappear). Stop if any hash differs;
do not overwrite user changes. To return to the baseline candidate, regenerate
a separate standard copy from the freshly checked upstream. No engine/cache
deletion, runtime overwrite or service action is part of this rollback recipe.
Actual deployment/flag configuration waits for M0 and base-device validation.

## Execution checklist

Independent CPU review caught three candidate defects before publication:
an initially inconsistent host pointer could be accepted; a changed binding
name could skip camera H2D; and changing the allocation-owner binding map could
make cleanup free a foreign allocation. Regression checks now cover initial
pointer/array consistency and the complete binding ownership/name contract.
These are CPU_FAKE reproductions and fixes, not real CUDA observations.

The rolling fetch also now configures LF on each **new** reference checkout.
An explicit global-autocrlf fixture first reproduced changed before hashes and
expanded patch contexts, then passed with the fix. Existing reference contents
were not rewritten. Canonical upstream blobs, rather than Windows checkout EOL,
are the basis for the published candidate manifests.

1. [x] Fresh latest compatibility check and relevant-source diff evidence.
2. [x] Feature-by-feature comparison, DeviceState ordering/failure review.
3. [x] Default-off validation-preserving DeviceState candidate + fake CUDA tests.
4. [x] Exact native input conversion/binding tests + optional staging candidate.
5. [x] Isolated AIO bounded ownership/failure tests; no transport activation.
6. [x] Existing regression, optional candidate composition and combination tests.
7. [ ] Fresh final rolling verification, independent review, provenance/manifest,
   continuation update, small commits and feature-branch push.

M0 → baseline V3 TRT build → baseline recurrent inference → USB protocol3 →
latency measurement → one-at-a-time DeviceState/InputFastpath → AIO only if
latency evidence warrants it. Optimization must not conceal a baseline failure.

