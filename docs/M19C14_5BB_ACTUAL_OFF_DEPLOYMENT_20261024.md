# M19-C1.4 — exact5bb actual recorder deployment OFF

**PASS — RECORDER_5BB_DEFERRED_NAV_V1_INSTALLED_OFF.** Actual branch remains
carrot-nav at `5bbbe160822c7cae4245d7a8e96b40d158941ff7`. The approved migration
from pure5bb plus the surviving a559-bound package changed exactly model.py,
input_recording/format.py and input_recording/hook.py. Actual HEAD/index were
not changed. There was one successful actual apply; rollback was not needed.

Ticket NOT_CREATED; activation NOT_RUN; writer0; frames0; dataset NONE. Storage
root remains ABSENT and was not created. Restart/capture NOT_RUN_BY_SCOPE;
Jetson access/mutation NONE. PARITY_UNDETERMINED; M2NO. Ready for storage
preparation YES under separate authorization; Ready for Vehicle10 NO.

Full sanitized rows, fresh observations, commitments and test ledger:
`artifacts/m19c14_5bb_actual_off_deployment_20261024.json`.

## Scope, development identity and prior evidence

Development started at `36caf8baf45a9d2852f52ab3fb609c5a1d4a0e35` on exact
feature/jetlink-multimodel-carrot, CLEAN/local=upstream=remote. Protected remote
main2519ad0b and old feature26c9c06a remain unchanged. Read first: continuation,
C04 wrapper report/artifact, C20 drift diagnosis report/artifact and C13 a559
deployment report/artifact. Historical366/810/060/a559 and prior review evidence
remain immutable. This stage adds documentation/evidence only to development;
the reviewed recorder candidate, patch bytes and regression cases are unchanged.

The only actual writes were the reviewed three-file source migration and its
private three-file backup outside the source tree. Patch bytes were passed on
stdin, so no extra patch copies were written on comma. No storage root, ticket,
capture, process restart, Params change, updater manipulation, model switch,
V3/P3 enable, host update or Jetson connection occurred. No vehicle transition
was requested.

## Fresh genuine OFF and exact identity

The first actual shell reads were exactly:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

Fresh values were1/0. The first simultaneous receive-only window lasted
12.062200593s and supplied22 deviceState,110 pandaStates and22 managerState fresh
messages, with source spans11.4303s/11.8605s/11.4279s. Started remainedfalse;
ignitionLine/ignitionCan remainedfalse/false; thermal wasgreen. Onroad-only
card/modeld/camerad/controlsd/selfdrived were absent in OS and manager evidence;
hardwared/pandad/jetlinkd were normal. Manager shouldBeRunning flags also matched
normal OFF policy. Ticket namespace was clean, writer0 and legacy capture env
absent. Result: GENUINE_OFF_PRECHECK_PASS.

Fresh Git reads retained branchcarrot-nav, exact5bb HEAD, tracked changes0,
49 untracked short-status entries and cached diff0. No fetch/pull/reset/checkout/
rebase, retarget or repatch was used. HEAD drift would stop the transaction.

Three further simultaneous12s windows passed: immediately before apply
12.009902159s (22/109/22), after apply12.046269091s (23/112/23), and final
12.038408035s (22/110/22). Each stream had over10s fresh source span and all
flags/started/ignition/process-policy checks passed. The final read-only health
check independently reconfirmed exact HEAD, six hashes, all33 normalized pins,
index, boot/process identities, absent ticket/writer and absent output roots.

The6 observed launcher/OFF-role process environments lacked
CARROT_V3_INPUT_CAPTURE and the four CPU-overlap/request-chunks/compact-reply/
deferred-NAV selectors. Reviewed source defaults are1; the environment was only
read. This scope is separate from the28 preserved runtime process identities.
Modeld remained inactive.

## Exact PRE and fresh private overlay

Pure5bb model hash was
`6e04d29bca6b1802ecc012f8f8ea154f28ec7854961dbf4fd4b6b963328eccee`, with zero
recorder footers. The surviving package was exactly the a559-bound five files:

| PRE file | SHA256 |
| --- | --- |
| __init__.py | e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca |
| format.py | f0bf4d1abbbc8bc89e02213198743d507fd57a6546a85b48f54fd46ea346cd25 |
| recorder.py | d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada |
| dataset.py | 25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7 |
| hook.py | 1e82abdfc93ab23f7add69c8f248677538ec2c20b47868b7bc06cb0195a18256 |

All33 C04 source pins were freshly verified, including deferred_map, client,
request chunks, native/Python request writer, ffs, host release, diagnostics,
projection and manager/modeld boundaries. PRE6/6 and33/33 were rechecked immediately
before actual apply. N16 source contract passed: model
01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a; canonical spec
63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71; statefultrue,
five server-owned state pairs, image(2,6,128,256), packed65595, first12=8/2/2.
Only source/spec metadata was checked; no model binary was loaded or executed.

New current PRE inventory covered49 untracked entries/2011 regular files/
417271762bytes,2206 ignored generated/native files/384889608bytes,15 model files,
4542 route metadata entries,28 process identities, boot identity, source canaries
and exact index bytes/metadata. Current U32/U46 paths remain covered privately.
The49 count was observed afresh, not treated as a whitelist; the ignored count
differs legitimately from older observations. No overlay was cleaned or moved.

The accepted PRE was collected again inside the transaction and compared with
the earlier fresh PRE across overlay/source/index/models/routes/boot/Params
binding/process identity before backup or write. Latest fresh PRE commitment:

`36650d1fb96f28d17b790664cf59717ad195b9b1e96d6f8792e5a7a83f8532e1`

Read-only no-follow/type/race checks and Git optional-lock suppression were used.
Atime is excluded. This is a bounded observation commitment, not an atomic or
continuous whole-device snapshot or unrelated Params-content equality proof.
Private paths, raw environments/argv, boot identity and route names remain private.

## Disposable proof, backup and actual apply

The exact actual six PRE file bytes were reproduced in a local disposable Git
root. All18 checks passed: forward/reverse SHA, forward check/apply, exact six
AFTER hashes, compile, explicit infer signature and wraps, one unchanged metadata
forwarding with tuple identity, observer ordering, footer/hash binding, Warp
callback/None/output forwarding, unchanged four-field schema, no-ticket no-import
OFF, reverse check/apply, byte-exact PRE restore and no index write.

| Approved surviving migration | SHA256 |
| --- | --- |
| forward | 8840e15e873526774d9c6f0ce1b2442dc1a3ee91cbf77326371bf643d79c6217 |
| reverse | 96e2232d00fcecdfc2fd9a7adfaa646d9719903bf69315c4a42355b28173aee3 |

Only patches/carrot-nav-5bb-v3-input-recorder.patch and its exact reverse were
used. Clean5bb/a559/060/810 patches were not used. Three touched source files
were backed up in a new private0700 directory outside the source tree, with
O_EXCL/O_NOFOLLOW, verified regular0600 files owned by the creating identity,
exact SHA checks and file/directory fsync. Only these three backup files exist.
The location is private; its commitment and file hashes are in the artifact.

After new12s genuine-OFF evidence, immediate OFF/HEAD/PRE6/pins33/ticket/writer/
index/storage checks passed. The actual commands were git apply --check then
git apply with the SHA-verified forward bytes on stdin, per-command
core.autocrlf=false and optional locks disabled. No --index or persistent Git
configuration change was used. The first operation after apply re-read branch
and HEAD. It remained exact5bb; six AFTER hashes and wrapper/footer checks passed.

## AFTER binding, wrapper and default OFF

| AFTER file | SHA256 |
| --- | --- |
| model.py | 65b9006aba819376344e72114b2de55330aa76cd358f30c7e80488f0dd9e799a |
| __init__.py | e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca |
| format.py | 838cbb11d254132f55ff808ef59e3010a18f0f0a0d157e7a215635229950810a |
| recorder.py | d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada |
| dataset.py | 25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7 |
| hook.py | 1b0331426cc13c3f1ec27910f69eea4c4bc210af339acdf63bebf5098e041f83 |

Pure5bb model body remains byte-identical, followed by exactly one
RECORDER_5BB_DEFERRED_NAV_V1 footer binding the exact hook hash. No old footer
or persistent environment activation exists. Installed wrapper signature is:

```python
(self, image, packed, frame, reset=False, source_sof=0, nav_metadata=None)
```

Installed AST has one capture.observe before one original_infer, forwarding
nav_metadata unchanged exactly once. It has no generic kwargs. Warp accepts
prepare callback/None and output_buffer and forwards them once, without extra
reservation/begin/complete/release. Fresh exact installed bytes and fresh CPU
fixtures establish compatibility; onroad modeld/inference was not executed here.

Dataset fields remain new_img/desire/traffic_convention/action_t only; no
nav_metadata/nav_map/navigation/recurrent tensors were added. FOUR_INPUT_SUFFICIENT
remains the frozen C04/C03 V3 contract decision, with its recurrent replay
conditions. No numerical parity or V3 approval is implied.

The installed footer alone was evaluated against the absent real ticket using an
import tripwire: no recorder package import/object, writer or tensor copy. Normal
OFF kept modeld absent, with pinned lazy-loading sources. No manager-memory
inspection, forced package import or restart was performed. Ticket namespace
remained absent: no arm.ticket, consumed marker or capture claim. Writer0,
activationNOT_RUN, frames0, datasetNONE. Both capture output roots remain absent.

## POST, review and tests

Fresh exact5bb POST commitment:

`c533303c7ee31582823b7f1241efc9344ba928ddd40f3fc9d497448af673d530`

All10 POST checks passed: six hashes/wrapper/footer/default-OFF; HEAD/branch/flags/
boot/Params binding/index; original current overlay; ignored/native files;
models/routes; process identities; source canaries/pins33; package namespace and
untouched files; only approved tracked model diff; unchanged storage namespace.
Touched file mode/owner/group were preserved. Model pin normalization removes
only the exact bound footer. The final read-only health pass verified33/33 again.
Operating preservation PASS; updater drift NONE. Rollback was NOT_RUN.
A further final read-only source guard passed before finalization: exact HEAD,
six hashes,33 normalized pins, index,28 process identities, boot, OFF flags/roles,
absent ticket/writer and absent storage roots. It performed no actual mutation;
the four fresh12s telemetry windows are recorded separately.

Pre-write independent review found helper recovery/transport verification gaps
and corrected them before actual writes. Rollback now requires confirmed own
apply and an identified AFTER footprint, with HEAD/OFF/index/profile rechecks
after reverse --check and immediately before inverse write; first-after-inverse
identity and exact PRE restoration are checked. Unknown/partial layouts stop with
evidence, protecting unidentified edits. This safe-reverse boundary may require
manual diagnosis instead of automatic recovery. No such failure occurred here.
Receipt transport was sized to420s with duplicate POST output removed; no retry,
inverse, restart or cleanup input is sent on a post-dispatch timeout.

The initial read-only PRE helper looked for JETLINK_DEFER_NAV in model.py; exact
source inspection located it in link.py while model uses client.deferred_nav.
The helper was locally corrected and a new full PRE collected before any source
write. Its failure receipt remains private. No device drift was concealed.

Fresh authoritative **1165 unique PASS/0FAIL/0ERROR/0SKIP** matches all C04 case
IDs:1021 prior-baseline cases +119 fixed-profile cases +25 paired-source cases,
each executed once for this stage. WSL Ubuntu24.04/Python3.12.3/NumPy2.5.4/
pytest9.1.1/cc13.3, CPU/POSIX synthetic fixtures only. No ORT/TRT/GPU/USB/vehicle
performance claim.295 source/support and110 test/dependency hashes were verified;
all6480 historical private report files remained unchanged. No new public tests
or recorder code were added. Disposable18 and private guard/rollback/runner49
checks are separate and are not added to1165. A private JUnit-prefix aggregation
mistake was reconciled to exact original IDs without rerunning/recounting tests.

Diagnostics4 remain separately dependency-blocked by missing zstandard. Known
root/backport live-network/SystemExit collection blocker remains separate and
was not executed. No dependencies were installed. Full-root PASS is not claimed.

Next action: **M19-C2.1 private capture storage preparation under separate
explicit authorization.** Storage remainsNOT_PREPARED, Vehicle10NOT_RUN,
PARITY_UNDETERMINED and M2NO. No ticket, capture or restart authority follows.

Result commit:
git log -1 --format=%H -- artifacts/m19c14_5bb_actual_off_deployment_20261024.json
