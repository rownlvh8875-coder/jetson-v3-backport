# FD-relative ProcView acquisition — offline candidate

Status: implementation design; actual integration is not approved.

The user requested the next step after M19-C1.5D: implement the acquisition
boundary in the development repository, test it offline, preserve the existing
strict sampler and actual dispatcher. No device access or operational action.
The implementer chooses Python standard library plus explicit Linux LP64 native
ABI bindings. No dependency installation, automatic fallback or kernel inference.

## API and ownership

`ProcView()` owns `/proc`, opened once with DIRECTORY/NOFOLLOW/CLOEXEC. Each
component thereafter is opened relative to a held directory, never through an
absolute `/proc/self/fd` proxy. Native fstatfs authenticates procfs, and statx
AT_EMPTY_PATH with returned STATX_MNT_ID authenticates every proc-backed FD,
including bootstrap and intermediate directories. Missing capabilities reject.
Supported native ABI: Linux little-endian LP64 x86_64/aarch64 with checked layouts;
glibc libc symbols are required. Only x86_64 is locally exercised. Returned
STATX_MNT_ID support requires Linux 5.8 or later; unsupported symbols, masks or
syscalls reject, with no fdinfo fallback. Actual kernel/libc compatibility is
unknown. [statx availability](https://man7.org/linux/man-pages/man2/statx.2.html).

The scope is one mounted view. Numeric `self` is resolved relative to that view
and held by generation; equality with getpid is required for this limited
profile, not interpreted as namespace equality. The native process-leader thread
and a single active Python thread are required. Owner status includes fsuid/fsgid;
native threads and privileged ABA mutations remain trust boundaries. Observed fork/thread/credential changes
invalidate use. FD ownership assumes trusted same-process code does not close,
replace or use private descriptors. Endpoint identity checks cannot detect a
malicious same-process close/reopen ABA. Context managers close all owned FDs,
including failed entry, and retain cleanup errors while attempting other closes.
All returned data is private and unsanitized; a separate allowlisted/redacted
emitter is required before any receipt/publication. This module has no emitter
or filesystem writer.

Closed operations: fresh PID enumeration; fresh PID stat probe; held generation
stat/status/cmdline/cgroup, exe/cwd links, executable target stat; parent brackets;
owner/boot/uptime/mountinfo/namespace scope snapshot; mapped child handshake
comparison. All metadata providers use the same view object. No arbitrary path,
read/write method, process control, subprocess, service or sampler entry point.

Generation handles keep numeric lookup and held-generation lookup distinct.
Metadata retains individual failures, brackets stat, command and executable observations,
and does not claim an atomic image of mutable process state. A stale handle never
automatically reopens its PID. Fresh enumeration opens `.` anew, not dup of a
shared directory offset. Proc exe target stat is an explicit cross-filesystem
exception: bind the proc symlink through a checked parent, follow only the fixed
exe target with O_PATH, compare link/target before and after, never read contents.
Readlink uses bounded native readlinkat on the held symlink FD and detects full
buffers, avoiding Python readlink truncation. No pathname-proxy fallback.
[readlink truncation](https://man7.org/linux/man-pages/man2/readlink.2.html).

Audit retention is a 512-operation private tail with sequence IDs, timestamps,
failure phase/errno and explicit dropped count; eviction makes `complete=false`.
It never becomes full-window evidence. Fatal metadata errors retain private
partial evidence. Sampler integration still needs a bounded complete evidence
stream and independently measured cadence. No existing sampler is modified.

## Visibility and child boundary

Endpoint mountinfo restrictions, boot, mount namespace, owner generation and
credentials are checked; ENOENT PID namespace remains an explicit observation.
Permission/unsupported failures remain errors. Endpoint comparisons do not rule
out remount/filter ABA, exec ABA, hostile privileged mutations or invisible tasks.
Required trust assumptions are reported as assumptions, never accepted booleans.
Runtime scope/negative PID witness/policy/fallback acceptance stay false.

A child opens its own view and reports mapped PID/start and mount/boot binding.
Parent verifies it through its own held view with parent-generation brackets.
This proves a matching current mapping only; no wait/signal authority, descendant
exclusion or lifetime bound follows. A future owned pipe protocol must establish
where a child record came from. This library never forks, signals or reaps.
The implemented comparison accepts a supplied mapping record; the owned pipe
protocol is not implemented. Native acquisition and injected fixture output have
distinct backend tags. There is no automatic conversion to the old record schema.

## Tests and non-goals

Use controlled real temporary directory fixtures with explicit native-boundary
doubles for adverse mount/permission/race cases, plus bounded local Linux procfs
tests. Reject traversal, intermediate symlinks, same-device different mount,
non-proc roots, root rebind, fork/credential drift, malformed/truncated stat,
PID reuse, stale handle and unsupported ABI/capability. Verify repeated scans,
field errors, parent brackets, mapping mismatch and descriptor cleanup.

All current tracked files except prepend-only continuation remain unchanged.
Historical receipts cannot be upgraded. Actual adapter, cadence, temporal
visibility, helper policy, redeployment and Vehicle10 remain separate gates.

Primary interfaces: [openat](https://man7.org/linux/man-pages/man2/open.2.html),
[fstatfs](https://man7.org/linux/man-pages/man2/statfs.2.html),
[statx](https://man7.org/linux/man-pages/man2/statx.2.html),
[statx UAPI](https://raw.githubusercontent.com/torvalds/linux/v6.1/include/uapi/linux/stat.h),
[glibc statfs](https://raw.githubusercontent.com/bminor/glibc/release/2.39/master/sysdeps/unix/sysv/linux/bits/statfs.h).
