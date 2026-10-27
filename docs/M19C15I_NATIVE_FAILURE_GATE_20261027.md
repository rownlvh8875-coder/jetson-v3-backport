# M19-C1.5I — native failure projection and unconditional gate · 2026-10-27

**PASS_OFFLINE_FAILURE_PROJECTION_AND_UNCONDITIONAL_GATE. Actual queries:0.**

Development started CLEAN/equal at51be5e93a40ad97ff5cb2b0b4e681f426aa35675 on
feature/jetlink-multimodel-carrot. This is an offline continuation. No current
device identity/OFF/runtime state was observed; no comma/Jetson access, deployment,
storage write, ticket, activation, writer/capture, restart, Params/service/USB/
updater or model change occurred. Frames0/datasetNONE; parityUNDETERMINED;M2NO.

Schema2 capability results add only fixed reason/phase/errno and runtime-mode
fields. Known exact acquisition reasons are allowlisted; arbitrary errors become
generic blocked codes. Raw messages, type names, paths, PIDs, argv, environment
values and exception causes are not emitted. Constructor/enter/scope/close are
distinguished. A rejection code identifies a software boundary, not a physical
kernel/ABI root cause. Native requirements and the old strict defaults are intact.

Optimized probes reject before view construction; payload runtime guards precede
bundled source execution. Missing -B also rejects. Blocked JSON formatting runs
with bytecode writes suppressed, but cannot undo interpreter startup writes if
the caller omitted -B. Literal -B from startup remains an external invocation gate.
Module aliases and bytecode state are restored. No retry, window or native fallback.

The new standalone decoder has explicit checks instead of production asserts:
runtime flags, bounded/canonical base64, one complete zlib stream with no trailing
data, bounded source bytes and exact SHA before executing or outputting source.
execute is for independently reviewed trusted preflight code, not a sandbox.
stdout sends exact verified capability bytes to a separate python -B stdin
receiver. The unchanged legacy preflight543612... can run only after optimization
is explicitly disabled; -O/-OO reject before its assertions could be omitted.

The new schema2 payload is72286bytes, SHA256
`e8116a412a79224105065c067d7b54d4c330febb0ed41386291e7c3f58c725c1`.
Separate pinned preflight/capability decoders and a strict schema2 private receiver
are prepared. The receiver rejects legacy schema1, extra/free-form fields, bad
authority flags and source/decoder SHA drift. It uses POSIX quoting for decoder
text. The entire handoff is NOT_DISPATCHED and creates no target file installation.
Fresh first OFF cats, genuine OFF, full source/profile/storage/namespace and exact
asset SHA gates still precede at most one future read-only query. No automatic
sampler, redeployment, recorder repair, ticket or capture follows any result.

Fresh Python/CPU/POSIX validation:342 unique PASS/0FAIL/0ERROR/0SKIP =52 new+290
retained cases. Earlier component/RED runs are not added. Separately12 local
transport cases pass:11 fake-only VM cases and one WSL POSIX quote roundtrip.
The initial quote escaping failure is retained; its fix passed. No device was
contacted by tests. Existing root collection, diagnostics4 and native FFmpeg
blockers remain separate/not rerun/not counted. No dependencies were installed.

Independent static code review checked source/tests, saved JUnit and exact bundled
bytes/pins without executing project helpers or contacting a device.351 prior
tracked hashes outside the authorized capability edit/continuation prepend and
561 historical private files are unchanged. Old be13 payload, actual H inputs/
receipts and recorder patches/source pins remain immutable. H remains
BLOCKED_NATIVE_CAPABILITY with unknown cause and unconfirmed fullPRE6/41 assurance.
Nothing here reconstructs missing details or upgrades historical validation.

Next: fresh OFF/source/profile and new asset-SHA revalidation, then at most one
schema2 read-only failure query. Actual policy/global/helper preservation,
redeployment and Vehicle10 readiness remain NO. Actual native compatibility has
not been retested in this stage.

Result commit:
`git log -1 --format=%H -- artifacts/m19c15i_native_failure_gate_20261027.json`
