# ADR — PID-namespace-independent proc-view evidence

**Status:** Proposed; offline record model only; not an accepted runtime replacement.
**Date:** 2026-10-26
**Review:** process-proof and integration-boundary reviewers, independent of implementation.

## Context and decision

The previous actual attempt failed before PID enumeration. A later bounded read
found `/proc/self/ns/pid` unavailable. That observation does not identify kernel
configuration. No device access is performed in this review. Historical receipts,
the recorder candidate and the default strict sampler remain unchanged.

The objective is to determine whether equivalent scope evidence is possible,
without skipping a failed identity check. This review distinguishes three claims:

1. One genuinely held procfs mount supplies one mounted PID view.
2. Supplied records are mutually consistent with that view.
3. Actual acquisition, complete temporal visibility and operating preservation
   have been established.

Only the second claim is evaluated by the new offline model. It cannot establish
the first from supplied integers or the third from matching snapshots. A positive
model result is `CONDITIONALLY_CONSISTENT_MOUNTED_VIEW`, always marked
`OFFLINE_NOT_ADMISSIBLE`. No existing runtime consumer calls it.

## Alternatives considered

| Approach | Assessment |
|---|---|
| Ignore missing namespace file or accept matching PID numbers | Reject: absence of evidence becomes approval; numeric IDs are not namespace identity. |
| Attest kernel CONFIG_PID_NS=n | Potential separate proof, but no authenticated running-kernel/config binding is available. ENOENT is insufficient. |
| Bind a procfs view through continuously owned directory FDs | Selected for offline examination by the implementer. Stronger acquisition obligations and provider adaptation are necessary. No user technology choice is implied. |

## Linux basis and limits

A procfs mount determines its visible PID view; self is expressed in that view.
Equal numeric self IDs do not establish namespace equality or host-global coverage.
[PID namespaces](https://man7.org/linux/man-pages/man7/pid_namespaces.7.html).

Kernel procfs state holds a PID-namespace reference. This provides a basis for a
mount-view binding, independent of the namespace symlink interface. It is generic
Linux source evidence, not an identification of the comma kernel.
[Linux v6.1 procfs](https://raw.githubusercontent.com/torvalds/linux/v6.1/fs/proc/root.c).

fdinfo supplies a mount ID, but IDs may be reused after unmount. A continuous FD
lease must be established by a trusted collector; matching numbers cannot attest
that lease. A detached held mount may no longer have a current mountinfo row.
[fdinfo](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html),
[mountinfo](https://man7.org/linux/man-pages/man5/proc_pid_mountinfo.5.html),
[mount lifetime](https://raw.githubusercontent.com/torvalds/linux/v3.18/fs/namespace.c).

Most importantly, holding the mount does not freeze filtering. Linux v4.9 remount
parses hidepid options into the shared procfs namespace state. Equal unrestricted
endpoints admit an A→B→A filtering history. This independent visibility obligation
also applies to the old snapshot-based method; a namespace identifier alone does
not solve it. No full equivalence or lifetime approval is inferred.
[Remount implementation](https://raw.githubusercontent.com/torvalds/linux/v4.9/fs/proc/root.c).

An open process directory does not prevent PID reuse, but its operations do not
silently switch to the new process. A future exit probe needs a fresh numeric-PID
lookup, while metadata reads need the held generation directory and brackets.
[Kernel procfs behavior](https://www.kernel.org/doc/html/v6.5/filesystems/proc.html).

## Proposed evidence contract

The model receives one explicit synthetic or privately acquired record, optionally
compared with a baseline. It has
no file, process, network, signal or device APIs and cannot acquire evidence.
It accepts only the versioned `PINNED_PROC_VIEW_RECORD_V1` shape:

- CLOCK_BOOTTIME read interval, numeric values with exact types and bounded order.
- Declared live lease ID, owner PID/start generation, read-only/no-follow directory
  acquisition mode, root/named-root device+inode, procfs magic, fdinfo mount IDs.
- An explicit synthetic `LINUX_ASM_GENERIC` flag ABI. Raw root/named-root flags
  must agree with read-only DIRECTORY/NOFOLLOW/CLOEXEC intent; optional fdinfo ino
  must agree with fstat inode when supplied. The target's ABI is not inferred.
- One current whole-root `/proc` mountinfo row with matching ID/device/type, no
  ambiguous/duplicate IDs, restricted filters, unsupported options or omitted row.
- Observer self mapping, status UID/GID/groups, boot and mount-namespace digests.
  Missing PID namespace is retained as ENOENT; permissions/other errors reject.
- Every required observation and any metadata/parent observation names the same
  lease and DIRFD scheme, with matching mount ID/device and bracketed timestamps.
- Both successful and ENOENT PID-namespace results require a correlated operation.
  Operation fdinfo describes the read target for directory/file operations and
  the held parent directory for `readlink_parent` operations. This distinction is
  enforced. Proc-backed metadata is modeled; resolved executable-target fstat
  still needs a separately reviewed generation/target binding.
- Baseline/current core fingerprints agree. No rebind after close, fork or mount
  drift is accepted. All exceptions are constant reason codes; raw values are not
  echoed in results.

Baseline comparison is a core fingerprint comparison. Identical or overlapping
snapshot intervals can be conditionally consistent; it establishes neither a
sequential observation chain nor elapsed-time/lifetime evidence. Backward interval
extents reject. The model does not authenticate any acquisition ABI or descriptor.
Flag values are based on [Linux asm-generic UAPI](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/asm-generic/fcntl.h).

These are *record relationships*, not proof of successful system calls. The model
cannot authorize runtime scope, negative-PID witnesses, lifetime, policy,
redeployment or capture, even when all relationships match. Caller-supplied
"verified" flags cannot override those results. Unknown schema/fields reject.

## Acquisition obligations before any integration

1. Freeze and attest the collector source. Authenticate real procfs using a
   reviewed native fstatfs ABI and PROC_SUPER_MAGIC, not parseable text alone.
2. Own the root FD continuously; verify each opened directory/file's mount and
   generation, including intermediate components. O_NOFOLLOW on the root alone
   does not prevent descendant submounts or magic-link escapes.
3. Use a closed relative-field API, rejecting absolute paths, `..` and arbitrary
   fd/magic-link content. A `/proc/self/fd/N` pathname proxy is insufficient.
4. Open fresh directory streams relative to the root lease for enumeration.
   dup/fork-shared directory offsets must not manufacture incomplete empty lists.
5. Prove observer-to-view mapping without inferring namespace equality. After fork,
   bind the child through an owned-pipe mapped-view identity handshake; the numeric
   fork-return PID alone must not label a proc-view actor as observer-owned.
6. Define and validate an independent temporal-visibility assurance, including
   remount/filter changes and supported-kernel event coverage. Matching endpoint
   rows or one mount-event channel are not assumed sufficient across kernels or
   namespaces. No such assurance is implemented here.
7. Preserve PID/start generation, parent-before/child/parent-after brackets,
   censoring, direct exit checks, measured cadence and incomplete-read errors.
8. Retain default-SIGCHLD/single-thread/owned-child wait safeguards. No process
   basename allowlist, privilege escalation or operating-process signals.

## Existing integration gap

The old metadata provider opens absolute `/proc` paths for status, cmdline, exe,
cwd, cgroup and parent stat. The receive-only/common helpers do likewise for role,
boot and uptime observations. Owned-child identification in `with_observer` uses
the strict path reader. These are separate legacy observations until explicitly
adapted; they cannot share a pinned-view token merely because values agree.

A future `ProcView` interface must provide view-bound enumeration, fresh generation
probes, held-generation field reads, link reads and fstat on reviewed targets. All
providers must receive that interface explicitly. Missing or cross-view fields
remain UNKNOWN. The existing default reader and dispatcher are not modified.

## Validation and readiness

Use literal CPU fixtures for coherent records and counterexamples: close/reopen,
same mount ID with different identity, mount removal/stacking, submount crossing,
missing namespace vs permission denial, credentials/boot/owner changes, fork-owner
reuse, absolute provider reads, partial operations, malformed input and clock
reversal. A coherent endpoint pair must still deny temporal visibility and runtime
acceptance. No raw device receipt becomes a valid synthetic record automatically.

Actual FD acquisition, remount instrumentation, kernel identity, cadence, helper
safety and full process preservation remain unverified. Recorder deployment,
Vehicle10 and M2 readiness remain NO. The next design gate is temporal visibility
assurance and a complete FD-relative acquisition contract; this ADR alone cannot
open a new actual sampling window.
