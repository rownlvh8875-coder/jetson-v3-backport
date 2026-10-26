# M19-C1.5G — actual capability attempt · 2026-10-27

**BLOCKED_DEVICE_UNREACHABLE. Capability payload invocation:0.**

The user continued the next read-only step. The development feature branch
started CLEAN and equal to its fresh remote at
`f2b5e070d878b8900496e9ee3db484f0754d8f13`. Protected remote refs were unchanged.
The prepared66708-byte in-memory payload and its reviewed source hashes were
reverified before attempting the existing user-provided comma terminal endpoint.
No new address was guessed, no other device was tried and no network scan ran.

The single connection attempt returned `BLOCKED_ACCESS_ERROR` with zero retained parsed
terminal frames and no owned-session metadata observed. No command send was recorded before
that failure receipt was written.
The first intended reads remained the two IsOffroad/IsOnroad cats; even these did
not run before the failure receipt. The private failure receipt is retained
with its digest in the artifact.
The legacy driver did not record socket closure or post-receipt send state.
Its metadata handler lacked a terminal-state guard, so a late owned metadata
frame after finish could send the cats. There is no evidence that happened in
this ACCESS_ERROR attempt; later driver activity is not established. The driver
never invokes the capability payload, so its target invocation count is0.
This transport error does not establish whether the device is powered off,
its address changed or the network path failed.

Fresh OFF/source/profile/pins/storage/namespace/writer checks are NOT_RUN or
NOT_OBSERVED. Historical values are not current evidence. Capability invocation
count is0; its result is NOT_RUN, not BLOCKED_SCOPE_PROFILE. No sampler/observer
window, recorder deployment, target file installation, ticket, activation,
capture, restart, Params/USB/service/updater change or Jetson access occurred.

Payload SHA256:
`be13b17d4318d4dd0b9c0ff7e9f1e620c49a9690a5143092af44a0b98bf71767`.
It stays prepared only. Future use still requires fresh OFF/source gates,
whole-payload SHA verification and `python -B` over stdin from startup.
No automatic60-second observation, retarget, fallback or deployment follows.

All348 prior tracked working-byte hashes outside the continuation prepend and
493 selected historical private files were checked unchanged. Prior290 unique
passing tests remain historical; they were not rerun or added to a new total.
Tracked runtime/tools/tests remain unchanged. A separate private future-use
transport adds terminal/send-state guards and saves final closure evidence or
an explicit unknown after a bounded wait. It rejects malformed packets and only
permits cleanup after the cats were successfully queued. Offline VM fixtures fake every socket,
timer and filesystem operation:12 unique PASS/0FAIL/0SKIP. RED variants and the
initial runner setup error are retained privately and not added to that count.
The guarded driver was not dispatched; the actual driver/receipt remain intact. Root
collection, diagnostics4 and native FFmpeg blockers remain separate. No packages
were installed. The prior continuation body remains byte-exact after the prepend.

The current power/OFF state and IP were requested because connectivity is missing;
this is not another deployment/capture approval request. Do not turn ignition ON
for this check. Next step: restore known connectivity with OFF power maintained,
then start again with the two fresh OFF/ON reads before any capability query.

Policy/helper attribution and deployment readiness remain unproved. Vehicle10:NO.
Parity:UNDETERMINED. M2:NO. Raw/private paths and the device address are not public.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15g_actual_capability_20261027.json`
