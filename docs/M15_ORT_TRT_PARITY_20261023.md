# M1.5 ORT ↔ TensorRT semantic parity — 2026-10-23

**Numerical decision: PARITY_UNDETERMINED. Ready for M2 parked USB: NO.**

101 actual paired recurrent frames completed, with exact contracts and all
outputs finite. Actual Nav parser execution succeeded; numerical parser parity
is **NOT_AVAILABLE as an approval verdict**, because no applicable physical
error budget is approved and one desire_pred classification disagreed. This
must not be reported as PARITY_PASS or a vehicle behavior result.

Software adapter tests are a separate gate. The engine remains DO_NOT_INSTALL;
USB/comma inference, parked vehicle and road tests are NOT_RUN. After observing
the parser disagreement no further model adoption, USB or GPU variant was run.
Machine-readable complete metrics: `artifacts/m15_ort_trt_parity_20261023.json`.

## Exact setup and sequence

- Original V3:766354845 bytes, SHA
  `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`.
- Existing M1 plan:768580676 bytes, SHA
  `8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa`.
  No rebuild, new tactics, engine setting, workspace/swap/clock/package change.
- ORT1.31.0 CPUExecutionProvider, NumPy2.5.4 on the existing PC environment;
  TensorRT10.3.0, NumPy1.26.4, actual Orin-sm87/L4T36.4.7/CUDA12.6.
- Evidence: ORT_REAL_MODEL + TRT_REAL/JETSON_REAL/SYNTHETIC_INPUT. Original
  ONNX graph metadata is real-model source evidence, not a synthetic graph.
- Frames0..100 (101 frames), seed73. Original `build_trt_v3.frame_inputs` bytes
  and initial zero states were retained. Each runtime used its **own** advanced
  image/desire/feature state, with every named shape/dtype/finite gate intact.
- Nonstate frame digests matched101/101, normalizing only the intentional exact
  UINT8 image→FP16 representation. ORT reference arrays were file-hash/NPY-header/
  contract/finite checked before CUDA and while consumed. No teacher forcing
  from ORT into TRT. Reference NPZ files are private and absent from Git.
- The sequence is a numerical stress sequence: frame0zero, later random image
  noise, changing desires and action_t=frame/20, reaching5s. The upstream V3
  verifier explicitly bounds representative action horizons around0.2–0.4s.
  This extension preserves M1 comparability but is not representative driving.
  The desire disagreement already occurs at frame14 (0.7s); it cannot be
  dismissed as only a >1s late-horizon effect. No causal explanation is proven.
- Actual unmodified Nav366d6eae parser/constants were verified by SHA before
  execution: parser45b38da9f929bd59ca28ff9e19f64e8718286ae3ccbeccddb7868ffbcd88fc85;
  constants5d597d287df626d08b234a17db05e884302fead646ff4e7f0153079547c8010c.
  Slices are copied because softmax/MDN parsing can mutate views.

## Error arithmetic and denominator policy

All differences use float64 to avoid unsigned wrap or FP16 overflow. MAE and
RMSE are over all elements; p95/p99 are exact pooled element percentiles over
101 frames, not averages of frame percentiles. The artifact also records each
frame, tensor dtype, sample count, reference scale and epsilon range.

Relative error is abs(actual-reference)/max(abs(reference),epsilon), where
epsilon=float-reference-dtype-eps×max(1,maxabs(reference)) per tensor/frame;
integer reference uses one value quantum. This is a **resolution diagnostic**,
not an acceptance tolerance. Large near-zero relative values remain visible
beside absolute error and scale. No whole-vector epsilon is reused to hide
smaller semantic values. The aggregate max relative is the maximum of these
documented frame-local diagnostics.

## Every actual raw output slice

All15 logical/raw slices and physical driving output are float32. N is elements
per frame; pooled element counts equal N×101. Names and contiguous boundaries
come from the exact ModelSpec; there is no standalone longitudinal/trajectory
slice to invent. Those meanings are represented by actual plan columns/action.

| Actual slice | N | Reference min..max | Max abs | MAE | RMSE | p95 abs | p99 abs | Max relative |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| lane_lines | 528 | -9.1875..7.6953125 | 0.0625 | 0.0057184051 | 0.0081990807 | 0.015625 | 0.02734375 | 162.62184 |
| lane_lines_prob | 8 | -6.1992188..4.1601562 | 0.12109375 | 0.027919524 | 0.035070342 | 0.0703125 | 0.08984375 | 1.8004793 |
| road_edges | 264 | -10.171875..8.1015625 | 0.08203125 | 0.0078224287 | 0.011135354 | 0.0234375 | 0.0390625 | 41.924471 |
| meta | 55 | -8.484375..5.0585938 | 0.11035156 | 0.017769437 | 0.02499474 | 0.0546875 | 0.07421875 | 103.25073 |
| desire_pred | 32 | -8.8515625..4.0820312 | 0.0703125 | 0.014803453 | 0.018665812 | 0.036352539 | 0.05056839 | 5.3196653 |
| pose | 12 | -6.4257812..9.90625 | 0.0625 | 0.004312829 | 0.0095753642 | 0.0234375 | 0.0390625 | 53.068702 |
| wide_from_device_euler | 6 | -7.6445312..0.033081055 | 0.0234375 | 0.0040025377 | 0.0066116877 | 0.015625 | 0.017578125 | 0.25 |
| road_transform | 12 | -7.6523438..1.4033203 | 0.03125 | 0.0042840283 | 0.0072600319 | 0.015625 | 0.0234375 | 0.43250397 |
| plan | 990 | -511.25..69.3125 | 4.25 | 0.015455221 | 0.096381959 | 0.03515625 | 0.171875 | 219.07547 |
| lead | 144 | -348.5..111.25 | 4 | 0.055458907 | 0.21616774 | 0.25 | 1.0625 | 55.299017 |
| lead_prob | 3 | -3.1523438..51.1875 | 0.125 | 0.029261523 | 0.038060859 | 0.063378906 | 0.09375 | 2.4595336 |
| desire_state | 8 | -78.125..85.5625 | 0.25 | 0.05635796 | 0.073229541 | 0.15625 | 0.1875 | 0.63097514 |
| action | 4 | -5.0703125..7.0234375 | 0.0546875 | 0.0074695549 | 0.012811939 | 0.029711914 | 0.046816406 | 0.64585275 |
| hidden_state | 16384 | -22.75..15.289062 | 0.296875 | 0.0091030206 | 0.012534104 | 0.025390625 | 0.0390625 | 9659.7195 |
| pad | 2 | 0..0 | 0 | 0 | 0 | 0 | 0 | 0 |

Whole outputs: max abs4.25, MAE0.009748817, RMSE0.031811548. The old five-frame0.625 maximum is not the101-frame result.

## Actual downstream parser comparison

The real Parser.parse_outputs from the actual Nav SHA processed both full V3
outputs. This is the same direct-plan branch used by Nav contracts.parse_outputs
for V3's990-value plan. All22 returned fields matched shape/dtype and were
finite. It does not execute cereal publication, vehicle-control smoothing or
modeld action conversion; those boundaries remain NOT_RUN. This successful
execution/schema check is separate from numerical acceptance.

MDN means and exponentiated standard deviations are reported separately.
Action, hidden_state and pad pass through unchanged. Actual modeld consumes
action[0,0] after speed-squared conversion and action[0,1] as desired acceleration;
no fake action mean/std split or vehicle speed is assumed here.

| Parsed field | Max abs | MAE | RMSE | p95 abs | p99 abs | Reference min..max |
|---|---:|---:|---:|---:|---:|---|
| lane_lines | 0.0625 | 0.0051682588 | 0.0085722888 | 0.01953125 | 0.03125 | -9.1875..7.6953125 |
| lane_lines_prob | 0.023774087 | 0.00205504 | 0.0036651669 | 0.0075822309 | 0.015561075 | 0.0020269002..0.9846347 |
| road_edges | 0.08203125 | 0.008322299 | 0.012841449 | 0.02734375 | 0.044921875 | -10.171875..8.1015625 |
| meta | 0.025142133 | 0.0024054591 | 0.0040178431 | 0.0093235433 | 0.013386179 | 0.00020662983..0.99368566 |
| desire_pred | 0.010278881 | 0.00059736263 | 0.0012664691 | 0.0029650532 | 0.0052102163 | 3.1845047e-06..0.95209759 |
| pose | 0.0625 | 0.0047967595 | 0.012597215 | 0.03125 | 0.046875 | -0.095275879..9.90625 |
| wide_from_device_euler | 0.00024414062 | 5.0764273e-05 | 7.440057e-05 | 0.00016107559 | 0.00019828796 | -0.014907837..0.033081055 |
| road_transform | 0.001953125 | 0.00014963658 | 0.00039133429 | 0.0009765625 | 0.001953125 | -0.0071258545..1.4033203 |
| plan | 4.25 | 0.018865297 | 0.13531987 | 0.04296875 | 0.5 | -511.25..69.3125 |
| lead | 4 | 0.10047407 | 0.30540063 | 0.5 | 1.5 | -348.5..111.25 |
| lead_prob | 0.015032589 | 0.00075383761 | 0.0025619681 | 0.0060284048 | 0.01366622 | 0.040999025..1 |
| desire_state | 0.011746988 | 0.00017354954 | 0.0011164358 | 0.00015414978 | 0.0074145358 | 0..1 |
| action | 0.0546875 | 0.0074695549 | 0.012811939 | 0.029711914 | 0.046816406 | -5.0703125..7.0234375 |
| hidden_state | 0.296875 | 0.0091030206 | 0.012534104 | 0.025390625 | 0.0390625 | -22.75..15.289062 |
| pad | 0 | 0 | 0 | 0 | 0 | 0..0 |
| pose_stds | 0.058407784 | 0.0028467567 | 0.0088634084 | 0.02056551 | 0.044774866 | 0.0016192677..8.2109509 |
| wide_from_device_euler_stds | 0.0019164085 | 0.00033256152 | 0.00050091514 | 0.0011183269 | 0.0013622189 | 0.00047865463..0.095220268 |
| road_transform_stds | 0.00044112094 | 7.0347374e-05 | 0.00011278546 | 0.00024731085 | 0.00034194086 | 0.00047492969..0.07159581 |
| lane_lines_stds | 0.68162537 | 0.031086753 | 0.055268941 | 0.13257484 | 0.20061359 | 0.036424998..94.706367 |
| road_edges_stds | 7.0007935 | 0.2211558 | 0.40071686 | 0.85011292 | 1.4820406 | 0.17024651..649.73364 |
| lead_stds | 888.53516 | 2.9119834 | 30.730034 | 0.20386639 | 85.563145 | 3.8832619e-05..59874.141 |
| plan_stds | 30.440369 | 0.12144456 | 0.63198961 | 0.51051121 | 1.8961927 | 0.00023236817..1195.0431 |

The parsed plan maximum4.25 occurs in POSITION[0] (frame45); lead maximum4.0
occurs at frame46. Exponentiation makes plan_stds maximum difference30.440369,
so a raw logstd bound alone would hide downstream sensitivity. Probability
absolute differences and raw logits are not interchangeable.

Actual desire_state argmax disagreed0 times across101 frames. desire_pred
argmax disagreed **once at frame14**, among404 predicted categorical vectors.
The stored count identifies a sensitivity, not a proven unsafe maneuver or an
approved small-error exception. No classification-equivalence claim is made.
Hard-brake/confidence rolling decisions and actual control publication were
not executed; a generic parser cannot stand in for those stateful consumers.

### Actual Plan channel sensitivity

Names/grouping are the actual constants.Plan slices. Each mean channel has
33×101 values. Table shows mean-channel max/MAE/RMSE and corresponding std max;
complete std metrics/relative errors/scales are in the artifact. No physical
error budget follows from these numbers.

| Plan channel | Max abs | MAE | RMSE | Matching plan_stds max abs |
|---|---:|---:|---:|---:|
| plan.POSITION[0] | 4.25 | 0.23076213 | 0.52130483 | 30.440369 |
| plan.POSITION[1] | 0.15380859 | 0.0072803955 | 0.015692092 | 0.12272167 |
| plan.POSITION[2] | 0.05859375 | 0.0043679017 | 0.0082852117 | 14.777649 |
| plan.VELOCITY[0] | 0.296875 | 0.032869794 | 0.050623883 | 4.5840607 |
| plan.VELOCITY[1] | 0.0025634766 | 0.00059475256 | 0.00073467265 | 0.16669941 |
| plan.VELOCITY[2] | 0.0031738281 | 0.00072721576 | 0.00088430937 | 1.3795662 |
| plan.ACCELERATION[0] | 0.029296875 | 0.0040579368 | 0.005605306 | 2.2971954 |
| plan.ACCELERATION[1] | 0.0070800781 | 0.0010111565 | 0.0013316166 | 0.037972808 |
| plan.ACCELERATION[2] | 0.0057067871 | 0.00067029899 | 0.00090340709 | 5.7057037 |
| plan.T_FROM_CURRENT_EULER[0] | 0.00051879883 | 5.6711253e-05 | 8.6411629e-05 | 1.3087006 |
| plan.T_FROM_CURRENT_EULER[1] | 0.00050354004 | 7.8242229e-05 | 0.00011008472 | 13.41095 |
| plan.T_FROM_CURRENT_EULER[2] | 0.0029296875 | 0.00028982314 | 0.00047991794 | 20.387146 |
| plan.ORIENTATION_RATE[0] | 0.00028610229 | 4.5505061e-05 | 6.2131403e-05 | 2.2720566 |
| plan.ORIENTATION_RATE[1] | 0.0002822876 | 4.5473712e-05 | 6.1778519e-05 | 1.7368317 |
| plan.ORIENTATION_RATE[2] | 0.00061035156 | 0.00012211865 | 0.00015731029 | 1.4784546 |

## Recurrent drift and what can be inferred

Image/desire feedback error is exactly0 at every frame. Original image feedback
is UINT8 and physical feedback FP16; all integer values0..255 are exactly
representable. Feature feedback is float32 on both sides.

| Frame | feat max abs | feat mean abs | feat RMSE |
|---|---:|---:|---:|
| 0 | 0.109375 | 6.2456874e-05 | 0.00096307598 |
| 1 | 0.109375 | 0.00012897273 | 0.0014098734 |
| 5 | 0.1484375 | 0.00040789491 | 0.0025849044 |
| 10 | 0.1953125 | 0.00077581841 | 0.0036338263 |
| 25 | 0.2734375 | 0.0018483127 | 0.0056521843 |
| 50 | 0.2734375 | 0.0036354415 | 0.0079312279 |
| 100 | 0.296875 | 0.0071828522 | 0.011133943 |

Observed feature max and mean error are nondecreasing across these101 frames;
max reaches0.296875, mean0.0071828522. No plateau is established. This does not
prove unbounded dynamical growth: the state is a128-entry stored feature queue,
still filling from initial zeros throughout this observation window.

Actual original ONNX source was re-hashed and inspected: node_cat_5 concatenates
Slice(state_feat_q,start1,axis0) with unsqueezed Slice(outputs,2066:18450,axis1).
Thus it shifts the prior127 entries and appends the current hidden_state. The
measured state-error mean equals sum of instantaneous hidden_state MAEs/128
exactly; RMSE equals sqrt(sum of their squared RMSEs/128) to5.21e-18 arithmetic
residual, and max equals the running hidden-state max exactly. Full per-frame
reconstruction and actual graph/index constants are in the artifact.

This explains the observed monotonic **stored-history** error. Instantaneous
feature MAE changes from0.00799448 on frame0 to0.00895152 on frame100, while the
initial zero history is replaced. It is not a proof of a uniform long-run bound:
feedback can affect future features, and101 frames do not complete a128-step
turnover. No plateau/stability acceptance follows from finite values alone.

Downstream differences are present in plan/lead/probabilities and desire. This
independent-recurrence experiment combines per-frame FP16 and accumulated-state
effects; it does not isolate causality via a separate teacher-forced run.

## Acceptance provenance and proposed criteria

| Source | Existing numeric rule | Applicability here |
|---|---|---|
| [Jetlink V3 verify_parity](https://github.com/zoompilot/jetlink/blob/d24328d849b0e5154b55f149dc18c5dfe8bd79cc/scripts/verify_parity.py) | correlation>=.999; minimum16 samples; tiny/quiet fraction.05; small-value error rule.1×reference magnitude/.001×spread | Real same-model wiring precedent; not parsed physical/state-stability approval. Constant correlation can miss offset changes. Not adopted or claimed passed here. |
| [Official comma replay](https://github.com/commaai/openpilot/blob/ff47f484e606ce5a2c3f8768ba5f5bf01b81e90e/openpilot/selfdrive/test/process_replay/model_replay.py), [comparison](https://github.com/commaai/openpilot/blob/ff47f484e606ce5a2c3f8768ba5f5bf01b81e90e/openpilot/selfdrive/test/process_replay/compare_logs.py) | PC tolerance.3 after excluding many trajectory/lane/lead fields; bound=max(t,t×maxabs) | Selected-field platform replay, also present in actual Nav source. Cannot transplant.3 to every V3 slice or vehicle behavior. |
| [NVIDIA accuracy guidance](https://docs.nvidia.com/deeplearning/tensorrt/10.x.x/inference-library/accuracy-considerations.html) | Golden-output and application accuracy evaluation; no universal atol/rtol | Guidance only. Redirected current docs are not a10.3-specific approval. |
| Existing project M1/build verifier | Optional caller tolerance; otherwise exit3/no approval | No pre-existing approved V3 semantic/physical error envelope was found. |

Existing strict invariants (identity, exact shape/dtype, finite, complete state
commit, reset/generation) remain enforced. They are not numerical equivalence.

**PROPOSED_THRESHOLD, NOT_APPROVED:** no categorical desire disagreement on an
approved representative sequence. The current stress sequence does not satisfy
that proposed diagnostic (one desire_pred change). This criterion alone still
cannot approve trajectory/lead/control error.

**PROPOSED_THRESHOLD, NOT_APPROVED:** physical channel/slice-specific absolute
and relative budgets, probability/decision margins, and recurrent drift after
at least a full queue turnover on representative inputs. Numeric budget values
remain UNDEFINED pending domain review; no1.0/.3/.1 blanket cutoff is invented.
The denominator epsilon above is never an approval value.

Final decision remains **PARITY_UNDETERMINED**. Large longitudinal/lead tails,
the classification disagreement, nonrepresentative input and missing approved
budgets block model adoption and M2 readiness. This is not PARITY_FAIL against
a fabricated tolerance, and not PARITY_PASS based on correlation/finite alone.

## Memory incident and exact retry boundary

The first actual measurement attempt failed before any frame while deserializing
the same plan: CUDA requested735,338,624 bytes and returned OOM. Linux reported
about1.03GB immediately free but5.85GB available including5.08GB cached. This
was a resource failure, not semantic numerical evidence. Original failure log
and guardian exit1 are retained.

An explicit default-OFF private-file cache preparation option was reviewed and
tested (10 RED→GREEN cases,25 semantic tests total). Its first preparation was
refused **before CUDA** because upload umask had left nested private directories
0775/files0664. The gate was kept: only101 owned reference files plus the owned
isolated M1 source/plan were tightened to0600 and reference directory0700.
M1 plan/source bytes, sizes and hashes stayed identical. Operating permissions
and files were not changed.

The corrected run hash-checked the same pinned read-only FD before advising
POSIX_FADV_DONTNEED on exactly103 private files (2,588,748,109 bytes), with
owner/inode/nlink/mode/mount/metadata checks. It did not read file contents
again after the final advice before CUDA. Actual MemFree increased884,748,288
→3,496,996,864 bytes; Cached decreased5,188,825,088→2,599,829,504; swap free
stayed3,215,646,720. A strict measured-improvement gate would have blocked CUDA
without recovery of the failed allocation size. Advice itself did not assert
CUDA availability. The one corrected actual GPU retry then completed101 frames,
guardian PASS, worker **exit3 by numerical policy**, elapsed45.061s.

No global drop_caches/sync, operating cache advice, service action, swap,
workspace, TRT/JetPack/CUDA or clock change occurred. All three inference
optimization flags stayed0; BASE execution and M1 plan were unchanged. This is
harness resource preparation, not a fast input/device-state/AIO optimization.
The original M1 recovered64,704,384-byte tactic OOM remains documented too;
no rebuild or tactic change followed either incident.

## Reproducibility and preservation

Implementation checkpoint5812a6587a1cd6211151cb10c82cd196e8214ccb;
executed revised semantic tool SHA
76da628b54a2c1c6ba82b6086ca949185a13b25ce5ef800e848fc5257e816a58.
Export/old-failure source and revised source occupy separate new paths; no
frozen M1 tool/report/plan was overwritten. ORT101 manifest SHA
dcae27b7576d787d5786d6ff22d9c65fc30820bd86a04a715fb1c8a5f528e0d2.

The actual commands used existing interpreters, candidate PYTHONPATH and these
tool modes (personal interpreter/access paths omitted):

```sh
"$ORTPY" -B tools/jetson_m15_semantic.py export-ort --onnx "$EXACT_ORIGINAL_V3" --spec artifacts/cinque_v3.json --parser-source .reference/m05-carrot-nav-366d6eae/openpilot/selfdrive/modeld --out-dir .reports/m15-20261023/ort-reference-101
```

The device argv, recorded under a live30s offroad lease/1s owned-child guardian,
was the following. D is the existing isolated M1 root and J the existing runtime
venv Python. This is a record, not permission to rerun into existing outputs or
launch without the guardian.

```sh
"$J" -B "$D/m15/repo-cache-v2/tools/jetson_m15_semantic.py" measure-trt --development-root "$D" --engine "$D/build/cinque-v3.plan" --spec "$D/repo/artifacts/cinque_v3.json" --reference-dir "$D/m15/ort-reference-101" --base-report "$D/results/base-10-1000/report.json" --parser-source "$D/m15/parser" --out-dir "$D/m15/result-101-cache-prepared" --release-private-file-cache
```

Before/after operating inventory digest remained
ca2ac82d26a0eed7bc622f9887bfef9027216ed86c0b71a7382bf5bc6a50a6a1,
also identical to M1: all8 operating cache files including V2/Nav ONNX/plans,
timing cache/sidecars/last-loaded record, current symlink, five-release
membership, effective ExecStart and unit hash. Dependency metadata equal.
This is not full release-source-tree attestation. Actual comma remains
Nav366d6eae with offroad1/onroad0. Temporary monitor/agent/master/relay closed;
zero owned workers remained. Raw addresses/keys/NPZ/process logs stay out of Git.

Next: resolve representative-input and semantic acceptance criteria in an
isolated numerical stage before authorizing model adoption. The separately
prepared Nav bridge and M2 parked USB plan remain reviewable software assets;
they do not override this numerical hold.
