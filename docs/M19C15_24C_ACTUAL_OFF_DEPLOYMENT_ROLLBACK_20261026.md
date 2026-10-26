# M19-C1.5 — exact24c actual OFF deployment: rollback receipt

2026-10-26 · **ROLLED_BACK**

The reviewed three-file migration was applied once and all six AFTER hashes,
wrapper/footer/default-OFF checks passed. Full POST attestation failed exactly
one of ten checks: process-set preservation. The guard therefore applied the
exact reverse once and verified **pure24c + surviving5bb package byte restoration**.
There was no reapply, restart, ticket, activation, capture or Jetson access/change.

Actual final branch/HEAD: carrot-nav / `24c1ba5e4b3428f56fa0e402f5a10097e2e94c32`.
Final OFF/ON1/0; fresh deviceState.started=false; Panda ignitionfalse/false.
Final recorder footer count0. **RECORDER_24C_HUD_HOST_V1 is NOT installed.**
Ready for Vehicle10=NO; PARITY_UNDETERMINED; M2=NO.

## Fresh first gate, source and PRE

The user's comma-only power connection supplied fresh first cat OFF/ON1/0.
Initial simultaneous12.008738154s receive-only window PASS:23deviceState,
114pandaStates,23managerState. Every service covered10+seconds of fresh source
time. Source was exact24c, tracked modifications0, cached diff0. Pure model,
surviving5bb package and all41 pins matched exactly. N16 model/spec/API passed.

Fresh current PRE covered49untracked entries/
2011files/417272129bytes,
2206ignored nodes,15model files,
4565route metadata entries and28runtime identities.
The current overlay was inventoried anew, not matched to a historical digest.
Private raw names/addresses/environment/boot/process data are not published.
Immediate PRE commitment: `0bd76d2cb7cbc6b1daf8cbef9838010f6d076a51286043e7f4683f3343116b2c`.

The existing /data/v3_input_capture remained canonical, real, empty0700,
UID/GID1000:1000 on internal/removable0 ext4 /data. Its device/inode/mode/owner/
timestamps/contents were compared unchanged. Available PRE bytes:
28365828096. No mkdir/chmod/chown/probe or child creation
was performed in this storage root.

## Disposable proof, backup and one apply

The exact fresh actual PRE blobs passed18 disposable checks: both patch SHAs,
apply-check/forward/AFTER6/syntax/wrapper/metadata identity/Warp/footer/defaultOFF,
inverse check/apply/byte restoration and no index mutation. Fresh regression
passed1313 unique CPU_FAKE/POSIX cases:1165 controls+148 exact24c,0fail/error/skip,
no retries/double counting. Independent helper review passed76 local static/
mocked guards; these and disposable18 are separate from1313.

Three source files were backed up outside the source tree in one private0700
directory, exclusive/no-follow0600 regular files with exact hashes and file,
directory and parent fsync. Backup files remain private and retained.

After another fresh12.050015901s OFF window, immediate exactHEAD/PRE6/41pins/N16/
index/boot/namespace/writer/storage gates passed. Forward apply ran once on stdin,
without staging/config change. First post-apply identity stayed exact24c.
AFTER6/one24C-footer/hook binding/explicit nav_metadata once/shared Warp/CPU
overlap/four-input/default-OFF checks passed. No modeld/inference was executed.

Forward SHA: `28e68ced23a9ca9f0bea33c430346801272ae17532a73ffacf7c33ed5099162d`.
Reverse SHA: `643eaa68f5c579d8874032817279a59c0754b6c98aa694fcc76949d569489d40`.

## POST failure and exact rollback

After-apply fresh12.064529771s OFF observation passed. Full POST had9 PASS checks
and1 FAIL. Source/canaries41/AFTER6,HEAD/flags/boot/Params binding/index,
original overlay,ignored/native files,models/routes,package namespace/untouched
bytes,expected tracked diff and capture storage were preserved.

**PROCESS_IDENTITIES failed because28 became29.** Every one of the original28
identity rows was unchanged; none was removed or restarted. Exactly one new
`nmcli` executable with source-root cwd was observed. Its caller, arguments,
purpose and duration are not established by this evidence. It is not assumed
to be a harmless query or caused by this workflow. The gate was not weakened.

The inverse required confirmed own apply, exact24c HEAD, OFF1/0, unchanged index/
boot and all six known AFTER bytes. These gates were checked twice around
reverse --check. One exact inverse restored all six PRE hashes, then rechecked
HEAD/flags/index. Unknown footprint or HEAD drift would have denied inverse.
Result: PASS_EXACT_PRE_RESTORED. No reset/clean, auto-retarget or retry was used.

A separate final read-only guard passed: exact24c,6PRE,41pins,zero footer,
unchanged index/boot/storage,N16/API and a new12+second genuine-OFF window.
The final bounded process observation again matched all28 PRE identities.
This verifies final source restoration; it does not retroactively turn the
failed strict POST process-set check into PASS. Operating preservation for
this deployment remains FAIL_PROCESS_MEMBERSHIP_ADDITION.

## Final report

| Field | Result |
|---|---|
| Status / final source state | ROLLED_BACK / ROLLED_BACK |
| Branch / HEAD | carrot-nav / 24c1ba5e4b3428f56fa0e402f5a10097e2e94c32 |
| Offroad / Onroad / genuine OFF | 1 /0 / PASS |
| deviceState.started / ignitionLine / ignitionCan | false / false / false |
| PRE pure24c / surviving5bb / overlay / ticket / writer | PASS / PASS / PASS / CLEAN /0 |
|41 pins / N16 model/spec / exact infer API | PASS / PASS / PASS |
| Forward SHA / reverse SHA / disposable | PASS / PASS / PASS |
| Actual forward apply | PASS, then reversed |
| AFTER model/init/format/recorder/dataset/hook |6/6 PASS at installed stage, before inverse |
| nav_metadata accepted/once/unchanged/order | PASS (exact installed bytes +fresh CPU/static proof) |
| Shared input / CPU overlap / footer | PASS at installed stage |
| Dataset fields / sufficiency | FOUR_INPUT_UNCHANGED / FOUR_INPUT_SUFFICIENT |
| Ticket / activation / writer / frames / dataset | NOT_CREATED / NOT_RUN /0 /0 / NONE |
| Default OFF / current footer | PASS / ABSENT |
| Storage root / state / mutation | /data/v3_input_capture / VALID_EMPTY / NONE |
| Restart / capture / Jetson mutation | NOT_RUN_BY_SCOPE / NOT_RUN_BY_SCOPE / NONE |
| POST / operating preservation | FAIL / FAIL_PROCESS_MEMBERSHIP_ADDITION |
| Source/PRE restoration / updater drift | PASS / NONE |
| Ready for Vehicle10 / parity / M2 | NO / PARITY_UNDETERMINED / NO |
| Fresh CPU tests |1313 PASS /0 FAIL /0 SKIP |

Diagnostics4 missingzstandard,root/backport collection blocker and nativeFFmpeg
unavailability remain separate and uncounted; no package install/model/GPU work.
The evidence is bounded observations, not a continuous or atomic whole-device
snapshot. Existing28 identities retained is a narrower fact than exact process
set preservation. Current source bytes/index/storage restoration passed.

Development started at `9f80b563b97cf4c1599c491266bdfdbc1076b886`, exact feature branch CLEAN/equal.
Historical unreachable/deferred/onroad receipts are immutable; this distinct
rollback report/artifact preserves the new attempt. The reviewed C05 candidate,
patches/readers/tests are unchanged. Continuation is prepend-only.

Next action: offline review of the additional nmcli observation and preservation
policy before a new coordinated fresh-OFF attempt. No automatic reapply.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15_24c_actual_off_deployment_rollback_20261026.json`
