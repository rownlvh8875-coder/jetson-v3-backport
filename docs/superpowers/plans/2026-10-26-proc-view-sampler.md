# ProcView sampler integration implementation plan

> For agentic workers: superpowers:executing-plans; root implements and two
> independent reviewers audit the final source and receipts.

Goal: connect ProcView to a diagnostic collector with complete bounded private
semantic records and owned-pipe provenance, without changing strict defaults.

Architecture: optional fixed acquisition sink, canonical private journal, opt-in
provider/new collector, isolated direct-child protocol, public allowlist.
Tech stack: Python standard library + existing WSL pytest; no dependencies.
Spec: docs/superpowers/specs/2026-10-26-proc-view-sampler-design.md

## Tasks

1. Private journal: create tools/proc_view_journal.py and tests/test_proc_view_journal.py.
   Interfaces: PrivateJournal.append(kind,data), seal(summary), abort();
   verify_journal(path,anchor). RED/GREEN canonical chain, EOF/truncation, safe
   creation, finite budgets, short writes, fsync/close failure, byte encoding.
2. Acquisition stream/provider: extend tools/pinned_proc_view.py with optional
   fixed audit_sink; create tools/proc_view_sampler.py and integration tests.
   Interfaces: ProcViewReader.enumerate/probe/metadata; collect_acquisition.
   RED/GREEN bootstrap/close/error stream, sink poison, complete journal beyond
   tail retention, PID/start match, no legacy baseline or lifetime acceptance,
   scope/cadence/budget/overrun failure, closed public summary.
3. Owned pipe: create tools/proc_view_observer.py and tests/test_proc_view_observer.py.
   RED/GREEN canonical nonce/mapping/ACK/readiness, bounded drains, direct-child
   wait/signal guards, timeout/early-exit/invalid metadata and cleanup.
   Add tools/proc_view_capability.py with focused no-write/no-fork/no-window tests;
   this is a one-query handoff function, not a device driver.
4. Independent reviews, necessary fixes with RED/GREEN, fresh disjoint relevant
   regression, preserved old bytes except explicit acquisition extension and
   continuation prepend. Sanitized M19-C1.5F docs/artifact; feature commit/push,
   CLEAN/equal/protected refs. No actual device work.

Review focus: valid-prefix truncation, sink failure in finally, baseline coverage
vs cadence, PID reuse, inherited writers after fork, ownership loss, secret echo.

- [x] Journal
- [x] Stream/provider/collector/summary
- [x] Owned observer protocol
- [x] Final review, regression, preservation and publication

Completed 2026-10-27 Asia/Seoul with 290 unique relevant tests: 90 new plus
200 unchanged existing cases. Failed intermediate receipts are retained privately;
their counts are not added. Prior tracked/private evidence remains byte-preserved.
The deterministic source-pinned count-only payload is prepared, not dispatched.
Target use requires fresh OFF/source verification, its exact payload SHA and
`python -B` from process startup. Actual diagnostic-window, policy, redeployment,
Vehicle10 and M2 readiness are not established. Final Git equality/cleanliness
is checked after the feature-only push.
