# Lightweight process diagnosis implementation plan

> **For agentic workers:** Use `superpowers:executing-plans` task by task. Independent reviewers cover evidence and read-only boundaries; root implements.

**Goal:** Replace the slow broad metadata loop with measured fast generation scans and retained birth/exit evidence, without changing recorder or preservation policy.

**Architecture:** Direct `/proc` PID-list and stat probes form the fast loop. Sanitized metadata is cached outside the window and refreshed for new generations; existing reviewed metadata logic is injected rather than duplicated. A separately owned, forked receive-only observer avoids sharing the native messaging GIL with the fast loop. Lifetime bounds use one observer CLOCK_BOOTTIME domain and explicit retained absence/reuse probes, not kernel start-tick conversion.

**Tech stack:** Python standard library, pytest, Linux/POSIX fixtures; existing read-only transport/guards. No new dependencies.

**Spec:** `docs/M19C15B_READ_ONLY_PROCESS_DIAGNOSIS_20261026.md`, its continuation and the user's instruction to proceed with the next step. Existing requested interval0.25–0.5s,60s observation and fail-closed metadata/lifetime rules remain constraints.

## Constraints and approaches

- Work on the already approved clean feature checkout; no protected-ref changes.
- No actual source/policy patch, ticket, capture, restart, configuration change or Jetson access.
- Broad full-metadata polling failed cadence; retain its immutable evidence.
- Kernel tracing would require new privileges/configuration and is outside scope. Choose cheap generation scans plus bounded new-generation metadata. This is the implementer's choice within the approved next step, not a claimed user technology selection.
- A collection/lifetime bound never implies a safe-helper or deployment policy PASS.
- Preserve unknown/private command values as hashes, using the existing reviewed metadata provider.

## Review focus

- Complete enumeration versus partial/read-failed snapshots: no absence proof from incomplete evidence.
- Same PID with changed start ticks, exec changes and censored boundaries: never substitute a PID-only identity or sampled span for lifetime.
- Wrong timing domain, reversed clocks, visibility changes and scan overruns: retain explicit limits; no default PASS.
- Metadata storms: measure overruns; never hide time spent on new generations or promise achieved cadence from requested sleep.
- Fork/pipe ownership: fork before native imports/threads, close unused descriptors, drain IPC, reap only the owned child; no operating-process termination.

## Task 1 — generation tracker and direct reader

Files: create `tools/comma_process_sampler.py`, `tests/test_comma_process_sampler.py`.

Interfaces: `ProcReader.enumerate()`, `ProcReader.probe(pid)`, `GenerationTracker.poll(reader)`, `GenerationTracker.result()`, `collect(reader, duration=60, interval=.25, ...)`.

- [x] Write failing tests for exact preceding PID-list absence + direct exit, left/right censoring, partial enumeration, unreadable probes, PID reuse,10s boundary, changed visibility and backward clock.
- [x] Run RED; implement the smallest tracker supporting those literal fixtures; run GREEN.
- [x] Add real temporary-proc-file tests and deterministic collector tests proving metadata caching, measured cadence, observer timestamps and overrun reporting. Run RED/GREEN.
- [x] Independent source/evidence review; fix findings with regression cases.

## Task 2 — read-only integration and validation

Files: private staged runner excluded from Git; public stage report/artifact and prepend-only continuation.

- [x] Reuse reviewed guards, metadata provider and exact24c source profile; retain their source commitments.
- [x] Separate the receive-only observer using an owned child/pipe; test fork completion and failure without a device.
- [x] Run fresh1313 authoritative controls plus new unique tests; retain the static root-collection blocker without executing its live fetch/exit code. Document other blockers separately.
- [x] Only after tests/review, first actual commands remain OFF/ON cats. If connected and exact/OFF gates pass, perform one60s read-only verification; otherwise stop actual work and preserve the reason.
- [x] Independently verify achieved cadence, absence/exit evidence, source/index/storage/OFF and privacy. Do not reclassify the historical PID or proceed to installation/capture.
- [x] Commit/push handoff prepared for the specified feature branch only; final Git receipt verifies CLEAN/equal/protected refs after publishing.

## Actual failure and offline correction

The one device attempt failed before PID enumeration: the required scope lookup
returned ENOENT and all241 records were empty/incomplete. Empty-loop timing is not
process cadence or lifetime evidence. Source/index/storage and fresh OFF checks
passed separately. A bounded capability read identified /proc/self/ns/pid as
unavailable; no second sampling window or device repair was attempted.

The offline correction retains PID lists and exact field errors, retains failed
baseline evidence, stops before the fast window on unavailable prerequisites and
requires valid coverage as well as timer cadence. The scope gate remains closed.
Final61 sampler cases replace earlier54/60 runs in the unique count. The final
revision has not been run on the device; no deployment/ticket/capture follows.
