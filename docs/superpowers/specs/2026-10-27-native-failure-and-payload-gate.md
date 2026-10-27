# Native failure projection and unconditional payload gate

M19-C1.5I is offline only. Actual H result remains BLOCKED_NATIVE_CAPABILITY,
cause unknown and full PRE6/41 assurance unconfirmed. Nothing here upgrades it.

Use existing acquisition events/exceptions to project only a closed reason code,
failure phase and errno symbol. No raw text, path, PID, argv, exception type name,
environment value, cause chain or kernel configuration is emitted. Known exact
AcquisitionError reasons and selected errno values are allowlisted; unknowns stay
generic blocked results. Do not modify ProcView requirements or strict defaults.
Schema2 also records fixed optimization/bytecode modes. Optimized capability
execution rejects before constructing a view. Keep one query/no retry/no fork,
file, journal, sampling window, fallback or policy acceptance.

Raw tracebacks would expose private context. Changing native checks to force a
supported result would weaken the gate. Reuse the existing error boundary instead.

Add a standalone decoder builder with explicit runtime, encoding/size/compression
and SHA checks, before executing exact pinned preflight source or outputting exact
pinned capability bytes to stdin. Reject optimized interpreters and missing -B
before ordinary imports; never use assert as a production guard. Legacy preflight
assertions may execute only after this unconditional optimization guard. No old
receipt/source transformation or retroactive full-pin claim is permitted.

New schema2 payload/source pins are a distinct offline candidate. Keep the old
payload be13... and every actual/private historical receipt byte-identical.
The caller still supplies independently reviewed expected SHA pins; this is not
producer authentication or device/global/helper-policy approval. No dispatcher,
SSH, target file install, device access, deployment, ticket or capture is added.

Validate with failing tests first: closed failures/privacy, constructor/enter/
scope/close, errno and unknown errors, optimized execution, whole-payload/source
tamper, bounded decompression/trailing data and execute/stdout modes. Exercise
normal and -O/-OO local interpreters and fresh relevant regressions once. Stage
and publish only intended public source/tests/design/report/artifact changes.
Actual kernel/ABI and future device compatibility remain untested.
