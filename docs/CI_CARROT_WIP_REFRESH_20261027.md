# Current carrot-wip CI compatibility repair — 2026-10-27

Status: PASS_CPU_SOFTWARE_CONTRACTS. GitHub post-push result is recorded below after execution.
This work is offline software preparation. No comma/Jetson connection or mutation occurred.

## Failure and repair

Run [40518639645](https://github.com/rownlvh8875-coder/jetson-v3-backport/actions/runs/40518639645)
failed while building the candidate: `current server source body changed; review required: spec.py`.
The full-body guard correctly rejected new upstream code. This was unrelated to device reachability.
The previous local process/recorder suites did not prove rolling upstream compatibility.

Fresh carrot-wip is `604bc0a22733e648ec05b268da1ffaae7db52a69`.
Six of ten guarded server bodies changed: spec, queues, session, ONNX patcher,
TRT builder and TRT engine. The adapter now accepts either the complete old
reviewed profile or the complete new profile plus twelve native dependencies,
including both C implementations. Mixed/unknown bodies still require review.
No historical baseline, recorder pins, migration patches or evidence was changed.

Native N16 protocol2 keeps its current warm/infer/shape/HELLO implementations,
compact input/output, state feedback and native engine. Its canonical wire spec
is unchanged. Existing managed V3 code moves to `managed_engine.py`; opt-in
experiments use `managed_device_state` and `managed_input_cast` so they cannot
replace upstream N16 modules. Managed offroad, model/spec identity, exact physical
shape/dtype, all-output finite, state-transaction and generation gates remain active.
Native publication retains upstream fsync/replace and CacheEntry metadata handling.
Managed V3 publication retains the reviewed recoverable-pair rollback and persistent
engine digest check; this is not a claim of crash-atomic pair publication.

N16 is not enabled on protocol3 by this repair. It is rejected before adoption,
HELLO preserves its resident state, and late worker notifications cannot authorize
it or replace a previously adopted generation. V2 and managed V3 protocol3 continue
through their existing tested paths. No model, engine, runtime or package installation
was performed.

## Verification

Fresh complete command: `python -B tools/check_latest_carrot_compat.py --report <private-report>`.
ONLINE_LATEST PASS; all three upstream refs were rechecked unchanged at completion.
No baseline update. Every required suite executed, with no skip/xfail waiver.

| Group | PASS |
| --- | ---: |
| Current comma/server integration | 44 |
| Multi-model policy | 9 |
| TRT builder CPU contracts | 41 |
| Upstream Linux socket phases | 6 |
| Upstream wire/model/cache | 69 |
| Upstream modeld IPC/warp | 30 |
| Upstream native N16/state/compact paths | 113 |
| Optional optimization contracts | 99 |
| Rolling checker and read-only baseline/provenance gates | 150 |
| **Unique workflow total** | **561** |

FAIL0 / SKIP0. Environment: WSL Ubuntu24.04 x86_64, Python3.12.3,
pytest9.1.1, NumPy2.5.4, ONNX1.23.2. GitHub uses its declared pytest8
and NumPy2/ONNX1 ranges and must pass separately.
A supplemental old-layout run passed80 cases; these and focused/reviewer reruns
are not added to the unique workflow total. The root-wide collection, separate
diagnostics dependency and native FFmpeg limitations are outside this workflow;
none is represented as a passing hardware or full-root test.

Independent review reproduced missing C pins and unsupported P3/N16 adoption
(including late notification). Each was fixed with RED→GREEN tests. Final targeted
review is clean. No actual GPU/TRT, USB, vehicle inputs or numerical parity was tested.
Private full reports/logs remain outside version control. The accompanying artifact
contains sanitized source pins and counts, without device addresses or private paths.

## GitHub post-push verification

PENDING. A local PASS is not a GitHub Actions PASS. Inspect the run for the pushed
software commit and retain its job result before declaring the recurring failure fixed.

## Handoff

Feature branch only; protected refs remain unchanged. No workflow disabling,
required-check removal, source-hash bypass or automatic baseline advance.
Vehicle10 and parity remain NOT_RUN / UNDETERMINED; M2 remains NO.
Future upstream source drift must be reviewed through this gate again.
