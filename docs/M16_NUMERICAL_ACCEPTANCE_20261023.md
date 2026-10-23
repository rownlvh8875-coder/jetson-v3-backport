# M1.6 numerical acceptance — 2026-10-23

**PARITY_UNDETERMINED. Ready for M2 parked USB: NO. DO_NOT_INSTALL.**

Historical512 paired frames completed on the exact existing M1 plan:512 independent and512 ORT-state teacher-forced TRT executions. Both512-frame ORT references completed. The bounded TRT job failed at engine deserialize, before frame0, despite the unchanged authorized private-file preparation. No automatic retry or new memory workaround followed. Representative driving inputs remain unavailable. No application tolerance is invented.

Evidence: ORT_REAL_MODEL / TRT_REAL / JETSON_REAL / SYNTHETIC_INPUT; teacher branch also TEACHER_FORCED_DIAGNOSTIC. No RECORDED_INPUT, USB_REAL, COMMA_REAL inference, VEHICLE_PARKED or ROAD_TEST. Adapter/production sources were frozen.

## Target, runtimes and sequence isolation

| Target | Identity |
| --- | --- |
| Actual comma / numerical parser base | 366d6eae9aa9962104391e1d997fe956dea8f64d |
| Original ONNX | 404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4 /766354845 bytes |
| M1 plan | 8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa /768580676 bytes |
| Parser SHA | 45b38da9f929bd59ca28ff9e19f64e8718286ae3ccbeccddb7868ffbcd88fc85 |
| Constants SHA | 5d597d287df626d08b234a17db05e884302fead646ff4e7f0153079547c8010c |

Existing Orin-sm87, L4T36.4.7, TRT10.3.0, toolkitCUDA12.6; PC ORT1.31 CPUExecutionProvider with NumPy2.5.4; device NumPy1.26.4; offline same-parser analysis NumPy2.3.5. No package/JetPack/workspace/clock change, rebuild or graph capture. All DeviceState/InputFastpath/AIO flags stayed0. Existing M1 reset/reload proof is bound to the same plan and was not rerun.

D1 historical: exact M1 seed73, frame_inputs and zero initial states, frames0..511. action_t=frame/20 reaches25.55s, so this is OOD numerical stress. D2 bounded: same images/desire/traffic, only action_t replaced by the pinned verifier formula [.25+.1*sin(.5*i),.35+.1*cos(.5*i)], cast float32. Exact analytic envelopes [.15,.35] and [.25,.45]s, not the verifier comment’s approximate .2–.4. D2 is still synthetic noise, including the historical none/unnamed-desire stress pulses; it is not representative driving. D1/D2 results are never pooled.

Original [upstream generator](https://github.com/zoompilot/jetlink/blob/d24328d849b0e5154b55f149dc18c5dfe8bd79cc/scripts/verify_parity.py) is provenance for the action formula only. We did not claim to copy its whole input generator. Both ORT histories use their own outputs. Every compact reference reconstructs128-row feature state from shift+current hidden and proves exact bytes against the real full ORT output; each consumer rechecks full feature SHA. Image/desire states are stored exactly. This storage representation changes no model state.

Historical first101 ORT continuity:404 arrays/1053704720bytes per side match M1.5 byte-for-byte. First101 TRT aggregate max/MAE/p99 match; two float64 RMSE reduction deltas up to1.39e-17 are retained. Original M1.5 TRT arrays were not saved, so this is not a claim of original-TRT byte equivalence or a new acceptance tolerance.

## Exact worst-case localization

Frame indices are zero-based. The [actual parser](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/parse_model_outputs.py) takes plan990 and lead144 as direct mean/std layouts. **Neither selects MDN hypotheses.** Legacy five-plan/two-lead hypothesis constants do not apply to these shapes.

| Item | Plan POSITION[0] | Lead X |
| --- | --- | --- |
| Frame | 45 | 46 |
| Trajectory node | 32 | 5 |
| Trajectory time seconds | 10 | 10 |
| Head / mode | single direct plan | direct head0; probTime0s |
| ORT | -377.25 | -260.5 |
| TRT independent | -373 | -256.5 |
| Signed TRT−ORT | 4.25 | 4 |
| Absolute error | 4.25 | 4 |
| Reference magnitude | 377.25 | 260.5 |
| Relative error | 0.0112657389 | 0.01535508637 |
| Raw mean index | 1397 | 1927 |

Plan4.25m is the last10s longitudinal position, not the current or first trajectory point. ORT predicts−377.25m under synthetic noise and action_t2.25s: the sign/scale itself is OOD context. All33 nodes can still influence MPC; the far tail must not be discarded as unused. Exact [time constants](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/constants.py) are10*(i/32)^2, not uniform time sampling.

Lead4.0m is **x/distance**, direct head0, node5/time10s; it is not y, relative velocity, acceleration or a low-probability alternative. ORT/TRT head0 probability is1.0; head1 is also1.0, head2≈.999999762. There is no MDN selection to discount. The publisher copies all three heads; probTime[0,2,4] is separate from each trajectory’s[0,2,4,6,8,10]s. ORT x std=5.337752819m, TRT std=5.583001614m. Predicted std is model uncertainty, not a parity approval allowance. Source: [publisher](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/fill_model_msg.py), actual schema LeadDataV3.

### Complete33-point frame45 POSITION[0] profile

| Node | Source time s | ORT x | TRT x | Signed difference | Abs difference |
| --- | --- | --- | --- | --- | --- |
| 0 | 0 | 0 | 0 | 0 | 0 |
| 1 | 0.009765625 | -0.0224609375 | -0.02160644531 | 0.0008544921875 | 0.0008544921875 |
| 2 | 0.0390625 | -0.06365966797 | -0.06066894531 | 0.002990722656 | 0.002990722656 |
| 3 | 0.087890625 | -0.09643554688 | -0.09027099609 | 0.006164550781 | 0.006164550781 |
| 4 | 0.15625 | -0.1960449219 | -0.1851806641 | 0.01086425781 | 0.01086425781 |
| 5 | 0.244140625 | -0.2614746094 | -0.2443847656 | 0.01708984375 | 0.01708984375 |
| 6 | 0.3515625 | -0.3376464844 | -0.3154296875 | 0.02221679688 | 0.02221679688 |
| 7 | 0.478515625 | -0.673828125 | -0.6411132812 | 0.03271484375 | 0.03271484375 |
| 8 | 0.625 | -0.8671875 | -0.8217773438 | 0.04541015625 | 0.04541015625 |
| 9 | 0.791015625 | -1.458984375 | -1.3984375 | 0.060546875 | 0.060546875 |
| 10 | 0.9765625 | -2.484375 | -2.40625 | 0.078125 | 0.078125 |
| 11 | 1.181640625 | -4.203125 | -4.09375 | 0.109375 | 0.109375 |
| 12 | 1.40625 | -7.44140625 | -7.28515625 | 0.15625 | 0.15625 |
| 13 | 1.650390625 | -11.703125 | -11.4765625 | 0.2265625 | 0.2265625 |
| 14 | 1.9140625 | -17.84375 | -17.546875 | 0.296875 | 0.296875 |
| 15 | 2.197265625 | -24.828125 | -24.4375 | 0.390625 | 0.390625 |
| 16 | 2.5 | -32.03125 | -31.53125 | 0.5 | 0.5 |
| 17 | 2.822265625 | -40.875 | -40.28125 | 0.59375 | 0.59375 |
| 18 | 3.1640625 | -53.6875 | -52.96875 | 0.71875 | 0.71875 |
| 19 | 3.525390625 | -66.0625 | -65.1875 | 0.875 | 0.875 |
| 20 | 3.90625 | -78.625 | -77.625 | 1 | 1 |
| 21 | 4.306640625 | -95.125 | -93.9375 | 1.1875 | 1.1875 |
| 22 | 4.7265625 | -111.6875 | -110.25 | 1.4375 | 1.4375 |
| 23 | 5.166015625 | -130.75 | -129.25 | 1.5 | 1.5 |
| 24 | 5.625 | -153 | -151 | 2 | 2 |
| 25 | 6.103515625 | -173.125 | -171 | 2.125 | 2.125 |
| 26 | 6.6015625 | -200.375 | -198 | 2.375 | 2.375 |
| 27 | 7.119140625 | -223.5 | -220.625 | 2.875 | 2.875 |
| 28 | 7.65625 | -251.875 | -249 | 2.875 | 2.875 |
| 29 | 8.212890625 | -283 | -279.75 | 3.25 | 3.25 |
| 30 | 8.7890625 | -312.75 | -309.5 | 3.25 | 3.25 |
| 31 | 9.384765625 | -345.75 | -341.75 | 4 | 4 |
| 32 | 10 | -377.25 | -373 | 4.25 | 4.25 |

### Source-based horizon scopes

There is no canonical near/mid/far partition. Reporting bins use actual consumers: nodes0..16 are CONTROL_N17/time0..2.5s;17..18 provide turn-preview interpolation support (node18 at3.1640625 brackets3s);19..32 are the remaining MPC tail. These labels are not accuracy thresholds. Lateral MPC uses all33 nodes and longitudinal resampling uses the full horizon. Source: [drive_helpers](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/controls/lib/drive_helpers.py), [turn_accel](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/controls/lib/turn_accel.py), lateral/longitudinal planners at the same SHA.

| Variant | POSITION[0] scope | Max | MAE | RMSE | p99 |
| --- | --- | --- | --- | --- | --- |
| independent | far_MPC_tail_19_32.POSITION[0] | 4.25 | 0.2682621117 | 0.4477847534 | 1.75 |
| independent | mid_preview_support_17_18.POSITION[0] | 0.71875 | 0.0753288269 | 0.1151390004 | 0.4375 |
| independent | near_control_nodes_0_16.POSITION[0] | 0.5 | 0.0152212522 | 0.03277819331 | 0.1328125 |
| teacher_forced | far_MPC_tail_19_32.POSITION[0] | 4.5 | 0.272210085 | 0.4403938539 | 1.75 |
| teacher_forced | mid_preview_support_17_18.POSITION[0] | 0.78125 | 0.07717132568 | 0.1134461157 | 0.40265625 |
| teacher_forced | near_control_nodes_0_16.POSITION[0] | 0.484375 | 0.01594366822 | 0.03277378869 | 0.125 |

All15 physical plan channels and every raw/parsed field have separate metrics in the numerical artifact; mixed physical units are not pooled into an approval budget. Relative errors use the unchanged M15 dtype-resolution denominator policy, purely diagnostic.

## Frame14 desire confidence and downstream meaning

| Runtime | Top1 | Probability | Top2 | Probability | Margin |
| --- | --- | --- | --- | --- | --- |
| ORT | none | 0.4479192197 | turnRight | 0.4403294027 | 0.007589817047 |
| TRT | turnRight | 0.4468784928 | none | 0.4414565563 | 0.005421936512 |

**NEAR_TIE_FLIP**, a descriptive classification of these measured44.79/44.03% and44.69/44.15% alternatives, not an invented universal cutoff. The top2 margin is0.759/0.542 percentage points. The measured probability changes reverse their ranking; there is no high-confidence dominating maneuver changing to a different high-confidence maneuver. This classification does not approve the mismatch.

| Class | ORT logit | TRT logit | ORT probability | TRT probability | Abs probability delta | ORT/TRT rank |
| --- | --- | --- | --- | --- | --- | --- |
| none | 0.6020507812 | 0.6079101562 | 0.4479192197 | 0.4414565563 | 0.006462663412 | 1/2 |
| turnLeft | -1.34765625 | -1.314453125 | 0.06374596804 | 0.06456783414 | 0.0008218660951 | 3/3 |
| turnRight | 0.5849609375 | 0.6201171875 | 0.4403294027 | 0.4468784928 | 0.006549090147 | 2/1 |
| laneChangeLeft | -2.7109375 | -2.69921875 | 0.01630749181 | 0.01616665348 | 0.000140838325 | 5/5 |
| laneChangeRight | -3.703125 | -3.748046875 | 0.006046243012 | 0.005663956515 | 0.0003822864965 | 6/6 |
| keepLeft | -2.322265625 | -2.314453125 | 0.02405388467 | 0.02375317924 | 0.0003007054329 | 4/4 |
| keepRight | -5.05859375 | -5.09375 | 0.001558881253 | 0.001474648365 | 8.423288818e-05 | 7/7 |
| UNNAMED_SCHEMA_SLOT_7 | -8.75 | -8.734375 | 3.887367711e-05 | 3.868878412e-05 | 1.848929969e-07 | 8/8 |

This is prediction slot0; actual Nav source defines no seconds mapping for the four prediction slots. Class7 has no enum name and stays UNNAMED_SCHEMA_SLOT_7. Synthetic frame14 input desire is one-hot class6 keepRight and action_t=[.7,.7]; both parsed desire_state argmax values are keepRight, probability1.0. Actual live control desire is derived through DesireHelper/desire_state, not prediction argmax. No lane-change/control transition is inferred.

LDW consumes first-slot classes3/4 probabilities with its existing.1 predicate. They are about.01631/.00605 ORT and.01617/.00566 TRT: both predicates stay false. This checks only that existing probability predicate, not the full LDW/FSM/vehicle state. Source: [LDW](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/controls/lib/ldw.py), modeld570–574 and DesireHelper at the same SHA. No controls/planner replay with vehicle configuration or CAN transmission ran.

| Frame | ORT slot0 top1 | Prob | Margin | TRT slot0 top1 | Prob | Margin |
| --- | --- | --- | --- | --- | --- | --- |
| 10 | none | 0.4652835727 | 0.07633474469 | none | 0.4655022323 | 0.07599040866 |
| 11 | turnRight | 0.5256383419 | 0.1933525801 | turnRight | 0.525629282 | 0.1934709251 |
| 12 | turnRight | 0.4234349132 | 0.01282727718 | turnRight | 0.4319845736 | 0.02913400531 |
| 13 | none | 0.4215697348 | 0.00946393609 | none | 0.4240962565 | 0.01534968615 |
| 14 | none | 0.4479192197 | 0.007589817047 | turnRight | 0.4468784928 | 0.005421936512 |
| 15 | turnRight | 0.5485578179 | 0.1971384287 | turnRight | 0.5483909845 | 0.1961337924 |
| 16 | turnRight | 0.486043036 | 0.125991106 | turnRight | 0.4921313822 | 0.1378354728 |
| 17 | none | 0.4621571004 | 0.03473162651 | none | 0.4593598545 | 0.02888348699 |
| 18 | turnRight | 0.5262947679 | 0.2314483225 | turnRight | 0.5311576128 | 0.2405332923 |

Full raw logits/probabilities/all rankings for all prediction slots and desire_state in neighboring10..18 frames are retained in the worst-case artifact. The14..20 table below describes simultaneous errors; argmax is never fed back in this probe and correlation is not causation.

| Frame | Parsed plan max | Parsed lead max | Action raw max | Desire_state MAE | Hidden MAE |
| --- | --- | --- | --- | --- | --- |
| 14 | 0.1875 | 0.3125 | 0.01550292969 | 0.0244140625 | 0.008948867217 |
| 15 | 0.03125 | 0.09375 | 0.0068359375 | 0.03833007812 | 0.009055084578 |
| 16 | 0.03125 | 0.1875 | 0.005615234375 | 0.02661132812 | 0.009148634617 |
| 17 | 0.09375 | 0.1875 | 0.005859375 | 0.044921875 | 0.009095379544 |
| 18 | 0.0625 | 0.1875 | 0.009765625 | 0.0537109375 | 0.009195757768 |
| 19 | 0.1875 | 0.1875 | 0.01171875 | 0.02783203125 | 0.009406145367 |
| 20 | 0.0625 | 0.40625 | 0.005859375 | 0.0322265625 | 0.009299693978 |

## Independent versus ORT-state teacher forcing

Every teacher step receives the same nonstate inputs and all three exact ORT recurrent inputs; source/physical image conversion is only exact UINT8→FP16. Normalized state digests are compared before execution. The independent step publishes only its own complete validated states. This separates state-conditioned differences from a fixed-state backend difference. It does not identify which TensorRT tactic, fusion, model Cast or accumulation operation caused the remaining error, nor compare to a newly rebuilt FP32 engine.

| Raw tensor/slice | Variant | Max | MAE | RMSE | p99 |
| --- | --- | --- | --- | --- | --- |
| outputs | independent | 4.25 | 0.009325116958 | 0.02031321842 | 0.04296875 |
| outputs | teacher_forced | 4.5 | 0.009348880061 | 0.02037920369 | 0.04296875 |
| plan | independent | 4.25 | 0.01033396179 | 0.05479442827 | 0.125 |
| plan | teacher_forced | 4.5 | 0.01044495262 | 0.05392256904 | 0.125 |
| lead | independent | 4 | 0.03210975805 | 0.1145904989 | 0.421875 |
| lead | teacher_forced | 4.25 | 0.03447668245 | 0.1188873656 | 0.46875 |
| desire_pred | independent | 0.078125 | 0.01513929167 | 0.0190017996 | 0.05078125 |
| desire_pred | teacher_forced | 0.078125 | 0.01513929167 | 0.0190017996 | 0.05078125 |
| action | independent | 0.0546875 | 0.006455302238 | 0.01102967864 | 0.03814453125 |
| action | teacher_forced | 0.0576171875 | 0.006444934756 | 0.01101544205 | 0.03515625 |
| hidden_state | independent | 0.296875 | 0.00914753997 | 0.01258947215 | 0.03930664062 |
| hidden_state | teacher_forced | 0.296875 | 0.00914753997 | 0.01258947215 | 0.03930664062 |

At frame45/node32 x: teacher error2.75 versus independent4.25. At frame46 lead x: teacher error4.25 versus independent4.0; teacher is not uniformly closer. Global teacher plan maximum is4.5 at frame46/node32. Desire_pred and hidden outputs of the two TRT branches are **byte-value identical across all512 frames** (paired difference max0). The same desire flips occur at14,252,271,311,439 in both branches; desire_state argmax changes0. Thus those prediction flips persist at identical state inputs and are not produced by independent recurrent feature drift in this experiment. Signed pointwise error decomposition is possible, but pooled magnitudes do not yield causal percentages.

## Full128-slot turnover

After frame127, all128 initial zero feature rows have been replaced; post-turnover diagnostics use128..511. Both state trajectories are finite, image/desire errors remain0. Independent feature errors reproduce rolling128-frame hidden-error mean/max exactly and RMSE to1.22e-17. Teacher outputs contain127 exact ORT history rows plus the current TRT row, explaining their much smaller stored-state MAE; this is not evidence of128-fold dynamical amplification.

### independent feature checkpoints

| Frame | Stored state max | Stored MAE | Stored RMSE | Current hidden max | Current hidden MAE | Current hidden RMSE |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.109375 | 6.245687354e-05 | 0.0009630759804 | 0.109375 | 0.007994479813 | 0.01089596091 |
| 1 | 0.109375 | 0.000128972728 | 0.001409873375 | 0.109375 | 0.008514029374 | 0.01164942622 |
| 5 | 0.1484375 | 0.0004078949108 | 0.002584904427 | 0.140625 | 0.00926942228 | 0.01280865841 |
| 10 | 0.1953125 | 0.0007758184123 | 0.003633826328 | 0.140625 | 0.00958909413 | 0.01310663587 |
| 25 | 0.2734375 | 0.001848312743 | 0.005652184342 | 0.1953125 | 0.009080806361 | 0.01256325784 |
| 50 | 0.2734375 | 0.003635441471 | 0.007931227855 | 0.140625 | 0.009126375171 | 0.01253737183 |
| 100 | 0.296875 | 0.007182852221 | 0.01113394341 | 0.171875 | 0.008951515934 | 0.01225069384 |
| 127 | 0.296875 | 0.009106710221 | 0.01253792401 | 0.1484375 | 0.009090564694 | 0.01256731446 |
| 128 | 0.296875 | 0.009117696557 | 0.01255430984 | 0.1640625 | 0.009400730894 | 0.01309007564 |
| 129 | 0.296875 | 0.009122648097 | 0.01256013822 | 0.1015625 | 0.009147826437 | 0.0124276035 |
| 192 | 0.296875 | 0.00914407115 | 0.01258865451 | 0.1640625 | 0.009753752118 | 0.01343651971 |
| 255 | 0.2421875 | 0.009166407307 | 0.01260999192 | 0.1875 | 0.00939024728 | 0.01302824645 |
| 256 | 0.2421875 | 0.009163860767 | 0.0126065749 | 0.19140625 | 0.009074773712 | 0.01266178886 |
| 384 | 0.2265625 | 0.009158586126 | 0.01259809946 | 0.1328125 | 0.009480267163 | 0.01309112558 |
| 511 | 0.2578125 | 0.009161624144 | 0.01261515248 | 0.171875 | 0.009024085652 | 0.01253887933 |

### teacher_forced feature checkpoints

| Frame | Stored state max | Stored MAE | Stored RMSE | Current hidden max | Current hidden MAE | Current hidden RMSE |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 0.109375 | 6.245687354e-05 | 0.0009630759804 | 0.109375 | 0.007994479813 | 0.01089596091 |
| 1 | 0.109375 | 6.651585448e-05 | 0.001029673535 | 0.109375 | 0.008514029374 | 0.01164942622 |
| 5 | 0.140625 | 7.241736157e-05 | 0.001132136153 | 0.140625 | 0.00926942228 | 0.01280865841 |
| 10 | 0.140625 | 7.491479789e-05 | 0.001158473888 | 0.140625 | 0.00958909413 | 0.01310663587 |
| 25 | 0.1953125 | 7.09437997e-05 | 0.001110445602 | 0.1953125 | 0.009080806361 | 0.01256325784 |
| 50 | 0.140625 | 7.129980602e-05 | 0.00110815758 | 0.140625 | 0.009126375171 | 0.01253737183 |
| 100 | 0.171875 | 6.993371824e-05 | 0.001082818586 | 0.171875 | 0.008951515934 | 0.01225069384 |
| 127 | 0.1484375 | 7.102003667e-05 | 0.001110804159 | 0.1484375 | 0.009090564694 | 0.01256731446 |
| 128 | 0.1640625 | 7.344321011e-05 | 0.001157010156 | 0.1640625 | 0.009400730894 | 0.01309007564 |
| 129 | 0.1015625 | 7.146739404e-05 | 0.001098455338 | 0.1015625 | 0.009147826437 | 0.0124276035 |
| 192 | 0.1640625 | 7.620118842e-05 | 0.001187631775 | 0.1640625 | 0.009753752118 | 0.01343651971 |
| 255 | 0.1875 | 7.336130687e-05 | 0.001151545176 | 0.1875 | 0.00939024728 | 0.01302824645 |
| 256 | 0.19140625 | 7.089666963e-05 | 0.001119154596 | 0.19140625 | 0.009074773712 | 0.01266178886 |
| 384 | 0.1328125 | 7.406458721e-05 | 0.001157102959 | 0.1328125 | 0.009480267163 | 0.01309112558 |
| 511 | 0.171875 | 7.050066915e-05 | 0.001108290825 | 0.171875 | 0.009024085652 | 0.01253887933 |

Post-turnover MAE band 0.009117696557..0.009183172411; MAE slope 5.516259918e-08/frame; RMSE slope 8.756263256e-08/frame. Positive/negative MAE steps 198/185. Previous/last-quarter means and all rolling128 maxima/p95-of-frame-MAE values are in the turnover artifact.

| Quarter | Mean max error | Mean MAE | Mean RMSE |
| --- | --- | --- | --- |
| 256..383 | 0.2333984375 | 0.009150166113 | 0.0125792075 |
| 384..511 | 0.2427978516 | 0.009160238899 | 0.01261344613 |

**Post-turnover classification: INCONCLUSIVE.** The observed rolling-history band no longer shows the initial fill ramp, and no explosive growth occurred in these512 frames. Small positive slopes remain. No approved plateau/stability cutoff or universal bound exists, and finite-window bounded values alone do not prove stable recurrence. Do not relabel this diagnostic as application acceptance.

## Bounded synthetic and representative evidence

D2 ORT512 completed and full references/hashes were staged. Its ORT feature-state output SHA matches D1 for all512 frames; lane/edge/meta/desire_pred/pose/hidden raw outputs also match, while plan/lead/probability/desire_state/action can change with action_t. This is ORT-only source/input evidence, not a bounded TRT comparison. D2 TRT independent/teacher/turnover: **NOT_RUN — BLOCKED_RESOURCE_OUT_OF_MEMORY**.

Scoped inventory searched only the current and previously authorized prior project, before M16 generation. It found106 synthetic ORT NPZs,190 QR fixtures,75 model ONNXs,6 CapnProto schema sources; the prior root held4 ONNXs. No exact recorded driving inputs or reconstructible approved replay/camera assets were found. **BLOCKED_REPRESENTATIVE_INPUT**, sequences0, RECORDED_INPUT evidence NONE. No broader user-file scan or log download occurred. Synthetic D1/D2 cannot establish production equivalence or missing scenarios.

## Actual external diagnostics and acceptance provenance

Actual pinned [Zoompilot functions](https://github.com/zoompilot/jetlink/blob/d24328d849b0e5154b55f149dc18c5dfe8bd79cc/scripts/verify_parity.py) and matching pure spec source were hash-checked and loaded with the caller namespace restored. No source function was rewritten. Exact frame/shape checks precede comparisons, avoiding upstream truncation. Record MIN_CORR.999/MIN_SAMPLES16/QUIET_FRACTION.05/TINY_TOLERANCE.1/CONSTANT_FRACTION.001, per-slice correlations, quiet columns and small-value rules separately.

Historical independent **ZOOMPILOT_HEURISTIC FAIL**: plan frame26 correlation0.9988452612; all pooled slices/columns pass. Teacher **ZOOMPILOT_HEURISTIC PASS**, while retaining all5 desire prediction flips and a4.5 plan maximum. This directly demonstrates why heuristic PASS is not APPLICATION_PARITY_PASS.

[Official comma replay](https://github.com/commaai/openpilot/blob/ff47f484e606ce5a2c3f8768ba5f5bf01b81e90e/openpilot/selfdrive/test/process_replay/model_replay.py) and actual Nav replay use selected-field PC tolerance.3 and exclude substantial position/lead/lane/edge data. Their compare_logs API requires aligned CapnProto messages; raw arrays cannot stand in for those events. **COMMA_REPLAY_DIAGNOSTIC NOT_RUN**, not PASS. NVIDIA application-specific accuracy guidance and prior M15 provenance supply no universal physical/error budget. No new numerical tolerance is approved.

## Resource failure and preservation

Historical guardian PASS/workerexit3;512 pairs completed in322.0934249s (supervisor349.46613s). This includes heavy diagnostics/two executions per frame and is not20Hz or USB latency evidence.

Both attempts called the **unchanged** M15 preparation on exactly103 existing private files/2588748109bytes, never the new M16 references or operating files. Historical MemFree 100495360→2591494144 bytes; bounded 108318720→1809616896. Both passed the original measured-recovery gate, which does not guarantee CUDA allocation. Bounded then failed to allocate735338624bytes while deserializing, zero frames, guardian PASS/workerexit1. Post-failure read-only meminfo/buddyinfo/RSS was collected; operating service RSS≈1.009GB. This is a resource failure, not numerical PARITY_FAIL. No blind retry, service termination, new cache allowlist/advice, global drop, swap/workspace/package/clock change or rebuild occurred.

Initial uncompressed transfer was stopped only at its owned local staging process;157 partial files remain as unused private evidence. A fresh tar.xz transfer delivered identical reference bytes and hashes in separate paths. The first offline analysis encountered a verifier/current-host ModelSpec import mismatch; matching pinned pure spec was used, tested with namespace restoration, then analysis reran into a new directory. These preparation failures did not alter model/plan/parser/adapter or any device inference gate.

Before/after operating digest **ca2ac82d26a0eed7bc622f9887bfef9027216ed86c0b71a7382bf5bc6a50a6a1** equals M1/M15:8 operating cache files (V2/Nav ONNX/plans, sidecars, timing/last-loaded), current target, five-release membership, unit hash/ExecStart/dependency metadata unchanged. This is not full release-tree attestation. Source/plan/parser/tool/reference manifests also rehashed unchanged; zero owned workers. Actual comma remainsNav366/offroad1/onroad0. Monitor/master/temporary agent/single-use relay closed. No old file permission was changed this session.

## Moving upstream and frozen adapter boundary

| Source | Start | End |
| --- | --- | --- |
| carrot-nav | 366d6eae9aa9962104391e1d997fe956dea8f64d | 3da803836786acdd9f6699ce75ef1134d1aabc6e |
| carrot-wip | 813369b0c53bb9c997b7ffbe17fca90222a755b8 | 3fdf82b268d69db31c1bf6d4137198d65cd548fe |

Latest Nav changes11 integration files: daemon/link/model plus new shared_input.py introduce ram_input_v1 memfd/SCM_RIGHTS, nonce/generation/deadline ownership and Warp output_buffer, with tests. Latest WIP changes2 mobile DHCP helper/test files (owned dnsmasq shutdown2→5s), not inference timeouts, TRT/spec/parser. Neither change was applied. Actual and numerical parser/constants remain byte-identical to their pins. All previous adapter/code/patch hashes stay frozen; its708 CPU evidence applies to actual366, **latest Nav compatibility NOT_REVALIDATED**. Future software/M2 preparation must review shared-input lifecycle before adopting a moved branch. Other three upstream heads remained unchanged.

## Decision and reproducibility

Gate1 strict historical invariants PASS and previous M1 reset/reload preserved. Gate2 representative behavior BLOCKED, with no approved selected-lead/near-plan/action/desire budgets. Gate3 full history turnover measured but general stability INCONCLUSIVE. Gate4 external heuristics are diagnostic only. Additional resource gate: bounded engine load failed under protected operating-service conditions. **PARITY_UNDETERMINED / M2 NO** remains the justified decision; no synthetic PASS or fabricated numerical FAIL is used.

CPU **PASS75 / FAIL0 / SKIP0**:24new diagnostics +25unchanged M15 semantic +26frozen Nav adapter/wire/loopback. Original708 record and repeated review cases are not added. One public pinned-source fixture test skips only when those optional reference source files are unavailable; they were present and it passed here. Initial wrong interpreter/missing candidate environment, TDD RED cases and failed analysis are retained privately and are not current passing-suite failures.

Implementation9515053 (unchanged executed tool SHA29a8bacc9b04df83925a51fc6ff6588c804d66867888706b157c87d3f32a09aa); offline analysis05d0e06. All actual commands used existing interpreters/PYTHONPATH and the owned live offroad guardian. D is the existing private M1 root; no command below is authorization to overwrite existing outputs or bypass the guardian.

```sh
"$ORTPY" -B tools/jetson_m16_acceptance.py export-ort --onnx "$EXACT_ORIGINAL_V3" --spec artifacts/cinque_v3.json --parser-source "$PINNED_NAV_MODELD" --sequence historical --frames 512 --out-dir "$NEW_ORT_HISTORICAL"
# Export bounded to a DIFFERENT fresh directory with --sequence bounded.
"$J" -B "$D/m16/repo/tools/jetson_m16_acceptance.py" measure-trt --development-root "$D" --engine "$D/build/cinque-v3.plan" --spec "$D/repo/artifacts/cinque_v3.json" --reference-dir "$D/m16/reference-historical-xz" --base-report "$D/results/base-10-1000/report.json" --parser-source "$D/m15/parser" --sequence historical --out-dir "$D/m16/result-historical" --release-private-file-cache
# Bounded invocation used reference-bounded-xz/result-bounded, same gates; failed before inference.
"$PY" -B tools/jetson_m16_analysis.py --reference-dir "$ORT_REFERENCE" --result-dir "$TRT_RESULT" --parser-source "$PINNED_NAV_MODELD" --spec artifacts/cinque_v3.json --zoompilot-source "$PINNED_VERIFIER_PY" --sequence historical --out-dir "$NEW_OFFLINE_ANALYSIS"
```

The verifier source must be accompanied by its exact pinned jetlink_spec.py. Fresh WSL CPU command supplied CARROT_NAV_REFERENCE_ROOT, CARROT_NAV_CANDIDATE_ROOT and CARROT_HOST_CANDIDATE_ROOT, then:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_jetson_m16_acceptance.py tests/test_jetson_m16_analysis.py tests/test_jetson_m15_semantic.py tests/test_carrot_nav_adapter.py tests/test_carrot_nav_wire.py tests/test_carrot_nav_loopback.py
```

Machine artifacts: artifacts/m16_numerical_acceptance_20261023.json, m16_worst_cases_20261023.json and m16_recurrent_turnover_20261023.json. Raw NPZs/logs remain ignored or under isolated m16; no ONNX/plan/timing cache/private access details entered Git.

Next precise stage: review the already-collected read-only memory/cache-residency evidence and define a separately approved bounded-run recovery; no new workaround is authorized here. On a fresh confirmed Jetson shell, the first read-only commands remain `cat /proc/meminfo /proc/buddyinfo`, operating hashes/current/ExecStart and comma offroad checks. Representative exact model-input tensors with privacy/provenance and approved semantic budgets are still required afterward. No M2 activation or optimization A/B.
