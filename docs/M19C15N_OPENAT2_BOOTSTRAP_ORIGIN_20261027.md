# M19-C1.5N — independent openat2 bootstrap origin · 2026-10-27

**Local bootstrap implemented and tested. Actual device capability remains unknown.**

Development started CLEAN/local-remote equal at
cd43033271bab680f9621df89691b995fc26cfd6 on
feature/jetlink-multimodel-carrot. This stage adds a separate local experiment,
tests, design/plan and sanitized evidence. There was no actual comma or Jetson
access. The selected strict ProcView/provider, defaults, schema2 release,
historical receipts, recorder patches and source pins remain unchanged.

## Bootstrap decision

The fdinfo-only recursive/witness proposal is rejected. A genuine fresh witness
record authenticates that lookup, but cannot authenticate sibling readers. A
static same-superblock bind substitution can return a shadow FD's record with
matching device/inode/flags and a different mount origin. A finite reciprocal
reader chain ends in an unauthenticated cycle. This countermodel does not require
a mount change during observation and is not evidence of device tampering.

The new [local module](../tools/proc_openat2_bootstrap.py) uses an independent
kernel premise: every intermediate and leaf below a held procfs root is opened
with NO_XDEV, NO_MAGICLINKS, NO_SYMLINKS and BENEATH. Thus reader origin is
established before fdinfo interpretation. The initial named procfs root is the
only allowed mount-crossing acquisition; its parent remains held. The self link
is held with O_PATH/NOFOLLOW and read through bounded readlinkat, without traversal.
Linux documents NO_XDEV as rejecting bind-mount crossings too, and permits that
final held-symlink form with the other resolve guards.
[openat2 semantics](https://man7.org/linux/man-pages/man2/openat2.2.html).

The induction is finite: native root type/filesystem identity anchors the first
parent; a protected successful open anchors the next reader's mount; native
fstat/flags and exclusive ownership bind each held FD. A genuine kernel fdinfo
reader can then describe a still-owned target FD. Its own record is not needed
to authenticate the reader, so no recursive certificate is introduced.

The bootstrap checks procfs/device/type/flags/CLOEXEC, self mapping, owner
PID/start/credential/status brackets, strict fdinfo mount/flags/optional inode,
all persistent targets, and a separately reopened named root. Reads are bounded
to 16KiB, restricted opens to 64, read calls to 4096. Failures stop immediately:
no retry, weaker flags or ordinary-open fallback below procfs. Owned descriptors
are closed once; all remaining closes are attempted on error. Cleanup failure
cannot return success or replace the primary failure.

Trusted native bindings and exclusive same-process FD ownership remain premises.
The proof does not detect unobserved privileged mount/filter ABA or native-thread
interference. Closing a lease ends it; the returned snapshot is not authority for
later operations. See the [design](superpowers/specs/2026-10-27-openat2-bootstrap-origin.md).

## ABI and compatibility limits

The binding accepts only Linux/glibc little-endian LP64 x86_64/aarch64 and checks
the 24-byte open_how layout. Syscall 437 is taken from the reviewed
[x86-64 table](https://github.com/torvalds/linux/blob/v5.6/arch/x86/entry/syscalls/syscall_64.tbl)
and [asm-generic table](https://github.com/torvalds/linux/blob/v5.6/include/uapi/asm-generic/unistd.h),
used by [arm64](https://github.com/torvalds/linux/blob/v5.6/arch/arm64/include/uapi/asm/unistd.h).
The [UAPI](https://github.com/torvalds/linux/blob/v5.6/include/uapi/linux/openat2.h)
defines the layout and resolve flags. It reuses checked legacy fstatfs/readlinkat
bindings, but never calls legacy describe/statx. The legacy constructor's statx
symbol is still required; missing-symbol support is not implemented.

openat2 is documented from Linux 5.6. Actual comma kernel/libc/openat2 support is
NOT_RUN/UNKNOWN, and actual aarch64 execution is NOT_RUN. ENOSYS, EINVAL, EPERM,
EXDEV, EAGAIN or any other open error reject. This candidate may also be
unsupported on the target. The historical L UNSUPPORTED_MOUNT_ID/CONSTRUCT/errno
NONE receipt is unchanged, and its exact kernel/libc cause is still unknown.

## Validation

Initial collection was RED because the module did not exist. The adverse suite
then exposed inconsistent early-close error classification; the fix retains the
primary error and reports cleanup failure without retrying close. Independent
review also found cleanup aborting if identity lookup failed after FD registration.
Three RED cases reproduced it; cleanup now closes registered FDs even without an
identity entry. Focused tests
are followed by one full fresh unique regression run; focused/RED/historical
runs are never added to the total.

Fresh local WSL Linux x86_64, glibc 2.39, Python 3.12.3/pytest 9.1.1:
**406 unique PASS / 0 FAIL / 0 ERROR / 0 SKIP** = 358 retained + 48 new cases.
Real local cases exercise own-proc bootstrap, existing cross-mount EXDEV,
symlink traversal rejection and final held-link behavior. The resulting mount ID
matches an independent statx calibration oracle; the candidate does not call it.
Controlled fixtures cover syscall failures, intermediates/leaves, malformed and
substituted fdinfo, optional inode, owner/status/generation drift, FD replacement
and flags, named-root replacement, limits, partial reads and cleanup failures.

No privileged bind mount was created. Bind-mount coverage here is documented
kernel semantics plus injected EXDEV cases, not an actual hostile bind-mount test.
Injected success is explicitly labelled INJECTED_FIXTURE; it is not native proof.
Root collection, diagnostics4 and nativeFFmpeg blockers remain separate and were
not rerun or added. No dependencies were installed.

## Scope and handoff

The finite origin candidate is separate from a complete ProcView backend. It
does not inspect the full mount profile, namespace/global/temporal visibility,
process policy, helper lifetimes or negative PID witnesses. All authority flags
remain false, including on success. The root lease is closed before return.
No provider adaptation, sampler, journal, new payload/decoder/dispatcher or actual
query was added. No source/branch retarget, deployment, Params/storage/service/
USB/model/updater change, ticket, activation, capture or restart occurred.

Independent whole-change review approved the bounded proof/code after the cleanup
correction; a separate final publication pass checked counts, hashes and privacy.
All 370 prior tracked files outside the continuation prepend are byte-preserved.
The earlier carrot-wip604bc transition review remains a public snapshot review,
not actual identity or runtime approval. Its wider runtime/model-catalog changes
still need exact-source compatibility review before a new recorder profile.

Next: review an offline ProcView integration using this protected opener while
retaining every scope/ownership/temporal gate, before preparing any source-bound
actual capability query. Actual redeployment and Vehicle10 remain NO; M2:NO;
PARITY_UNDETERMINED.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15n_openat2_bootstrap_origin_20261027.json`
