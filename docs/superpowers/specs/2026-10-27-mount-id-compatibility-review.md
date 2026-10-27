# Mount-ID compatibility after the actual schema2 rejection

Status: **OFFLINE DESIGN REVIEW ONLY. No replacement backend or deployment payload.**

The user requested the next step after M19-C1.5L and reported consolidation into
carrot-wip. This review characterizes the unchanged native guard and specifies
the proof needed for a distinct compatibility implementation. No actual device
access, source switch, upgrade, restart, ticket or capture is authorized by this
document. The prior continuous-execution authorization is not a reason to bypass
any actual source/profile or process-policy gate.

## Established evidence and its limits

The fresh L result is UNSUPPORTED_MOUNT_ID during construction, errno NONE.
NativeLinux.describe requires both the returned STATX_MNT_ID bit and a positive
mount ID. It does not silently accept a successful statx call lacking that data.
The fixed result does not retain raw mask/ID values or identify the exact kernel,
libc, build configuration or backport responsible. Historical H remains unknown.

[statx documentation](https://man7.org/linux/man-pages/man2/statx.2.html) places
STATX_MNT_ID in Linux5.8 and distinguishes success from returned-field support.
The [glibc2.39 Linux wrapper](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/unix/sysv/linux/statx.c)
can use a generic implementation on ENOSYS, and that
[generic implementation](https://github.com/bminor/glibc/blob/glibc-2.39/io/statx_generic.c)
returns basic attributes. This is a possible explanation consistent with L,
not proof of the actual device's execution path.

The [fdinfo interface](https://man7.org/linux/man-pages/man5/proc_pid_fdinfo.5.html)
reports mnt_id since Linux3.15, while its ino field is newer. The
[Linux4.9 implementation](https://github.com/torvalds/linux/blob/v4.9/fs/proc/fd.c)
obtains the target file reference and emits its mount ID. This makes a separately
reviewed FD-relative acquisition path worth investigating. It does not make an
arbitrary fdinfo text record an authenticated replacement for statx.

## Alternatives

1. **Retain strict NativeLinux:** selected now. All existing code, default
   dispatch, source pins and historical payload bytes remain unchanged. The
   unsupported environment continues to reject.
2. **Distinct opt-in FD-relative fdinfo backend:** proposed, unimplemented. It
   must preserve mount identity, filesystem, owner, FD lifetime, same-view,
   generation, cleanup and provenance checks. No automatic fallback on failure.
3. **name_to_handle_at:** rejected as the general procfs solution. The
   [documented interface](https://man7.org/linux/man-pages/man2/name_to_handle_at.2.html)
   does not provide general procfs file-handle support; no error output is
   promoted into successful identity evidence.
4. **Device kernel/libc upgrade or skipping mount checks:** outside scope.

## Compatibility-backend proof obligations

The builder must settle the bootstrap dependency before implementation is
declared usable. Reading self/fdinfo through the same procfs view must not be
treated as already authenticated by the mount ID it is meant to establish.

- Own a real procfs root and every intermediate FD. Use native fstatfs/fstat,
  read-only/no-follow/close-on-exec opens and the existing native ABI checks.
- Establish the owner mapping and generation through held descriptors, including
  the kernel self link, numeric owner directory and starttime/credential brackets.
  Matching numeric PIDs does not prove namespace equality or full-host coverage.
- Resolve the owner's fdinfo directory relative to held FDs. Do not reopen an
  absolute proc path or proxy through /proc/self/fd to obtain target identity.
- Define and independently review a **finite bootstrap certificate** for the
  root, owner directory, fdinfo directory and auxiliary fdinfo readers. An
  unverified reader, recursive self-certification, or matching device/inode
  without mount identity must reject. This proof is open in this review.
- Bind each query to the exact still-owned target FD before/after reading.
  Detect observed close/reuse, owner or namespace change, cross-mount reads,
  root replacement, symlink traversal and bootstrap-reader replacement.
- Parse bounded kernel-generated records with exactly one positive decimal
  mnt_id. Missing/duplicate/malformed fields and permission failures remain
  errors. If ino is present it must match native fstat; absence on older kernels
  cannot remove the native inode/generation checks.
- Preserve the fixed visibility/submount profile, parent/executable brackets,
  same-view operation provenance, cleanup and incomplete-stream rejection.
- Reuse the existing record/model/provider boundaries rather than implementing
  a second process sampler. Keep injected fixture and native provenance distinct.
- Keep all runtime/global/temporal visibility, negative-PID witness, helper
  lifetime and process-policy authority flags false. Acquisition support alone
  cannot permit recorder redeployment.

The existing trust assumptions concerning trusted same-process FD ownership,
native threads and unobserved privileged mount/filter ABA remain explicit. A
certificate cannot turn endpoint observations into continuous-visibility proof.

## Validation before any future actual query

Add failing tests for the new implementation before production changes. Cover
bootstrap origin and cyclic certificates; same-device/different-mount bind
cases; record substitution; FD/PID reuse; no-follow and O_PATH symlinks; partial
and oversized reads; missing/duplicate mnt_id; optional ino; permission/ENOENT;
namespace/root/credential races; cleanup failure; no retry or automatic fallback;
strict-default preservation; fixed public reason projection and payload SHA.

Controlled local Linux tests and injected old-kernel returns must remain labeled
as such. Actual aarch64 capability is NOT_RUN in this review. A new source-bound
payload and receiver require independent review and fresh actual OFF/source
gates. The historical schema2 payload must not be overwritten or reinterpreted.

## Source transition is a separate gate

The observed public carrot-wip reference is frozen for review at
604bc0a22733e648ec05b268da1ffaae7db52a69. It is not an automatically approved
replacement for carrot-nav@24c. Effective catalog model selection, release
overrides, library/cache maintenance, physical blinker coexistence and changed
host/session dependencies require a new exact-source recorder review. Existing
24c patches, pins and source gates remain frozen; no branch switch is performed.

Decision: **DESIGN_CANDIDATE_WITH_BOOTSTRAP_PROOF_OPEN; IMPLEMENTATION_NOT_READY.**
