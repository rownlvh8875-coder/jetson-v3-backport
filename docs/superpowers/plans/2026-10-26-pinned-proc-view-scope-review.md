# Pinned proc-view scope review implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` task by task. Independent reviewers assess proof and integration boundaries; root implements the offline model.

**Goal:** Test a namespace-file-independent evidence proposal without weakening or wiring the actual sampler.

**Architecture:** A pure, versioned record assessor checks mount/lease/self/credential relationships. All successful results are conditional and offline, with runtime/negative-witness/policy acceptance false. No acquisition adapter is implemented.

**Tech Stack:** Python standard library and existing pytest environment; no dependencies or device APIs.

**Spec:** `docs/superpowers/specs/2026-10-26-pinned-proc-view-scope-design.md`.

## Constraints

- Exact existing feature branch; protected refs and historical evidence unchanged.
- No actual comma/Jetson access, sampler repeat, source patch, storage, ticket or capture.
- Existing strict sampler and all deployment/runtime adapters remain byte-identical.
- No kernel-config inference from ENOENT, no namespace equality from numeric self IDs.
- No temporal-visibility or lifecycle acceptance from matching endpoints.

## Review focus

- A mount ID or self PID can match while the underlying ownership/view differs.
- Permission failure is not absence; closed leases and lazy-detached mounts reject.
- Every observation/provider must belong to the declared view; no absolute fallback.
- Parser ambiguities, bool-as-int, oversized values and backward clocks reject.
- Coherent fake evidence must never be reported as actual proof or readiness.

## Task 1 — pure record assessor

Files: create `tools/proc_view_scope_model.py` and `tests/test_proc_view_scope_model.py`.

Interface: `assess(record, baseline=None) -> dict`; no OS imports or side effects.

- [x] Write literal RED cases for coherent ENOENT records, missing lease evidence,
  permission-denied namespace, changed mount/owner, legacy absolute provider and
  unconditional denial of temporal/runtime acceptance.
- [x] Implement strict schema, field validation and baseline comparison; GREEN.
- [x] Add malformed/filter/submount/fork/rebind/clock/ABA regression cases; RED/GREEN.
- [x] Independent review; fix findings in this implementation, not the old sampler.

## Task 2 — evidence and publication

- [x] Run fresh new model suite plus relevant existing sampler61, disjoint once.
  Do not recount historical1313 as fresh; retain root/diagnostic/native blockers.
- [x] Hash-check old sampler, runtime adapters, patches and historical receipts.
- [x] Publish sanitized M19-C1.5D report/artifact and prepend-only continuation.
- [x] Prepare feature-branch commit/push handoff; final Git receipt verifies clean/equal and protected refs after publication.

## Outcome

135 fresh relevant PASS:74 new record-model fixtures +61 unchanged strict-sampler
fixtures. Earlier iterations and historical1374 are not added to this count.
The model remains OFFLINE_NOT_ADMISSIBLE in every path. Full scope equivalence,
acquisition, temporal visibility and runtime/policy readiness remain unproved.
No actual device work or acquisition adapter was implemented.
