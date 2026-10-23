# M2 parked protocol-3 USB execution plan — NOT EXECUTED

Date2026-10-23. This document authorizes no device changes. M1 plan remains
**DO_NOT_INSTALL**. M1.5 numerical measurements cannot be promoted to behavioral
approval without applicable criteria. A later separately approved M2 must use
the final reviewed manifests and fresh actual hardware state, not remembered IPs
or permanently pinned moving branches.

## Entry gates

- No vehicle control/driving. Confirm actual physical parked state, ignition
  status, no engagement, and fresh IsOffroad1/IsOnroad0 on comma. Unavailable or
  conflicting observations stop the session. Carry a live fail-closed guardian.
- Fresh actual comma/source hash must match the candidate base or a newly
  reviewed regenerated adapter; do not automatically upgrade to latest Nav/WIP.
- Verify exact original models/plans, operating cache/timing files, current
  symlink, five releases, unit/drop-ins/ExecStart, and the isolated M1 V3 plan.
- Numeric gate: review M1.5 semantic/parsed differences and establish approved
  acceptance criteria or obtain an explicit separate scope for non-adopting
  synthetic transport diagnostics. No implicit model adoption is authorized.
- Review the complete host/comma candidate manifests and prepare before/after
  hashes plus exact source rollback. A Nav comma patch is not a Nav host port.
- Actual FunctionFS endpoints must have one owner. Existing operating service
  owns USB: no parallel candidate can bind/rebind those endpoints. Before M2,
  explicit authorization and a reviewed handoff/restore procedure are required
  for any operating service stop/start or comma development launcher. Do not
  guess installed gadget/controller/bootstrap behavior from source candidates.
- Keep operating releases/current/cache/selected.json untouched. Use private
  development source/cache/status/control paths and the existing isolated plan;
  no install/update/migration/boot entrypoint, cache pruning, model download,
  build, package/JetPack/TRT/CUDA/power/clock changes.
- Flags0 throughout BASE:
  CARROT_TRT_DEVICE_STATE, CARROT_TRT_INPUT_FASTPATH, CARROT_JETLINK_AIO_WRITE.

## Phase0 — read-only preflight

First commands on the confirmed Jetson shell, without importing CUDA/TRT:

```sh
readlink /opt/carrot-jetlink/current
systemctl show carrot-jetlink.service --no-pager --property=ExecStart,ActiveState,SubState,FragmentPath,DropInPaths
sha256sum /run/carrot-data/jetson-v3-m1-20261023/build/cinque-v3.plan
```

Expected plan SHA:
`8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa`,
768580676 bytes. Also rehash source ONNX404a18cf/766354845 and bound sidecar.
Read-only operating model/cache inventory must equal the previous checkpoint;
no repair/removal if it differs. Use `tools/jetson_runtime_inventory.py` or
equivalent reviewed commands; raw serials/addresses/credentials stay ignored.

On comma read branch/HEAD and both road flags; compare source files with patch
before hashes. No checkout/update/Params/model approval write in preflight.
Re-query Nav/WIP/carrot-jetson/Jetlink/review refs and analyze relevant drift.
Confirm mount/disk/RAM/swap and service ownership. Record temperature/power/
throttle read-only before load; do not change clocks to improve results.

## Phase1 — development-only launch

After separate M2 authorization, perform the reviewed exclusive endpoint
handoff. Never invoke operating server.py/update/boot tools merely to start a
candidate: those can migrate/prune/change runtime. Use a reviewed direct host
launcher with explicit development cache/control/status paths, resident exact
M1 artifact and trusted offroad provider. Confirm the host cannot download,
build, switch model or write operational files during an attached session.

Comma development process must use the six-file candidate and private approval/
IPC/status paths. Simply setting PYTHONPATH on an already running manager is
not isolation. Determine actual boot/manager path behavior read-only first;
validate a development launcher without replacing the live checkout. Abort if
no isolated process/endpoint ownership can be established. Keep native small
model available and do not activate a vehicle control publisher.

## Phase2 — protocol-3 HELLO

Capture actual framing version and HELLO identity together: protocol3,
carrot_host=jetson, backend=trt, actual Orin device/runtime, explicit
carrot_model_selection_v1 version1/selectionhost, and resident loaded SHA.
Capability is descriptive, not authentication. Reject missing/wrong identity,
unloaded/missing engine or unsupported model; no arbitrary big-model fallback.
ENGINE_REQ must bind exact SHA/size/spec/dtype maps to reviewed V3, preserve
snapshot/generation and require first approval offroad. Reconnect may reuse
only exact approved spec. Malformed capability must not fall into legacy Nav.
Record clean HELLO/re-HELLO reset and old-session response rejection.

## Phase3 — controlled BASE synthetic USB

Start with zero reset and small bounded deterministic inputs, not vehicle
camera/control adoption. Use full output and every recurrent state validation;
no Nav N16 projection for V3. Compare wire bytes/counts, sequence/frame IDs,
RESET_QUEUES, shapes/dtypes/finite and generation/reload-zero behavior. Keep
original production deadlines. A lost guardian or state validation failure
retires the process/session; no invalid generation retry. Expand duration only
after each gate passes. Classify USB_REAL/JETSON_REAL/SYNTHETIC_INPUT explicitly.

## Phase4 — actual parser

Send measured responses through actual Nav daemon IPC/parser in the isolated
comma development process. Compare raw semantic slices and final parsed
trajectory/lead/probability/meta/desire/action shapes/values against the bound
local references. Parser success does not grant a numeric error budget. Record
source SHA and all needed runtime mocks/seams; actual comma inference is a new
COMMA_REAL gate, not an extension of CPU fake results.

## Phase5 — controlled timeout/disconnect/identity faults

Inject only into the dedicated development session. Test dropped response,
truncated/short reply, wrong/stale frame/sequence, bad SHA/spec, disconnect,
bad dtype/shape, driving NaN/Inf and next-state failure. No operating process
kill, cable reset while shared, arbitrary packet corruption or timeout increase.
Confirm first invalid reply never becomes an OK result; partial state failure
invalidates generation; reconnect/reload starts zero state. Onroad transitions
must reject new model approval/selection/preparation; do not drive to test this.

## Phase6 — local-small fallback

Verify actual small engine is pre-executed and remains usable. On timeout,
disconnect/identity/state failure, the real JoiningModel path returns finite
small-model outputs and closes remote IPC. If already active externally,
existing reset/fault/commIssue behavior must be preserved; no silent switch
under control. Record failure→fallback latency and first valid local frame,
camera age and modelExecutionTime. Do not claim fallback from a UI ready bit.

## Phase7 — V2/Nav rollback

Restore the exact original approved endpoint owner/launcher state, source
hashes and current link; do not overwrite/delete any model or plan. Verify
original Nav P2 stateful_v2, maps/navigation, five state pairs and exact N16
projection negotiation. Verify V2 P2 bytes/prev_feat against its reference,
without replacing Nav's original exact default selection with V2. Any actual
model selection change requires its own explicit offroad scope and restore
record. Rollback is not accepted merely because old files exist.

## Phase8 — latency, memory and thermal measurement

Capture each region separately with documented timestamp boundaries. Do not
subtract unsynchronized comma/Jetson clocks to infer one-way USB latency.
Use same-host monotonic clocks, roundtrip spans, USB completion instrumentation
or a separately validated clock-mapping method; unavailable regions stay
NOT_MEASURED. Instrumentation must not change production deadlines.

| Region | Required boundary |
|---|---|
| Jetson GPU | CUDA events around actual execute, completion waited |
| Jetson server total | validated request received → complete validated response ready |
| USB request TX | comma send start → actual transfer completion, not queue acceptance |
| USB reply RX | first/completed receive boundaries on comma; include framing handoff |
| comma client total | request begin → validated reply for matching frame |
| modelExecutionTime | actual modeld published field with documented included stages |
| camera frame age | same-host camera source timestamp → inference submission/result |
| parser publish age | camera/result timestamp → completed parsed publication |

For every region: sample count, cold/warm distinction, p50/p95/p99/max, >50ms
count and ratio, dropped/late/stale frames and timeout count. Keep first frames
and outliers. Also record RSS/available RAM/swap, GPU memory if available,
temperature/power/throttle, concurrent operating load and duration. M1's
46.849ms local host mean and47.107ms p99 exclude camera/USB/production scheduling;
its93.131ms cold host tail remains evidence. No average-only20Hz approval.
The recovered M1 tactic64,704,384-byte OOM stays in the record; do not rebuild,
increase workspace, tune swap or change TRT settings because of it.

Only after BASE end-to-end/fallback and thermal gates: separately approved
DeviceState A/B → DeviceState+InputFastpath → AIO only for a measured TX-tail
problem. Each variant gets the same numerical/fault/latency gates and rollback.

## Phase9 — cleanup/restore and stop rules

Stop only owned candidate workers, drain/release endpoints safely, restore
only the explicitly authorized original owner/launcher, close temporary
controllers/SSH relays and verify no workers remain. Repeat all before/after
hashes, unit/drop-in/ExecStart/current/release membership and road flags.
Keep all evidence and the private M1 plan. Do not auto-delete experimental
outputs or repair changed operating files. Nonmatching preservation is FAIL.

Abort on uncertain offroad/parking, identity/spec drift, invalid state,
nonfinite/malformed output, behavior-sensitive numeric anomaly, regression,
unsafe endpoint cleanup, operating hash change or unresolved memory/thermal
fault. Report phase, source/engine SHA and observed result; no automatic retry,
upgrade, relaxed gates or deployment. ROAD_TEST is a distinct later stage.
