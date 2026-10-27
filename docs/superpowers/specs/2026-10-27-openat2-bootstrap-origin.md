# Finite bootstrap origin with an independent noncrossing primitive

Status: offline/local candidate only. No actual dispatcher or ProcView integration.

The user requested continuation of M19-C1.5M's bootstrap proof. Independent
reasoning rejects the fdinfo-only/challenged-witness proposal: a valid witness
lookup cannot authenticate substituted sibling fdinfo/mountinfo records. A finite
cycle of reader records has no independently authenticated origin leaf. The
countermodel uses static same-superblock bind sources, so no privileged change
during the observation window is needed. This is not evidence of device tampering.

## Selected independent anchor

Use a separate Linux openat2 primitive. Every component and leaf below the held
procfs root must be opened with NO_XDEV, NO_SYMLINKS, NO_MAGICLINKS and BENEATH.
The kernel enforces noncrossing, including bind mounts, before any fdinfo bytes
are trusted. The final self symlink is held with O_PATH|O_NOFOLLOW and read through
the existing bounded native readlinkat helper; it is never traversed.
[openat2 semantics](https://man7.org/linux/man-pages/man2/openat2.2.html).

The finite induction is: native fstatfs/fstat authenticates the held root; a
successful restricted open from an already-held parent authenticates the next
reader's mount origin; fstat/flags and owner brackets bind its lifetime. Thus an
fdinfo reader is authenticated by its own open, not by recursively reading its
fdinfo. The kernel-generated record can then describe a still-owned target FD.
The target/reader distinction must remain explicit. Arbitrary supplied records
or dependency cycles never establish this native premise.

## Implementation scope

Create tools/proc_openat2_bootstrap.py with NativeOpenat2.open_component and a
bounded bootstrap_procfs_origin function. It reads only its own fixed procfs
bootstrap paths and returns PRIVATE snapshot evidence after closing all FDs.
It is not a ProcReader/provider, sampler, policy attestor, deployment helper or
replacement for NativeLinux. Existing source, defaults, payloads and pins stay
unchanged. No new actual payload is prepared.

Use Linux little-endian glibc LP64 x86_64/aarch64 only. Reuse the checked legacy
native fstatfs/readlinkat bindings, without calling its statx describe method.
The new syscall binding uses the reviewed open_how24 layout and openat2 number437
for these two ABI profiles; all unsupported profiles reject. The required
syscall is documented from Linux5.6. Neither a kernel version string nor the
old statx result proves target availability. ENOSYS/EINVAL/EPERM/EXDEV/EAGAIN and
other errors stop immediately, without retry, weaker flags or ordinary-open
fallback. Sources: [UAPI layout](https://github.com/torvalds/linux/blob/v5.6/include/uapi/linux/openat2.h),
[x86-64 table](https://github.com/torvalds/linux/blob/v5.6/arch/x86/entry/syscalls/syscall_64.tbl),
[asm-generic table](https://github.com/torvalds/linux/blob/v5.6/include/uapi/asm-generic/unistd.h).

The initial named /proc root is the sole mount-crossing anchor exception. Hold
its / parent as well; reopen the named root at the end and compare native
identity and authenticated fdinfo mount ID. No other unprotected component is
allowed. All proc-backed FDs must be procfs and match the root's device/type
expectations; directory/file/link modes and CLOEXEC must match. Owner PID/start,
Python leader/thread count, credentials and full UID/GID/status brackets must
remain stable. Trusted same-process FD ownership and absence of unobserved
privileged ABA/native-thread interference remain explicit assumptions.

Bound reads, descriptor/operation counts and link lengths. FD-relative fdinfo
must have unique positive mnt_id, valid flags matching fcntl, and matching ino
when present. Missing optional ino does not remove native fstat checks. All
bootstrap target IDs must agree with the held root. Failed entry and reads
attempt all owned closes; cleanup failure cannot return supported evidence or
mask a primary error. Numeric IDs/paths/argv/private exceptions are not emitted
to public artifacts.

## Proof boundary

A successful result establishes only a bounded local bootstrap-origin path
under the stated native/ownership assumptions. Its root lease is closed before
return. It establishes no complete mounted-view profile, namespace equality,
global/temporal visibility, negative PID witness, helper lifetime or policy.
All such authority flags remain false, including for injected success fixtures.
Actual aarch64/old-kernel support is NOT_RUN. A new source-bound actual query and
receiver require separate review/fresh OFF/source gates; carrot-wip604bc is not
automatically approved by this work. The historical L failure remains unchanged.

## Validation

TDD: reject unsupported syscall/ABI, changed flags, symlink/magic-link traversal,
cross-mount intermediates and leaves, same-device bind EXDEV, malformed or
substituted fdinfo, wrong owner, FD identity/flag drift, named-root replacement,
oversize/partial reads and close failures. Use controlled local files and
injected syscall returns for adverse cases; label those distinctly. Add real
local Linux syscall/open/own-bootstrap tests and compare resulting mount IDs to
the existing statx oracle for calibration only. This oracle is not used by the
candidate. No privileged mount is created. Source-level bind semantics and
injected EXDEV cases must not be reported as an actual bind-mount/device test.

Ruling: continuous execution authorizes this bounded offline implementation and
tests. It does not authorize actual access, switching branches, process-policy
relaxation or deployment. No repeated approval question is needed for local work.
