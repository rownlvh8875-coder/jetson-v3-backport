# M1.6 numerical acceptance investigation plan

> **For agentic workers:** Execute inline with superpowers:executing-plans and TDD. Independent read-only parser/provenance research supports the implementer; one fresh final review checks the complete branch.

**Goal:** Localize the exact M1.5 anomalies, compare independent and ORT-state teacher-forced BASE execution after full feature-history turnover, and issue an evidence-limited numerical/M2 decision.

**Architecture:** Add only a measurement harness, `tools/jetson_m16_acceptance.py`, reusing unchanged M1/M1.5 identity, parser, session, input generator and isolation gates. Export compact exact ORT references: driving output plus image/desire states, reconstruct the feature shift queue and prove byte identity against every actual ORT feature output. Run both TRT variants with the same nonstate frames and exact physical contracts, storing small raw driving outputs for offline source-bound analysis after closing CUDA. Keep historical and bounded sequences separate.

**Tech Stack:** Existing PC ORT1.31 CPU, existing Orin TRT10.3/CUDA12.6, NumPy, existing Python interpreters and live offroad guardian. No dependency installation.

**Spec:** User2026-10-23 M1.6 request; AGENTS.md; M1/M15/M2 reports and exact V3 ModelSpec. Detailed execution scope and final report fields come from that request.

## Global constraints

- Required feature branch only; freeze all adapter/production files and M1/M15 tools. Preserve main and old feature. Normal feature push is explicitly authorized.
- Exact original ONNX404a18cf/766354845, M1 plan8f831b5a/768580676, actual Nav parser45b38da9/constants5d597d28. Numerical target never follows moving upstream.
- No operating cache/selection/current/release/service/comma/Params changes, rebuild, USB inference/CAN/vehicle activity, package/workspace/swap/clock changes or optimization flags.
- All new device writes in an exclusive `m16` subtree of the existing private M1 development root. No output overwrite. No old evidence deletion.
- Fresh known-access read-only inventory, exact identity/storage gates and live offroad owned-worker guardian precede CUDA. Preserve full operating before/after evidence.
- Only the unchanged reviewed M15 private-file cache preparation may be used, against its exact existing allowlist; no new memory workaround or global/operating cache advice.
- Sequences D1 historical512 (same seed73/generator, OOD action_t retained and disclosed) and D2 bounded512 (action_t from the pinned upstream verifier's actual source range), never pool them.
- Teacher forcing supplies all three ORT states with exact dtype/shape and only validated UINT8-image→FP16 representation conversion. Validate complete outputs before any state publication.
- Artifacts contain metrics and public provenance only; no raw tensors/logs, private addresses/credentials or user path details. Real/synthetic/teacher evidence remain distinct.
- No PARITY_PASS without representative data and applicable approved semantic criteria. No failure threshold invented. Finite values alone cannot establish recurrent stability.

## Review focus

- V3 single-mode plan and direct three-head lead must not be mislabeled as legacy MDN hypotheses; time values must come from exact constants.
- Equal argmax can hide probability differences; a flip must include all logits, probabilities, top2 margins, neighbors and downstream-use semantics. Class7 has no named enum in actual schema.
- Full queue turnover is measured after128 frames; window slope/rolling statistics are descriptive, not universal bounds or approval thresholds.
- Compact state reconstruction must match actual ORT output byte-for-byte at every frame; no unverified state shortcut is allowed for teacher forcing.
- Same input/hash/source contracts and equal frame counts precede diagnostics; upstream heuristic truncation must never discard samples silently.

## Task1 — localization and diagnostic primitives

Files: new tool and `tests/test_jetson_m16_acceptance.py`.

- [x] Write/run failing CPU tests for exact worst index/value/profile, nonlinear horizon mapping, desire ranking/margins, direct lead head/field mapping, state replacement/conversion, feature shift proof, turnover checkpoints/slopes, input manifest/privacy/output collision guards.
- [x] Implement minimal pure numerical helpers using unchanged M15 metrics/parser. GREEN:17 new +25 M15 +8 frozen Nav adapter +5 wire =55. Initial command omitted the required candidate environment variable; all5 wire cases failed before execution, then passed with the documented environment. No adapter source changed.

## Task2 — exact references and guarded actual comparison

Interfaces: `export-ort --sequence historical|bounded --frames 512`; `measure-trt` consumes exact compact references, existing plan/base evidence/parser and a new output directory.

- [x] Revalidate actual comma HEAD/offroad flags and complete Jetson preservation/source/plan/parser identities before any CUDA. Exact M1 inventory digest and plan/source pins retained,9.068GB disk available; new private m16 subtree only. No scans.
- [ ] Export both PC ORT sequences; prove feature reconstruction against real outputs, exact input digests and manifest shape/hash/dtype/finite gates. Stage only reviewed code and references in new private paths.
- [ ] Run512 independent+512 teacher-forced TRT executions per sequence, with unchanged BASE session and live guardian. Strict complete-state/finite checks, no hidden warmup, no result mixing. Retain outputs privately; copy only small result archives to PC.
- [ ] If a real constraint blocks GPU, retain all independently possible source/localization/CPU analysis and report precise BLOCKED evidence; never imply hardware PASS.

## Task3 — offline semantic/causal analysis

- [ ] Localize historical frame45 plan and frame46 lead maxima to exact indices/time/value/scale/adjacent profile and actual direct-mode/head semantics; verify continuity with prior101 metrics.
- [ ] Analyze frame14 desire probabilities/logits/all rankings and neighboring10..18, plus frame14..20 plan/lead/action/desire_state/hidden differences. Base flip classification on actual margins and observed perturbation, with no acceptance cutoff.
- [ ] Produce per-sequence independent/teacher max/MAE/RMSE/p99 tables, actual-time structural near/mid/far plan regions, selected/direct lead and probability context.
- [ ] Analyze all requested checkpoints, hidden vs128-slot history, post-turnover slope/rolling max/p95/quarter changes and honest descriptive classification. Difference-of-differences is diagnostic, not causal linear decomposition.

## Task4 — representative sources and external diagnostics

- [ ] Scoped inventory only current and previously authorized project assets; use recorded inputs only with exact model-input/preprocessing provenance. Otherwise BLOCKED_REPRESENTATIVE_INPUT.
- [ ] Run actual pinned Zoompilot array diagnostic functions on the same complete paired driving outputs, recording correlations/tiny/quiet/small-value details separately from application approval.
- [ ] Run official replay only with valid aligned schema logs; otherwise NOT_RUN with source-backed exclusions/applicability. Do not promote scalar tests to model replay.

## Task5 — decision, preservation and publication

- [ ] Recheck complete operating preservation and actual comma state, close only own workers/access/monitor. Query upstreams again; keep numerical pins fixed.
- [ ] Write docs/M16_NUMERICAL_ACCEPTANCE_20261023.md and sanitized m16 artifacts with worst cases/turnover/teacher/reference/diagnostics/decision/blockers. Update continuation.
- [ ] Run new CPU suite and frozen adapter smoke; verify hashes/manifest/privacy/diff, obtain independent final review, commit/push only feature and verify clean remote equality/protected refs.

Execution ruling: user supplied the detailed ordered implementation and authorized standalone extended GPU measurement and same-branch publication. Earlier no-intermediate-question preference persists; no additional design/execution permission question is required. The existing requested feature checkout plus exclusive device/output copies provide isolation. Record limitations instead of inventing representative inputs or numerical approval.
