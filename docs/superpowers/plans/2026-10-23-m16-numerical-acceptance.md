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
- [x] Export both PC ORT sequences; prove feature reconstruction against real outputs, exact input digests and manifest shape/hash/dtype/finite gates. Historical/bounded512 complete; lossless compressed staging into fresh private paths verified. Partial earlier transfer preserved unused.
- [x] Execute guarded attempts separately: historical512 independent+512 teacher-forced TRT executions complete, all strict gates PASS. Bounded exact-plan deserialize OOM before frame0; zero bounded inference frames. Private results retained, all512 historical result archive hashes checked. The intended second1024 executions remain BLOCKED, not completed.
- [x] Resource constraint recorded without new workaround or retry: requested735338624bytes allocation after exact unchanged103-file preparation. Independent source/localization/CPU work completed. No numerical FAIL fabricated from OOM.

## Task3 — offline semantic/causal analysis

- [x] Localize historical frame45 plan/node32@10s and frame46 leadhead0/X/node5@10s, exact values/profiles and direct semantics. First101 ORT404arrays byte-match M15; TRT max/MAE/p99 match, two RMSE last-bit reduction deltas disclosed.
- [x] Frame14 logits/probabilities/all rankings, neighbors10..18 and outputs14..20 analyzed. NEAR_TIE_FLIP based on actual0.007589817/0.005421937 margins, no universal cutoff; all5 prediction flips persist teacher-forced, current desire differs conceptually.
- [x] Historical independent/teacher complete raw/parsed/physical-region tables and actual head probability context published. Bounded ORT-only action sensitivity separated; bounded TRT tables NOT_RUN/resource blocked.
- [x] All checkpoints and post-turnover statistics recorded. Rolling128 moments account for stored error, I/T hidden and desire_pred byte-identical all512. Small positive slopes/no approved stability criterion yield INCONCLUSIVE; no finite→stable or additive causal claim.

## Task4 — representative sources and external diagnostics

- [x] Authorized project inventory found no recorded input/reconstructible replay. BLOCKED_REPRESENTATIVE_INPUT,0sequences; no broad search/download or synthetic substitute.
- [x] Actual hash-pinned Zoompilot functions plus matching pure spec loaded under restored namespace: historical independent FAIL(planframe26 corr0.9988452612), teacher PASS. Quiet/small/columns/per-frame metrics retained separately from application approval.
- [x] Official replay NOT_RUN: no aligned recorded schema messages/camera/calibration provenance; selected-field tolerance excludes critical driving fields. No fake replay PASS.

## Task5 — decision, preservation and publication

- [x] Before/after preservation digest identical to M1/M15; source/plan/manifests unchanged; comma366/offroad1/onroad0,0ownedworkers, access/monitor closed. Five upstreams re-queried twice at end, moved Nav/WIP relevant diffs analyzed without adoption. Numerical pins fixed.
- [x] M16 report and3 sanitized artifacts published locally; continuation/README updated. Independent review required raw OOM console removal; structured failure+private excerpt hash retained and cleared. Decision PARITY_UNDETERMINED/M2NO.
- [x] Fresh targeted CPU75PASS/0FAIL/0SKIP (24new+25M15+26frozenNav); no prior708/reviewer repeats added. Independent final numerical/code/evidence review cleared. Frozen old hashes unchanged.
- [ ] Complete final metadata/privacy/diff check, commit/push only feature, verify clean remote equality and protected refs. Publication verification is recorded in the containing handoff commit and private execution ledger; no device work remains authorized here.

Execution ruling: user supplied the detailed ordered implementation and authorized standalone extended GPU measurement and same-branch publication. Earlier no-intermediate-question preference persists; no additional design/execution permission question is required. The existing requested feature checkout plus exclusive device/output copies provide isolation. Record limitations instead of inventing representative inputs or numerical approval.
