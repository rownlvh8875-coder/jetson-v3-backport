# M19 retry — parked capture blocked at live stationary gate

2026-10-24. **BLOCKED_STATIONARY_UNCONFIRMED.** Fresh exact dirty-baseline
attestation **PASS**. Actual installation/restart/arming/activation/capture
**NOT_RUN**. The current user explicitly authorized those conditional operations;
the live stationary gate, rather than a missing approval or old clean-tree rule,
prevented them. No additional permission question was needed.

Actual carrot-nav remains
`366d6eae9aa9962104391e1d997fe956dea8f64d`, Offroad/Onroad **1/0**, tracked
modifications0. Original48 entries /2,006 files /417,208,589bytes remain exact.
Numerical decision **PARITY_UNDETERMINED / M2 NO**. Ready for256/512 road capture:
**NO**. There is no dataset and no actual-comma recorder overhead measurement.

## Actual execution boundary

The first actual shell commands were only:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

They returned1/0. The previously authorized Carrot terminal was reused with fresh
owned helper sessions. No SSH/key/host configuration, network scan or device
package change was made. Reviewed collection code ran in shell memory with history
and bytecode persistence disabled. There was no source/probe file upload.

Fresh baseline collection used the unchanged final M192 checker, its independently
pinned private manifest, a new collection challenge and the exact M18 patch. It
checked actual branch/HEAD, tracked/index status, private original paths/content/
metadata/tree digests, models, source pins, process/boot/environment identities,
route metadata and physical namespace. The old checker retains its intentional
PARTIAL on U32 alone; all22 other checks pass. No legacy policy was relaxed.

Current boundary8 hashes match exact366. The M193 direct-recorder isolation proof
was reviewed against those fresh observations, retaining current U32 runtime use
**UNKNOWN**. The independent canonical proof pin is
`d6e7f101e968af5e94b1789cf4983e88ee42643778aa9997b380548e1dc41558`;
the recomputed historical+fresh evidence-index commitment is
`05f9a81bdaf696b396e7a6b14a16a5b151b71bab6f4eaa8ff6aaf8d1779dbaf0`.
The fixed M193 composer validates schema/scope/condition keys and both commitments,
resulting in **M193_ATTESTED_BASELINE_PASS**. Receipt hashes correlate trusted
observations; they do not authenticate an operator or make stored data fresh.
The current user prompt supplies conditional execution authority separately.

Original aggregate digest:

```text
8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5
```

The runtime26 and generated/backup20 remain in place. U46 retains its resolved
legacy-generated policy. U32 is accepted only for isolation with the frozen
recorder, never relabeled unused. Recorder path/physical namespace conflict: NO.

## Live stationary evidence

After PRE passed, a bounded existing-telemetry check observed fresh messages for
**3.04245161s**. All six requested service queues existed before subscription.
No absent endpoint was intentionally created, no publisher/CAN reader/control
process was launched, and no producer/model/Params/USB policy was changed.

| Service | Received messages | Relevant result |
|---|---:|---|
| carState | **0** | No fresh vEgo/standstill available |
| managerState |5| card/modeld/camerad false, jetlinkd true in all5 |
| deviceState |5| started false in all5 |
| modelV2 |0| No model timing/output sample |
| roadCameraState |0| No camera sample |
| wideRoadCameraState |0| No camera sample |

This is a functioning telemetry observation with missing carState data, not an
inferred zero speed, stale route replay or synthetic stationary message. **Vehicle
stationarity is NOT_CONFIRMED; this is not evidence that the vehicle was moving.**
The gate requires live evidence, so no mutation phase followed.

The pinned native subscriber opens existing queues with O_RDWR/O_CREAT, performs
ftruncate/shared mapping and standard reader/cursor registration. “Receive-only”
describes authority: there is no publication/control output. It does not mean zero
native IPC bookkeeping writes. Pre-existing endpoint checks are not an atomic
promise against concurrent queue replacement. The operational source, overlay,
route and model preservation results below are measured separately.

Exact366 process_config starts modeld/card only_onroad, camerad under driverview,
and Jetlink daemon always_run. The observed managerState agrees with normal
Offroad behavior. No process was forced on to supply speed or image tuples, no
model selected, and no onroad/USB condition changed. The later **parked tuple
availability gate was NOT_RUN**. This is not CAPTURE_ZERO_FRAMES_UNAVAILABLE or a
failed capture attempt; the attempt never began.

## Gate outcomes

| Gate / operation | Result |
|---|---|
| Initial/final flags and exact366 | PASS |
| Fresh exact PRE dirty baseline | PASS under explicit M193 scope |
| Live stationary | **BLOCKED_STATIONARY_UNCONFIRMED** |
| Storage/capability gate | NOT_RUN after stop |
| Device disposable patch roundtrip | NOT_RUN |
| Private on-device source backup | NOT_RUN |
| Actual patch / six after hashes | NOT_RUN |
| Restart / patched-OFF health | NOT_RUN |
| Tuple availability / ticket / activation | NOT_RUN |
| Stationary capture | NOT_RUN; frames0 |
| Dataset / continuity / digest | NONE / N/A / absent |
| Reader replay / ORT / TRT | NOT_RUN |
| Actual observer/copy/queue/RSS metrics | NOT_MEASURED |
| Model timing comparison | INSUFFICIENT_SAMPLE |

The frozen patch SHA is unchanged:
`3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee`.
Its expected one existing-file change and five additions were not installed.
Recorder remains OFF by absence, rather than a claim of tested patched-OFF health.

The theoretical10-frame binary is3,938,176bytes. With the existing64MiB reserve,
its minimum is71,047,040bytes. A final read observed28,430,614,528bytes free. These
are arithmetic/read-only observations, **not a completed storage/capability PASS**.
No output, ticket, backup or disposable directory was created on the device.

## Cleanup and preservation

No activation/ticket was created, so neither was removed/invalidated as if an
installed recorder had run. Final observations show no capture environment in
three inspected manager/Jetlink-related processes, writer0, package absent and
proposed capture root absent. No other owned audit helper remained. No rollback
or restart was needed. Final source state **BLOCKED / NOT_INSTALLED**, unchanged
original PRE profile, rather than ROLLED_BACK or PATCH_LEFT_INSTALLED_OFF.

Fresh final collection again verifies the frozen original manifest/challenge.
Legacy PARTIAL remains U32-only. Original48 and all other structural/preservation
checks match. Private original-path mappings were used; IDs were not remapped.

| Preserved group | Before/final result |
|---|---|
| Original48 content/mode/UID/GID/mtime/ctime | Exact original digest |
| U32/U46 | Exact SHA unchanged |
| Selected source files |8 hashes unchanged |
| Selected model files |15 hashes unchanged |
| Runtime/boot/resolution identities |31 unchanged |
| Route metadata |4,497files; digest unchanged |
| Git index/native library/U32 cache canaries |3 unchanged |
| Recorder namespace | Absent |
| Branch/HEAD/flags | Unchanged |

U32 SHA:
`07e2bd4cdac1479f85447c1f96182c8f24603a9184b11045086d7433b68e5b70`.
U46 SHA:
`21ac37949a83dcb5b2799007c8ebc93909efaff7bf6d6481fb49a8eb2a43314e`.
Route metadata digest:
`4bf474e52edc1b6ad250ed125b23a87a34ecd781799fa47040247aebef499c24`.
This hashes relative path/mode/size/mtime, not all route contents. Atime is excluded;
ordinary reads may update it. **Operating preservation PASS** within this observed
scope, not an atomic whole-device image, live-module or inference-health proof.

## Offline regression and evidence

Fresh **CPU_FAKE/FIXTURE:258 PASS /0 FAIL /0 SKIP,29.37s**. Unique scope is M18
recorder131 + M192 checker68 + layout1 + M193 provenance58. Older session counts
are not added. No recorder core, adapter, checker or production code was changed.

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_u32_provenance.py tests/test_comma_dirty_baseline.py tests/test_comma_dirty_layout.py tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py --tb=short
```

The [sanitized artifact](../artifacts/m19_parked_capture_20261024.json) contains
counts/statuses/commitments and metrics only. Raw paths, argv/environment,
addresses, service payloads and private manifests remain in ignored local evidence.
No raw tensor/image/video/log or credential is committed. No captured dataset
exists to transfer or upload. The earlier frozen M15/M18 software remains intact.

COMMA_REAL_READ_ONLY observation occurred. COMMA_REAL_CAPTURE, actual parked
validation, ROAD_TEST, Jetson, USB_REAL, ORT and TRT were NOT_RUN. The existing
M1 plan remains DO_NOT_INSTALL and was not accessed this stage. Numerical decision
is still **PARITY_UNDETERMINED / M2 NO**.

One independent final read-only review **PASS**, with no Critical/Important/Minor
finding. The reviewer recomputed fresh proof/bundle/receipt commitments, original48
and preservation evidence, telemetry counts and public-path privacy. It did not
contact devices, rerun tests, certify stationarity/capture, U32 non-use or whole-
device/inference health. Final normal feature push/clean/protected-ref checks are
the executor's separate publishing step; this review grants no device authority.

## Next exact action

Perform a separate offline source-backed review of whether live stationary
evidence and the exact model input tuple can coexist under required Offroad1/
Onroad0 policy. This result authorizes no forced producer, onroad transition,
model/Params/USB change or road capture. Repeating installation or extending a
telemetry timeout cannot replace the missing gate evidence.

Development started clean/remote-equal at
`78de3b2eb8f92e5b7b14367ac792be310526b5d4` on the required feature branch.
Result commit resolves with
`git log -1 --format=%H -- artifacts/m19_parked_capture_20261024.json`.
Protected main and old-feature refs remain unchanged; only feature docs/evidence
are committed/pushed.
