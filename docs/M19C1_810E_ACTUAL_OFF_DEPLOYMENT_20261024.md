# M19-C1 — OFF deployment blocked before migration

**BLOCKED_NOT_OFFROAD. No actual migration was performed.**

The first two actual comma commands read `IsOffroad=0 / IsOnroad=1`.
Required values were1/0. Per the explicit STOP rule, no subsequent source,
runtime-overlay, ticket, process or model inspection was performed. In
particular, this session does **not** freshly confirm actual branch/HEAD,
deviceState.started, pure810e model, surviving package, namespace or writer state.
The target remains carrot-nav@810e14aaf51176f1a50a113939dc2e70907b394b; it is
an expected target, not a newly observed actual HEAD.

## Access and safety

Development branch was exact `feature/jetlink-multimodel-carrot`, clean and equal
to origin at `0d1c6bd811c5d7d798a26d2b08ee964d4297f84d`. C0 continuation,
design and machine evidence were read before deployment work.

The previous known device endpoint was unreachable; no terminal or command was
created there. After the user supplied a new address, the existing Carrot web
terminal connection method opened a fresh private session. Its first commands
were only the two required flag reads. They returned0/1 and stopped deployment.
The helper sent terminal exit and closed the websocket. Local network metadata
and known-peer lookup introduced no network scan or device configuration change.
Addresses, terminal frames and session details remain in ignored private evidence.

There was no attempt to substitute historical stationary data for genuine OFF,
force Params/ignition, start or stop producers, or continue with a source audit
after the first safety gate failed. Vehicle stationary status is not asserted.

## Offline identity checks

The approved `surviving366` migration assets still match C0:

| Asset | SHA256 | Result |
|---|---|---|
| forward patch |8e0260c8ef25661d4e49bace1671d2095734cdd87a68a1926dd55391f44db19d |PASS |
| reverse patch |b36b3379de5740c3ff0a365a8c1749503e89d2d27346a50c966a6b1b9a8302a0 |PASS |

These are development-file checks only. The expected before/after profiles are
copied into the C1 artifact explicitly as **expected** values; no actual file
match or POST profile is claimed. No clean810e patch or historical366 patch was
applied. No private device backup/disposable copy was created.

## Execution result

| Gate/action | Result |
|---|---|
| First actual flags |0/1; genuine OFF FAIL |
| Actual Git branch/HEAD/tracked source |NOT_RUN after failed gate |
| Old package/source pins/N16 status/spec |NOT_RUN |
| Fresh private overlay/model/routes/index/process/boot/Params attestation |NOT_RUN |
| Ticket namespace/writer/environment inspection |NOT_RUN; existing state unknown |
| Actual-device disposable roundtrip/backup/apply |NOT_RUN |
| Actual six after hashes/footer/wrapper/OFF health/POST |NOT_RUN |
| Ticket/activation/capture |NOT_CREATED /NOT_RUN /NOT_RUN |
| Restart/ignition/Jetson/USB/package/model changes |NOT_RUN |
| Stage-created frames/dataset |0/NONE |
| Final source state |BLOCKED; no migration or rollback |

No requested operational mutation was executed. **Operating content preservation
was not attested**, since no fresh before/after hashes were collected. This is
different from asserting that an updater or another process could not change
the device independently. No actual comma Git commit was made.

## Fresh development verification

The unchanged authoritative scoped suite ran afresh: **415 unique PASS,
0FAIL,0SKIP in103.98s**, CPU_FAKE/FIXTURE. This is one current run, not an addition
of prior counts. No new deployment receipt tests were needed because no
deployment receipt exists. Exact command and JUnit SHA are in the C1 artifact;
the private log/JUnit remain ignored. The historical bare-pytest collection
blocker from `test_backport.py` remains documented in C0 and was not rerun here.

No production code, recorder generator, patch, historical evidence or tests were
changed. Only this result, its sanitized artifact, README and continuation change.
Protected main/old-feature refs remain untouched.

Public upstream metadata was read without retargeting: Nav
060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c, WIP
9fa59128bdff6b6c0b9501aec2898205492b389f, carrot-jetson
d0dc96fa32410403dfb2fefff3e2909c11ec109b, zoompilot
d24328d849b0e5154b55f149dc18c5dfe8bd79cc, external review
a890f6df1bd3eb0478754c68d8b5f92f15e8b722. These do not establish actual device
HEAD. No pull/checkout/reset/rebase or updater change was attempted.

## Next action

After normal ignition OFF and the natural manager transition, rerun the fresh
genuine-OFF preflight. The existing C1 authorization remains bounded by all
gates: proceed only on fresh1/0, started=false, ignition false/false, inactive
onroad producers, then exact810e/source/old-package and fresh private attestation.
Do not force Params or process state to make the gate pass. If HEAD/profile has
moved, stop instead of automatically rebasing/repatching.

Ready for M19-B2 vehicle10: **NO**. Numerical decision remains
**PARITY_UNDETERMINED**, M2 **NO**. No ticket or capture authorization is added.
Result commit resolves with
`git log -1 --format=%H -- artifacts/m19c1_810e_actual_off_deployment_20261024.json`.
