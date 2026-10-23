# Codex continuation — 2026-10-23

## Latest checkpoint: M1.5 software bridge PASS; numerical hold; M2 NOT authorized

Read in order: this section, `docs/M15_ORT_TRT_PARITY_20261023.md`,
`docs/M15_CARROT_NAV_PROTOCOL3_ADAPTER_20261023.md`,
`docs/M2_PARKED_USB_PLAN_20261023.md`, and both corresponding m15 artifacts.
Keep the historical M1/M0 checkpoints below. **DO_NOT_INSTALL** remains active.

- **101 actual paired recurrent frames completed**, original ORT1.31 CPU versus
  same exact M1 TRT10.3 plan on Orin. Every contract/finite gate passed;
  normalized nonstate input digests101/101 matched; each runtime used its own
  zero-initialized recurrent state. All15 actual output slices,22 actual Nav
  parser fields and30 plan mean/std physical channels were measured.
- **PARITY_UNDETERMINED; Ready for M2 parked USB: NO.** Whole/plan maximum
  absolute error4.25 (plan POSITION[0], frame45); lead maximum4.0 (frame46).
  Parsed desire_pred argmax differed once at frame14, desire_state never.
  Parser execution/shape/dtype/finite PASS; parser numerical approval
  NOT_AVAILABLE because no approved criteria and a classification disagreement.
  No model adoption or further actual GPU variant followed that observation.
- Feature-state max0.109375→0.296875, mean0.000062456874→0.007182852221,
  RMSE0.000963076→0.011133943 at frame100. Mean/max nondecreasing; image/desire
  state difference0 throughout. Actual ONNX Slice(state_feat_q,1)+current
  hidden_state[2066:18450] fills a128-slot queue. Cumulative hidden error
  moments reconstruct every measured state mean/max exactly and RMSE to5.21e-18.
  This explains stored-history growth; it does not establish infinite boundedness
  or plateau before full queue turnover, or isolate state causality downstream.
- Same M1 random-noise generator/seed73 retained, action_t=frame/20 reaches5s.
  It is OOD numerical stress, not vehicle input. Disagreement at frame14 must
  not be dismissed as solely a >1s horizon problem. Actual parser source was
  hash-pinned and unmodified; safe copies prevent parser mutation of references.
- Source precedents found: Jetlink V3 correlation.999/tiny/quiet heuristics,
  comma/Nav PC replay tolerance.3 with many driving fields excluded, NVIDIA
  application-specific accuracy guidance. None supplies approved V3 parsed/
  physical/recurrent error budgets. Proposed no-desire-flip criterion is labelled
  PROPOSED_THRESHOLD/NOT_APPROVED and is not satisfied by this stress sample.

### Current sources, commits and files

Session start local/remote feature HEAD:
`12c53ef8d9d4d64bc84dcc3c3a880fc8f12f960c`, clean correct branch.
All five upstream refs were freshly queried; observations remain:

| Source | Full SHA |
|---|---|
| Actual comma carrot-nav | `366d6eae9aa9962104391e1d997fe956dea8f64d` |
| Upstream carrot-nav | `366d6eae9aa9962104391e1d997fe956dea8f64d` |
| Latest carrot-wip | `813369b0c53bb9c997b7ffbe17fca90222a755b8` |
| carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| External review | `a890f6df1bd3eb0478754c68d8b5f92f15e8b722` |

Implementation commits: b0d721043f529340d308a0eaa2e0497294d35be2 semantic tool;
7a80a0090f89f1889cd43c8ba6a0b46511cb785b minimal Nav bridge;
5812a6587a1cd6211151cb10c82cd196e8214ccb explicit private file-cache preparation;
b5f24feef15decad312229148ad24b5e8e37ea69 exact wire and patch rollback tests.
Evidence/docs publication72d53b3c6c351f101639bab7665f52af6ca7dfd3 was normally
pushed to the same feature branch and verified remote-equal, clean, with main
and old feature refs unchanged. Final handoff commit contains this record; resolve containing
HEAD with `git rev-parse HEAD` / `git log -1 --format=%H -- docs/CODEX_CONTINUATION.md`.
Never hardcode these as permanent upstream branch pins.

New code: `tools/jetson_m15_semantic.py`, `adapters/carrot/nav.py`; new tests
`test_jetson_m15_semantic.py`, `test_carrot_nav_adapter.py`,
`test_carrot_nav_loopback.py`, `test_carrot_nav_wire.py`. Existing test peer only
gains the Nav camera prepare callback and first-frame diagnostic assertion.
New requested reports, m15 artifacts, M2 plan and
`patches/carrot-nav-protocol3-managed.patch`; rolling baseline/README/this handoff
updated. No large ONNX/plan/NPZ/private log/credential in Git.

### Nav software candidate and regression evidence

- Actual366d6eae base, comma-only **six files:3existing+3new**. Add explicit
  managed dispatch before existing Nav pin and preserve optional dtype maps.
  Empty maps stay omitted, keeping exact legacy V2/Nav dictionaries and N16
  spec hash63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71.
  Exact catalog V2/Nav/V3; unknown/missing/stale/mismatched model rejects.
  Existing offroad approval/reconnect and SHA/spec checks reused.
- model/link/parser/daemon/selection/contracts/client/warp/inputs/updater bytes
  untouched. Nav maps/navigation/five state pairs/P2 stateful_v2/N16 remain.
  Existing Nav default is exact Nav, not WIP's V2 default. Same-SHA live spec
  guard belongs paired reviewed host's prepared object/spec snapshot; HELLO is
  not authentication and comma SHA telemetry alone is not a spec attestation.
- Fresh expanded LF reference `.reference/m15-carrot-nav-366d6eae` includes
  navigation; candidate `.candidate/m15-carrot-nav-complete-366d6eae`. Earlier
  sparse-reference missing-navigation collection errors affected control and
  candidate equally; old refs/results preserved, new complete runs passed.
- Patch SHA bfeca1f882cbd12fe4130d17f9358b80472cdecc5a4e0e69af8a26289b535267.
  Manifest records base and all before/after hashes. Reverse/forward checks and
  exact restoration executed only on disposable copies, not actual devices.
- Target CPU suite executions **PASS708 / FAIL0 / SKIP0**, branch/configuration
  variants counted separately: rolling WIP288 +startup103 +local136 +Nav
  upstream170 +Nav managed11. Separate original Nav control170 also PASS and
  not added. Reviews repeat cases and are not added; final independent review
  reran38 cases with0 failures/0 skips and found no must-fix. local136=M1regression85+
  semantic/cache25+Nav adapter/rollback8+Nav loopback13+wire snapshots5.
- Nav upstream counts24NavRL+53App+11statefulprotocol+42projection+40mac match
  original control. Source metadata is exact; actual Nav model inference not run.
  Five actual-client TCP snapshots preserve V2 P2/P3 and Nav P2/full/N16/map-codec
  plus Nav P3 full bytes. Separate-process Nav comma/WIP host uses real client,
  daemon IPC, parser and JoiningModel, replacing only hardware seams. Faults
  close/reject and reach real small-fallback path; no USB or comma inference.
- One WIP-specific legacy V2-default test was explicitly deselected under Nav;
  a new exact Nav default test replaces it. A new stale-sequence test's incorrect
  <1s expectation was corrected to actual existing3s deadline and existing4s
  harness envelope, with no runtime timeout increase. Legacy bare pytest
  collector SystemExit limitation remains; use maintained explicit suites.

### Actual memory failure, correction and preservation

The first101-frame TRT job failed in engine deserialize with735338624-byte
CUDA OOM, zero frames; original logs/guardian exit1 preserved. A reviewed
default-OFF `--release-private-file-cache` option was added to the measurement
harness only. Its first preparation was rejected before CUDA for private
upload permissions0775/0664. Gates were retained: only owned103 reference/M1
source/plan files became0600, reference directory0700; byte hashes unchanged.
No operating permissions, caches or services were altered.

Same read-only pinned FD validates full SHA/size/owner/nlink/mode/device and then
advises DONTNEED; no content reread after final advice before CUDA. Exactly
2588748109 bytes of private-file cache were advised, not global drop_caches.
MemFree884748288→3496996864; Cached5188825088→2599829504; swap unchanged.
Without measured recovery>=the failed allocation size, the resource gate would
have blocked CUDA. One corrected actual retry completed101 frames in45.061s,
guardianPASS/workerexit3 (intentional no-approval result). No further retries,
rebuild, workspace/swap/package/clock changes. M1's older recovered64MB tactic
OOM remains in the history. All three inference optimization flags stayed0.

Existing M1 root/model/plan remain; new results below
`/run/carrot-data/jetson-v3-m1-20261023/m15/`:
`result-101-cache-prepared/report.json`, cache-preparation.json, three distinct
process/guard records, ORT101 reference/manifest, original/revised tool source
and parser copies. Do not overwrite or delete evidence. Revised executed tool
SHA76da628b54a2c1c6ba82b6086ca949185a13b25ce5ef800e848fc5257e816a58.

Before/after operating inventory matches M1 digest
ca2ac82d26a0eed7bc622f9887bfef9027216ed86c0b71a7382bf5bc6a50a6a1:
V2/Nav ONNX/plans, sidecars, timing/last-loaded files (8cache files), current,
five-release membership, service unit hash/ExecStart and dependency metadata
unchanged. Full release source-tree hash was not measured. Isolated M1 plan
still768580676 bytes/SHA8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa;
source still404a18cf/766354845. The private permission change is explicitly not
an engine-byte change. Final comma remainsNav366/offroad1/onroad0. Zero owned
workers; monitor/master/agent/relay closed and relay port closure checked.

### Commands, remaining gates and next first action

Fresh local command: existing WSL Python, explicit Nav reference/candidate and
separate WIP host roots in CARROT_NAV_REFERENCE_ROOT/CARROT_NAV_CANDIDATE_ROOT/
CARROT_HOST_CANDIDATE_ROOT; then:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_jetson_m1.py tests/test_jetson_m1_recurrent.py tests/test_jetson_m1_parity.py tests/test_jetson_m15_semantic.py tests/test_carrot_nav_adapter.py tests/test_carrot_nav_loopback.py tests/test_carrot_nav_wire.py
PYTHONDONTWRITEBYTECODE=1 "$PY" tools/check_latest_carrot_compat.py --work-dir .candidate/m15-carrot-wip-5812a65 --report .reports/m15-20261023/carrot-compat.json --update-baseline
```

Exact real ORT/TRT argv and source hashes are in the semantic report. Raw helper
commands, private connection details and logs remain ignored in
`.reports/m15-20261023`. No unlocked agent or live offroad controller remains.

PASS: software/strict invariants/preservation. Numerical approval BLOCKED;
PARITY_UNDETERMINED remains. Initial actual OOM and preparation refusal were
real failures retained in evidence, not hidden in the passing CPU count.
USB_REAL/COMMA_REAL inference/VEHICLE_PARKED/ROAD_TEST NOT_RUN by scope.

Next first action is authenticated read-only preflight, not an installation:
on confirmed Jetson shell run `readlink /opt/carrot-jetlink/current`,
`systemctl show carrot-jetlink.service --no-pager --property=ExecStart,ActiveState,SubState,FragmentPath,DropInPaths`,
and `sha256sum /run/carrot-data/jetson-v3-m1-20261023/build/cinque-v3.plan`;
recheck actual comma HEAD/road flags and all operating hashes against this
checkpoint. Query five upstreams again. Then resolve representative sequence,
desire disagreement and approved physical/recurrent criteria in an isolated
numerical stage. No automatic M2 activation. M2 plan phases0..9 requires a
separate scope and exclusive USB owner/restore authorization. Keep BASE then
DeviceState → DeviceState+InputFastpath → only-if-needed AIO after BASE gates.

---

## Previous checkpoint: M0.5 reconciled; actual isolated M1 build and BASE recurrence

Read these first: `docs/M05_CARROT_NAV_VS_WIP_20261023.md`,
`docs/M1_JETSON_V3_TRT10_BUILD_20261023.md`, and sanitized
`artifacts/m1_jetson_v3_20261023.json`. Preserve the older M0 and optimization
history below. The user explicitly authorized this isolated conditional M1
build; operating activation, USB/comma inference and vehicle work were excluded.

- **M0.5 PASS_RECOMMEND_A:** retain actual carrot-nav. Nav already has generic
  P3 client/dynamic IPC/approval/fallback and its own five-state-pair Nav model.
  A whole WIP switch changes239 files and removes Nav-specific behavior.
  The future small Nav port needs dtype-preserving ModelSpec serialization and
  explicit managed Jetson dispatch before its legacy exact Nav pin. No comma
  source change was made; full WIP server adapter correctly refuses Nav drift.
- **M1 TRT_BUILD_PASS:** actual Orin-sm87/TRT10.3.0 built exact Cinque V3 once.
  **BASE recurrent TRT_REAL_PASS:**10 smoke+1000 stress+2 reset/reload replay
  executions; every output exact physical shape/dtype/finite. Both replay tests
  exact. This is JETSON_REAL/TRT_REAL/SYNTHETIC_INPUT, not camera/vehicle input.
- **ORT↔TRT MEASURED_NO_ACCEPTANCE_THRESHOLD:**5 independent recurrent frames,
  actual original-model ORT1.31 CPU vs actual TRT. Outputs maximum absolute
  error0.625, mean of frame means0.008650338405; feature state max0.1484375,
  mean0.000197953225; image/desire state error0. Feature mean drift increases
  across these5 frames. Measurement intentionally exits3; no approved numerical
  tolerance exists, so no parity approval or deployment readiness claim.
- **DO_NOT_INSTALL.** Engine/sidecar remain below the isolated development root.
  USB/COMMA/VEHICLE/ROAD_TEST and optimization A/B NOT_RUN. Optional DeviceState,
  InputFastpath and AIO flags all0; no CUDA graph. No operational server.py,
  updater, service restart, model selection, Params/package/clock/remount change.

### Fresh source and development checkpoints

All five upstreams were queried at session start and after the GPU work;
unchanged. Re-query on every subsequent session; these are not permanent pins.

| Source | Full SHA |
|---|---|
| Actual comma carrot-nav / latest carrot-nav | `366d6eae9aa9962104391e1d997fe956dea8f64d` |
| Latest carrot-wip | `813369b0c53bb9c997b7ffbe17fca90222a755b8` |
| carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| External review | `a890f6df1bd3eb0478754c68d8b5f92f15e8b722` |
| Session-start actual local/remote feature HEAD | `5aa0bbac095686afd480627eddb627b1d011dc19` |
| M0.5 analysis commit | `29e613f7af448348a9c10b6e3e542068a20a64dc` |
| Build/recurrent code used on device | `e945e5665f8162910d5571231151607c64530764` |
| Parity implementation / frozen rolling checkpoint | `c64fdd3057b8d403975922a6fd3d4e776feeb701` |

Final evidence/continuation commits follow these checkpoints. Obtain the actual
current containing HEAD with `git rev-parse HEAD` and
`git log -1 --format=%H -- docs/CODEX_CONTINUATION.md`; the final response records
the resulting remote HEAD. Only feature/jetlink-multimodel-carrot is the target.
Evidence publication commit **f467036265dfdbf21f1a1abf38accb24e5828c02** was
normally pushed and verified equal to the remote feature HEAD, with a clean
tree, before this final handoff-only update. This update does not change any
executed implementation, source hash or device result.
Main remains2519ad0bdbf6e796fa590063fc90d4d6461b6b8d; old feature remains
26c9c06a5e51ff0e8d3a1e8575eece548e87f3b5.

### Device artifacts, isolation and preservation

Actual NVMe/L4T/TRT/CUDA baseline remains the authoritative M0 inventory below.
Read-only permissions/mount/disk checks chose a NEW exclusive directory:
`/run/carrot-data/jetson-v3-m1-20261023` (uid1000,0700). Existing NOPASSWD policy
was verified; privileged use was limited to creating/chowning this new directory.
No parent permission or mount changed. Minimum free-space gate6GiB passed;
12,482,035,712 bytes before,10,123,317,248 after. HOME/tmp/CUDA/XDG caches and
all new source/model/plan/report files are isolated there, bytecode disabled.

- Original: `models/big_driving_supercombo_v3.onnx`,766354845 bytes,
  SHA404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4.
  Official HF source pinned to model repository commit
  eed9e515dccd5aa9be969a2d6c57eb469174a97d; TLS/stream/full post-write hash PASS.
- Patched: `build/cinque-v3-patched.onnx`,766352690 bytes,
  SHA38f8664e65da3c8140674df0b56c8fc444be86ff41a1e54c13d9d9cc96273037.
  Raw and physical graph contract PASS; only verified V3 image queue boundary
  UINT8→FP16, full model identity and three state-pair gates retained.
- Plan: `build/cinque-v3.plan`,768580676 bytes,
  SHA8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa.
  Bound sidecar `build/cinque-v3.json`; builder149.5s, worker162.975s;
  workspace1536MiB, FP16, optimization3, no timing cache. The builder log contains
  one recovered64,704,384-byte tactic-allocation OOM (one warning/two error
  entries); TRT skipped it and produced a validated plan, exit0. No retry or
  gate relaxation. Memory/swap and exact log identities are in the artifact.
- Reports: `build/m1-build-result.json`, `build/guard-result.json`,
  `results/base-10-1000/report.json`, `results/ort-trt-measurement-v1/report.json`,
  plus per-frame timings, process logs, source/reference manifests. Keep them.
  All53 original staged source hashes and7 parity/reference hashes verified
  again afterward. Existing outputs deliberately refuse overwrite.
- Stress GPU mean22.145ms; host roundtrip mean46.849/p99 47.107/max47.968ms.
  Smoke host max93.131ms and2/10 above50ms were retained. These measured regions
  exclude USB/camera/production scheduling and are not end-to-end20Hz approval.
- Live read-only comma observations issued a30s remote monotonic lease, renewed
  about3s, checked by1s own-worker supervisor and builder callbacks. Loss/unsafe
  flags retire only this process group. No production provider was fabricated.
- Before/after full hashes of8 operating cache files, service unit/ExecStart,
  working directory, current link and membership of5 releases matched exactly.
  V2 ONNX/plan, Nav ONNX/plan, sidecars, last-loaded record and timing cache
  **UNCHANGED**. Dependency metadata also equal. No full source-tree attestation
  of packaged releases is implied. Canonical inventory digest both times:
  ca2ac82d26a0eed7bc622f9887bfef9027216ed86c0b71a7382bf5bc6a50a6a1.
- Final comma read-only check: carrot-nav366d6eae, IsOffroad1/IsOnroad0 unchanged.
  Params monitor, temporary SSH master/signing agent and single-use relay closed;
  relay port closure and zero owned M1 workers confirmed. Connection/credential
  details stay only in ignored `.reports/m05-m1-20261023`. No reusable unlocked
  agent or live controller remains; re-establish access/observations next session.

### Files, actual test commands and outcomes

New tools: `tools/jetson_m1.py`, `tools/jetson_m1_recurrent.py`,
`tools/jetson_m1_parity.py`; matching three tests. Reused current candidate
builder/patcher, existing build_trt_v3 validation/frame generation and lightweight
ONNX metadata. No model/link/parser/daemon rewrite or optimization integration.
New docs/evidence: M05 report+`artifacts/m05_nav_wip_20261023.json`, M1 report+
`artifacts/m1_jetson_v3_20261023.json`, execution plan. Updated rolling baseline
and this continuation. No ONNX/plan/NPZ/timing cache/raw private logs in Git.

Fresh commands (`PY`=existing WSL test interpreter):

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_jetson_m1.py tests/test_jetson_m1_recurrent.py tests/test_jetson_m1_parity.py tests/test_v3_build_verify.py
PYTHONDONTWRITEBYTECODE=1 "$PY" tools/check_latest_carrot_compat.py --work-dir .candidate/m1-carrot-20261023-frozen --report .reports/m05-m1-20261023/carrot-compat-frozen.json --update-baseline
PYTHONDONTWRITEBYTECODE=1 "$PY" .reports/m05-m1-20261023/check_startup_regression.py
```

- PASS: focused126 (new85 +existing builder41); rolling288; startup/priority/
  watchdog103. Distinct CPU cases **476**, FAIL0, SKIP0. Counts overlap as
  described; independent reviews61+24 overlap and are not added. CPU_FAKE/FIXTURE.
- PASS: actual GPU build,10+1000 BASE recurrence, reset/reload and preservation.
  Full device argv and measured metrics are recorded in the M1 report.
- MEASURED: actual five-frame ORT↔TRT; intentional exit3, not a numerical PASS.
- BLOCKED: numerical acceptance until approved per-tensor/slice/drift criteria.
- SKIP/NOT_RUN by scope: USB/COMMA/vehicle/road/end-to-end thermal/fallback/
  optional optimization A/B. Prior M0 privileged setup/clock queries were not
  rerun and are not silently promoted to PASS.
- Diagnostics retained: first online attempt refused concurrent source drift,
  no baseline advance; frozen rerun passed. First ORT invocation lacked candidate
  PYTHONPATH; corrected environment succeeded. Historical bare pytest aggregator
  aborts on test_backport.py top-level SystemExit; use explicit maintained suites.

### Next work / first device action

First device action remains authenticated read-only inventory: recheck branch,
offroad flags, current/service/cache hashes and development marker/plan identity
against this checkpoint. Do not rerun a builder into existing paths, activate
USB or restart anything merely because a plan exists. `tools/jetson_runtime_inventory.py`
or equivalent read-only commands remain the inventory entry point; keep raw
identifiers out of Git and retain the M0 decision to omit nvidia_smi if avoiding
GPU initialization. Re-query upstreams and analyze relevant drift first.

Then establish reviewed numerical acceptance criteria and validate a minimal
Nav-specific ModelSpec dtype/managed-selection adapter in a separate development
copy with V2/Nav/P2/P3 regressions. A separately scoped M2 must validate parked
USB/parser/local-small fallback and full latency/thermal behavior. Current plan
stays **DO_NOT_INSTALL**. Order remains BASE → DeviceState → DeviceState+
InputFastpath → only-if-needed AIO; vehicle behavior conclusions remain untested.

---

## Previous checkpoint: home devices, authenticated read-only M0

Read `docs/M0_READ_ONLY_CHECKPOINT_20261023.md` and sanitized
`artifacts/m0_20261023_summary.json` before continuing.

- Start development HEAD `254cd09106d6d01bc40010437416d227c389fd2b`, correct
  feature branch, initially clean. This session changes evidence/docs/baseline
  only. Resolve containing HEAD with `git rev-parse HEAD` and
  `git log -1 --format=%H -- docs/CODEX_CONTINUATION.md` after the docs commit.
- **SSH succeeded.** Existing SSD SSH key registration was correct: verbose SSH
  returned Server accepts key. PC key was encrypted; unattended signing failed.
  User unlocked it locally in a temporary WSL agent, key lifetime20 minutes.
  Earlier Jetson registration-failure diagnosis was corrected. No key enrollment
  or private-key copy/forwarding to either device. Comma's separate GitHub-key
  mismatch remains; its standard web terminal supplied a one-use TCP relay.
- First helper failed for missing WSL agent lifetime/TTY; both were fixed and
  user-only local passphrase entry succeeded. Never collect passphrases in chat
  or reports. See ignored local helpers for access details; prepare a fresh
  agent/unlock when needed. This session's agent keys were cleared/process
  stopped, and the temporary relay was confirmed closed before commit.
- **M0 core inventory PASS11, FAIL0; two privileged queries BLOCKED.** Original
  inventory ran over authenticated SSH on stdin, with only nvidia_smi omitted,
  Python bytecode/Git optional locks disabled. Read-only metadata/file-hash
  follow-ups ran. No build/load/inference/GPU initialization, operating-file,
  Params, power/clock, service restart or model-selection change.
- Actual comma: carrot-nav `366d6eae9aa9962104391e1d997fe956dea8f64d`, aarch64;
  road flags IsOffroad1/IsOnroad0. Actual installed branch differs from candidate.
- Actual Jetson: NVMe root p1 **ro**, p17 CARROTDATA mounted/bound rw at runtime;
  L4T36.4.7, kernel5.15.148-tegra, Ubuntu22.04.5, Python3.10.12;
  TRT package10.3.0.30-1+cuda12.5/Python metadata10.3.0, CUDA toolkit12.6/nvcc12.6.68;
  runtime venv cuda-python12.9.0/cuda-bindings12.9.9 (metadata only, no GPU test).
  MAXN_SUPER mode2 query succeeded. jetson_clocks --show requires root; no sudo.
  Provisioning result is root-only/setup partition unmounted; no mount performed.
- Actual service user jetlink, ExecStart venv Python + current/tools/jetlink/
  server.py --backend trt --transport usb --cache /opt/carrot-jetlink/cache
  --control-socket /run/carrot-jetlink/control.sock. Main/Wi-Fi/HUD/display active.
  current points to release54e706fa0573e91dc3b4a0d4f625b9d81a6b68cc; no .git,
  so this is a release ID, not full source attestation. Existing releases kept.
- V2 ONNX **exact SHA09d080f3/766040736 bytes verified**, preserved V2 plan hash
  matches imported-plan sidecar5d7a4a40. Nav ONNX01effc67/814591107 bytes and
  plan2c5c5a5e verified by CPU hashing; cache has no Cinque V3 among listed files.
  No engine loaded or inference/rollback acceptance claim. Metadata identity
  differs from target Cinque V3; do not adopt it as V3 or arbitrary replacement.
- Saved peer is Protocol2/Orin-sm87/TRT10.3/stateful_v2/Nav-u8/N16, engine_state
  none. Nav spec has five state pairs. USB topology shows CDC/vendor interfaces
  at5000M: enumeration only, no throughput/inference test. Existing ready/inactive
  state and single temperature sample are not thermal/performance acceptance.
- Latest carrot-wip **813369b0c53bb9c997b7ffbe17fca90222a755b8**;
  carrot-jetson d0dc96fa32410403dfb2fefff3e2909c11ec109b;
  zoompilot/jetlink d24328d849b0e5154b55f149dc18c5dfe8bd79cc.
  External review remains a890f6df1bd3eb0478754c68d8b5f92f15e8b722.
  Relevant diff from ba1869151 reviewed (5 added/11 modified); no adapter change.
- ONLINE rolling **PASS288/FAIL0/SKIP0**, baseline updated; additional isolated
  new startup/priority/watchdog tests **PASS103/FAIL0/SKIP0**, CPU_FAKE/FIXTURE.
  Heads freshly re-queried after M0 still match the tested sources. Distinct
  current CPU cases391. Historical469/15 hardware blockers below were
  not re-counted as fresh hardware results. TRT/USB inference/vehicle NOT_RUN.
- Raw addresses/device IDs/host keys/key paths are only in ignored local
  .reports/m0-20261023. Sanitize all evidence before Git. Current feature is the
  only push target; main and old feature branch remain preserved.

Next: reconcile actual carrot-nav + installed Nav/Protocol2 runtime with the
carrot-wip/Protocol3 candidate before choosing the host patch or any write.
Prepare later development in a separate writable copy; preserve current/cache/
V2/releases. Keep BASE V3 build → recurrence → USB protocol3 → latency/fallback
before DeviceState → DeviceState+InputFastpath → optional AIO. M0 discovery does
not authorize blind deployment of a patch for another branch. Privileged clock
and setup-result queries remain explicit BLOCKED; no optimization was enabled.

---

# Previous checkpoint — 2026-10-20

## Current task and checkpoint

This session reviews external inference optimizations, not a second V3 port.
Read `docs/JETSON_REVIEW_A890_ANALYSIS.md` for the complete comparison and
decisions. Preserve the historical 2026-10-19 evidence below.

Branch: `feature/jetlink-multimodel-carrot`.
Session start: `8bf5e1e3379a37575a3420ef074bd74e96f06ff0`, clean tree.
Verified implementation checkpoint:
`fcecd9c31f2e29c741f2e5bf161a6e318d63ed88`.
Final evidence/docs commits follow that code checkpoint; obtain the containing
development HEAD with `git rev-parse HEAD` and `git log -1 --format=%H -- docs/CODEX_CONTINUATION.md`.
Final response reports the resulting remote/development HEAD without a
self-referential commit hash inside its own document.

Ready for Jetson M0: **YES**. Installation/vehicle validation: **NO**.
No Jetson/USB connection, operating-runtime update, build, service restart,
Params modification, model/engine deletion or Wi-Fi port occurred.

## Fresh source observations

| Source | Full SHA |
|---|---|
| latest ajouatom/openpilot carrot-wip | `ba186915179816a9b0476cec52bf321e73d2d4b0` |
| ajouatom/carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| tjdgus200/openpilot codex/jetson-review | `a890f6df1bd3eb0478754c68d8b5f92f15e8b722` |
| external inference parent / excluded Wi-Fi | `de75c056712fbe19943892919f19960f3e6d565b` |
| external carrot-nav base | `74955c98560435895df28a8ae6f9af4d3d414d5f` |

The relevant carrot-wip blobs are unchanged from previously validated5032afca.
The branch did move; analysis and tests use the newly queried ba1869151.
Never treat either SHA as a permanent pin. External HEAD was also freshly
rechecked and remained a890f6df. All15 inference-commit files were reviewed;
before/after blobs and SHA256 are in `artifacts/jetson_review_a890_sources.json`.

## Completed work / commits / changed files

- `e640c4fc6483ce1ac2011e669e5fcee29cf6e528`: default-off DeviceState and
  exact InputFastpath candidates, provenance/license, CPU tests and composition.
- `861406d747e2222c8088d6a15545fc941b9d0086`: isolated bounded AIO controller,
  native ownership wrapper and CPU fake failure/framing tests.
- `fcecd9c31f2e29c741f2e5bf161a6e318d63ed88`: rolling optional-candidate
  generation/required tests, source freezing, LF reference checkout and CI path.
- Following evidence/docs commit: analysis, continuation, source provenance,
  refreshed portable baseline and separate standard/experimental manifests.

Ported/adapted files: `experimental/jetson_optimizations/{device_state,
device_adapter,direct_inputs,input_cast,fastpath_adapter,ffs_aio,
aio_writer_native}.py`, `input_cast.c`, package/provenance/license;
`tests/test_jetson_{device_state,input_fastpath,aio_candidate,
optimization_integration}.py` and device/input subprocess peers;
`adapters/carrot/integration.py`, checker/tests/workflow and README.

Not ported: external DeviceStateQueues replacement, next_state D2H suppression,
reply-event wrapper, navigation compact-map/spec/wire code, daemon scheduling,
benchmark service assumptions, production AIO transport hook, Wi-Fi/HUD/
credential/power changes. Current comma model.py/link.py/parser/daemon and wire
remain unchanged. Existing V2 assets/engine/branches are preserved.

DeviceState retains every output D2H and CPU exact shape/dtype/finite gate;
D2D follows successful host commit. It saves state H2D only. Reset/HELLO/close
drain pending work; partial failure invalidates until reload. Independent review
reproduced initial host-pointer inconsistency, mutable binding-name H2D omission
and allocation-owner map drift; all now fail closed, including explicit None
container changes. No finite/spec/shape/time budget was relaxed.

InputFastpath compiles/self-tests exact CPU byte→binary16 LUT once during
requested preparation; validates all bindings/source storage and aliases before
writing. It is restricted to canonical V3 scalars12, no navigation codec.
AIO remains isolated and explicitly disabled, retaining at most32 private32KiB
payloads until proven completion; unsafe ownership refuses cleanup/rebind.

## Classification / actual evidence

| Option | Result |
|---|---|
| DeviceState | READY_FOR_JETSON_AB — validation-preserving H2D-only variant |
| InputFastpath | READY_FOR_JETSON_AB — exact native CPU bits, no Orin timing |
| AIO | DEFER_UNTIL_LATENCY_PROBLEM — no generated transport hook |
| Direct Wi-Fi | OUT_OF_SCOPE |

All new tests are **CPU_FAKE / FIXTURE**. Actual native C CPU conversion is not
TRT_REAL or JETSON_REAL. The old ORT_REAL_MODEL evidence remains historical;
its numerical acceptance gates are not reinterpreted as passed optimizations.
External test/performance numbers are author records, not ours.

### Final verification / actual commands

WSL Ubuntu24.04 Python3.12.3, existing isolated
`~/.venvs/cinque-v3-stage3/bin/python` (`$PY`), NumPy/pytest/ONNX/cc.
No new device runtime/system package was installed.

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" tools/check_latest_carrot_compat.py --work-dir .candidate/rolling-a890-fcecd9c --report .reports/carrot-compat-a890-final.json --update-baseline

export CINQUE_PRODUCTION_ROOT="$PWD/.candidate/historical-lf2-jetson"
export CINQUE_COMMA_ROOT="$PWD/.candidate/historical-lf2-comma"
export CARROT_CANDIDATE_ROOT="$PWD/.candidate/a890-frozen-standard"
export CARROT_REFERENCE_ROOT="$PWD/.reference/carrot-wip-ba186-lf"
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest tests --ignore=tests/test_backport.py --ignore=tests/test_stateful_safety.py -q --junitxml=.reports/a890-all-final.xml

CARROT_CANDIDATE_ROOT="$PWD/.candidate/rolling-a890-fcecd9c/optimization-candidate" CARROT_TRT_DEVICE_STATE=0 CARROT_TRT_INPUT_FASTPATH=0 PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q tests/test_current_carrot_server.py
"$PY" tests/test_backport.py
"$PY" tests/test_stateful_safety.py
```

- Final ONLINE: **PASS288 / FAIL0 / SKIP0**, exit0, fresh three heads identical
  before/after. Portable baseline updated;813 relevant blobs,44 source hashes.
- All repository pytest: **PASS368 +6 subtests / FAIL0 / SKIP0**, exit0.
- Additional upstream101 → **unique pytest PASS469 / FAIL0 / SKIP0**.
- Existing regression **366 PASS**, new **103 PASS** (Device8 +Input58 +AIO30
  +composition3 +checker4). No repeats/internal assertion inflation.
- Optional candidate bothflagsOFF: **9 PASS**, existing current server suite.
- Independent final review: **123 PASS**, no remaining actionable findings;
  three reproduced Device binding flaws fixed, explicit None guarded.
- Standalone scripts: **76 assertion checks PASS**, optional ONNX sections
  **SKIP3**. Prior ORT acceptance **2 deferred/not rerun**, preserving the five
  separately tracked optional/deferred gates; no new ORT optimization claim.
- Final unresolved test **FAIL0**. Initial wrong-interpreter collection and RED
  characterization failures were resolved; ignored logs retain the evidence.
- New optimization real-device **BLOCKED7** (analysis table); prior15 open gates
  retained, overlaps not summed. No TRT_REAL/JETSON_REAL/USB_REAL/COMMA_REAL PASS.

Portable results: `artifacts/jetson_review_a890_validation.json`.
Standard patch remains SHA256
`04c7b08fd1fbcd21efddb103bdb0b336fe0ef92bffe0837b7fe2eb7344bffcf3`
with16 touched files; manifest now records ba1869151.
Experimental full patch SHA256
`c67cef9dac197ee8254dc928d72fdccdc30b840266ff3f9a78a7931cf8169776`,
20 touched files, is separate at
`patches/experimental-jetson-optimizations-a890.patch` with
`artifacts/experimental_jetson_optimizations_manifest.json`.
It starts from clean upstream; **do not stack on the standard patch**.
Hash verification and reverse/apply roundtrip passed in disposable copies.
Never delete V2 engines or overwrite an existing runtime to roll back.

### Push / CI confirmation

`ab796d3798523a9a9ebdc657553cbeb34e16d4fa` was normally pushed to the same
feature branch and the remote SHA matched. GitHub Actions
[run39350896683](https://github.com/rownlvh8875-coder/jetson-v3-backport/actions/runs/39350896683)
completed **success**: CPU dependency setup,24 checker tests, fresh latest
reference/candidate verification and evidence upload all succeeded. The final
documentation-only commit records this result and finalizes the checklist;
the44 validated implementation/helper/provenance source hashes remain unchanged.
The latest carrot-wip was queried again afterward and remained ba1869151.

Protected remote refs remained main
`2519ad0bdbf6e796fa590063fc90d4d6461b6b8d` and feature/cinque-v3-jetson
`26c9c06a5e51ff0e8d3a1e8575eece548e87f3b5`. No merge, force push or reset.
Manual/scheduled workflow registration on the default branch remains separately
blocked; feature push CI works and no main change was made.

## Next work / first Jetson command

Retain order: M0 → base V3 TRT10.3 build → base recurrent inference → USB P3 →
latency → BASE/DeviceState/DeviceState+InputFastpath A/B → AIO only if needed.
First actual device execution, from the directory containing the existing tool:

```sh
python3 tools/jetson_runtime_inventory.py --pretty
```

M0 is read only: inventory NVMe boot/L4T/kernel/TRT/CUDA/Python, power/clocks,
service names/ExecStart/runtime/cache/V2/current release/network. No build/load,
GPU initialization, restart, overwrite, Params changes or USB inference. Compare
inventory before choosing an isolated writable runtime and actual host changes.
Do not enable an optimization to hide a baseline failure.

Seven optimization-specific real-device gates remain BLOCKED (listed in the
analysis). The prior15 device/vehicle/CI-registration gates below remain open;
overlapping gates are not summed as additional independent test failures.

---

# Historical continuation — 2026-10-19

## Current checkpoint / HEAD

Offline software candidate: **PASS (CPU_FAKE / FIXTURE)**.
Actual ONNX CPU measurements completed; numerical acceptance deferred.
Ready for Jetson M0: **YES**. Ready for installation/vehicle use: **NO**.

Branch: `feature/jetlink-multimodel-carrot`. Initial workspace was empty;
cloned the authorized branch. No pre-existing changes were removed. No main or
existing-branch edits, force push, reset, engine deletion or device connection/
installation/restart/Params modification occurred.

Current verified code HEAD: `0a474c31172a0da33d55acdec40b8b0a84867c40`.
The following documentation/evidence commit contains this file and manifests.
Resolve its containing HEAD without a self-referential SHA:

```sh
git log -1 --format=%H -- docs/CODEX_CONTINUATION.md
git rev-parse HEAD
git status --short
```

Final response reports actual resulting development/remote HEAD. Use this file
and git log to continue; older PROJECT_STATE/V3_JETSON_PLAN are historical.

Push/CI verified: `4c07d018e468ccf2ba94a0c675aef8d5f372fd65` was normally
pushed to the authorized feature branch and remote SHA matched. GitHub Actions
[run 39208594966](https://github.com/rownlvh8875-coder/jetson-v3-backport/actions/runs/39208594966)
completed **success**, including CPU dependency setup, checker unit tests and
fresh latest-upstream compatibility checks on Ubuntu. The following commit only
records this observed CI result in documentation; code and manifests are unchanged.
Remote main remained `2519ad0bdbf6e796fa590063fc90d4d6461b6b8d` and the existing
feature/cinque-v3-jetson remained `26c9c06a5e51ff0e8d3a1e8575eece548e87f3b5`.

## Fresh upstream heads

Queried at session start and before/after final ONLINE tests, unchanged:

| Repository / branch | Full HEAD |
|---|---|
| ajouatom/openpilot carrot-wip | `5032afca77a96e31a077a5e9ac738d9ac08a99df` |
| ajouatom/carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |

These are observations, not a permanent pin. Next session must query again.
`artifacts/carrot_compat_baseline.json` holds the last online-validated heads,
813 relevant Git blobs and 26 implementation/test source hashes. Initial machine
baseline was absent, so all integration blobs were listed as added; historical
analysis heads were separately confirmed identical. Future runs compare blobs.

## Completed work / changed files / commits

- `71628eb2d23b9bf140025d1b6654dc2a8d1db9da`: rolling checker, focused tests,
  Actions, plan/ignore rules, integer-only capability version (bool rejected).
- `0a474c31172a0da33d55acdec40b8b0a84867c40`: source adapters and current
  integration tests, strengthened provenance/reference isolation and CI caveat.
- Following evidence/docs commit: this file, validation/rollback guide,
  portable online baseline, actual-model evidence, candidate patch/manifest.

Maintained files: `adapters/carrot/{integration,peer_policy,server}.py`, existing
`jetlink/multimodel_policy.py`, `tools/check_latest_carrot_compat.py`,
`.github/workflows/carrot-wip-compat.yml`, `tests/test_current_carrot_*.py`,
`tests/current_carrot_*.py`, `tests/test_latest_carrot_compat.py`.
All 16 generated upstream touched files and exact hashes are in the manifest.
Current model.py/link.py/parser/JetlinkClient are unchanged. Existing V3 assets,
V2 engines and branches are preserved. No runtime/device changes.

Implemented:

- Correct protocol 2/3 HELLO and explicit managed Jetson capability only on P3.
- Protocol 2 V2 preserved; protocol 3 V2 retains prev_feat on the server.
- Stateful warm/reset, full output/state existence/shape/dtype/finite gates,
  validated commit, invalid generation on failure/partial commit, reload zero.
  Valid P3 HELLO resets state without reload; invalid generations stay invalid.
- HELLO/resident generation/full-spec binding; managed wire requests cannot
  build/upload/select another engine. First approval offroad; exact reconnect
  allowed; missing selected engine defers to internal model without download.
- Actual daemon IPC/parser/JoiningModel fallback/reset/FAULT tested.
- Current TRT builder retained; exact V3 source/hash/size/spec/graph gate,
  persistent engine record, physical contract before allocation, recoverable
  publication rollback. Crash-atomic two-file commit is not claimed.
- Managed host control prepare/download/import/build defaults DENY without an
  injected trusted offroad callback returning exactly True and no attached P3
  session. Worker/publication/warm boundaries recheck. `--managed-jetson` enables
  the gate at startup; actual installed provider hookup awaits M0 inventory.
- Reviewed upstream source body guards fail closed on drift. Compatibility run
  freezes adapter/builder/test/helper sources and rejects required skips/xfails/
  empty collection/failures before updating the portable baseline.

## Actual tests / final PASS, FAIL, SKIP

Linux: WSL Ubuntu-24.04 Python 3.12.3, isolated
`~/.venvs/cinque-v3-stage3/bin/python` (`$PY` below), numpy/pytest/onnx.
Windows actual-model comparison: prior isolated Python 3.12.14 / ORT 1.31.0.
No system package upgrade or real CUDA/TensorRT execution.

| Actual command (repository root) | Final result | Class |
|---|---|---|
| `$PY tools/check_latest_carrot_compat.py --work-dir .candidate/rolling-verified-0a474c31172a --report .reports/carrot-compat-verified.json --update-baseline` | 189 PASS, 0 FAIL, 0 SKIP / exit 0; fresh heads before/after, baseline updated | CPU_FAKE / FIXTURE |
| `CINQUE_PRODUCTION_ROOT=$PWD/.candidate/historical-lf2-jetson CINQUE_COMMA_ROOT=$PWD/.candidate/historical-lf2-comma CARROT_CANDIDATE_ROOT=$PWD/.candidate/final-freeze PYTHONDONTWRITEBYTECODE=1 $PY -m pytest tests --ignore=tests/test_backport.py --ignore=tests/test_stateful_safety.py -q --junitxml=.reports/full-final.xml` | 265 PASS + 6 subtests PASS, 0 FAIL/SKIP / exit 0 | CPU_FAKE / FIXTURE; all repository pytest tests, including historical assets |
| `$PY tests/test_backport.py` | 36 assertion checks PASS, one optional real-model section SKIP / exit 0 | FIXTURE + live pointer metadata lookup |
| `$PY tests/test_stateful_safety.py` | 40 assertion checks PASS, two optional real-model sections SKIP / exit 0 | CPU_FAKE / FIXTURE |
| Windows isolated `$PY .reports/current_real_model.py` | actual-model 10 frames / all four outputs finite / every max+mean abs error 0 / exit **3** | ORT_REAL_MODEL; 2 acceptance gates SKIP/UNDETERMINED |
| independent reviewer: current-server + checker pytest | 29 PASS; concrete defects independently reproduced then verified fixed | CPU_FAKE / FIXTURE |
| `python -m compileall -q adapters tools/check_latest_carrot_compat.py tests/test_current_carrot_adapter.py tests/test_current_carrot_server.py tests/test_current_carrot_loopback.py tests/test_current_carrot_integration.py` | exit 0 | syntax only |

Online groups: current integration 38 + policy 9 + builder CPU 41 + upstream
phase 6 + upstream wire/model/cache 65 + upstream modeld IPC/warp 30 = 189.
Last 101 upstream cases are additional to repository pytest 265.
**Unique pytest total: PASS 366 / FAIL 0.** Separately, 76 standalone assertion
checks and 6 subtests passed. **SKIP 5** optional sections/acceptance gates.
**BLOCKED 15** gates below. Intermediate repeats are not added to PASS totals.
Internal current-server fault/contract/TRT fixture assertions are not counted twice.

Resolved failures, preserved in ignored local logs:

- Unadapted current P3 HELLO selected protocol 2. Missing stateful/approval/
  candidate APIs and initial tests failed before implementation (RED evidence).
- Bare pytest aborted while importing two existing standalone scripts calling
  sys.exit. Final invocation excludes them and runs both separately; no rewrite.
- Initial full run used previous **unpatched** historical references: 53 FAIL /
  23 ERROR. Created separate development copies at exact old C/J SHAs, applied
  old patches and verified all manifest hashes; final full suite passes.
- Windows Git native EOL caused disposable historical-copy hash failures.
  Fresh copies use core.autocrlf=false/core.eol=lf and Git blob bytes; no gate
  weakening and no existing directory modification.
- Review found missing/renamed new_img allocating 20 buffers; fixed, independent
  reproduction confirms zero allocations on both invalid descriptors.
- Review found offroad loss during warm still publishing ready; fixed, now job
  fails, loaded stays None, candidate engine closes. Added HELLO-without-RESET
  regression, complete helper provenance and clean-reference CI environment.

## Actual ONNX (ORT_REAL_MODEL)

Reused original in prior 2026-10-11 workspace read only; whole-file identity
checked before/after. No model downloaded, overwritten or committed.

- Original: 766354845 bytes,
  `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`.
- Current patched: 766352690 bytes,
  `38f8664e65da3c8140674df0b56c8fc444be86ff41a1e54c13d9d9cc96273037`.
- Executed actual generated current onnx_patch.py, SHA
  `a8f0b9165e67d8bcbd2d4b72099ef5ed240d51b42310fa122831a7ca954952f6`.
  Same bytes in final candidate after session-only review fixes.
- CPUExecutionProvider only; seed 73; recurrent and same-state each 5 frames;
  outputs + next_state_img/desire/feat finite, every max/mean abs error 0.
- No new tolerance basis selected. Acceptance UNDETERMINED/exit 3, not TRT_REAL
  or JETSON_REAL PASS. Portable evidence:
  `artifacts/current_carrot_real_model_evidence.json`.

Exact reproduction recipe and boundaries are in
`docs/CURRENT_CARROT_VALIDATION_20261019.md`.

## Candidate / manifest / rollback

- Base carrot-wip: `5032afca77a96e31a077a5e9ac738d9ac08a99df`.
- Patch: `patches/current-carrot-multimodel.patch`.
- Patch SHA256:
  `04c7b08fd1fbcd21efddb103bdb0b336fe0ef92bffe0837b7fe2eb7344bffcf3`.
- Manifest: `artifacts/current_carrot_candidate_manifest.json`, all 16 touched
  files before/after SHA256, upstream/code heads and software evidence.
- Real reverse/apply test checked every before/after hash in a disposable copy.
  Added files disappear on reverse. V2 engines/cache are never deleted.
- Fixed patch is one candidate; rolling source adapters/tests are maintained.
  Do not layer historical protocol-2 V3 patches over it.

Ignored reports retain exact stdout/JUnit/commands; committed artifacts contain
no private absolute paths/addresses/keys. Continuation+manifests support a fresh
session without ignored references or candidates.

## BLOCKED gates (15)

Real-device entries are **BLOCKED: JETSON_REAL REQUIRED**, with extra labels
where applicable; no fake PASS:

1. Actual TensorRT 10.3 build/cache reload/ORT↔TRT parity (TRT_REAL).
2. Actual CUDA pinned memory.
3. Actual CUDA graph/capture cleanup.
4. Actual Orin GPU timing / sustained 20 Hz.
5. Actual C4↔Jetson USB 3/re-enumeration/buffering (USB_REAL).
6. Actual Jetson service installation.
7. Actual systemd restart/recovery.
8. Actual NVMe/runtime/cache/release and trusted offroad provider hookup (M0).
9. Actual power/thermal/throttle.
10. Actual comma modelExecutionTime.
11. Actual stop→restart steering behavior.
12. Actual comma camera/parser/fallback/commIssue path (COMMA_REAL).
13. Integrated stationary vehicle validation (VEHICLE_PARKED).
14. Road validation (ROAD_TEST; not authorized/attempted).
15. GitHub manual/daily trigger activation: default-branch registration required;
    **repository administration decision**, not hardware. Main remains untouched.
    Feature push CI completed successfully in the linked run above.

Existing Protocol 3 has no authenticated connection epoch for artificially
replayed identical sequence/frame tuples. Tests reject stale differing tuples
and exercise actual ordering; stronger anti-replay protection is not claimed.
Physical buffered reconnect behavior remains USB_REAL verification.

## Next work / Jetson first execution

Every new session: verify branch/dirty tree, read specified project documents and
this file, query three fresh upstream heads and inspect relevant diff first.
Do not reimplement completed dynamic client/parser/approval/fallback support.

On the Jetson, from a directory where this tool is already available, first run:

```sh
python3 tools/jetson_runtime_inventory.py --pretty
```

M0 reads NVMe boot/L4T/kernel/TRT/CUDA/Python/nvpmodel/clocks/services/ExecStart/
runtime/cache/V2 engine/current release/network. No build/restart/overwrite/
Params changes/USB inference. Compare actual inventory, then select a writable
development copy and trusted offroad-provider source. Preserve V2, test actual
TRT state/parity/latency, then USB/comma stationary fallback and V2↔V3.
Default-branch CI registration requires a separate allowed repository decision;
no automatic merge or main change was performed.
