# M19-C1.5Q — fresh actual OFF/source gate · 2026-10-27

**BLOCKED_DEVICE_UNREACHABLE. No device command was sent.**

Development started CLEAN/local-remote equal at
a897eb06a053125c8a566c80b287b6101ca6ba89 on
feature/jetlink-multimodel-carrot. The user approved the proposed next fresh
read-only OFF/source check. This stage did not authorize a schema3 query,
recorder deployment, ticket, activation or capture.

The remote-access plugin inventory reported no online devices. The existing
reviewed Cweb endpoint, previously supplied by the user, was tried once through
the prior bounded first-flag transport. Only the unique stage session label was
changed. The source was syntax-checked locally before invocation. No alternate
address, scan, SSH fallback, retry, network configuration or updater control ran.
Endpoint, session and raw connection evidence remain private.

The transport returned BLOCKED_ACCESS_ERROR before any metadata/screen packet:

- Connection attempts:1.
- Device command sends:0; IsOffroad/IsOnroad reads:0.
- Received frames:0; owned terminal creation:NOT_OBSERVED.
- Socket close event:OBSERVED; final ready state:3.
- Late frames:0; terminal gate closed.

The actual state is **unobserved**, not a failed OFF result. No new evidence of
power, ignition, branch, HEAD, profile/source pins, storage, ticket namespace,
writer or process state was obtained. The connection failure does not establish
that the device is powered off, its IP changed, or its source drifted. Subsequent
receive-only observation and source checks were not run.

No schema2/schema3 payload was dispatched, and no reply receiver ran against the
device. The P release and historical L/O evidence are unchanged; the local
UNREVIEWED_SUBMOUNT result is not upgraded to actual evidence. No actual source,
Git, Params, storage, service, USB, model or updater command was issued. No ticket,
activation, writer, capture, restart/reboot or Jetson access was initiated.
Frames0/no dataset created by this workflow. Actual operating/source preservation
could not be re-attested and is not reported as PASS.

All390 prior tracked files outside the continuation prepend remain byte-identical.
There is no production/test implementation change. Node syntax validation of the
private first-flag transport passed. Python regressions were not rerun: the prior
558 passes remain historical and are not added to a fresh count. Existing root,
diagnostics4 and nativeFFmpeg blockers remain separate.

The user was asked to confirm powered, ignition-OFF availability and the current
address. No ignition ON is required. A new user-triggered connection can start
with the exact IsOffroad/IsOnroad reads, then proceed to fresh observations/source
identity only if OFF passes. Do not reuse historical OFF or auto-retarget source.
Schema3 query/deployment/Vehicle10 readiness:NO; M2:NO; PARITY_UNDETERMINED.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15q_fresh_off_source_gate_20261027.json`
