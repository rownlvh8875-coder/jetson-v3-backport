# M19-C2.0 — source/profile drift read-only diagnosis

**PASS_DIAGNOSIS. Primary classification: MULTIPLE_DRIFT.** Actual carrot-nav is
now `5bbbe160822c7cae4245d7a8e96b40d158941ff7`, ten commits after approved a559,
with a559 confirmed as an ancestor. The tracked model body changed and its local
recorder footer is absent. The surviving untracked a559 recorder package remains
exact5/5, while20/30 reviewed source pins still match. No tracked/index anomaly
was found. Decision: **OFFLINE_COMPATIBILITY_REVIEW_REQUIRED_FOR_NEW_HEAD**.

Actual mutations NONE. No repair, candidate for the new HEAD, patch, storage
mkdir, ticket, capture, restart, updater control or Jetson access occurred.
Numerical PARITY_UNDETERMINED/M2 NO remain unchanged.

Full six-file expected/actual/match rows, all30 source-pin rows, mismatch groups,
bounded reflog and sanitized runtime/preservation evidence are in
`artifacts/m19c20_source_profile_drift_diagnosis_20261024.json`. Private first
identity/status/terminal/process evidence remains in ignored local reports.
Historical C13/C2/C2.1/366/810/060 evidence is unchanged.

## Identity and Git evidence retained before comparison

Development started CLEAN/local=remote on feature/jetlink-multimodel-carrot at
`48e28947b576f34737ccce0c8b10c77667a0c820`. Protected main/old feature refs were
unchanged. Required continuation/C13 and latest C2/C2.1 reports/artifacts were
read. A new owned actual-comma terminal connected through the existing authorized
path. The first actual data observations were these four Git reads, in order:

```sh
git branch --show-current
git rev-parse HEAD
git status --short
git diff --cached --name-only
```

Each exit status/stdout/stderr was retained privately immediately, before any
expected-value assertion. Independent sections continued after a mismatched
value; section errors would be preserved instead of discarding earlier evidence.
No unreadable/error section occurred in the accepted diagnosis.

| Observation | Actual |
|---|---|
|ACTUAL_BRANCH |carrot-nav |
|ACTUAL_HEAD |5bbbe160822c7cae4245d7a8e96b40d158941ff7 |
|HEAD classification |HEAD_ADVANCED_DESCENDANT |
|a559 ancestor |YES |
|Commits a559..current |10 |
|TRACKED_STATUS_COUNT |0 |
|UNTRACKED_STATUS_COUNT |49 |
|INDEX_DIFF_COUNT |0 |

Expected historical HEAD remains
`a559fcd971ccaa5a87befb8ec080f59a2966325b`; this diagnosis does not approve the
new HEAD. Latest commit is5bbbe160, parent
`fc2109c4360eff20a042ea54e943ea5bc3c8a3fe`, subject
"Record USB power and deferred NAV trials with final deployment".

The49 count is short-status untracked entries, not a new full-overlay content
attestation. Full untracked paths/status and the first receipt remain private.
No untracked content was deleted, moved, cleaned or treated as a count whitelist.

## Installed profile, footer and pure body

| File | Actual SHA256 | Expected a559 match |
|---|---|---|
|model.py |6e04d29bca6b1802ecc012f8f8ea154f28ec7854961dbf4fd4b6b963328eccee |MISMATCH |
|__init__.py |e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca |MATCH |
|format.py |f0bf4d1abbbc8bc89e02213198743d507fd57a6546a85b48f54fd46ea346cd25 |MATCH |
|recorder.py |d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada |MATCH |
|dataset.py |25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7 |MATCH |
|hook.py |1e82abdfc93ab23f7add69c8f248677538ec2c20b47868b7bc06cb0195a18256 |MATCH |

Footer classification **FOOTER_REMOVED**. The a559 marker occurs0 times, footer
header count0, reviewed-hook SHA line absent. No old366/M18,810 or060 footer is
present. Current full model bytes therefore are its pure body; hash6e04d29b does
not equal pure a55993c2858e. The difference is **UNDERLYING_MODEL_AND_FOOTER_CHANGED**,
not merely footer removal. The current model bytes equal the current HEAD's Git
blob exactly. No editing or reconstruction of the actual file was performed.

The installed six-file profile is5/6, but its untracked package is intact5/5.
The surviving hook still binds a559, and the reviewed model-footer discovery
binding is absent. This is not an authorized path to capture under the new HEAD,
even though the package bytes survived.

## Source pins and N16 declaration

**20/30 match.** Model pin comparison uses the detected pure-body boundary; the
current file has no footer to remove. Full-file hashes are retained alongside
the normalized model pin. Mismatches group as follows:

| Group | Changed paths |
|---|---|
|RECORDER_HOT_PATH |openpilot/selfdrive/modeld/jetlink/model.py; openpilot/selfdrive/modeld/jetlink/link.py |
|TRANSPORT |openpilot/selfdrive/modeld/jetlink/daemon.py; third_party/jetlink/jetlink/client.py; third_party/jetlink/jetlink/request_chunks.py; third_party/jetlink/jetlink/transport/ffs.py; third_party/jetlink/jetlink/transport/request_writer.py; third_party/jetlink/jetlink/transport/request_writer.c; tools/jetlink/server.py |
|HOST_RELEASE |openpilot/selfdrive/modeld/jetlink/host_release.json |
|DIAGNOSTICS / OUTPUT_PROJECTION / MANAGER/MODELD / OTHER |No mismatched reviewed pin |

All30 current tracked source files equal their current HEAD Git blobs, including
the ten mismatches against a559. Nine additional C2.1 ownership/uploader/storage
boundary pins also remain exact. This supports committed source evolution rather
than local working-tree/index modification. It does not establish compatibility
of the changed input/transport paths; no new-HEAD candidate or tests were built.
The changed host_release.json is source evidence, not a claim about a live Jetson
release, plan, service or operational model.

N16 declared model SHA remains
`01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`.
Canonical spec SHA remains
`63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`.
Source contract PASS: stateful=true, five server-owned state pairs,
warped_shape=(2,6,128,256), packed_nelem=65595, first12 desire8/(8,),
traffic2/(1,2), action2/(1,2). Only the hash-verified pure ModelSpec metadata class
was evaluated; no model binary, inference, GPU or Jetson operation was run.

## Runtime, namespace and updater evidence

Fresh short receive-only observation:3.047875852s,6 valid fresh deviceState and28
valid fresh pandaStates samples. OFF/ON1/0, started=false, thermal=green, one
cuatro Panda with ignitionLine=false/ignitionCan=false and harnessnotConnected.
This satisfies the requested short diagnosis status read; it is not a10second
capture-arm preflight. Diagnosis imposed no OFF requirement.

Volatile namespace absent: arm.ticket ABSENT, arm.ticket.consumed ABSENT,
capture-ID claims0. Writer0, capture memfds0, CAPTURE_ACTIVE=false, capture output
processes0. Both the approved new storage root and historical proposed output
root are absent; no dataset child from this workflow exists. The approved
`/data/v3_input_capture` classification is **ABSENT**, not created or probed.

Bounded ten-entry local reflog shows:

```text
2026-10-24 20:02:54 +0900: a559fcd9 reset: moving to HEAD
2026-10-24 20:02:54 +0900: 5bbbe160 merge: Fast-forward
```

Earlier pairs show the same reset→fast-forward pattern through366/810/060/a559.
This is consistent with updater-style replacement of tracked source, losing the
local footer while the untracked package survives. **Inference:** an update-style
transition explains the observed layout. The reflog alone does not prove which
executable/person initiated it, so exact actor/cause attribution remains unknown.

## Classification, preservation and next action

Primary **MULTIPLE_DRIFT**: B HEAD drift, C installed model/footer drift and
D source-pin drift. A branch drift is false. E index/working-tree anomaly is
false: no tracked diff or staged change, and current source matches current Git
blobs. This is broader than HEAD-only drift or an intact a559 body losing only
its footer. Current observations resolve the drift category; they do not recover
the missing values from the historical C2.1 receipt retroactively.

Scoped preservation PASS. Before/after identities/status,49 selected source/
package/boundary/native files including metadata, index bytes/metadata, read OFF
flags, ticket/output-root states and recorder process inventory were unchanged.
A follow-up read-only Git blob proof again found the same HEAD, index and source
hashes. No source/Params/ticket/storage/restart/Git/updater mutation or Jetson
access occurred. Read atime is excluded; no full unrelated Params/route/overlay
equality claim is made.

Local diagnostic verification passed seven footer/body cases plus a section-
failure continuation case, and AST checks found no mutation API in the actual
scripts. These are LOCAL_FIXTURE_ONLY checks, not compatibility/numerical tests.
No production reader/tool or pytest case changed. Prior627 CPU PASS is historical,
not rerun/recounted. Existing diagnostics4/root collection blockers remain separate.

Decision **OFFLINE_COMPATIBILITY_REVIEW_REQUIRED_FOR_NEW_HEAD**. Pin exact
5bbbe160822c7cae4245d7a8e96b40d158941ff7 and separately review a559..5bbbe160
recorder input/execution compatibility before any candidate or deployment. Do not
repair a559's footer onto the new HEAD, create storage, arm or restart here.

Result commit resolution:
`git log -1 --format=%H -- artifacts/m19c20_source_profile_drift_diagnosis_20261024.json`.
