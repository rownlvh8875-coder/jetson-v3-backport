# ProcView acquisition implementation plan

> For agentic workers: use superpowers:executing-plans inline. Root implements;
> independent reviewers audit acquisition and integration boundaries.

Goal: exercise actual FD-relative acquisition on local Linux without modifying
the strict sampler or wiring a device dispatcher.

Architecture: a native capability boundary authenticates opened FDs; ProcView
and generation handles own closed relative reads. Scope/mapping evidence stays
conditional and cannot authorize negative witnesses or operating policy.

Tech stack: Python standard library, ctypes, existing WSL pytest environment.

Spec: docs/superpowers/specs/2026-10-26-proc-view-acquisition-design.md

## Constraints

Feature branch only; no actual comma/Jetson access; no ticket/capture/runtime
changes. Preserve all historical bytes and old strict sampler. No dependency
installation, generic arbitrary-path API or fallback on missing statx mount ID.

## Task 1 — acquisition primitives and generation ownership

Create tools/pinned_proc_view.py and tests/test_pinned_proc_view.py.
Interfaces: ProcView context manager; enumerate(), probe(pid), generation(pid),
scope(); Generation context manager with identity() and metadata().

- [x] RED: real fixture read, no-follow traversal, unsupported/cross-mount native
  boundary, repeat enumeration, root drift/closed/fork/credentials, bounded reads.
- [x] Implement fd-relative acquisition and native capability validation; GREEN.
- [x] RED/GREEN: generation reuse/stale handle, metadata errors/parent brackets,
  exe-target distinction, snapshot evidence and mapped-child checks.

## Task 2 — review and publication

- [x] Exercise local real procfs, no operating process control or broad sampling.
- [x] Independent code review; fix findings with failing regression cases.
- [x] Run fresh new tests plus prior135 relevant fixtures once with unique counts.
- [x] Preserve old hashes; document unsupported actual capabilities and visibility
  assumptions; sanitized M19-C1.5E report/artifact; prepend continuation.
- [x] Prepare feature-only publication; final Git receipt verifies commit/push,
  CLEAN/equal and protected refs after publication.

Review focus: circular fdinfo bootstrap, repeated enumeration offsets, submount
crossings, generation/exec races, child provenance vs wait authority, remount ABA.

Outcome: 200 fresh unique relevant PASS =65 new acquisition +74 unchanged record
model +61 unchanged strict sampler. Earlier198 and historical1374 are not added.
Both final static reviews have no outstanding offline source finding. Native
reads succeed locally; the local full-scope endpoint profile refuses submounts.
Actual compatibility and integration, complete evidence stream, owned-pipe origin,
visibility/cadence/helper policy remain unproved. No actual device action.
