# M19-C1.5E — FD-relative ProcView acquisition · 2026-10-26

**PASS_OFFLINE_ACQUISITION_WITH_LIMITS. Actual integration is NOT APPROVED.**

Implemented `tools/pinned_proc_view.py` as a development-only acquisition library.
The existing strict sampler, record model, runtime adapters, recorder patches and
source pins are unchanged. No actual comma/Jetson access or operational action
occurred. Current actual identity, OFF state, namespace and recorder state were
not freshly observed and are not inferred from historical receipts.

The library holds one procfs root, uses component-wise relative opens and checks
the native filesystem and mount ID for proc-backed descriptors, including the
bootstrap self symlink. It provides fresh enumeration/probes, held-generation
metadata, parent/command/executable endpoint brackets and private scope evidence.
An executable-target O_PATH stat is the explicit cross-filesystem exception;
executable contents are never read. Missing fields remain errors. A direct target
open failure is distinguished from an owner/native capability failure.

Native support is intentionally narrow: Linux little-endian glibc LP64 on
x86_64/aarch64 with checked layouts and returned `STATX_MNT_ID`; only x86_64 was
executed locally. Mount-ID support requires Linux 5.8+, and unavailable symbols,
syscalls or masks stop acquisition. Actual comma compatibility is UNKNOWN; there
is no fallback to fdinfo, PID numbers or the legacy reader.
[statx interface and availability](https://man7.org/linux/man-pages/man2/statx.2.html).

Bounded native readlinkat detects a full/truncated buffer. Descriptor cleanup
attempts all owned handles, preserves a primary read/rejection error and records
cleanup failures. Failed entry closes its handles. Observed owner generation,
leader-thread, Python-thread-count and credentials/fsuid/fsgid changes reject.
[readlink truncation](https://man7.org/linux/man-pages/man2/readlink.2.html).

Fresh validation: **200 unique PASS / 0 FAIL / 0 ERROR / 0 SKIP**: 65 new
acquisition tests, 74 unchanged record-model tests and 61 unchanged strict-sampler
tests, in the existing Python 3.12.3/pytest 9.1.1 WSL environment. Earlier iterations
and the historical 1374 full result are not added. Root collection's live-fetch/
exit blocker, diagnostics4 dependency blocker and native FFmpeg blocker remain
separate and were not rerun. No dependency was installed.

Tests cover controlled real filesystem fixtures, native capability boundaries,
mount crossing, traversal/symlinks, PID reuse/closed handles, metadata/parent races,
namespace/owner failure provenance, cleanup failures and bounded audit retention.
Local Linux native procfs reads succeeded; its full scope endpoint profile
correctly refused `UNREVIEWED_SUBMOUNT`. That environment was not skipped and the
existing restriction was not relaxed. There is no local full-scope approval.

Independent review findings were reproduced with failing tests, then corrected:
entry/local cleanup, bootstrap binding, target/namespace ENOENT phase confusion,
readlink truncation, worker-thread credential scope, command/parent unknowns and
private/injected provenance. Saved final reviews assess source/receipts only;
reviewers did not execute acquisition or access a device.

The acquisition records are **private and unsanitized**. This module has no public
emitter. Its bounded 512-operation diagnostic tail reports dropped records and
`complete=false` on eviction, and is not complete sampling-window evidence. Fatal
metadata errors retain private partial evidence. Matching child mapping records
do not authenticate their origin or grant ownership, wait or signal authority;
the owned-pipe handshake still needs integration.

Every runtime-scope, temporal/global visibility, negative-PID-witness, operating
policy and legacy-fallback acceptance flag remains false. This is a new
acquisition schema, not automatic conversion of the old pure record model.
Trusted FD ownership, supported ABI and absence of unobserved privileged
mount/filter mutations are explicit assumptions; matching endpoints cannot prove
them or exclude A→B→A behavior. No lifetime, cadence or helper-safety claim follows.

All 330 frozen prior tracked files except the planned continuation prepend and
10 critical historical private files retained exact working-byte hashes.
Historical actual failures remain unchanged. No actual sampler, deployment,
storage, ticket, activation, capture, restart, Params/service/USB/updater or Jetson
operation was performed. Vehicle10: NO. Parity: UNDETERMINED. M2: NO.

Next action: offline integration review for the ProcView provider, a complete
bounded evidence stream, child-pipe provenance and supported visibility contract.
Keep the strict default and actual dispatcher unchanged until those gates pass.

Result commit: `git log -1 --format=%H -- artifacts/m19c15e_proc_view_acquisition_20261026.json`
