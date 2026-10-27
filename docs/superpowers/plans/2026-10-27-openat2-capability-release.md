# Endpoint capability release plan

> **For agentic workers:** Use superpowers:executing-plans inline and one independent whole-change review.

**Goal:** Prepare a distinct source-pinned endpoint-only payload and strict one-shot receiver offline.
**Architecture:** Five frozen/native-source modules load in memory after identity/runtime checks; independently constrained receiver validates only a closed schema3 frame. Reuse existing source decoder without changes.
**Tech Stack:** Python stdlib, existing WSL Python/pytest, no installs.
**Spec:** docs/superpowers/specs/2026-10-27-openat2-capability-release.md

## Constraints and review focus

- Actual access/query/mutation, ticket/capture/restart: NO. Old modules/defaults/schema2 unchanged.
- Exact-source and interpreter guards before bundled execution, no assertion gates/fallback.
- Fixed response projection, no private context or unjustified native/global/policy authority.
- Strict one-frame receiver relationships, independent expected pins/challenge, no authentication claim.
- No repeated counts; preserved old bytes, private releases and sanitized public evidence.

## Tasks

- [x] Save CLEAN/equal baseline and prior hashes.
- [x] Add tests/test_proc_openat2_payload.py and tests/test_openat2_reply_gate.py; observe RED.
- [x] Implement tools/proc_openat2_capability.py and tools/openat2_payload_gate.py; focused GREEN.
- [x] Fresh458 retained plus new unique regressions; separate real local end-to-end result.
- [x] Independent proof/code/publication review; implement required corrections with RED/GREEN.
- [x] Generate private pinned release/receiver/decoder and public sanitized report/artifact; prepend continuation.
- [x] Authorized feature commit/push; CLEAN/local-remote equal/protected refs unchanged.

## Outcome before publication

Fresh558 unique PASS=458retained+100new,0fail/error/skip. Three private-activity
contract failures and whole-source gate limit defect reproduced RED and fixed.
Independent100PASS/code review clean. Exact-source local pipeline returned
BLOCKED_ENDPOINT_SCOPE/UNREVIEWED_SUBMOUNT, unchanged through receiver; no native
scope approval. Generated release106250B, receiver13750B. Private challenge/raw
reply remain local; no actual query/access. Publication/release review PASS. Final push verification is recorded in the
private ledger and final response, without rewriting historical receipts.
