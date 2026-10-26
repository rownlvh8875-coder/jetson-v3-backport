# M19-C1.5D — proc-view scope review · 2026-10-26

**PASS_OFFLINE_REVIEW. Runtime replacement is NOT APPROVED.**

A continuously owned real procfs descriptor can supply a basis for one mounted
PID view without relying on a PID-namespace symlink. This is conditional kernel
reasoning, not proof that a collector acquired or retained such a descriptor.
Full equivalence, helper safety and process preservation remain unestablished.
The existing strict sampler, recorder candidate, patches and source pins are
unchanged. No actual comma or Jetson access occurred in this stage.

## Findings

Procfs has its own mounted PID view. Equal self/getpid values identify a caller
mapping; they do not prove namespace equality or host-global coverage. A future
child needs an explicit mapped-view handshake, separate from direct-parent wait
authority. [PID namespace documentation](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html).

Upstream procfs stores a PID-namespace reference, supporting a mount-view design.
No upstream version or CONFIG_PID_NS setting is attributed to the actual device.
[Linux v6.1 procfs initialization](https://raw.githubusercontent.com/torvalds/linux/v6.1/fs/proc/root.c).

Mount pinning does not freeze visibility policy. Remount can alter hidepid in
shared procfs state; matching unrestricted endpoints cannot exclude a filtered
interval between them. That limitation also exists for the legacy endpoint
method. It must remain an explicit trust/evidence boundary, rather than becoming
an unstated assumption or a reason to silently allow a missing gate.
[Linux v4.9 remount implementation](https://raw.githubusercontent.com/torvalds/linux/v4.9/fs/proc/root.c).

The old metadata and parent readers, common/receive-only process observations and
owned-child identity probe reopen absolute proc paths. Their values cannot be
assigned a pinned-view token merely because they match. A complete FD-relative
interface, per-target mount checks, generation brackets, fresh directory streams,
closed field allowlist and native filesystem/flag-ABI authentication remain future
acquisition work. Held-generation descriptors and fresh numeric-PID probes serve
different purposes; a stale descriptor does not switch to a reused PID.
[Kernel procfs behavior](https://www.kernel.org/doc/html/v6.5/filesystems/proc.html).

## Deliverable and validation

The proposed ADR and plan accompany `tools/proc_view_scope_model.py`. This is a
pure record-relationship assessor, not a ProcReader or acquisition implementation.
It has no device, file-acquisition, process, signal or network APIs. Its strongest
result is `CONDITIONALLY_CONSISTENT_MOUNTED_VIEW` with `OFFLINE_NOT_ADMISSIBLE`.
Runtime scope, temporal visibility, namespace equality, full-host visibility,
negative-PID witnesses, policy and fallback acceptance remain false in every path.

The model correlates mount/fdinfo/device/inode records, owner generation and
credentials, boot/mount-namespace binding, complete operation provenance and
baseline fingerprints. Missing PID namespace is retained as ENOENT; permissions
do not become absence. PID namespace results have a required same-view operation.
File-read fdinfo describes its target, while readlink-parent fdinfo describes the
held parent directory. These are not interchangeable.

Independent review found contradictory raw flags/inodes and missing namespace
operation provenance. Regression cases failed before correction and passed after
it. The final model uses an explicit synthetic asm-generic flag ABI, never an
inferred device ABI. Raw access/directory/no-follow/close-on-exec relationships and
optional root inode are checked; this still cannot authenticate the acquisition.
[Flag UAPI reference](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/asm-generic/fcntl.h),
[fdinfo format](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html).

Fresh relevant validation: **135 PASS / 0 FAIL / 0 ERROR / 0 SKIP** —74 new CPU
model fixtures and61 existing CPU/POSIX sampler fixtures, with disjoint IDs.
Earlier iterations are not added. The previous1374 full result is historical,
not rerun or recounted here. Root live-fetch/exit collection, diagnostics4 dependency
and native FFmpeg blockers remain separate; no dependency was installed.

Two independent reviewers checked the final model, design, saved JUnit and claim
boundaries. All324 frozen prior tracked files, excluding the planned continuation
prepend, and10 private critical evidence files retained exact working-byte hashes.
The previous failed actual receipt is rejected by this model's schema; it has not
been repaired, converted into valid process evidence or replaced by synthetic data.

## Handoff

Actual current source, OFF state, ticket, writer and dataset were **not freshly
observed in this stage**. No actual sampling retry, deployment, ticket, storage
operation, activation, capture, restart, Params/service/USB/updater change or
Jetson operation was performed. The previous A5 unknown remains unresolved.
Ready for actual diagnostic adapter: NO. Recorder redeployment: NO. Vehicle10: NO.
Numerical parity: UNDETERMINED. M2: NO.

Next action: implement and offline-test a complete FD-relative ProcView acquisition
adapter with explicit visibility trust assumptions. Keep the current strict
default and actual dispatcher unchanged until its separate review gates pass.

Result commit: `git log -1 --format=%H -- artifacts/m19c15d_proc_view_scope_review_20261026.json`
