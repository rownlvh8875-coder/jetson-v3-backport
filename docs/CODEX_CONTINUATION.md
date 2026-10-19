# Codex continuation — 2026-10-19

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
