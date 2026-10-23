# M19 parked capture — stopped before installation

2026-10-23. **BLOCKED_DIRTY_TREE.** Actual comma returned Offroad1/Onroad0,
carrot-nav at366d6eae9aa9962104391e1d997fe956dea8f64d, and the five M18 original
source pins matched. Its `git status --short` nevertheless contained **48 untracked
short-status entries**, including build-like outputs, a controller backup and a
custom controls source. No tracked modification appeared. These are collapsed
status entries, not a recursive count of48files, and their ownership/generation
was not established. They were preserved, not ignored, stashed, reset or deleted.

The user's clean-tree gate admits no automatic generated-file exception. STOP
RULE D therefore stopped all actual installation/restart/activation/capture
operations. The M18 patch and core are unchanged. **No dataset, no stationary10
capture attempt, no road capture, no M2 USB, no Jetson/ORT/TRT execution.**
Numerical decision stays **PARITY_UNDETERMINED / M2 NO**.

## Authority, access and observed source

The current prompt explicitly authorized the exact366 patch, minimum normal
restart and temporary10-frame parked capture, conditional on every gate. No
additional approval question was required to execute those authorized phases;
the source gate itself prevented them. The earlier future-plan approval language
was satisfied by this prompt and was not used as a reason to stop.

Development started clean/remote-equal on
`feature/jetlink-multimodel-carrot` at
`3940a8d3a8d130342e66a14a96c128a7237772a7`. Main and old-feature remote refs were
read for preservation. Actual runtime was not updated, switched, pulled or rebased.

Direct SSH with strict host checking could not establish a trusted session;
no missing host key was accepted/bypassed and no key/agent/SSH configuration changed.
The existing previously used Carrot web terminal provided the authorized shell.
Only fresh owned helper sessions were opened. The **first actual shell commands**
were exactly:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

They returned1/0. The initial display parser expected a trailing newline; Params
files have none, so their next prompt follows the digit. Private raw evidence
retains that output, and a corrected fresh read confirmed1/0. Subsequent probes
also read/required1/0 first. This was a parser retry, not a changed device state.
History/bytecode persistence was disabled in owned helpers after the initial two
required reads; commands stayed in memory and no probe source was uploaded.

Manager-argv candidate processes resolved from their real cwd to the **same**
source repository. A fork child retains the manager argv, so a unique argv match
was not assumed to prove a unique manager. Current branch/HEAD/status and source
hashes were read from that observed running root. No private source-root, network
address, process argv, route name, coordinates or raw logs are in the public JSON.

The running source/head/tree were checked before importing a live telemetry
subscriber from that tree. Once the dirty gate failed, no subscriber/control/CAN
reader was launched. **Stationary telemetry is NOT_RUN / stationary NOT_CONFIRMED.**
Offroad does not establish zero vehicle speed. Neither historical logs nor default
zero values were substituted for live carState evidence.

## Gate and capture result

| Gate / operation | Result | Meaning |
|---|---|---|
| Actual Offroad / Onroad | PASS:1/0 | Fresh initial and final reads |
| Running source root | PASS | Process cwd→repository resolution |
| Exact branch/HEAD | PASS | carrot-nav366 throughout observed window |
| Original M18 source pins | PASS:5/5 | Original bytes, not installed after hashes |
| Clean source tree | **FAIL** |48 untracked short-status entries |
| Current vehicle stationary | NOT_CONFIRMED | Live telemetry phase not entered |
| Device capability / disposable patch / backup | NOT_RUN | No device development files created |
| Actual patch apply / after hashes | NOT_RUN | One existing/five new files not installed |
| Patched recorder OFF health/performance | NOT_RUN | No patched runtime was loaded |
| Restart | BLOCKED / not performed | No manager/modeld/service/control change |
| Tuple availability / ticket / activation | NOT_RUN | No inference/joining/selection forced |
| Stationary capture | **NOT_RUN_BLOCKED_DIRTY_TREE** | Zero captured frames; no attempt |
| Dataset / continuity / digest | NONE / N/A / absent | No COMPLETE or INCOMPLETE dataset |
| Actual observer/copy/queue/CPU/RSS/timing | NOT_MEASURED | No actual-comma performance acceptance |

This is **not** CAPTURE_ZERO_FRAMES_UNAVAILABLE: that classification would require
an actual allowed availability/capture test. Here the stop occurred earlier.
The reviewed process configuration starts modeld/card only_onroad, and the live
process inventory did not observe modeld/card/camerad. That is consistent with
normal offroad policy, not proof of a broken model process or permission to force
one to start. The always-running Jetlink daemon was not changed or exercised for
inference. No onroad/USB/model/Params workaround was attempted.

## Read-only preservation window

Because the source gate already failed, snapshots were used only for preservation;
they were not followed by a mutation. Both snapshots retained exact branch/head,
flags and the same48-entry status. Comparison PASS:

| Compared evidence | Result |
|---|---|
| Original M18 target/related files |5 identical SHA256s, all reviewed pins match |
| Manager/process configuration/modeld source |3 identical SHA256s, also match pinned Git objects |
| Two selected untracked backup/custom source canaries |2 identical content SHA256s |
| Model directory regular files |15 identical content SHA256s; no pickle executed |
| Observed manager-lineage/Jetlink processes |3 identical PID/argv/cwd/start-time identities |
| Existing routes |4497 inventory entries, identical metadata digest |
| Recorder package / proposed output root |Absent in both snapshots |
| Recorder activation in inspected process environments |Absent in both snapshots |
| M18 writer processes |0 in both snapshots |
| Other owned M19 terminals at final probe |0; current helper exits automatically |

Route inventory SHA256:
`4bf474e52edc1b6ad250ed125b23a87a34ecd781799fa47040247aebef499c24`.
It hashes relative paths/mode/size/mtime; it is **not** full-content hashing of
all route recordings. Other untracked file contents were not exhaustively hashed.
The narrower measured window and content scope are not presented as a complete
session-start attestation of every device file. The count differs from historical
M17 inventory; only the fresh M19 before/after counts/digests are compared here.

There was no actual source application, backup, recorder-output/ticket directory,
activation, restart or rollback. **Source final state: BLOCKED_NOT_INSTALLED.**
No route/model/cache file or user source was written by these read-only probes.
No valid unused ticket was created; activation cleanup is NOT_CREATED, not evidence
of an installed recorder being turned off. Actual normal manager/daemon identities
were preserved; functional V2/Nav inference/OFF timing was not tested.

Read-only free-space observation was about28.4GB. The fixed10-frame binary would
be3938176bytes; the existing writer's64MiB reserve makes its minimum71047040bytes.
This arithmetic is not a storage/capability PASS: output-root permissions, memfd,
pass_fds, allocation, fsync/link and writer compatibility were not exercised after
the stop. No package installation was attempted.

## Offline verification and source pin

M18 patch SHA256 still matches both the artifact and repository:
`3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee`.
No existing M18 recorder, adapter, numerical tool or patch was edited. No new
evidence-parser production code was needed; only docs/sanitized evidence change.

Independent final local read-only review PASS: counts, all preservation groups,
unchanged patch SHA, source/stop/NOT_RUN classifications, privacy and matching
start/end upstream values verified, with no blocking or important findings.
The reviewer made no actual-device connection or command. Final normal feature
push/clean/remote/protected-ref verification remains the publishing step.

Fresh WSL CPU_FAKE/FIXTURE regression: **PASS131 / FAIL0 / SKIP0**,26.34s.
This is the four unchanged M18 files'131 tests, not prior218/708 added again,
and not an actual device disposable test or capture. Existing reviewed interpreter
was used with no package changes. Reproducible command from repository root:

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py
```

Start and end upstream re-queries returned identical observations:

| Source | Full HEAD |
|---|---|
| Latest carrot-nav |810e14aaf51176f1a50a113939dc2e70907b394b |
| Latest carrot-wip |dfab65d03fcd7100f572fe9e6908f4c6d1e988f6 |
| carrot-jetson main |d0dc96fa32410403dfb2fefff3e2909c11ec109b |
| zoompilot/jetlink main |d24328d849b0e5154b55f149dc18c5dfe8bd79cc |
| external review |a890f6df1bd3eb0478754c68d8b5f92f15e8b722 |

The actual target stays366; no latest upstream source is adopted. The M1 plan
8f831b5a… remains DO_NOT_INSTALL, supported by existing evidence and the fact that
no Jetson access occurred, not a fresh Jetson hash. ORT, TRT, USB_REAL,
COMMA_REAL_CAPTURE, VEHICLE_PARKED and ROAD_TEST remain NOT_RUN this stage.

## Decision and next action

**M19 capture goal NOT ACHIEVED. Ready for256/512 road capture: NO.**
Numerical decision PARITY_UNDETERMINED; M2 readiness NO. No road continuation.

Next exact step: a read-only ownership/generation audit of the48 untracked
short-status entries, preserving their contents and resolving the clean-tree
gate explicitly. Do not clear them with reset/stash/delete/ignore manipulation
or relabel unknown custom/backup files as harmless build artifacts. Current M19
authorization does not waive that gate. After it is legitimately resolved, a new
parked preflight must also establish current stationary evidence and whether the
unchanged existing path can supply the tuple under offroad policy.

Full sanitized machine evidence is
`artifacts/m19_parked_capture_20261023.json`. Raw private access/source/status/
preservation evidence stays ignored on the PC. The M19 documentation commit is
resolved by `git log -1 --format=%H -- docs/CODEX_CONTINUATION.md`; final development
HEAD by `git rev-parse HEAD`. No raw tensor, image, route or credential is committed.
