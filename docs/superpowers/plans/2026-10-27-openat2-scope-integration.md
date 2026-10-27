# Protected endpoint scope integration plan

> **For agentic workers:** Use superpowers:executing-plans inline, then one independent whole-change review.

**Goal:** Integrate strict scope endpoint rules with protected reader origins in one live local lease.

**Architecture:** A separate one-shot inspector reuses frozen N native/lease helpers and frozen mount/stat validators. It never consumes a closed bootstrap snapshot and never impersonates an existing ProcView backend.

**Tech Stack:** Python stdlib, existing WSL Python3.12/pytest; no installs.

**Spec:** docs/superpowers/specs/2026-10-27-openat2-scope-integration.md

## Global constraints

- No actual access/mutation/query, ticket/capture/restart or new payload.
- Preserve every old source, default, release/pin and historical receipt.
- All authority flags false; no namespace/global/temporal/policy acceptance.
- Strict openat2 guards, no fallback/retry; owned FDs all closed before success.
- Feature branch only, authorized commit/push; no merge/PR/protected-ref changes.

## Review focus

- Same continuously held lease for bootstrap and all scope endpoints.
- Every path protected; exact leaf ENOENT only, no nested/readlink error laundering.
- No omitted strict scope gate, stale FD/certificate, relabelled backend or waiver.
- Error/cleanup ownership and finite budgets; native local vs injected claims.
- 406 retained cases not double-counted; old source/evidence/privacy preserved.

## Task1: Single-lease endpoint inspector

Files: new tools/proc_openat2_scope.py and tests/test_proc_openat2_scope.py.
API: inspect_protected_scope(root='/proc', *, _native=None), PRIVATE closed-lease result or exception.

- [x] Save CLEAN/equal baseline and all prior file hashes.
- [x] Write positive equivalence and adverse contract tests; observe missing-API RED.
- [x] Implement minimal same-lease inspector; focused GREEN, failure cases first for corrections.
- [x] Run retained406 plus new unique tests, save JUnit and actual local outcome privately.
- [x] Fresh independent whole-change proof/code/publication review and required corrections.
- [x] Publish sanitized M19-C1.5O report/artifact + prepend continuation; feature commit/push and final CLEAN/equal/protected-ref checks.

Keep generation/metadata/exe target, child mapping, journal/sampler/provider and
schema2 integration explicitly pending; these are separate approval boundaries.

## Outcome and rulings

Fresh458 unique local PASS =406retained+52new,0fail/error/skip. Real local native
scope rejected UNREVIEWED_SUBMOUNT without a waiver or FD leak. Reviewer P2 broad
ENOENT catch reproduced in2RED cases; fixed with native-open-origin tagging and
independent52GREEN. Publication review PASS after EXDEV coverage wording narrowed. Final authorized
feature push checks are recorded in the private ledger and final response.
Ruling: review capability-only payload/receiver next, before complete process
provider work or actual access. This avoids treating the endpoint candidate as a
ready sampler/backend; all broader gates remain closed.
