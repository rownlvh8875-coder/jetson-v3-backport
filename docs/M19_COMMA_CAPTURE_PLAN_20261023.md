# M19 — future comma capture plan; NOT_EXECUTED

**2026-10-24 gate update:** the user explicitly replaced the earlier clean-tree
requirement with the exact private attestation gate in
[M19.2](M192_ATTESTED_DIRTY_BASELINE_20261024.md). Preserve all48 runtime-overlay
entries in place. This is not a count whitelist or installation approval.
Require ATTESTED_DIRTY_BASELINE_PASS with freshly bound identity/content/metadata,
resolved or explicitly reviewed U32/U46 isolation and zero recorder collision.
The current actual result is PARTIAL on U32, so installation remains blocked.
The parked/stationary, disposable device test, OFF health and separate execution
authorization below still apply. M19.2 itself performs no install/restart/capture.

This plan requires separate explicit user approval before any actual installation,
restart, activation or recording. M18 only prepared/tested an offline default-OFF
candidate. Numerical parity is PARITY_UNDETERMINED, M2 USB readiness NO. No V3
engine is selected/installed by this plan, and no Protocol3 USB session is started.

## 1. Parked/offroad preflight — first action

In the existing authorized actual-comma session, first run only:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

Require exactly1/0; otherwise stop installation/arming. Establish fresh process
identity and actual source root from the running process/M0 inventory. Read its
branch/HEAD/working tree and require carrot-nav
`366d6eae9aa9962104391e1d997fe956dea8f64d`; latest Nav is not a replacement.
Capture private before hashes of the five M18 source pins, existing model files,
current launch/manager/modeld process identities, and route file inventory. No GPS,
route names or network/SSH details go to public evidence. Any tracked change,
unattested untracked content or pin mismatch stops deployment; never
stash/reset/delete changes automatically.

Read-only inspect candidate storage mount/permissions/free space. Recommended
root `/data/media/0/v3_input_capture/` is not yet created or verified. It must be
outside realdata, source, runtime and operating caches. Confirm Linux memfd,
SOCK_DGRAM, pass_fds, posix_fallocate/fsync/link and target Python/NumPy support
in a development area. No package/clock/power/JetPack change to make a test pass.
512 frames require268537856 bytes free including64MiB reserve; preserve extra
operating logging headroom as observed on device. No route/cache deletion.

## 2. Preservation and review before applying

Review M18 patch and its before/after/patch hashes and verify local package hashes.
Prepare an off-device and separate private on-device source backup; never back up
over an existing path. First repeat forward/reverse verification in a disposable
source copy on the device. The generated footer changes one existing file and
adds five modules; original methods are unchanged. Do not combine this patch with
the frozen M15 adapter or any newer Nav shared-input work automatically.

Only after approval and all parked source gates, apply to the reviewed operating
source with no other source/runtime/model/Params changes. No manager restart is
implied by patch approval. Verify all six after hashes and existing source hashes.

## 3. CPU smoke and OFF gate

Run CPU fixture/reader smoke in the separate development copy first. Do not load
M1 TRT/ONNX or initialize USB/GPU to test the recorder. Verify explicit environment
variable absent, no tickets, and no recorder files/process/ring/copies at OFF.
Verify source imports are possible in the device environment and no existing
manager/modeld/import exception changes. Restart modeld/manager **only with separate
explicit authorization**, while parked/offroad and after preservation evidence.
An unchanged OFF restart must precede enabling anything.

Record existing model input/output/timing/IPC baseline where existing diagnostics
allow it; do not add telemetry that changes vehicle control. Scheduler, CPU affinity,
writer RSS/child lifecycle and camera cadence must be measured here. Offline host
p99 does not establish a safe on-device overhead budget. Agree this gate using
existing model timing/frame-age/deadline behavior; never increase inference timeouts.

## 4. Explicit short stationary capture

Read fresh offroad flags again. Confirm an **already authorized existing V2/Nav
Jetlink nonstate path** supplies the borrowed image+packed tuple with exact ticket
source SHA/spec. Recorder must not create/force that path or change its model.
If the device is internal-small-only or the source handshake/layout differs,
stop: capture is unavailable on this hook. Do not activate USB or select V3 to
bypass the condition. New hooks would need another reviewed offline stage.

After separate activation approval, create a fresh private output root and a
short-lived one-shot ticket via the reviewed `arm_ticket` helper (frames10,depth4),
passing source SHA/spec verified from the existing source and fresh trusted offroad
proof. No Param or persistent environment/service configuration is created. Pass
CARROT_V3_INPUT_CAPTURE only to the explicitly authorized temporary process/launch
invocation. Ticket consumption is once-only, boot-bound and expiring. No unattended
automatic rearm; do not reuse `.consumed` claims or old capture IDs.

No exact launcher command is finalized until actual launch environment and approval
are confirmed; do not substitute an invented production restart command. This
stationary trial may return0frames if existing joining is not permitted while
parked. Treat it as unavailable; do not modify join/control predicates to pass.

Validate the resulting dataset privately with `tools/v3_input_dataset.py validate`.
Require exact expected10frames, COMPLETE, all hashes/spec/source identities,
continuity/finite/scalar/transform checks. Compare saved input bits against existing
source fixture/authorized diagnostics where possible. Check queue high-water,
writer scheduling and process count, model frame timing/age/deadline counters,
memory/thermal/storage and original result/exception behavior. Any performance
regression or writer-induced model delay blocks road capture.

Explicitly exercise recorder-only stop/invalid ticket in the disposable copy, then
verify private-child cleanup and retained bounded mapping/zombie limitation. Reboot
or normal authorized process exit is the current definitive resource release;
no blocking close/wait belongs in the inference hot path. No service/process is
killed as an automatic memory workaround.

## 5. Separately approved road capture

Only after stationary gates and user approval of the recording drive, arm one new
256- or512-frame ticket while offroad. Recorder may then observe onroad inputs
without modifying controls, CAN, model selection or USB. Keep the established
operating model/service/transport and existing driver safety procedures. This is
data acquisition, not a V3 road test. No automatic controls/planner replay or CAN
output is authorized. No driver interaction with scripts while moving.

Prefer a continuous sequence in naturally available straight/curve/lead/stop-go or
desire-change conditions. Do not invent labels, change settings to force scenes,
or ask the driver to induce lane changes for a synthetic category. First overflow,
source gap/reset/spec drift or writer fault invalidates only capture. Do not retry
automatically onroad. Cap completion terminates recording. Do not save full camera,
GPS, cabin video or rlog as a workaround.

## 6. Disable, validate, transfer and restore

At parked/offroad return, remove the temporary activation from the future launch
environment; ensure no new valid ticket remains. Do not delete user routes or prior
recordings. Confirm no recorder continues writing; child/ring release follows the
authorized close/process lifecycle. Privately copy only the new completed datasets
to the approved development area; verify source/copy full SHA256 and counts before
accepting them. INCOMPLETE datasets cannot support numerical acceptance.

With separate rollback/restart authorization and fresh offroad gates, verify after
hashes, apply the exact reverse patch and verify the original model.py SHA plus
absence of the five added package files. If source drift is observed, stop and
inspect; never reset or blindly reverse other changes. Preserve recorder outputs
separately. Restore only authorized temporary launch settings, then perform the
approved restart/reboot and verify OFF behavior, original HEAD/branch/user tree,
manager/modeld process state, model/service/cache hashes and route preservation.
M19 report must separate pre-existing changes from this session's changes.

## 7. Next numerical stage and holds

M1.9 parity uses only validated exact logical datasets, original V3 ONNX
404a18cf… and unchanged M1 plan8f831b5a…, with zero initial state and each runtime's
own recurrence. Keep recorded and synthetic results separate. Include independent
and teacher-forced comparisons, parser/selected lead/desire/near-term trajectory,
full128-slot turnover and source/privacy-safe provenance. Collect approved semantic
tolerances before PARITY_PASS. Neither capture success nor hash consistency grants
numerical, M2 USB, comma inference, vehicle or road-test approval.

All optimizations remain OFF: CARROT_TRT_DEVICE_STATE=0,
CARROT_TRT_INPUT_FASTPATH=0, CARROT_JETLINK_AIO_WRITE=0. No plan rebuild, cache publish,
selected.json/current symlink change, package upgrade or USB Protocol3 activation.
