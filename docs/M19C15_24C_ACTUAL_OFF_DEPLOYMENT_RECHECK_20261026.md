# M19-C1.5 — exact24c deployment: user-resumed first-gate recheck

2026-10-26 · **BLOCKED_NOT_OFFROAD**

The user reported the vehicle ignition ON and comma/Jetson connected. The
previous timing deferral was therefore lifted for a fresh first-gate attempt.
A new owned comma terminal connected successfully. Its first shell reads were:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

Fresh executed output: **IsOffroad=0 / IsOnroad=1**. Required:1/0.
The workflow stopped immediately after this rejection. Only the owned terminal's
ephemeral history suppression and shell exit followed; no further operational
read, source command, process restart, storage or Params change occurred.

Actual branch/HEAD/profile were intentionally not read after the failed first
gate. The expected24c identity is not asserted as a fresh actual identity.
deviceState/Panda ignition, ticket namespace, writer count, current storage and
dataset state are UNKNOWN/NOT_READ. Past OFF/empty/writer0 evidence is not reused.

| Deployment field | Result |
|---|---|
| Connection | PASS |
| OFF / ON | 0 /1 |
| Genuine OFF | FAIL_FIRST_FLAGS;10s observation NOT_RUN |
| Actual branch / HEAD | UNKNOWN / UNKNOWN |
| PRE6 /41pins / N16 / API / overlay | NOT_RUN |
| Disposable / backup / actual apply / rollback | NOT_RUN |
| AFTER6 / wrapper / footer / POST | NOT_RUN |
| Source / index / storage / Params mutation | NONE |
| Ticket / activation / capture | NOT_CREATED / NOT_RUN / NOT_RUN |
| Writer started / frames written by workflow | NO /0 |
| Existing writer / dataset / storage | UNKNOWN_NOT_READ |
| Manager/modeld restart / reboot | NOT_RUN |
| Jetson access / mutation | NO / NONE |
| Updater drift | UNKNOWN_NOT_OBSERVED |
| Final source state | BLOCKED |
| Ready for Vehicle10 | NO |
| Numerical decision / M2 | PARITY_UNDETERMINED / NO |

The approved source mutation remains exact24c OFF deployment only. A parked
vehicle with ignition ON is not the required comma offroad state. The previously
reported power-loss-on-ignition-OFF arrangement remains unresolved. No vehicle
transition, electrical modification, state override or gate bypass was requested.

Development began at `b327b7727ab18c5a06068a4a7f3d5a4f91acc0bc`, correct feature
branch, CLEAN/local=upstream=remote. The C05 candidate and all its frozen tested
source bytes remain unchanged. No new recorder/tool/test code was created.
Fresh CPU/POSIX regression was NOT_RUN because the mandatory first gate failed;
historical C05 1313 passes are not counted again. Receipt parser/integrity checks
are local evidence checks, not new regression cases. Existing diagnostics/root/
native-FFmpeg blockers remain separate historical limitations.

Prior C1.5 unreachable/deferred report and artifact remain immutable. This new
receipt records the successful connection and fresh rejected flags. Only this
report/artifact and a prepend-only continuation checkpoint change in development.
No source deployment, ticket, capture or operating restart occurred.

Next action: establish a connection with power retained in genuine OFF before a
new fresh first gate; do not patch onroad or retry automatically.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15_24c_actual_off_deployment_recheck_20261026.json`
