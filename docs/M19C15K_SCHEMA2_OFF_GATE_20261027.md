# M19-C1.5K — schema2 resumption OFF gate · 2026-10-27

**BLOCKED_NOT_OFFROAD. Connectivity restored; schema2 queries:0.**

The user clarified that work should resume after the a9d7fa9 reconnect receipt,
rather than continue the intervening Git-pull diagnosis. Development started
CLEAN/equal on the required feature branch at
`a9d7fa9ba4f3992ef04e773c3b5f349fe9e7ebc3`.

One fresh owned terminal connection to the user-provided endpoint succeeded.
Its first two reads returned IsOffroad=0 and IsOnroad=1. The first OFF gate
therefore failed. The connection was closed with closure observed/state3.
No retry, genuine-OFF observation, full source/profile preflight, schema2
capability query or postflight was run. Current ignition, source/profile,
storage, namespace and writer state were not revalidated by this resumption.
Earlier read-only Git-lock observations belong to a separate diagnosis and do
not substitute for these gates. The historical J unreachable receipt remains
unchanged; it is not retroactively converted into a successful connection.

The prepared 72286-byte schema2 payload, both decoders, three bundled-source
pins and reviewed transport freshly match their recorded hashes locally.
The payload remains NOT_DISPATCHED. These local matches do not establish
actual device capability or process-policy acceptance.

No recorder deployment, source/Git/Params/service/USB/updater/model/storage
write, ticket, activation, writer start, capture, restart/reboot or Jetson
access was initiated by this resumption. Captured frames0; no dataset created.
There is no full-host preservation claim. Source/runtime/test code did not
change, so historical342 Python and12 transport passes were not rerun or added;
root/diagnostics4/nativeFFmpeg blockers remain separate.

Next: park safely and maintain comma power with ignition OFF, then repeat the
fresh first reads. Genuine OFF, exact source/profile/storage/namespace and
reviewed asset checks must all pass before at most one schema2 query. Do not
turn ignition ON for that check. Redeployment/Vehicle10 readiness:NO; M2:NO;
PARITY_UNDETERMINED.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15k_schema2_off_gate_20261027.json`
