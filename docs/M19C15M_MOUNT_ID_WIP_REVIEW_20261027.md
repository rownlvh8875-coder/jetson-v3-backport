# M19-C1.5M — mount-ID compatibility / carrot-wip transition · 2026-10-27

**PASS_OFFLINE_REVIEW_ONLY. The actual native blocker remains unresolved.**

Development started CLEAN/local-remote equal at27db8beb3cc12e33a1a47b01c8f1b810dbd3860c
on feature/jetlink-multimodel-carrot. No actual comma or Jetson access occurred.
Only a new characterization test, review/design documents, sanitized artifact and
prepend-only continuation are added. Production code/defaults, strict sampler,
historical payloads, recorder patches and pins remain byte-identical.

## Native compatibility

The L receipt remains UNSUPPORTED_MOUNT_ID / CONSTRUCT / errno NONE. The existing
guard correctly rejects either a missing returned mount-ID bit or a nonpositive
ID, even if the native call succeeded. New tests characterize these failures,
separate syscall errors, no retry, descriptor cleanup, procfs identity and fixed
fixture receipt authority. They do not implement or prove a compatibility fix.

[statx](https://man7.org/linux/man-pages/man2/statx.2.html) documents mount IDs from
Linux5.8. [fdinfo](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html)
documents its older mnt_id field, also visible in the
[Linux4.9 source](https://github.com/torvalds/linux/blob/v4.9/fs/proc/fd.c).
The linked design discusses a possible libc emulation explanation without
attributing that path or a kernel version to this device.

The distinct FD-relative fdinfo backend is a **proposal, not implemented or
implementation-ready**. Its finite bootstrap must independently authenticate the
root/owner/fdinfo/auxiliary-reader chain. Plain text, device/inode equality or
reciprocal self-certification cannot satisfy that obligation. The strict backend
stays selected. No missing check, fdinfo fallback, new payload or actual retry
was introduced. Global/temporal visibility and process-policy authority remain
unestablished. See the [design](superpowers/specs/2026-10-27-mount-id-compatibility-review.md).

## Public source consolidation

The [official integration note](https://github.com/ajouatom/openpilot/blob/604bc0a22733e648ec05b268da1ffaae7db52a69/docs/carrot_wip_consolidation_20261027.md)
states that carrot-nav/carrot-nav-blink were merged and deleted. Fresh GitHub
branch reads and public ls-remote confirm carrot-nav absent and carrot-wip at
**604bc0a22733e648ec05b268da1ffaae7db52a69** for this point-in-time review.
The GitHub exact comparison reports208 ahead/0 behind from approved24c, with
merge base24c and183 changed paths. Independent local endpoint-tree comparison
matches all183 paths. The local reference is shallow: its85 count is truncated
history, not an independent full-history confirmation of208. No unshallow,
checkout, reset or ref move was performed. Existing reference submodule changes
were preserved.

All41 historical pins match the24c blobs. At604bc,35 remain byte-identical and6
change: contracts.py, daemon.py, host_release.json, modeld.py, server/session.py
and tools/jetlink/server.py. Complete old/new hashes are retained in the artifact
as **comparison data, not an activation profile**. model.py/link.py/client.py/
deferred_map.py and pinned camera/shared-input/transport/HUD core remain identical.
This proves a narrow source boundary only, not whole-runtime compatibility.

New effective model selection uses the boot-frozen catalog on /TICI; an unchanged
jetson_model.json alone no longer proves the selected model. Selection/release
override precedence, model-library maintenance, offroad cache cleanup, physical
blinker protocol/workers, cache/TRT recovery and modeld/desire dependencies need a
fresh exact-source review. Bundled blinker defaults do not establish actual
activation; hardware, negotiation and configuration guards still matter. Upstream
owner vehicle/CI claims are not our exact-target or device evidence. MD v3 catalog
retirement does not approve or change the frozen Cinque V3 parity target.

The declared N16 artifact and canonical spec hashes remain01effc.../63b209...;
no binary was accessed. Repository-expected host source changes toc3f2aeeb...→
0d494749..., bundle SHA a9cbc29723ea74046cfbd042116ef3f07b40c33d4f09aabe3256baf7d96a1f28,
size64822535. Declared aarch64/L4T36.4.7/TRT10.3 remains the same. Signature bytes
change but were not cryptographically verified here. Actual Jetson host: NOT_RUN.

## Validation and handoff

Fresh **358 unique PASS /0 FAIL /0 ERROR /0 SKIP** in existing local WSL
Python3.12.3/pytest9.1.1:16 new native-return characterization fixtures plus342
retained cases. The earlier16-only run and historical totals are not added.
No dependency installation. Root/diagnostics4/nativeFFmpeg blockers remain
separate. Independent static reviews found no required corrections; their
implementation-not-ready and no-runtime-approval limits are retained.

All366 prior tracked files outside the continuation prepend are unchanged.
Reference HEAD/index/shallow metadata and its preexisting submodule status are
unchanged. No actual source/branch/Params/storage/updater/service/USB/model write,
ticket, activation, capture, restart/reboot or Jetson action occurred. No new
deployment candidate was generated and no source was automatically retargeted.

Next: settle the finite bootstrap certificate for a distinct FD-relative backend
offline before implementation or a new actual capability query. A separate exact
carrot-wip runtime/recorder compatibility gate remains required before migration.
Actual redeployment/Vehicle10:NO; M2:NO; PARITY_UNDETERMINED.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15m_mount_id_wip_review_20261027.json`
