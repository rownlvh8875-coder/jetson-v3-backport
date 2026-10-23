# M1: isolated Cinque V3 TensorRT 10.3 build and BASE recurrence

Date: 2026-10-23. **TRT_BUILD_PASS / TRT_REAL_PASS / DO_NOT_INSTALL.**

The exact Cinque V3 model built on the actual Orin Nano Super, then completed
10 smoke frames and 1,000 stress frames with every output shape, dtype and
finite gate enabled. Reset and unload/reload reproduced the first frame exactly.
The engine remains in a private development directory. No operating cache,
release, service, comma checkout, Params or model selection was changed.

Five independent recurrent ORT CPU/TRT frames were also compared. This is
**MEASURED_NO_ACCEPTANCE_THRESHOLD**, not numerical parity approval. USB,
comma inference, vehicle validation and optimization A/B were **NOT_RUN**.

Machine-readable sanitized evidence: `artifacts/m1_jetson_v3_20261023.json`.
Raw logs, SSH access details, reference arrays and private addresses remain in
ignored local reports or the device development directory; none are in Git.

## Source and strategy

M0.5 completed first: **PASS_RECOMMEND_A**. Retain actual carrot-nav; prepare
its small managed Jetson/dtype port separately rather than switching the whole
comma checkout. See `docs/M05_CARROT_NAV_VS_WIP_20261023.md` and its full diff
inventory. Nav already contains generic protocol-3 client support and five-pair
Nav recurrence; it is not Cinque V3. Its legacy managed-selection/dtype seams
still need a separately tested adapter.

| Source | Full SHA |
|---|---|
| Actual comma and latest carrot-nav | `366d6eae9aa9962104391e1d997fe956dea8f64d` |
| Latest carrot-wip | `813369b0c53bb9c997b7ffbe17fca90222a755b8` |
| carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| External review | `a890f6df1bd3eb0478754c68d8b5f92f15e8b722` |
| Session start / previous remote feature | `5aa0bbac095686afd480627eddb627b1d011dc19` |
| M0.5 analysis commit | `29e613f7af448348a9c10b6e3e542068a20a64dc` |
| Guarded build/recurrence implementation | `e945e5665f8162910d5571231151607c64530764` |
| ORT/TRT measurement and frozen rolling checkpoint | `c64fdd3057b8d403975922a6fd3d4e776feeb701` |

All five upstream refs were queried at the start and after the device work;
they did not move. The final online checker independently checked its three
upstreams before/after verification. These are observed snapshots, not
permanent branch pins. Resolve the final documentation-containing HEAD with
`git rev-parse HEAD`; a document cannot contain its own final commit SHA.

The device received the **standard WIP-derived candidate**, not the optional
optimization candidate. Source manifest hashes verified all 53 staged files
before and after GPU work. The separate parity tool/reference manifest verified
another seven files. Existing server entrypoints were never launched: their
updater, service, cache-pruning and migration behavior is outside isolated M1.

## Isolation, storage and offroad gates

Read-only inventory confirmed NVMe root `/dev/nvme0n1p1` remains read-only.
The writable CARROTDATA partition is `/dev/nvme0n1p17`; its runtime subtree is
bound at `/opt/carrot-jetlink`. The normal account cannot write the parent.
The home overlay had only about 285 MB available and was unsuitable.

After M0.5, existing verified NOPASSWD authorization was used only to create
one new exclusive directory and give the development account ownership:

`/run/carrot-data/jetson-v3-m1-20261023` — uid1000, mode0700.

No parent permission or mount changed. Root/path guards reject symlinks,
operating bind aliases, parent overlap and existing outputs. A private marker
binds the canonical root, owner, schema and exact model identity. All source,
ONNX, plan, reports, HOME, temporary, XDG and CUDA cache writes stay below this
directory. Python bytecode was disabled before imports, including runtime venv
imports. Installed packages were reused without modification.

The conservative free-space gate is **6 GiB**: original ONNX, saved patched
ONNX, builder's temporary patched copy, plan, temporary files and reserve.
Before staging: **12,482,035,712 bytes available**. Before the builder and at
authorization checkpoints the same gate was enforced. Final available space:
**10,123,317,248 bytes**. No original model or cache file was removed.

Comma's existing terminal supplied a dedicated read-only Params monitor:
IsOffroad1/IsOnroad0 observations refreshed a development-only lease about every
three seconds. The Jetson monotonic lease expires after30 seconds. Its parent
supervisor checks every second and retires only its own worker process group
if the observation becomes unsafe, stale or unavailable. Builder authorization
also checks the lease and storage. SIGTERM/SIGHUP and creation-time interruption
were CPU-tested before GPU execution. This lease guards this explicitly
authorized standalone M1 work; it is not a deployed production approval provider.

All three optional flags were forced to0:
`CARROT_TRT_DEVICE_STATE`, `CARROT_TRT_INPUT_FASTPATH`, `CARROT_JETLINK_AIO_WRITE`.
No CUDA graph capture was used. Temporary SSH master, signing agent, relay and
Params monitor were closed afterward; the known single-use relay port was
confirmed closed. Zero owned M1 GPU workers remained.

## Exact model and graph contract

The documented official source is
[commaai/openpilot_driving_models](https://huggingface.co/commaai/openpilot_driving_models/tree/eed9e515dccd5aa9be969a2d6c57eb469174a97d),
repository commit `eed9e515dccd5aa9be969a2d6c57eb469174a97d`, model path
`f78ed37d-afad-4dbc-8050-40ea885eedde/12864/big_driving_supercombo.onnx`.
PC and Jetson source metadata agreed before acquisition. The download used
this immutable commit with TLS verification, bounded byte count, streaming SHA
and an independent post-write full hash. Download time:497.595s.

| Artifact | Bytes | SHA256 |
|---|---:|---|
| Original V3 | 766354845 | `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4` |
| Saved patched ONNX | 766352690 | `38f8664e65da3c8140674df0b56c8fc444be86ff41a1e54c13d9d9cc96273037` |
| TensorRT plan | 768580676 | `8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa` |

`artifacts/cinque_v3.json` matched exact source identity, checkpoint, input and
output names/shapes/dtypes, output slices and three state pairs. The current
candidate's V3-specific patch checks the actual graph image paths and Cast
targets, retypes `new_img`, `state_img_q`, `next_state_img_q` to FP16 and keeps
the downstream vision Cast. It does not rewrite arbitrary UINT8 tensors.
Scalar/desire/feature and driving tensors remain float32. Raw ONNX and physical
TRT contracts were each validated, including all static dimensions.

The saved patch SHA matched the patch recorded by the actual parser-bound build.
Build record digest:
`9102f1a74c2b046d09d55bbd28350e69b1c8ae0f86f32e1a13c08d4739e20ae4`.

## Actual build evidence

Environment: Orin-sm87, L4T36.4.7/kernel5.15.148-tegra, Ubuntu22.04.5,
Python3.10.12, TRT package10.3.0.30-1+cuda12.5/Python10.3.0,
CUDA toolkit12.6/nvcc12.6.68, existing MAXN_SUPER mode2.
No JetPack/TRT/CUDA install, power or clock change occurred.

The guarded harness calls the standard candidate's
`jetlink.server.backends.trt.build.build_engine` directly. It preserves the
current builder, V3 patch and build-record gates; it does not use the operating
TrtBackend constructor or cache. Existing `build_trt_v3.py`/`onnx_meta_light.py`
validation is reused by the harness and recurrent probe.

| Item | Result |
|---|---|
| TRT_REAL_PRECHECK | PASS: TRT10.3.0, actual Orin CC8.7, builder/network/parser created |
| Source/raw/physical contract | PASS |
| Parse/build | Completed; valid serialized plan and bound sidecar produced |
| FP16 / optimization level | true /3 |
| Workspace | 1536 MiB =1610612736 bytes |
| Timing cache | None; cold build; operating timing cache never opened |
| Builder elapsed | 149.5s, including its patch/parse/build sequence |
| Entire guarded worker / supervisor elapsed | 162.975s /165.270s |
| Worker exit / guardian | 0 /PASS |
| Available memory before / after worker | 5438328832 /3592892416 bytes |
| Free swap before / after worker | 3995000832 /2916278272 bytes |

Memory after is sampled inside the worker before process cleanup, not peak
build memory. The builder used swap. Its complete4,137,298-byte log is retained
privately with SHA `a7936539d09039d7ad063ec3204c8b41e50babfa15783a40d90801915f813b99`.

**The log is not error-free.** It contains one GPU allocation warning and two
TRT error entries: a64,704,384-byte allocation failed with CUDA out-of-memory,
then TRT explicitly skipped that tactic. Tactic selection recovered and the
single build attempt finished with exit0 and a validated plan. There was no
retry, workspace/package upgrade or gate relaxation. No fatal parser failure
occurred. The sanitized exact entries and counts are in the JSON artifact.
This recoverable build event does not imply stress inference was OOM-free
under all operating workloads; service contention and thermal acceptance remain
separate future checks.

## BASE recurrent results

Classification: **TRT_REAL / JETSON_REAL / SYNTHETIC_INPUT**. Deterministic
synthetic frames use seed73, not camera or vehicle inputs. The standalone process
uses actual CUDA pinned buffers and execute_async_v3: all state inputs H2D,
execution, all outputs D2H, synchronization, complete shape/dtype/finite checks,
then atomic next-state publication. It uses no daemon, USB, graph, device-owned
state feedback or fast input path.

- Smoke10 frames: PASS.
- Reset to all-zero state and repeat frame0: exact output replay PASS.
- Stress1000 frames after reset: PASS; every driving and next-state tensor
  retained exact physical shape/dtype and finite values.
- Close/unload, fresh generation, zero-state frame0: exact replay PASS.
- Total1012 actual engine executions, including the two replay checks.
- Parent guardian PASS, worker exit0; process completed in55.073s.

| Timed region | Smoke mean / p99 / max ms | Stress mean / p99 / max ms |
|---|---|---|
| GPU execute, CUDA events | 25.653 /54.405 /57.594 | 22.145 /22.226 /22.263 |
| Completed H2D + execute + D2H | 28.557 /60.292 /63.811 | 24.680 /24.795 /24.867 |
| Host roundtrip including generation/validation/feedback | 53.226 /89.467 /93.131 | 46.849 /47.107 /47.968 |

Host roundtrips over50ms: smoke2/10, stress0/1000. These are measurements, not
an end-to-end20Hz acceptance gate. Cold-start tails are retained; no warmup
frames were silently discarded. The probe has no camera warp, USB, comma
parser, production scheduling or thermal endurance. Stress sampled RSS maximum
1,328,492,544 bytes, sampled available-memory minimum4,720,021,504 bytes;
process reported high-water1,785,597,952 bytes. Sampling is not GPU peak telemetry.

## ORT versus TRT measurement

The PC's already-installed ORT1.31.0 CPUExecutionProvider/Python3.12.14 was used
with the exact original model; no package was installed on Jetson. Five raw
named-output NPZ files and their manifest were hash/shape/dtype/finite checked
before GPU import and rechecked while consuming. Both sides used the same
seed/frame generator bytes and their **own** recurrent states, starting at zero.
ORT state was never fed into TRT. UINT8 image-state values and the patched FP16
representation were compared numerically; all values0..255 are exactly
representable in FP16.

| Tensor | Max absolute error over5 frames | Mean of frame mean absolute errors | Last max minus first max |
|---|---:|---:|---:|
| outputs | 0.625 | 0.008650338405 | 0 |
| next_state_feat_q | 0.1484375 | 0.000197953225 | 0.0390625 |
| next_state_img_q | 0 | 0 | 0 |
| next_state_desire_q | 0 | 0 | 0 |

Feature-state mean absolute error increased from0.000062456874 on frame0 to
0.000335477549 on frame4. Per-frame max/mean and drift metrics for all tensors
are retained in the artifact. Five frames do not establish long-run numerical
parity. No established per-tensor/driving-slice/drift tolerance was found for
this build, so the measurement deliberately returned **exit3**,
`MEASURED_NO_ACCEPTANCE`, acceptance UNDETERMINED. This is neither a failed
execution nor a numerical PASS. Establish approval criteria before installing
or extending a parity acceptance claim.

## Fresh software checks and diagnostics

| Scope | PASS | FAIL | SKIP | Evidence |
|---|---:|---:|---:|---|
| Online rolling seven required suites | 288 | 0 | 0 | CPU_FAKE / FIXTURE |
| Current startup/USB-priority/write-watchdog suites | 103 | 0 | 0 | CPU_FAKE / FIXTURE |
| New M1 guard / recurrent / parity tests | 26+35+24=85 | 0 | 0 | CPU_FAKE / FIXTURE |
| Focused command including existing builder tests | 126 | 0 | 0 | Contains41 tests already counted in rolling |

Distinct current CPU cases: **476**, not288+103+126. Hardware frame counts are
not pytest case counts. The final source-frozen online report updated the
portable baseline at implementation c64fdd3; none of these CPU counts is
promoted to USB/TRT/vehicle evidence.

Initial diagnostic attempts are retained: the first online run refused a
mid-verification test-source change and did not advance its baseline; the
complete frozen rerun passed. The first ORT command lacked the candidate
PYTHONPATH; correcting that environment yielded real ORT outputs without a
gate change. Bare `pytest` collection aborts in historical `test_backport.py`'s
top-level SystemExit; acceptance uses the maintained explicit suites, not that
invalid aggregator. Independent prebuild and parity reviews checked the code
and reproduced61 and24 overlapping CPU cases; their counts are not added again.

Actual commands, from repository root (`PY` is the existing WSL test Python):

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_jetson_m1.py tests/test_jetson_m1_recurrent.py tests/test_jetson_m1_parity.py tests/test_v3_build_verify.py
PYTHONDONTWRITEBYTECODE=1 "$PY" tools/check_latest_carrot_compat.py --work-dir .candidate/m1-carrot-20261023-frozen --report .reports/m05-m1-20261023/carrot-compat-frozen.json --update-baseline
PYTHONDONTWRITEBYTECODE=1 "$PY" .reports/m05-m1-20261023/check_startup_regression.py
```

The last local helper uses the checker's isolated execute_pytest_suite harness
on `test_connection_startup.py`, `test_usb_priority.py`, `test_write_watchdog.py`
from the generated current candidate. It does not access USB hardware.

Reviewed device worker argv below were executed under `jetson_m1.run_guarded`
with the live offroad controller; they are records, not instructions to rerun
against colliding output files. Define `D=/run/carrot-data/jetson-v3-m1-20261023`,
`J=/opt/carrot-jetlink/venv/bin/python`. All launches used Python-B,
PYTHONDONTWRITEBYTECODE1, PYTHONPATH `$D/candidate/third_party/jetlink`, and the
three optimization flags0. No installed server.py was launched.

```sh
"$J" -B "$D/repo/tools/jetson_m1.py" --development-root "$D" --onnx "$D/models/big_driving_supercombo_v3.onnx" --spec "$D/repo/artifacts/cinque_v3.json" --out "$D/build/cinque-v3.plan" --workspace-mib 1536 --offroad-lease "$D/offroad-lease.json"
"$J" -B "$D/repo/tools/jetson_m1_recurrent.py" --development-root "$D" --engine "$D/build/cinque-v3.plan" --onnx "$D/models/big_driving_supercombo_v3.onnx" --spec "$D/repo/artifacts/cinque_v3.json" --out-dir "$D/results/base-10-1000" --per-frame
"$J" -B "$D/repo/tools/jetson_m1_parity.py" measure-trt --development-root "$D" --engine "$D/build/cinque-v3.plan" --spec "$D/repo/artifacts/cinque_v3.json" --reference-dir "$D/ort-reference-v1" --base-report "$D/results/base-10-1000/report.json" --out-dir "$D/results/ort-trt-measurement-v1"
```

The ORT exporter command used the existing PC ORT Python, candidate PYTHONPATH,
exact original ONNX and `tools/jetson_m1_parity.py export-ort --onnx ORIGINAL
--spec artifacts/cinque_v3.json --out-dir .reports/m05-m1-20261023/ort-reference-v1`.
Personal interpreter/key paths are intentionally omitted. Existing output
directories/plan names must not be reused for future attempts.

## Preservation and handoff

Authenticated read-only before/after inventories fully hashed all8 regular
operating cache files with inode/size/mtime stability checks. Exact comparison
also covered the service unit hash, ExecStart, working directory, current
symlink and membership of all5 existing releases. All fields were equal:

`ca2ac82d26a0eed7bc622f9887bfef9027216ed86c0b71a7382bf5bc6a50a6a1`

is both canonical preservation-inventory digests. It is a digest of that
inventory, not a full release-source-tree attestation.

| Preserved artifact | SHA256 / result |
|---|---|
| V2 ONNX | `09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec` — UNCHANGED |
| V2 plan | `5d7a4a40ad3830fb4406694dddc1b13f1c05a8d47360586c6891bfce8f1f3ca2` — UNCHANGED |
| Nav ONNX | `01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a` — UNCHANGED |
| Nav plan | `2c5c5a5e0c736b4d60a6c56569539df219c9e5b32aee8fde26be6d446c96caa2` — UNCHANGED |
| Original sidecars, last-loaded record, timing cache | UNCHANGED |
| current -> releases/54e706fa0573e91dc3b4a0d4f625b9d81a6b68cc | UNCHANGED |
| All5 releases, service ExecStart/unit, dependency metadata | UNCHANGED |
| Actual comma branch/HEAD, road flags | carrot-nav366d6eae;1/0; UNCHANGED |

There is nothing to roll back in operating runtime: it was not activated or
replaced. Leave all development evidence and the plan isolated; do not copy the
plan into cache or change selected.json/current. Existing V2/Nav rollback assets
remain available. No service restart is required by this checkpoint.

Next stage: establish reviewed per-tensor/driving-slice/recurrent-drift numeric
criteria, then validate a Nav-specific minimal dtype/managed adapter and V2/Nav
protocol regression in a separate development copy. Only a separately scoped
M2 may connect the protocol-3 inference path, exercise parked USB/parser and
local-small fallback, and measure full latency/thermal/timeout behavior. Do not
infer a passing50ms budget from this standalone run. Keep BASE first; DeviceState,
then DeviceState+InputFastpath and only-needed AIO remain later A/B stages.

M1 build/recurrent: PASS. Numerical approval: BLOCKED_ACCEPTANCE_THRESHOLD.
USB/COMMA/VEHICLE/ROAD_TEST: NOT_RUN by stage boundary. All optional
optimizations: OFF. **DO_NOT_INSTALL remains in force.**
