# Openat2 bootstrap-origin implementation plan

> **For agentic workers:** Use superpowers:executing-plans inline, then one independent whole-change review.

**Goal:** Validate a finite independent reader-origin anchor offline, without changing the actual/default provider.

**Architecture:** A fixed-flag native openat2 opener and bounded own-procfs bootstrap reuse the existing native ABI/FD parsing helpers. Kernel noncrossing authenticates readers before fdinfo is interpreted. No recursive fdinfo certificate.

**Tech Stack:** Python stdlib/ctypes, existing WSL Python3.12/pytest; no installs.

**Spec:** docs/superpowers/specs/2026-10-27-openat2-bootstrap-origin.md

## Global constraints

- Offline/local only; no actual comma/Jetson connection or mutation.
- Preserve strict NativeLinux/ProcView/default sampler, historical payloads, patches, source pins and receipts.
- No fallback, retry, weaker resolve flags, process control, writer, ticket, capture or namespace/mount creation.
- All policy/global/temporal/negative-witness authority flags remain false.
- Stay on feature/jetlink-multimodel-carrot; no protected refs or user-state changes.

## Review focus

- Native syscall ABI/layout and fixed flags, including final O_PATH symlink exception.
- Every controlled component/leaf has independent noncrossing origin; no circular reader attestation.
- Descriptor ownership, owner generation/credentials, finite limits, replacement and cleanup.
- Injected versus real local provenance; no device/kernel support or full-scope approval inferred.
- Unchanged frozen sources/payloads/default dispatch and accurate unique regression counts.

## Tasks

- [x] Save starting source/private preservation hashes and a stage ledger.
- [x] Add tests/test_proc_openat2_bootstrap.py; observe RED for missing API.
- [x] Implement only tools/proc_openat2_bootstrap.py; run focused GREEN. Correct defects with concrete failing cases first.
- [x] Run the unchanged358 relevant cases plus new unique cases once; save JUnit and local environment.
- [x] Independent source/proof review; resume implementer for required corrections and justified reruns.
- [x] Sanitized M19-C1.5N report/artifact and continuation prepend, feature commit/push, CLEAN/equal/protected-ref verification.

The existing feature checkout is the user-required isolated development context;
no new branch/worktree or actual source retarget is introduced.

## Outcome

Fresh unique406 PASS =358retained+48new,0fail/error/skip. Review found a partially
registered FD cleanup defect;3 failing cases reproduced it before correction.
Independent focused48PASS and bounded native-origin proof/code approval. Runtime
integration/device capability/deployment remain unapproved. Publication review PASS; final
feature push verification is recorded in the private ledger and final response; prior authorization selects commit/push without
a new integration-options question. No merge, PR or protected-ref change.
