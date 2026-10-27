# Protected endpoint scope integration

The user approved the next offline scope integration review. Use the existing
feature checkout; no actual comma/Jetson access, query, deployment, ticket,
capture, restart, storage/Params/source/updater operation is part of this work.
Existing production/default modules, bootstrap N and historical evidence remain
byte-identical. This design is the implementer's scoped integration choice,
within the user's continuous local work authorization; no further question is
needed for a local proof/test candidate.

## Deliverable

Create tools/proc_openat2_scope.py with inspect_protected_scope(root='/proc',
*, _native=None). This is a one-shot PRIVATE endpoint inspection, not a full
ProcView provider, sampler, journal or schema2 receiver. It accepts no previous
bootstrap receipt: the N snapshot's FD lease was closed and cannot authenticate
a later observation. Open a fresh lease and retain it through every scope read,
all end checks and cleanup. Reuse N's fixed NativeOpenat2 and _Lease helpers and
the unchanged _mount/_stat parsers rather than copying relaxed validators.

## Existing source audit

The frozen ProcView includes root acquisition/reopen, regular component reads,
held symlinks, scope, generation/enumeration/probe and metadata. Generation's
fixed exe target deliberately follows a proc magic link across filesystems with
O_PATH, which is a different exception from scope. A wholesale opener injection
or a describe-only replacement would leave some paths unprotected, change the
bootstrap premise, or recurse while authenticating fdinfo. It is not approved.
Journal and public-summary backend allowlists also exclude a new native backend.
Do not relabel the candidate as the legacy statx backend to evade these guards.

## Single-lease protocol

1. Hold root parent and named procfs root, with the same sole mount-crossing
   acquisition exception as N. Fixture-only custom roots remain explicitly
   injected. Check procfs/type/device/flags, hold self link without traversal,
   bind numeric owner/stat/status and own fdinfo directory.
2. Authenticate persistent target mount IDs through protected own fdinfo readers.
   Every below-root component/leaf must use fixed openat2 guards, including
   sys/kernel/random/boot_id, uptime, ns/mnt, ns/pid and mountinfo.
3. Perform the exact frozen scope rules: boot digest, uptime, own namespace link
   endpoint equality, missing pid namespace accepted only when opening that exact
   leaf returned ENOENT, strict unique canonical /proc mount profile with no
   submounts/hidepid/unknown options, repeated mountinfo byte equality and repeated
   boot digest equality.
4. Recheck owner stat generation/full status/credentials, self mapping, persistent
   native FD identities/mount IDs, held parent and independently reopened named
   root. A different named root rejects even if old root is still readable.
5. Close every owned FD once before returning; primary errors survive cleanup
   failure. Reject every missing/unsupported/error path without retry or weaker
   opens. Bounds stay N's64 restricted opens,4096 reads,16KiB per file. The
   narrower bound may reject a large mount table; it never silently truncates.

Both present and absent pid namespace are compared at two endpoints. Parent ns
directory failure, readlink failure after a successful leaf open, EACCES, EXDEV
and other errors cannot become a supported absent namespace. The new code must
separate the exact leaf open from reading its held link.

## Result and boundary

The result is PRIVATE/unsanitized, has a distinct OPENAT2_ENDPOINT_SCOPE_V1 kind
and NATIVE_OPENAT2_SCOPE_ONLY or INJECTED_OPENAT2_SCOPE_ONLY backend label.
Report endpoint_checks_pass=true only after all checks and successful cleanup;
lease_closed=true, full_ProcView_interface=false. All runtime/global/namespace/
temporal/negative-witness/policy/fallback/lifetime authority flags remain false.
Endpoint checks do not exclude unobserved ABA. Retain N's native-binding,
exclusive-FD-ownership and native-thread/privileged-interference assumptions.

No backend default/provider/payload/decoder/observer change. Actual support of
openat2 remains UNKNOWN/NOT_RUN; Linux5.6 documentation is not a target check.
Inherited glibc LP64 x86_64/aarch64 and statx-symbol constructor limits remain.
Do not claim complete process-policy integration or carrot-wip approval.

## Validation

Add tests/test_proc_openat2_scope.py before implementation. Prove equivalence of
successful common scope fields against the frozen ProcView with controlled local
fixtures, while keeping backend labels distinct. Exercise the named scope component classes' EXDEV,
unsupported syscall, mount visibility/canonical/submount rejection, boot/mount/
namespace endpoint drift, exact-leaf ENOENT discrimination, owner/FD/named-root
drift, all-close/primary preservation, partial/oversize reads and budget failure.
No API accepts a closed certificate; no old backend/allowlist changes.

Exercise real local protected scope: either full endpoint checks pass or its
actual restricted local mount profile rejects. No waived profile or SKIP. Record
the result separately from injected positives. No privileged mounts or new
processes are created by the candidate. Fresh retained406 plus new unique tests,
independent whole-change review, sanitized report/artifact/continuation and
authorized feature commit/push complete the stage. Blockers stay separate.
