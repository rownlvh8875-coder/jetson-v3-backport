# ProcView sampler and complete private semantic evidence

Status: offline implementation; actual dispatcher/deployment remains unchanged.
The user requests continued execution of the next work after M19-C1.5E. Root
implements in the specified feature checkout, with independent static review.

## Decision and interfaces

Use an explicit opt-in provider, not a replacement for the strict ProcReader.
`ProcViewReader(view, journal)` supplies enumerate/probe/metadata for the existing
GenerationTracker. Scan `complete` and `visibility_supported` are always false;
NOT_FOUND becomes unadmitted UNREADABLE, never ABSENT. Metadata verifies the
requested PID/start generation. All runtime/negative/policy/fallback flags remain
false. The old prepare/collect and actual dispatcher stay byte-identical.

`collect_acquisition(reader, duration, interval)` is a separate bounded loop. One
unsupported baseline stops before a fast loop; no retries. It records actual
scan/probe/metadata timing and scope changes. A successful collection means a
private acquisition window only, not lifetime, helper, namespace, global or
temporal-visibility proof. Endpoint equality is not remount/filter/exec-ABA proof.

`PrivateJournal(path, max_bytes, max_events)` opens an exclusive regular 0600 file
through a held no-follow private-parent directory. Canonical versioned JSONL
stores a sequence and hash chain, bounded bytes/records/line sizes, typed bytes,
and an END count/digest. Write loops handle short writes. Overflow, sink, fsync or
close failure is sticky, preserves partial bytes and never returns a trusted
seal receipt. Terminal space is reserved. `verify_journal(path, trusted_anchor)`
checks canonical JSON/base64, duplicate keys/nonfinite values, sequence/hash,
footer, exact EOF, total digest/count and file metadata. Hashes are consistency
against that trusted anchor, not authenticity or omission proof by themselves.

ProcView gets an optional sink fixed before acquisition starts. It records
semantic public API begin/end/failure, constructor and close lifecycle plus its
instrumented low-level attempt records. This is complete *instrumented semantic*
coverage, not a trace of every native syscall. Its old512-entry tail stays bounded
and explicitly incomplete after eviction. Sink failure preserves the primary
exception, poisons subsequent reads and blocks a successful collection. No
callback detach or silent conversion of the old acquisition schema.

All raw process fields and failure partials remain private. The local journal is
not raw vehicle input capture. Public `public_summary` creates a closed
allowlist of enums, counts, whole-journal digests and finite aggregate timing;
never argv, links, identities, paths, raw error strings or per-secret hashes.

## Owned observer

`with_owned_observer(view, observer, collector, view_factory, timeout)` is opt-in.
Before forking: one leader Python thread, default SIGCHLD, passing endpoint scope.
Child closes inherited view/stream copies, opens a fresh view and sends a bounded
canonical mapping frame on an inherited anonymous pipe with a fresh parent
challenge. Parent verifies the challenge, exact child PID and mounted-view
mapping while retaining direct unreaped-child ownership. Child waits for ACK
before observer ready/collector start. Parent drains framed result before reap.
Early exit, invalid frame, wrong mapping, timeout or cleanup failure rejects.
Signal/reap target is only the fork-return owned PID, never a supplied view PID;
recheck wait ownership/SIGCHLD policy before signal. No operating-process signal.
Trusted callback code must not steal wait ownership or mutate signal policy.

This proves protocol origin under trusted fork/callback/FD ownership assumptions,
not child honesty, PID-namespace equality or a policy exclusion of descendants.
No actual observer/device connector is added. Controlled test backends are labeled
as fixtures; local WSL native scope refusal remains a refusal.

## Acceptance and preservation

TDD covers stream truncation/reorder/overflow/canonical errors/IO failure, sink
failure and late failure/cleanup, more than512 operations, generation reuse,
unchanged old baseline refusal, no BOUNDED lifetimes, cadence/overrun/drift,
owned-pipe handshake/mapping/timeout/early-exit/wait loss and summary privacy.
No dependency installs. Fresh relevant tests are counted once; old totals are not
added. Historical reports/artifacts/private evidence remain immutable. Only the
acquisition module receives the explicit sink extension; no recorder/source pins,
Params, services, USB/updater configuration, actual storage/ticket/capture changes.

Native target support, real kernel visibility and actual OFF/process preservation
remain unobserved until a separately gated device stage. This work cannot declare
Vehicle10 or M2 readiness or revive historical failed proof.

Primary interfaces: [pipe](https://man7.org/linux/man-pages/man2/pipe.2.html),
[wait ownership](https://man7.org/linux/man-pages/man2/waitpid.2.html),
[short writes](https://man7.org/linux/man-pages/man2/write.2.html),
[JSON bounds](https://docs.python.org/3.12/library/json.html).

## Implemented refinements and handoff

Reserved dictionaries are escaped separately from byte values; the data-only
decoder enforces writer depth/key/decoded-byte limits. Replay uses the trusted
byte budget while reading. Each SCOPE/SCAN/PROBE/available-METADATA record is bound
to a consumed matching CALL_RESULT in the same session. Capability success needs
a matching successful BASELINE scope; READY alone is insufficient. Public counts
and cadence reconcile with those bound scan/probe records. Fixture/native source
is a public fixed enum, never device validation.

Child semantic events relay over the framed pipe into the sole parent writer.
The callback must cooperatively call check at bounded intervals: there is no hard
preemption of a blocked Python callback/kernel syscall. RESULT/ERROR received
during an active collector rejects independently of waitpid. Inherited-view
cleanup failure stops before ready/callback execution.

`run_diagnostic` integrates cleanup/footer/replay/public summary. Default probe-only
never starts a child or fast loop. Native interval is .25–.5s; shorter intervals
are fixture-only. Rejections derive partial counts from replay and mark timing
unknown. Killed children can leave unclosed streams: retain anchor plus explicit
verification failure, never synthesize VIEW_CLOSED or waive replay.

Separate `probe_capability` is one read-only scope query with a discarding/count
sink: no journal/file, fork, fast loop or raw output. It is an offline-tested
handoff building block, not an actual dispatcher. Any future in-memory target
invocation still needs fresh OFF/source gates and pinned payload review. None is
executed here. Collector raw return is not duplicated into OBSERVER records;
SCAN/PROBE/METADATA/SUMMARY already retain its process evidence privately.

`build_payload` finishes the offline handoff: exactly the reviewed scope-model,
acquisition and capability module bytes must match the external closed source
manifest. A deterministic in-memory loader checks those pins before compiling
them into isolated temporary module aliases, restores aliases/bytecode policy and
prints one count-only capability result. It has no SSH/target-file/dispatcher path.
The whole payload SHA is an external invocation gate, not producer authentication
from self-reported hashes. Builder rejects source drift or extra/missing modules.
Tests execute it only as a bounded local Linux child and verify pin-tamper refusal.
