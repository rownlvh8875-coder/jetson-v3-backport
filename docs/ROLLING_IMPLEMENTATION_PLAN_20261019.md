# Rolling Carrot integration implementation plan

**Goal:** Continue the approved protocol 3 multi-model design without changing main,
legacy V2, upstream reference sources, or an installed runtime.

**Spec:** JETLINK_MULTIMODEL_PLAN_20261019.md and the 2026-10-19 user requirements.
**Architecture:** Small source adapters produce a disposable candidate from current
upstream. Compatibility is executable evidence, with a hash manifest and reversible
candidate patch per validated upstream SHA. Current client, server, IPC, parser and
JoiningModel remain the test path; only hardware boundaries use CPU substitutes.
**Stack:** Python 3.12, pytest/numpy/ONNX, Git, Linux subprocess TCP/Unix sockets.

## Constraints and review focus

- Branch feature/jetlink-multimodel-carrot only; no force/reset/user deletion.
- Read-only upstream reference; never commit or push to external repositories.
- Preserve V2, existing engines, timeouts and finite/shape/identity gates.
- New approvals and setup offroad; exact approved spec on reconnect; identity
  changes invalidate the connection. Capability metadata is not authentication.
- Validate every next-state output before commit. Partial commit invalidates the
  generation; RESET/HELLO cannot restore it; reload must zero state.
- Label CPU_FAKE, FIXTURE, ORT_REAL_MODEL, TRT_REAL and device evidence separately.
- Review malformed capabilities, stale HELLO/ready identity, cached nbytes mismatch,
  physical dtype narrowing, partial commits and changed upstream signatures.

## Tasks / verification

1. [x] Rolling checker and Actions: fetch fresh heads, compare relevant Git blobs,
   create read-only reference and separate candidate, execute checks, never report
   compatible on skipped/failed required checks. Test changed source and failure exits.
2. [x] Current server adapter: reuse StatefulState and Cinque V3 patch validation;
   preserve current TRT builder and V2. Test real EngineHost/Session over sockets,
   recurrent/reset/invalid outputs/commit/reload and protocol 2/3 metadata.
3. [x] Managed comma adapter: peer_policy + mac.prepare minimal changes only;
   reuse validation/approval/fallback. Test first approval, reconnect, onroad
   adoption/spec mutation, missing engine, V2/V3 selection and rollback preparation.
4. [x] Software end-to-end: separate import namespaces, current daemon IPC/parser/
   JoiningModel, deterministic CPU engine; test failures/stale/disconnect/timeout.
5. [x] Candidate patch/manifest and rollback: base and file SHA256, touched paths,
   patch SHA256; apply/reverse in disposable copy and confirm source restoration.
6. [x] Run complete applicable suites, fresh HEAD lookup, record PASS/FAIL/SKIP/
   BLOCKED and exact commands in CODEX_CONTINUATION.md; small commits and push
   only the authorized feature branch. Device-only work stays blocked at M0.

Execution is already authorized in the user request. No additional design approval
or installed-runtime action is inferred. Agents have disjoint file ownership;
the primary agent reviews and runs the combined integration suite before completion.

Completed software scope at code 0a474c31172a0da33d55acdec40b8b0a84867c40.
See CODEX_CONTINUATION.md for verified evidence and explicit blocked gates.
