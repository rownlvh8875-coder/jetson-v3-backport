# M19-C2 — vehicle10 capture stopped before arming

**BLOCKED_OUTPUT_ROOT_UNRESOLVED.** The reviewed proposed private capture root
does not exist on actual comma. The C2 instructions require an existing directory
and limit actual mutations to one ticket, natural activation/capture and dataset
creation by the recorder. No storage root was created or substituted. No ticket
was created, no ignition transition was requested, and no capture occurred.

Fresh genuine OFF, exact a559 HEAD, all six installed recorder hashes, all30 source
pins and the N16 source/spec contract passed before this storage gate stopped the
operation. The installed recorder remains default OFF. This is a capture
readiness prerequisite failure; it is not an inference, recorder, dataset or
numerical parity failure. Vehicle10 has not passed and M19-C3 is not ready.

Sanitized evidence: `artifacts/m19c2_vehicle10_capture_20261024.json`. Private
terminal/telemetry receipts remain under the ignored local reports directory.
No private root path, route identifier, raw input, image or boot ID is published.

## Fresh pre-arm evidence

Development started CLEAN/local=remote on feature/jetlink-multimodel-carrot at
`3695540554b6e7e9017137b1d7a921d6de105a01`. Protected main and old feature refs
were left unchanged. C13/C02 documents and artifacts were read before actual
access; their historical observations were not accepted as fresh evidence.

The first two actual shell commands were exactly:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

They returned1/0. A newly owned private terminal was required. The subsequent
receive-only SubMaster observation lasted12.016936835s and received22 fresh valid
deviceState samples,111 pandaStates and22 managerState samples. Source spans were
11.440093336s,11.992626905s and11.441475940s respectively. All freshness, age,
identity, normal OFF process and no-capture checks passed:
**GENUINE_OFF_CAPTURE_ARM_PRECHECK_PASS**.

Device started=false and thermal=green throughout. One cuatro Panda reported
ignitionLine=false/ignitionCan=false, harnessStatus=notConnected,
controlsAllowed=false and heartbeatLost=false. Card/camerad/modeld/controlsd/
selfdrived were inactive in fresh managerState and OS process inventory;
hardwared/pandad/jetlinkd ran normally. Ticket namespace was absent, with no
arm.ticket, consumed marker or capture-ID claims. Writer0, no capture memfd and
no legacy capture environment activation were observed. Vehicle speed/gear were
not collected: capture never reached the transition/stationary gate.

Actual branch remained carrot-nav and HEAD remained
`a559fcd971ccaa5a87befb8ec080f59a2966325b`. Six installed hashes exactly matched
C02's RECORDER_A559_EXECUTION_SWITCHES_V1 profile. All30 source pins matched,
normalizing model.py only by removing the exact bound footer. No source was
patched. Source hashes were read again after observation/storage inspection and
remained equal; the Git index bytes and metadata were unchanged. The only tracked
diff remains the previously installed model.py footer.

N16 source model SHA:
`01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`.
Canonical spec SHA:
`63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`.
Stateful=true, five server-owned state pairs, packed65595float32 and first12
desire8/traffic2/action2 were reverified. Expected saved logical inputs remain:

| Input | dtype | shape |
|---|---|---|
|new_img |uint8 |(2,6,128,256) |
|desire |float32 |(8,) |
|traffic_convention |float32 |(1,2) |
|action_t |float32 |(1,2) |

This is source/spec identity only. No model binary was downloaded or loaded;
current operational Jetson model/protocol/READY state were not inferred from
these source identities. The bounded Jetson telemetry preflight was not run
after the storage stop. Direct Jetson access and mutation were both NONE.

The initial private read-only helper omitted collector initialization while
selecting AST nodes and returned KeyError before source/profile/telemetry reads.
Initialization was restored locally, then a new successful fresh precheck ran.
Neither attempt wrote actual files, imported recorder activation or armed a
ticket. The helper is an in-memory read-only observer, not an installed tool.

## Why the output-root gate stopped capture

The exact proposed candidate was resolved from prior design/private evidence.
M18 calls it only a proposal; M19 says it was not yet created or verified. C13
also records it absent. Fresh actual lstat/parent checks confirmed that all
parent components are existing directories without symlinks, but the candidate
root itself is absent. Historical absence was not substituted for this read.

The current C2 instruction9 requires an existing directory, and instruction1
does not authorize root creation. The operation therefore stopped before
arm_discovered/arm_ticket. No alternative root was guessed, no operating-route
directory was selected and no mkdir/chmod/storage cleanup was attempted. No
capture ID or output child exists. Expiry was not assigned; the reviewed helper
default remains60s and no300s exception was used.

The dedicated exact-a559 strict reader already exists as
`tools/v3_input_dataset_a559.py`, bound through `adapters/carrot/recorder_a559.py`.
It was not modified or invoked on actual capture bytes because no dataset was
created. Manifest/provenance/record checksums/shapes/dtypes/per-frame hashes and
dataset digest are NOT_RUN/NONE, not PASS. No extra frame or recurrent tensor
was acquired; zero frames were written.

## Preservation, regression and next action

Actual mutations NONE. Ticket NOT_CREATED; activation NOT_RUN; writer NOT_STARTED;
frames0; dataset NONE. No manager/modeld restart, reboot, software ignition,
Params write, source patch, Git index write, updater manipulation, USB change,
model switch, V3/P3 operation or Jetson access/update occurred. No OFF→ON transition
was requested or observed. Final volatile namespace at the last read-only
observation was absent. No later actual access was made after the storage stop.

Preservation PASS is scoped to the fresh pre-arm window: branch/HEAD, six recorder
files,30 pins, index and OFF flags remained stable. No whole unrelated Params
equality or full overlay/route inventory is claimed in this C2 stage. The
workflow wrote no Params. C13's separate full overlay attestation remains
historical and unchanged.

Fresh relevant development regression: **627 unique PASS/0FAIL/0SKIP**,533 project
cases plus94 disjoint exact-a559 upstream transport cases. Existing WSL Linux
Python3.12.3/NumPy2.5.4; full commands, timings and JUnit/log commitments are in the
artifact. No reader/tool production change or new pytest case was added. These
are CPU_FAKE/FIXTURE tests, not vehicle capture or numerical inference. Four
diagnostics dependency-blocked cases remain separate and uncounted; zstandard was
not installed. The existing tests/test_backport.py:192 SystemExit(0)/pytest exit3
root collection blocker remains separate; full-root PASS is not claimed.

Vehicle10 FAIL_NOT_RUN_STORAGE_GATE; numerical PARITY_UNDETERMINED; M2 NO;
ready for real-input ORT↔TRT parity NO. Capture authorization is acknowledged,
but all fresh gates must be repeated before any future one-shot ticket.

Next action: separately prepare and verify the reviewed private capture root
under explicit storage-preparation authorization, then repeat C2's fresh OFF,
source/profile, storage, ticket-namespace and operational preflight gates before
creating exactly one ticket. No ticket was armed in this attempt.

Resolve this report's containing development commit with:
`git log -1 --format=%H -- artifacts/m19c2_vehicle10_capture_20261024.json`.
