# Offline endpoint capability payload and receiver

The user approved the next offline payload/receiver step. This stage prepares a
distinct schema3 endpoint-only release; it never contacts actual comma/Jetson,
executes an actual query, changes defaults, prepares storage, arms or captures.
Preserve all old source/receipts, schema2 payload/decoder, N/O modules and gates.
The existing feature checkout is the required development context. Prior user
authorization covers local implementation/review and feature commit/push.

## Payload

Add tools/proc_openat2_capability.py. Portable builder/projection imports must
not initialize native/GPU/device code. probe_endpoint accepts reviewed bundle
SHA and challenge, uses the O inspector exactly once after runtime checks, and
projects only fixed enums/booleans/counts plus these identifiers. An explicit
test inspector is labelled INJECTED_FIXTURE and cannot pass the native receiver.
Never stringify unknown exceptions or emit PID/path/namespace/FD/argv/raw errors.
Unknown errors stay blocked. Validate successful private result kind, backend,
closed lease, incomplete ProcView interface and all false authority flags before
reporting ENDPOINT_CHECKS_PASS. This is not a complete capability/provider pass.

build_payload(sources, expected_hashes, *, challenge) consumes exactly five UTF8
sources: proc_view_scope_model, pinned_proc_view, proc_openat2_bootstrap,
proc_openat2_scope, proc_openat2_capability. Every source SHA must match an
independently reviewed pin, each source <=262144 bytes, bundle <=1048576 bytes.
Embed a canonical JSON source bundle with SHA, base64 and a fixed private64hex
challenge. Runtime rechecks bundle/source identity before module execution.
The whole generated payload must also be <=262144 bytes to fit the unchanged
outer source gate; an otherwise valid smaller bundle can still exceed this cap.
Use fresh in-memory tools aliases, restoring prior aliases and bytecode mode
on success/failure. No import from a working tree, file installation, observer,
journal, sampler, subprocess, retry or fallback is part of the payload.

Generated scripts require optimize0, -B and -I before bundled source execution.
Flags remain reported on rejection; suppression set after startup cannot upgrade
missing -B. Emit one canonical ASCII JSON line, even for fixed blocked results.
The whole payload SHA is verified externally by the unchanged readonly decoder.
That gate is not a sandbox: only the exact reviewed payload may be executed.

## Schema3 and one-shot receiver

Add tools/openat2_payload_gate.py with OneShotReplyReceiver and build_receiver.
Receiver is independently closed, portable and self-contained. It receives a
reviewed expected payload SHA, source-bundle SHA and private challenge. accept
requires the caller's checked executed SHA, consumes at most8192 bytes, rejects
noncanonical/multiple/truncated/duplicate-key/nonASCII/NaN frames and exact-key,
type, enum, source/challenge/runtime/status-reason-phase/count mismatches.
Any attempted accept seals the object, including failure; no retry/replay.
Reject injected evidence for native-only reception. No true policy/visibility/
negative-witness/lifetime/fallback/device authority flag is accepted.

The generated receiver verifies its own source against the independently pinned
receiver-source SHA before executing it in a fresh namespace. It reads stdin
with an8193-byte overrun sentinel, emits exact validated canonical bytes, or a
fixed rejection marker/exit78 without raw context. Require -I -B optimize0 here
too. No eval of receipt data, process/network/file writer or actual dispatcher.

Expected IDs and the caller-supplied executed digest are trusted inputs from the
reviewed release and exact-source transport gate, not peer authentication. A
correct literal frame can satisfy the grammar; no signature/identity proof is
claimed. A private challenge rejects cross-query frames within the caller's
one-shot context, not global replay across new receiver instances. No automatic
restart/retry or privilege follows any result.

## Validation and release

TDD tests cover fixed error/privacy projection, result-contract rejection,
five-source/bundle/whole-payload tamper, flag guard precedence, memory alias
restoration, strict response relationships/types/canonical limits, injected
evidence, challenge mismatch, sealing, receiver source tamper and flag guards.
Use isolated local subprocesses for script execution; helper processes belong
to the harness, not the probe's processes_created=0. Real local pipeline must
retain O's UNREVIEWED_SUBMOUNT refusal or other honest native result, separate
from literal/injected positives. No privileged mount or actual operation.

Save private exact payload/receiver/decoder scripts and release manifest after
tests/review; public artifact only pins, sizes, challenge commitment, sanitized
results and counts. Do not publish private challenge/raw receipts. Fresh458
retained plus new unique tests; blockers separate. Independent whole-change
review and feature commit/push finish this stage. Ready for actual query remains
NO: fresh OFF/source/profile/storage/namespace gates and exact carrot-wip review
remain separate. No full process-provider/deployment/capture/parity approval.
