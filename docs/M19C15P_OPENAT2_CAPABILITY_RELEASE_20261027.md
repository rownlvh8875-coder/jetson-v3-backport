# M19-C1.5P — offline endpoint capability release · 2026-10-27

**PASS_OFFLINE_RELEASE_ONLY. The local native reply remains blocked by
UNREVIEWED_SUBMOUNT. Actual device support/query/deployment remain unverified.**

Development started CLEAN/local-remote equal at
57981c87e2c8b4c30b2f1abbdeecb1bfed92d775 on
feature/jetlink-multimodel-carrot. The user approved the next offline
payload/receiver step. No actual comma or Jetson access occurred.

## Distinct release and boundary

The new [builder/projector](../tools/proc_openat2_capability.py) packages exactly
five reviewed sources: scope model, pinned ProcView, N bootstrap, O endpoint
inspector and the new capability projector. Each source SHA and the canonical
source-bundle SHA are checked before in-memory execution. Fresh tools aliases
and bytecode mode are restored on success/failure. No device source imports,
file install, journal, sampling window, observer, retry or fallback are added.
Generated execution requires optimize0, -I and -B before bundled code runs.
Startup flag rejection cannot be upgraded by setting bytecode suppression later.

One endpoint inspection is projected into a distinct 29-field schema3 response.
It contains only closed enums, counts/false flags and reviewed bundle/query
identifiers. Unknown exception text, paths, namespace links, PID/FD/argv values,
cause chains and cleanup details are discarded. Cleanup failure is a fixed
blocked reason. A successful private endpoint must have the expected kind and
backend, closed lease, incomplete ProcView interface and false authority flags.
Unexpected activity/device claims also reject, rather than being normalized
into a supported endpoint. Tests reproduced and corrected three such cases.

The whole payload is independently checked by the **unchanged** readonly source
gate. The new builder enforces its 262144-byte whole-source ceiling in addition
to 262144 bytes per source and 1048576 bytes per bundle. A RED case exposed the
missing whole-script bound before release generation; the correction prevents
returning a payload that the frozen outer gate cannot receive.

The independent [reply receiver](../tools/openat2_payload_gate.py) consumes one
canonical ASCII JSON frame, at most 8192 bytes, and seals on any attempted accept.
It rejects schema2, duplicate/extra/missing keys, malformed/truncated/multiple
frames, noncanonical bytes, invalid types/enums/counts/runtime relationships,
injected evidence, mismatching bundle/challenge or unchecked execution digest.
All activity/authority flags must remain false. The standalone receiver checks
its own reviewed source SHA before execution, reads with an 8193-byte sentinel,
then emits exact validated bytes or a fixed rejection marker/exit 78.

This is **contract checking, not producer or transport authentication**.
The expected IDs and execution digest are caller trust premises. In particular,
the standalone receiver is configured with the expected execution digest; it
does not measure remote execution. The caller must independently verify the whole receiver/gate script SHAs and bind a
successful exact-source gate and transport result to that receiver context.
A literal fixture can satisfy the grammar. The challenge and sealing reject
cross-query/repeated input within this one-shot context, but do not establish
global replay protection across newly created receiver instances.

## Private release metadata

Exact scripts, a private random 64hex challenge and the full local receipt remain
in ignored local evidence. Public metadata contains source pins, sizes and the
challenge commitment, not the challenge or raw response. This is not raw vehicle
data; no vehicle dataset was read or created.

- Payload: 106250 bytes, SHA256
  3b78e52bd1215dec2faa4f5ee276ff453cea17c7f4f2c9b14abbc6ec9a41c00d.
- Standalone receiver: 13750 bytes, SHA256
  77ff59224dcdf5550210d359748dd849a58daa6ddd4d4c7fa8dbd587f35ab375.
- Exact-source gate SHA256:
  e69c448765f4357a4deadf69a2a482c27d23c12cce92ae7309fe6005bfdfb145.

All five source pins, receiver-source pin and remaining sizes are in the
sanitized artifact. Expected pins still require an independently trusted review;
matching hashes alone do not authenticate a peer. No actual dispatcher is added.

## Verification

Fresh local WSL x86_64/glibc 2.39, Python 3.12.3/pytest 9.1.1:
**558 unique PASS / 0 FAIL / 0 ERROR / 0 SKIP** = 458 retained + 100 new cases.
RED/focused/independent reruns and manual review mutations are not added.
No dependencies were installed. Root collection, diagnostics4 and nativeFFmpeg
blockers remain separate/not rerun/not counted.

Cases cover fixed privacy/result projection, source/bundle/whole-script bounds
and tamper, interpreter guards before poisoned fixture-module execution, alias
restoration on every outcome, receiver framing/type/relationship/sealing rules,
valid blocked results, receiver source tamper and full exact-source gate→payload
→receiver fixture chains. Synthetic source modules/literal receipts are fixtures,
not native observations or authentication evidence. The reviewer independently
retested 100 cases and found no remaining actionable code issue after the bound fix.

A separate exact-release local pipeline used the frozen source gate and newly
pinned scripts under -I -B. The response was schema3,
BLOCKED_ENDPOINT_SCOPE / UNREVIEWED_SUBMOUNT / INSPECT / errno NONE, attempts 1.
The strict receiver accepted this **blocked** contract unchanged; it did not
approve native scope. Both helper interpreters exited 0. Those two launch/receiver
helpers belong to the harness, separately from probe-created-processes 0. The
endpoint never became a full ProcView provider, device validation or policy pass.
A blocked reply's lease_closed=false means closure is not attested by the reply;
it is not a finding that descriptors leaked.
No mount profile was waived. Actual aarch64/kernel/libc support remains NOT_RUN. Final independent publication
review confirmed exact release rebuilds, all pins, privacy, unique test counts
and historical preservation; no further correction was required.

## Preservation and next step

All 382 prior tracked files outside the continuation prepend remain byte-identical,
including schema2 payload/tool/decoder, strict defaults, N/O modules and historical
recorder evidence/patches/pins. The old schema2 release SHA remains e8116a...;
the actual L UNSUPPORTED_MOUNT_ID/CONSTRUCT/errno NONE receipt is unchanged.
No actual branch/source identity was read, source/runtime/storage/Params/updater/
USB/model changed, ticket created, activation/capture/restart or Jetson action
performed. Frames 0; no dataset created. Numerical parity remains UNDETERMINED;
M2:NO. Neither current carrot-wip nor Vehicle10 deployment is approved here.

Next: fresh read-only OFF/source/profile/namespace gates for a separately
authorized at-most-one schema3 query. Current actual identity/support and those
gates are unobserved, so actual-query readiness remains NO. Do not auto-retarget,
retry, weaken scope, install a provider or redeploy the recorder on this result.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15p_openat2_capability_release_20261027.json`
