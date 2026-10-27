# M19-C1.5L — actual schema2 capability · 2026-10-27

**BLOCKED_NATIVE_CAPABILITY — UNSUPPORTED_MOUNT_ID / CONSTRUCT / errno NONE.**

The requested resumption after a9d7fa9/K reached the actual reviewed schema2
query. Development started CLEAN/local-remote equal at
`0b5dfd507f60abdfd1a81f04ca6c6fbcf0b2b618` on the required feature branch.
The first two reads returned IsOffroad=1/IsOnroad=0. Endpoint/session and raw
terminal data are private. No alternate address, scan or automatic retry ran.

Fresh receive-only PRE12.076s and POST12.012s observations both pass: started
false, ignitionLine/ignitionCan false/false, normal OFF managed roles, ticket
namespace absent, no recorder writer match, existing reviewed storage empty.
Actual source remains carrot-nav@24c1ba5e4b3428f56fa0e402f5a10097e2e94c32.
Both preflight endpoints pass exact PRE6/41 source-pin assertions. Unlike the
historical H assurance, this invocation uses the pinned unconditional decoder
which rejects optimization and enabled bytecode before executing the unchanged
preflight. Individual41 hash rows are not returned. N16's reviewed source/spec
file is pinned; this is not a fresh model-binary hash or model execution.

Nine local source/release/decoder/preflight hashes match. Exactly one72286-byte
payload, SHA e8116a412a79224105065c067d7b54d4c330febb0ed41386291e7c3f58c725c1,
was dispatched with the schema2 decoder/receiver. The strict result has18 fields:
events3, NATIVE_LOCAL_PROCFS, optimization DISABLED, bytecode SUPPRESSED,
UNSUPPORTED_MOUNT_ID in CONSTRUCT, errno NONE. All authority flags remain false.
The constructor stopped before a sampling window/journal/observer child.
The probe's processes_created=0 does not count the separate transport decoder
and receiver Python helpers. All three operation receipts record one execution,
no transport error and observed socket closure/state3.

Source analysis locates the failure in NativeLinux.describe: after successful
native descriptor queries, it requires the statx mount-ID mask bit and a positive
mount ID. The fixed projection does not distinguish which part was absent, nor
identify a specific kernel/libc cause. It establishes a native-backend
compatibility blocker, not recorder/input failure or device malfunction.
No fdinfo fallback, weaker gate, second query or automatic retarget was used.

The12 recorded source canaries, Git index digest and tracked/untracked status
digest match across all four PRE/POST endpoints. Managed-role endpoint identities
also match PID/starttime and recorded fields. These are not a full-host temporal
process-preservation proof; the reviewed writer scan is not an exhaustive
negative PID witness. No recorder redeployment, source/Git/Params/service/USB/
updater/storage/model write, ticket, capture, restart/reboot or Jetson access ran.
Frames0/no dataset created. Historical H/J/K receipts are unchanged; the new
reason does not retroactively establish H's failure cause.

No runtime/test implementation changed. Historical342 Python and12 transport
passes were not rerun or added; root/diagnostics4/nativeFFmpeg blockers remain
separate. Next is an OFFLINE compatibility review of the mount-ID backend while
preserving scope/identity gates. Actual redeployment/Vehicle10 readiness:NO;
process-policy acceptance:NO; M2:NO; PARITY_UNDETERMINED.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15l_actual_schema2_capability_20261027.json`
