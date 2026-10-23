# M1.7 actual comma recorded driving parity plan

> **For agentic workers:** Execute inline with executing-plans and test-driven-development. A fresh final reviewer checks read-only boundaries, provenance, and result claims.

**Goal:** Prioritize actual comma recordings over cloud discovery and compare only reconstructible recorded V3 inputs on the unchanged original ONNX/M1 plan.

**Architecture:** Discover the storage root from actual pinned source, inventory read-only, select up to5 recent routes, hash/copy only selected log segments into ignored private PC storage. Inspect the actual camera/log/preprocessing contracts before creating a dataset. Reuse M16 ORT/TRT/parser tooling only when complete calibrated paired-camera frames and all scalar inputs can be deterministically reconstructed; otherwise publish a precise missing-source hold without substituting qcamera, driver camera, model outputs or synthetic tensors.

**Tech Stack:** Existing comma read-only shell/web terminal and untouched raw-download endpoint; existing PC interpreters/CapnProto/log tooling; frozen actual Nav366d6eae source and M16 tools. No dependency/device/package/service changes.

**Spec:** User2026-10-23 M1.7 actual comma representative-source request; AGENTS.md; M16 hold and exact identities.

## Global constraints

- Feature branch only, preserve main/old feature/user changes, no force/reset. Session start5bd9bcb1b10d63c35eb6b16bd35ae8ae4ce0626f matches remote, clean.
- Immediately before each device operation: actual `cat /data/params/d/IsOffroad`=1 and `cat /data/params/d/IsOnroad`=0. Otherwise stop device work.
- No comma writes, branch/source/process/manager/modeld/camera/service/Params changes; no route removal or modification. Use only fresh owned terminal sessions; disable shell history and Python bytecode.
- No USB P3 inference, CAN/vehicle controls, engine rebuild, model/cache publication, optimizations, new memory workaround or operating-service intervention.
- Exact ONNX404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4 and plan8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa. Numerical parser actual366d6eae stays pinned, adapter frozen.
- Recordings/raw logs/video/actual route names/timestamps/GPS/addresses stay ignored/private. Public artifact only anonymous IDs, counts, hashes, source-backed summaries/metrics and explicit blockers.
- No representative PARITY_PASS without sufficient genuine model inputs and approval provenance. No random substitute or combined synthetic/recorded means.

## Review focus

- qcamera is a reduced road recording, not interchangeable with full road/wide images; dcamera is driver-facing. Available file names alone do not prove model-input provenance.
- Source files must remain unchanged before/after read/copy; copies require exact size/SHA identity. Route inventory digest covers names/sizes/mtimes/counts, not unread file contents.
- Calibration/timestamps/traffic/desire pulse/action_t history must be recorded or source-reconstructed, never taken from current Params to impersonate historical values.
- Existing P2/Nav model outputs are telemetry, not outputs of the target V3 pair; classification evidence and numerical parity are distinct.
- Missing recordings/resource conditions cause NOT_RUN/BLOCKED, never fake ORT/TRT PASS/FAIL.

## Tasks

- [x] Read handoff/frozen targets; fresh upstream and remote checks. Actual offroad1/onroad0 and Nav366 verified; root derived from actual hw.py, then confirmed present.
- [x] Inventory88routes/1037segments/4403files, select5 recent candidate routes and one nonempty middle rlog each. No fcamera/ecamera anywhere in confirmed root.
- [x] Initial route stat/source/process snapshot;10 selected original log content hashes and5 copied rlogs/61448059bytes identity PASS. Existing raw GET source inspected; no transform/upload/cache endpoint used.
- [x] Actual schema read431355events/5rlogs,6000 road/wide metadata pairs, all image payloads empty. Recorded calibration/DMS/Params/source/desire metadata summarized privately/safely. Warp/scalar/recording source and qcamera526×330 read-only ffprobe audited. Not full-route or V3 parity.
- [x] Pure gate/privacy/motion/exclusive-output tests RED missing module→GREEN12. Fresh87PASS/0FAIL/0SKIP including75 frozen M16/M15/Nav smoke, no production/adapter changes.
- [x] Conditional comparison gate BLOCKED_RECORDED_INPUT_RECONSTRUCTION: representative V3sequences0/frames0. ORT/TRT/parser/recurrent comparison NOT_RUN, no synthetic/video substitution or plan/device access. All independently useful source/log/preservation work completed; PARITY_UNDETERMINED/M2NO.
- [x] Exact before/after route stat digest and selected content hashes, source/tracked-process identity unchanged.15 model files later before/after hashes identical. Offroad1/onroad0 and actual366 retained. Initial incomplete owned terminal cleanup verified exactly; other owned M17sessions0. No protected process terminated.
- [x] Final5upstreams unchanged; publication/hash/privacy/frozen-source checks PASS. Independent review approved after correcting historical dirty-source wording. Evidence/docs089e5e009da28cc5b0a7f428900efd88a100a6a4 normally pushed only to feature, remote-equal/clean/protected refs verified. Final handoff records the verification; no further device work.

Execution ruling: the user explicitly chose actual comma recordings and autonomous read-only exploration/copy plus isolated comparison. Existing dedicated feature and fresh private paths provide isolation. The detailed request and earlier no-extra-question preference waive redundant design/execution approval; actual device safety and missing-data gates remain mandatory.
