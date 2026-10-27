# M19-C1.5O — protected endpoint scope integration · 2026-10-27

**PASS_OFFLINE_SCOPE_INTEGRATION_ONLY. Controlled fixtures pass; the real local
mount profile is rejected as UNREVIEWED_SUBMOUNT. Actual device support is unknown.**

Development started CLEAN/local-remote equal on feature/jetlink-multimodel-carrot
at c5e69c9736b2121d89dc27f722ec922acb4561c7. The user approved the proposed next
offline integration review. This stage adds a separate local endpoint candidate,
tests and sanitized evidence. No actual comma or Jetson connection occurred.

## Integration boundary

The new [inspector](../tools/proc_openat2_scope.py) performs one complete set of
scope endpoint checks within a fresh, continuously held root/owner/fdinfo lease.
It accepts no old bootstrap receipt. The N bootstrap snapshot's closed lease
cannot authenticate later reads. NativeOpenat2 and the N lifetime helpers are
reused unchanged, together with the frozen mount/stat validators.

Every component below the held root uses the fixed NO_XDEV/NO_MAGICLINKS/
NO_SYMLINKS/BENEATH opener. The named root's initial acquisition and independent
final reopen from its held parent remain the explicit mount-crossing exception.
All other paths, including fdinfo readers, sys/kernel/random/boot_id, uptime,
namespace links and mountinfo, are protected. The N native ABI and ownership
assumptions remain in force. Its syscall/layout provenance and limitations are
recorded in the [prior review](M19C15N_OPENAT2_BOOTSTRAP_ORIGIN_20261027.md).

The frozen scope gates remain: procfs/type/device/flags; self/owner mapping;
owner stat generation, credentials and full status brackets; persistent target
mount IDs; boot digest endpoints; namespace link endpoints; strict unique
canonical /proc mount profile, visibility options and no submounts; repeated
mountinfo bytes; final named-root and FD identity checks. All owned FDs close
before a result can return. Cleanup failure blocks success and preserves a
primary failure. Reads remain bounded to 16KiB per file, 64 restricted opens and
4096 read calls. Large mount tables reject rather than truncate. This narrower
bound is disclosed instead of weakening the old scope parser.

Independent review found one P2 defect: catching FileNotFoundError around the
entire lease.opened method could turn parent/post-open validation ENOENT into a
supported missing pid namespace. Two RED regressions reproduced that false
acceptance. The correction tags ENOENT only at the native component-open
boundary. Only that tag for the optional pid leaf can mean absence. Parent
checks, post-open retain/filesystem validation and held-link reads now propagate
their original errors. The N helper itself was not changed.

## What was not integrated

This function returns a PRIVATE OPENAT2_ENDPOINT_SCOPE_V1 snapshot, labelled
NATIVE_OPENAT2_SCOPE_ONLY or INJECTED_OPENAT2_SCOPE_ONLY. It has no complete
ProcView interface. It does not implement enumeration, generation handles,
metadata, executable target following, child mapping, journal/sampler/provider
adaptation, or an actual capability payload/receiver. Existing backend allowlists
and defaults remain unchanged; the new source is never relabelled as statx.

The source audit found independent paths in frozen ProcView/Generation. In
particular, executable metadata deliberately follows a fixed proc magic link to
an O_PATH target across filesystems. A wholesale opener or describe replacement
would need to address that distinct exception, scope bootstrap, fdinfo readers,
stream semantics and backend admission. This stage does not silently substitute
such a provider. The [design](superpowers/specs/2026-10-27-openat2-scope-integration.md)
records the boundary and all preserved checks.

Successful endpoints do not prove namespace equality, whole-host visibility,
continuous/temporal visibility, absence of processes, helper lifetime or process
policy. Those authority flags remain false, even for successful injected data.
The lease is closed before return, so its result cannot authorize later reads.
Native bindings, exclusive same-process FD ownership and the stated exclusions
of unobserved privileged ABA/native-thread interference remain assumptions.

## Fresh verification

Local WSL x86_64/glibc 2.39, Python 3.12.3/pytest 9.1.1:
**458 unique PASS / 0 FAIL / 0 ERROR / 0 SKIP** = 406 retained + 52 new cases.
Prior, RED, focused and independent reruns are not added to this total.

Controlled fixtures compare all common successful scope fields to frozen
ProcView while retaining distinct backend labels. Cases cover EXDEV rejection for 13 named component cases,
strict mount-profile rejection, endpoint boot/mount/namespace/owner drift,
exact-leaf absence and validation-error discrimination, same live root through
all opens, named-root replacement, FD flag drift, limits, partial/oversize reads,
primary error preservation and final cleanup failure. The independent reviewer
retested 52 cases and approved the corrected bounded candidate. A final publication
review verified counts, hashes, privacy and the separate native rejection. The
EXDEV test-coverage wording was narrowed to the actual named-component cases;
numeric owner-directory/fdinfo-reader fault injection is not claimed.

A separate real local run, without statx describe, reached the unchanged strict
mount parser and returned **REJECTED / UNREVIEWED_SUBMOUNT**, with no FD leak.
The local profile was not waived. This is a fail-closed local result, not a
positive native scope or actual-device compatibility result. No privileged mount
was created. No actual aarch64 test was run. Root collection, diagnostics4 and
nativeFFmpeg blockers remain separate/not rerun/not added; no dependency install.

Actual openat2/kernel/libc support remains NOT_RUN/UNKNOWN. The historical L
UNSUPPORTED_MOUNT_ID/CONSTRUCT/errno NONE receipt is unchanged. N's documented
Linux 5.6 primitive and required legacy statx symbol are not proof of target
support, and no automatic fallback is introduced.

## Preservation and next step

All 376 prior tracked files outside the continuation prepend remain byte-identical,
including the N bootstrap, strict ProcView, scope parser, journal, sampler,
capability tool, schema2 decoder and historical recorder evidence/patches/pins.
The historical schema2 payload is unchanged. No actual source/branch identity was
read this stage; no source/Params/storage/updater/service/USB/model write, ticket,
activation, dataset, capture, restart or Jetson action was performed.

The endpoint candidate is ready for an **offline review of a separate bounded,
source-pinned capability-only payload and receiver**. Such a future probe can
check native support before investing in complete process-provider adaptation.
No new payload or actual query is approved/generated here. Full process policy
and exact carrot-wip recorder/runtime compatibility still require their own
gates. Deployment/Vehicle10:NO; M2:NO; PARITY_UNDETERMINED.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15o_openat2_scope_integration_20261027.json`
