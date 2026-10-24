# M19-C2 exact5bb Vehicle10 — deferred before arming (2026-10-24)

STATUS: **DEFERRED_BY_USER_NOT_ARMED**.

The user deferred normal vehicle ignition until tomorrow because they were going
to sleep. No ticket was created. No recorder activation, writer, capture, output
child or dataset was created. Vehicle10 remains NOT_RUN; this receipt records the
completed read-only preparation and user deferral, without claiming a capture
failure or PASS. No automatic continuation or reminder was scheduled.

Sanitized evidence: [artifact](../artifacts/m19c2_5bb_vehicle10_capture_20261024.json). Historical C04/C14/C21 and earlier
reports remain immutable. The later capture attempt must receive a new dated
receipt; do not overwrite this deferred-stage evidence.

## Fresh actual observations

Actual `carrot-nav` HEAD remained
`5bbbe160822c7cae4245d7a8e96b40d158941ff7` with
`RECORDER_5BB_DEFERRED_NAV_V1_INSTALLED_OFF`. Six installed hashes and all 33
normalized source pins matched before and after the checks and in the final
read-only guard. The model pin removes only the exact reviewed bound footer;
the installed model hash is checked separately. Index bytes/metadata, boot
identity and Git status stayed stable; no updater drift was observed.

The first actual commands were exactly:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

They returned 1/0. A fresh simultaneous receive-only observation lasted
12.001085137 s: deviceState 22 samples over 11.427397416 s,
pandaStates 110 over 11.846569284 s, managerState 22 over 11.422006234 s.
`started=false`, ignitionLine/ignitionCan=false/false throughout. Normal OFF
manager policy and OS roles agreed: card/modeld/camerad/controlsd/selfdrived
inactive; hardwared/pandad/jetlinkd running. Legacy capture environment absent,
ticket namespace absent, writer 0 and capture memfds 0.

Result: `GENUINE_OFF_CAPTURE_PRECHECK_PASS`. **This evidence cannot be reused as
tomorrow's fresh OFF gate.** The final guard rechecked flags 1/0, source/profile,
normal OFF roles, namespace and empty storage; it is not a second 10 s telemetry
window.

N16 declared source contract matched: model
`01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`, spec
`63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`, stateful,
five server-owned pairs, image (2,6,128,256), packed 65595, first 12 = desire 8 /
traffic 2 / action 2. No model binary execution. Exact explicit nav_metadata API remains
pinned; dataset contract remains FOUR_INPUT_SUFFICIENT.

## Storage and operational telemetry

`/data/v3_input_capture` remained a canonical real empty directory, UID/GID
1000:1000, mode 0700, internal non-removable ext4 mounted at `/data`; no symlink,
route/Git overlap or uploader integration. Source boundary hashes and selected
uploader environment were rechecked read only. Writable access passed; no probe
was run and no storage write occurred this stage. Final available space:
28408254464 bytes / 27092.22265625 MiB /
30.053828% (minimum 100 MiB).

Existing comma-visible Jetlink telemetry while OFF reported `waiting`,
`App selection`, no peer/model SHA. Protocol and operational model are UNKNOWN;
READY was not established. This is not classified as JETLINK_NOT_READY because
no normal ON startup or capture attempt occurred. There was no Jetson access.

## Arm, vehicle and dataset

| Item | Actual result |
|---|---|
| Ticket / installed arm helper | NOT_CREATED / NOT_CALLED |
| Planned request | 10 frames, depth 4, 120 s; never armed |
| arm.ticket / consumed marker / claims | ABSENT / ABSENT / 0 |
| User ignition ON / transition / stationary capture | NOT_RUN |
| Activation / writer / frames | NOT_RUN / 0 / 0 |
| Dataset / digest / strict validation | NONE / NONE / NOT_RUN |
| Final recorder state | NOT_STARTED, default OFF |
| Source/Params/Git/storage/updater writes | NONE |
| Manager/modeld restart, reboot | NOT_RUN |
| Jetson access/mutation, V3/P3/model switch | NONE |

The local 120 s single-ticket monitor was prepared but **never executed**. No
ticket or claim exists to consume overnight. Existing exact5bb strict reader
`tools/v3_input_dataset_5bb.py` remains available; no real dataset exists to
validate. No raw input, image, device address, route/location, process arguments,
boot identity or private capture identifier is published.

## Fresh CPU/POSIX verification

At development HEAD `f2f646fca1825cd6c61f2f23577bcaed6fb60cbf`, fresh authoritative scoped regression:
**1165 PASS / 0 FAIL / 0 ERROR / 0 SKIP**, 1165 unique exact C04 case IDs, no duplicates.
Historical counts are not added a second time. Full exact commands, environments,
logs, JUnit and collected IDs remain private with SHA256 commitments in the
artifact. WSL Ubuntu-24.04, Python 3.12.3, NumPy 2.5.4, pytest 9.1.1, GCC 13.3;
native AIO tests used regular temporary files, not physical USB.

| Group | PASS |
|---|---:|
| historical_scoped | 533 |
| exact_transport_upstream | 108 |
| exact_deferred_upstream | 43 |
| remaining_exact_upstream | 203 |
| transport_supplementary | 34 |
| deferred_supplementary | 25 |
| direct_review | 7 |
| matrix | 68 |
| fixed_profile_api_matrix_migration_default_off | 119 |
| wrapped_unwrapped_source_equivalence | 25 |

Retained fixture receipts: 68 matrix, 36 fixed matrix, 25 paired source traces
(50 wrapped/unwrapped executions). All 6807 prior private report files,
extracted exact source/support, tested sources and patches stayed unchanged.
Independent local reconciliation rechecked JUnit/IDs/digests and actual receipts
without reconnecting to a device or re-executing the tests.

Separate synthetic stationary-proof checks: 10 PASS / 0 FAIL / 0 SKIP, excluded from the
authoritative 1165. They exercise bracketing of both camera SOFs and observer
times, movement/nonpark/standstill rejection, missing/stale/gapped samples,
empty records and non-mutation. They provide no actual vehicle evidence.
Diagnostics 4 remain dependency-BLOCKED by missing zstandard, excluded from PASS
and SKIP. Root collection/test_backport was not executed: static import-time
network calls and sys.exit blocker remain separate. No ORT/TRT/GPU/vehicle parity
claim is made.

## Resume condition

Vehicle10: NOT_RUN. Real-input parity readiness: NO.
Numerical decision: PARITY_UNDETERMINED. M2: NO.

Next action: **tomorrow, contact this chat before normal ignition ON**. Re-run
fresh OFF/source/profile/storage/namespace gates, then create exactly one valid
bounded ticket within the authorized capture scope. Only after ticket validation
should the user turn ignition ON normally while remaining parked in P. No
overnight arm or automatic retry. If HEAD/profile/storage drifts, stop under the
specified capture classification instead of repairing or retargeting it.

Development started `f2f646fca1825cd6c61f2f23577bcaed6fb60cbf`, CLEAN and local/remote equal. This stage changes
only this new report, its sanitized artifact and the continuation checkpoint.
Result commit: `git log -1 --format=%H -- artifacts/m19c2_5bb_vehicle10_capture_20261024.json`.
Final CLEAN/local-remote/protected-ref checks are retained in the private
completion receipt after the feature-only commit/push.
