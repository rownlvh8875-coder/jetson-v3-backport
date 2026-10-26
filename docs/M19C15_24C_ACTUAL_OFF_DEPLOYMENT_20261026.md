# M19-C1.5 — exact24c actual OFF deployment

2026-10-26 · **BLOCKED_DEVICE_UNREACHABLE / DEFERRED_BY_USER_NOT_DEPLOYED**

Actual deployment was not started. The previously successful, user-provided
comma cweb terminal endpoint failed before any metadata/screen frame arrived.
**Zero shell commands were delivered**, including the intended first OFF/ON
reads. All Remote Desktop Commander devices were also listed offline. These
observations do not establish whether comma itself was powered, its current
address, OFF state or current source identity.

The user then explicitly said they would connect at the vehicle later and tell
this chat. Actual connection retries and deployment are deferred until that
message. There is no automation or automatic resume. No ignition transition
was requested. Existing deployment authorization remains limited to exact24c
and fresh gates; this is not an onroad patch or capture authorization.

## Development and reviewed candidate

Start: feature/jetlink-multimodel-carrot at
`4f244f44139d8cd527dacfe8a94e1e0692a358cc`, CLEAN/local=upstream=remote.
Continuation, C05 report/artifact/manifest, C14 deployment report/artifact and
C21 storage report/artifact were read. Their hashes are retained in the artifact.

Intended actual target: carrot-nav at
`24c1ba5e4b3428f56fa0e402f5a10097e2e94c32`, pure model plus surviving5bb-bound
package. Intended installed profile: RECORDER_24C_HUD_HOST_V1_INSTALLED_OFF.
These are expectations; actual branch/HEAD/profile were NOT_OBSERVED today.

Both local patch hashes passed freshly:

- Forward: `28e68ced23a9ca9f0bea33c430346801272ae17532a73ffacf7c33ed5099162d`
- Reverse: `643eaa68f5c579d8874032817279a59c0754b6c98aa694fcc76949d569489d40`

Manifest structure retains41 source pins and6 PRE/6 AFTER hashes. All frozen
C05 tested source/candidate bytes remain unchanged. No new recorder code, patch,
reader or public test was created. Only this report/artifact and continuation
checkpoint are changed in development.

## Actual gate and terminal result

| Field | Result |
|---|---|
| First OFF/ON commands delivered | 0 |
| OFF/ON values | UNKNOWN / UNKNOWN |
| Genuine OFF receive-only observation | NOT_RUN |
| Actual branch / HEAD | UNKNOWN / UNKNOWN |
| PRE six /41 pins / N16 / API | NOT_RUN |
| Ticket namespace / actual writer count | UNKNOWN / UNKNOWN |
| Fresh overlay/index/boot/process attestation | NOT_RUN |
| Disposable actual-PRE roundtrip / backup / apply | NOT_RUN / NOT_RUN / NOT_RUN |
| AFTER six / footer / wrapper | NOT_RUN |
| Storage /data/v3_input_capture | UNKNOWN_NOT_READ; mutation NONE |
| POST / operating preservation / updater drift | NOT_RUN / NOT_RUN / UNKNOWN |
| Final source state | BLOCKED |

No source/storage/Params/index/updater write, ticket creation, activation,
writer start, dataset, rollback, restart/reboot or Jetson access/mutation was
performed by this workflow. Frames written by this workflow=0. Actual writer
count and existing dataset/storage state were not observed; past0/empty/OFF
evidence is not reused as a current proof.

## Tests and next gate

Fresh CPU/POSIX regression was NOT_RUN because execution stopped before the
first actual gate and the user deferred timing. No cases are claimed PASS,
FAIL or SKIP. C05's1313PASS/0FAIL/0SKIP remains historical evidence, is not
recounted as fresh and must not substitute for the deployment-stage checks.
Diagnostics4/root/native-FFmpeg historical blockers remain separate.

On the user's connection-ready message, begin again with exactly:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

Require1/0, then fresh10+second genuine OFF, exact24c/PRE6/41pins/N16/API,
clean namespace/writer0 and current overlay/storage/index preservation. Reproduce
the fresh actual PRE in a disposable copy, complete fresh relevant regression,
backup the exact3 touched files, then repeat immediate-before-write gates before
the reviewed patch. No auto-retarget, storage change, ticket or restart.

Ready for Vehicle10=NO. PARITY_UNDETERMINED; M2=NO.

Next action: **wait for the user to report comma connected with power retained
in genuine OFF; no automatic connection retry or deployment.**

Result commit:
`git log -1 --format=%H -- artifacts/m19c15_24c_actual_off_deployment_20261026.json`
