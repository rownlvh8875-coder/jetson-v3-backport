# M19-C1.1 — exact060de9 deployment blocked at first OFF gate

**BLOCKED_NOT_OFFROAD. Actual migration NOT_RUN.**

The first actual commands in a newly created private terminal were only:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

They returned **0 /1**, not required1/0. The explicit first STOP condition ended
actual work. No old1/0 observation was reused; deviceState.started/ignition and
process state were not inferred from user reports or historical data.

Development started on the exact feature branch, clean/equal origin at
`8c6bbac8aa9ab7dc5c7b58f8ed0f4834f43ae2c1`. The approved target remains
carrot-nav@060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c, profile
RECORDER_060DE9_REQUEST_CHUNKS_V1. This attempt did **not** query actual
branch/HEAD/tracked status after the failed flag gate. Target identity is
required-only, not a fresh observed HEAD.

## Actions and unobserved conditions

| Gate/action | Result |
|---|---|
| Fresh actual first flags |0/1; FAIL_OFF_GATE |
| Genuine OFF telemetry/process/writer proof |NOT_RUN |
| Git/model.py/old package/full28source pins/N16 identity |NOT_RUN |
| Private runtime-overlay/model/route/index/process/boot snapshot |NOT_RUN |
| Ticket namespace/env/writer inspection |NOT_RUN, state unknown |
| Device disposable roundtrip/private backup |NOT_RUN |
| Actual forward/reverse apply |NOT_RUN |
| Six AFTER hashes/footer/wrapper/transport independence |NOT_RUN on device |
| POST attestation/default OFF/operating preservation |NOT_ATTESTED |
| Ticket/activation/capture |NOT_CREATED_BY_STAGE/NOT_RUN/NOT_RUN |
| Restart/Params/source/config/model/USB/Jetson changes |NONE |
| Stage-created frames/dataset |0/NONE |
| Final source state/vehicle10 readiness |BLOCKED/NO |

No operating source or configuration was changed. That does not establish that
another process/updater could not change operating contents: fresh before/after
hashes were not collected. Existing namespace/writer state must not be reported
as absent/0. No source was installed, rolled back, committed or reset on comma.
No reason for the reported onroad flags was diagnosed after STOP.

Private terminal receipt is ignored locally. The helper required created=true,
sent exit and closed its connection. Public evidence contains its digest and
sanitized flags only, without network address/raw frames/argv/environment.
No scan, SSH trust bypass or Jetson access was used.

## Approved patch identities, checked locally

| Asset | SHA256 | Result |
|---|---|---|
|060de9 surviving366 forward |2b09f9753d5cf3e717b126898445ed2e33a44ad6871c0b64062aa2a24044e099 |PASS |
|060de9 surviving366 reverse |cd07d062c5fbd06e49d5581b908ea5108b633b69442cb15f548079daaa88d473 |PASS |

These are local candidate checks, not actual file/POST matches. Expected six
before/after profiles and source pins are included in the machine artifact with
an explicit expected-only label. The actual package filename is `__init__.py`
per the approved artifact; no `init.py` was created. No810e/clean-layout patch
was applied and no output directory, ticket or capture claim was created.

## Fresh development regression

The unchanged authoritative scope was run afresh as requested, with all
historical cases counted once. Project scoped and exact060 upstream transport
tests execute in separate processes/namespaces. Case IDs, counts, exit status
and JUnit SHA are checked in the artifact. No deployment-receipt tests were
added because no deployment receipt exists. No recorder/generator/patch/test
production change or gate relaxation was made to fit this outcome.

**543 unique PASS /0FAIL/0SKIP — CPU_FAKE/FIXTURE**:449 project scoped in139.25s
(includes historical415 once), plus94 exact060 upstream in8.53s. Both actual
pytest exit statuses are0; counts were reconstructed from fresh JUnit case IDs,
not copied from C0.1. This software PASS does not override the failed actual OFF
gate or prove device installation/health.

The existing root collection blocker remains tests/test_backport.py:192,
SystemExit0/pytest exit3, observed in C0.1 and not rerun here. A scoped result
does not establish whole-repository collection success. The private test helper
initially tried checking camera_gap in the limited upstream extraction; this
failed before pytest. Its extraction check was corrected to the actual
transport/tools files used by that separate suite. This setup failure is not a
device result and is distinct from the final fresh green suites.

## Rolling refs and next step

Public metadata was queried without retargeting: Nav
a559fcd971ccaa5a87befb8ec080f59a2966325b; WIP
4536a072b4bbd4b26ee147aea275722bc423b5fc; hostd0dc96fa32410403dfb2fefff3e2909c11ec109b,
zoomd24328d849b0e5154b55f149dc18c5dfe8bd79cc,
reviewa890f6df1bd3eb0478754c68d8b5f92f15e8b722. These do not identify actual comma.
WIP's two-commit increment fromdeb63e changes RuntimeDiagnostics and daemon timing
instrumentation: peak_metric=usb_exchange_ms and its measured field. CI/test files
also change. No current060 candidate pin or actual source was rebound to it.

Next is a **separate read-only OFF-state diagnosis**, observing fresh
deviceState/Panda ignition/manager process policy to explain the0/1 report;
never write Params, force ignition, restart producers or install while this gate
fails. Any later C1.1 retry still needs genuine OFF1/0 plus every exact060 gate.
If actual HEAD differs, STOP rather than pulling/resetting/checking out to match.

Numerical decision PARITY_UNDETERMINED, M2 NO, vehicle10 readiness NO.
Actual Jetson host identity NOT_REQUIRED_THIS_STAGE/NOT_RUN. Result commit resolves
with `git log -1 --format=%H -- artifacts/m19c11_060de9_actual_off_deployment_20261024.json`.
