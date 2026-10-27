# Native failure and payload gate implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline. Root implements;
> one independent whole-change review follows the final relevant regression.

**Goal:** Explain future native rejection safely and enforce exact-source guards
even when optimization would remove assertions.

**Architecture:** Extend capability projection/schema and its pinned builder;
add a standalone decoder builder. Existing acquisition/strict path stays fixed.

**Tech Stack:** Python stdlib, existing WSL/Python pytest, no installations.

**Spec:** docs/superpowers/specs/2026-10-27-native-failure-and-payload-gate.md

## Global constraints

- Offline only; no actual comma/Jetson access, deployment, ticket or capture.
- Keep historical be13 payload/actual evidence immutable; no gate weakening.
- Only tools/proc_view_capability.py and continuation may change among old files.
- Explicit rejects; no public arbitrary error data or automatic native fallback.
- Keep the required feature checkout; no protected branch changes.

## Review focus

Unknown/private exception strings; failure phase versus inferred cause; runtime
flags before import/exec; compression amplification/trailing bytes; unchanged
legacy source and historical result; candidate pins and no actual-dispatch claim.

## Tasks

- [x] Add tests/test_proc_view_failure_projection.py; observe RED for reason/
  phase/errno/privacy/runtime behavior. Implement minimal schema2 projection in
  tools/proc_view_capability.py. Run old capability tests plus new tests GREEN.
- [x] Add tests/test_readonly_payload_gate.py; observe RED. Implement
  tools/readonly_payload_gate.py: build_decoder(expected_sha, mode), with fixed
  source environment key, bounded canonical base64/zlib, explicit SHA and runtime
  guards, execute/stdout modes only. Verify normal/-O/-OO and no -B paths.
- [x] Update the capability payload template for schema2/runtime guards; add RED
  cases before changing it. Prepare a distinct deterministic source-pinned local
  candidate/manifest. Never overwrite or dispatch the old actual payload.
- [x] Fresh disjoint relevant tests, preserved byte hashes, independent final
  review/fixes, sanitized M19-C1.5I report/artifact/continuation; feature commit/
  push then CLEAN/equal/protected-ref checks. No actual workflow execution.

Ruling: repeated user instruction authorizes continuous execution of this scoped
offline next step; no repeated design-approval question. TDD remains required.

Outcome:342 unique Python PASS (52new+290retained), plus12 separate local
transport fixtures (11VM+1WSL quote roundtrip). Original actual H outcome remains
blocked/unknown, not upgraded. New candidate and schema2 handoff are prepared
offline only. Final Git cleanliness/equality/protected refs are checked after push.
