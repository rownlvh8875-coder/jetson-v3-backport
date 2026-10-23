# M1.7 actual recorded driving source audit — 2026-10-23

**PARITY_UNDETERMINED. Ready for M2 parked USB: NO. DO_NOT_INSTALL.**

Actual comma recordings were inspected before any cloud discovery.88 routes /
1037 segments /4403 files were inventoried, and5 recent routes supplied one
nonempty middle rlog each. The5 untouched rlogs were copied privately and
size/SHA256 verified:61448059 bytes,431355 events,6000 road/wide camera metadata
frame pairs. **Zero V3 input frames and zero representative model sequences
could be reconstructed.** No original road/wide video exists in the confirmed
route tree, and both camera image payloads are empty in all5 sampled logs.

ORT/TRT, numerical parser parity and anomaly reproduction on recorded input are
**NOT_RUN**, not PASS or numerical FAIL. The new evidence narrows the missing
representative-input blocker to camera pixels and still-unvalidated historical
preprocessing/scalars. It does not replace the M16 numerical hold.

## Targets, access and safety

| Item | Exact identity / status |
|---|---|
| Actual comma | carrot-nav366d6eae9aa9962104391e1d997fe956dea8f64d |
| Development start | 5bd9bcb1b10d63c35eb6b16bd35ae8ae4ce0626f, clean and remote-equal |
| New provenance helper | 66b220344ec1f4ce93e21b4d64611e1f08273acc |
| Original V3 ONNX target | 404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4 /766354845bytes |
| Existing M1 plan target | 8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa /768580676bytes |

The target pair is unchanged from M1/M16. M17 did not open, execute, rebuild or
publish either model/plan, or access Jetson. Previous exact-identity evidence is
retained; it is not a fresh M17 Jetson hash attestation.

Every device probe and each raw-log download preflight executed the actual read
commands, required exact strings1/0, and required actual HEAD366d6eae:

```sh
cat /data/params/d/IsOffroad
cat /data/params/d/IsOnroad
```

All checks returned **IsOffroad=1 / IsOnroad=0**. Existing read-only Carrot web
terminal access was reused with fresh owned sessions, history/bytecode disabled;
the prior SSH agent/relay had already been closed in M16. This session did not
claim or establish an active direct SSH connection, copy keys or change access
configuration. The existing raw-download GET handler streams original files
without log parsing, ffmpeg, thumbnail generation or file creation. No upload,
browser-video preparation or recording configuration endpoint was invoked.

No manager/modeld/camera/service restart, source checkout, Params write, route
deletion/modification, USB P3 inference, vehicle/CAN action, GPU load, package or
optimization change occurred. All copied logs and raw metadata remain under the
ignored private M17 report area on the PC; no video was copied or committed.

## Actual storage and candidate selection

The actual pinned `system/hardware/hw.py` defines device log_root as
`/data/media/0/realdata/`; the directory was confirmed on the device before use.
All recognized segment directories were read for file name/size/mtime metadata.
Routes were grouped from actual segment directory names and ranked by their
latest file modification time. Actual names, timestamps and location data remain
private. The recent5 route candidates contain29/105/103/83/14 segments.

| File | Count across all1037 segments |
|---|---:|
| rlog.zst | 1037 |
| qlog.zst | 1037 |
| qcamera.ts | 1036 |
| dcamera.hevc | 1036 |
| fcamera.hevc | **0** |
| ecamera.hevc | **0** |
| rlog.lock | 83 |
| qcamera.ts.lock / dcamera.hevc.lock | 87 /87 |

Lock-file presence was not treated as proof of complete/healthy recording. For
each selected route, a nonempty rlog near the middle of its actual segment list
was selected and successfully parsed. This is a5-minute telemetry sample, not a
claim that all334 segments in those routes or all88 routes were log-decoded.
Searching additional rlogs cannot restore the camera files absent from the
entire confirmed storage tree; no wider user-file or Google Drive search ran.

| Privacy-safe candidate | rlog bytes | Original = copy SHA256 |
|---|---:|---|
| REC_CANDIDATE_01 | 12455340 | d0d2b986188d647f38e623b6fc36d11d951c11a530052c557569b83745052ee2 |
| REC_CANDIDATE_02 | 13144070 | a284f5fe3db444359110cb7e96e429466217468f2d6df6b80d5418d01ec94064 |
| REC_CANDIDATE_03 | 13287446 | abc0c8c38b155713d698c3e1c50961ddbacf804883529be8a6e690dfb8e00f9b |
| REC_CANDIDATE_04 | 10890368 | cad6b4a584a91946116cc10a93e2f3bba1fed4e82bbd7b9cdd7d5ceac87e723b |
| REC_CANDIDATE_05 | 11670835 | 9f9dabe6d1fc28e04dc38e34c5b44d236a058626debfb957fdb4d0ead910a2a3 |

Each source was stat-checked around read/hash, copied to a fresh exclusive PC
file and rehashed, then source-hashed again at final preservation. All5 copied
rlogs and the selected5 qlogs' original hashes are unchanged. No qlog/video copy
was needed for the blocked model-input path.

## Observed conditions, without invented scene labels

The actual comma Python3.12/pycapnp2.1.0/zstandard0.25.0 parsed originals using
the current `openpilot.cereal` schema and `Event.read_multiple_bytes`, matching
the raw decompression/reader format in the pinned logreader. Only whitelisted
camera/scalar/model/radar fields were analyzed; no GPS field values were read
into the summaries or published. Source byte identities also bind PC copies.

Each sample contains1200 road and1200 wide camera metadata messages with
nonzero timestamps, increasing frame IDs without positive gaps, and1199 positive
timestamp steps per stream. Neither stream contains nonempty `FrameData.image`.
Each sample also has240 finite three-element liveCalibration records.

| Candidate | Logged vEgo range m/s | Standstill fraction | Radar lead status true / false | Published meta.desire | Desire transitions |
|---|---|---|---|---|---:|
| 01 | −0.003045..6.993724 | 0.386424 | 1200 /0 | none1200 | 0 |
| 02 | −0.002912..12.486046 | 0.240627 | 1114 /86 | none1157, turnLeft44 | 2 |
| 03 | 24.241556..28.891781 | 0 | 1200 /0 | none1201 | 0 |
| 04 | 22.106276..22.257536 | 0 | 7 /1193 | none1200 | 0 |
| 05 | 2.850598..13.504434 | 0 | 667 /533 | none1079, turnRight46, turnLeft75 | 5 |

These are recorded telemetry observations, not validated visual scene labels or
V3 inference. Radar lead status is `radarState.leadOne.status`; it does not prove
visual lead correctness. All sampled lane-change states are off. No logged
standstill→positive-motion transition was found in these middle segments, using
a tested state machine that retains a pending standstill through zero/negative
speed release samples. This does not establish that the rest of each route lacks
stop/go or lane changes. Straight/curve/complex-road categories were not invented
from an arbitrary steering-angle threshold. Negative tiny vEgo estimates are
reported as logged rather than silently clamped or classified as reverse motion.

The recorded initData source is e330e8552d4ca1927c6c3d476cb74f46f8bbd1a4 for01
and ec36d5e56ea8b501a41d3a817cbfb5fd13ff3939 for02..05, all carrot-nav.
Candidate01 records dirty=false; **02..05 record dirty=true**. The latter SHA
values alone cannot attest their historical source bytes; those unrecorded
changes are an additional reconstruction-provenance limitation. They predate
actual366; recorded model outputs are not target V3 outputs.
Historical `RecordRoadCam` is0 in all5 samples. Current source gates full-road
recording on>0 and wide recording on>1, consistent with the observed absence;
this is not a claim to have replayed or fully audited those older runtimes.
No current or historical parameter was changed.

## Deterministic input reconstruction audit

Actual source pins and SHA256s are in the artifact. Relevant sources are
[loggerd camera encoders](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/system/loggerd/loggerd.h),
[modeld](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/modeld.py),
[native Jetlink camera wrapper](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/jetlink/model.py),
[warp](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/compile_modeld.py),
and [scalar population](https://github.com/ajouatom/openpilot/blob/366d6eae9aa9962104391e1d997fe956dea8f64d/openpilot/selfdrive/modeld/jetlink/inputs.py).

| Required input/provenance | Evidence | Result |
|---|---|---|
| Selected original camera pixels | No fcamera/ecamera anywhere; camera message images empty | **MISSING** |
| qcamera substitute | Existing ffprobe: H.264,526×330,20fps; current logger source also specifies526×330 | Insufficient: reduced road view cannot recover missing originals or wide view |
| Driver camera substitute | dcamera is driver-facing per logger source | Rejected |
| Frame identity/timestamps |1200 messages per stream per sample, hash-bound IDs/timestamps | Metadata present; no decoded-image alignment possible |
| Calibration/transform |240 finite rpyCalib records per sample; os04c10 sensor metadata | Present, not reconstructed/validated per frame |
| traffic_convention | Recorded DMS isRHD all0 | Present, not frame-associated into model inputs |
| desire | Published meta.desire and transitions exist | Historical pulse input not reconstructed |
| action_t | Historical delay/smoothing keys and liveDelay records exist | Exact dynamic input history unvalidated |
| recurrent initial state | Required zero start followed by own continuous state | Not created/run |
| warp/preprocess | Actual current source and byte hashes inspected | Source verified; no warp executed |

The target `new_img` is UINT8[2,6,128,256]. The native path uses selected main/
extra camera buffers, padded NV12 geometry, calibration/device-sensor intrinsics,
historical yaw trim, nearest rounding/clamping, and six-channel Y00/Y10/Y01/Y11/
U/V packing. Actual stream selection can reuse a physical source in wide-only
mode; the two model views do not universally imply two distinct sensor files.
Neither original road nor wide source is available here in any case. Upsampling
qcamera or duplicating it would not establish the required preprocessing parity.

modeld takes DH.desire before inference, then updates DesireHelper and publishes
the new meta.desire afterward. `fill_inputs` clears class0 and forms rising-edge
pulses against previous desire. Published desire values/prediction argmax cannot
be copied blindly as the same-frame V3 input. `traffic_convention[int(isRHD)]=1`.
`action_t` is `[lat_delay_dynamic + .075, long_delay + .075]`, since DT_MDL=.05
and action_delay=.025; lateral delay/smoothing changes dynamically, and historical
Params/source matter. No arbitrary fixed action range/default was substituted.

All8 reconstruction proofs remain unvalidated as a complete dataset. The gate's
missing list means **not proven**, rather than claiming all8 data sources are
absent. The decisive missing source is pixels. No new_img tensor,128/256-frame
dataset, zero-state recurrence, ORT reference, TRT execution or parser result was
fabricated from metadata, existing P2 outputs or random data.

## Numerical decision

| Check | M17 result |
|---|---|
| Actual recorded source inspection/copy | PASS, metadata/telemetry only |
| Representative exact V3 input sequences | **0** |
| Reconstructed recorded input frames | **0** |
| ORT original V3 | NOT_RUN — input reconstruction blocked |
| Existing TRT10.3 plan / actual Jetson | NOT_RUN — no device access needed |
| Plan near/mid/far, direct leads/probability, action | NOT_RUN |
| Desire categorical disagreement/margins | NOT_RUN |
| Recurrent turnover/hidden drift | NOT_RUN |
| Actual parser parity | NOT_RUN |
| Synthetic anomalies reproduced on recorded input | **NOT_TESTABLE**, not a negative reproduction result |

M16 synthetic stress remains a separate population and was not rerun or pooled
with recorded telemetry. Its exact plan, numerical hold, absent approved
semantic budgets and bounded-deserialize resource hold remain unchanged.
**PARITY_UNDETERMINED / M2 NO**: lack of representative inputs cannot establish
either acceptable behavior or a repeatable V3 behavioral failure.

## Preservation, tests and continuation

**Operating comma preservation PASS within the measured scope.** Before/after
actual branch/HEAD/offroad flags and tracked working tree are identical. All88
routes/1037 segments/4403 files retain their name/size/mtime inventory digest
`f29eeb1934517f92bbd365d12019191fba27dbb36efadfa13d3514f3f1cc39d6`.
Selected10 rlog/qlog original content hashes and all5 copied rlogs match.
Five launcher/manager/modeld/warp source hashes match actual366 Git objects and
remain unchanged;3 operating process identities remain identical.15 model files
were additionally content-hashed in a later before/after window and are identical.
This is not a full content hash of every route/video or whole runtime, nor a
fresh session-start hash attestation for all15 model files. No service operation
or current source/cache/model mutation was issued. Jetson was not accessed.

Private shell preparation issues were retained: oversized input/terminal output
limits, a filename-counter bug, and one concurrent tmux creation failure. They
were confined to owned read-only helpers; new source compression/limited returned
detail corrected transport limits. A first incomplete-command terminal remained
after an initial close attempt; final audit detected it and removed only that
exact locally proven owned session. No other owned M17 sessions remain; final
offroad/HEAD checks passed. No operating process was terminated.

New pure helper/tests cover exact offroad strings, correct camera classification,
unvalidated scalar rejection, no metadata→input promotion, no implicit numerical
approval, standstill transition counting, anonymous identity/privacy fields,
SHA/count validation and exclusive output/no-NaN serialization. Fresh **87 PASS /
0 FAIL /0 SKIP**:12new provenance cases plus75 unchanged M16/M15/Nav adapter,
wire and loopback cases. Prior708 and reviewer repeats are not added.
Independent read-only final review verified copy hashes, counts, source pins,
privacy and scoped preservation. Its historical all-clean wording finding was
corrected to the actual dirty flags; no remaining actionable finding. No reviewer
device activity or repeated tests are included in these results.

```sh
# Existing WSL interpreter; provide the same3 frozen candidate/reference roots as M16.
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_recorded_driving_gate.py tests/test_jetson_m16_acceptance.py tests/test_jetson_m16_analysis.py tests/test_jetson_m15_semantic.py tests/test_carrot_nav_adapter.py tests/test_carrot_nav_wire.py tests/test_carrot_nav_loopback.py
```

The standalone reader used only read-only `Path.open('rb')`, zstandard stream
decompression and the actual CapnProto schema; raw byte/SHA evidence is above.
Private command/capture/copy manifests remain in `.reports/m17-20261023/` for
authorized continuation; raw route names, timestamps, videos/logs/coordinates,
addresses/credentials are excluded from Git. No dependency was installed.

Start and final upstream re-queries match: Nav3da803836786acdd9f6699ce75ef1134d1aabc6e,
WIP3fdf82b268d69db31c1bf6d4137198d65cd548fe,
carrot-jetsond0dc96fa32410403dfb2fefff3e2909c11ec109b,
zoompilotd24328d849b0e5154b55f149dc18c5dfe8bd79cc,
external reviewa890f6df1bd3eb0478754c68d8b5f92f15e8b722.
No adoption or frozen adapter modification; latest-Nav compatibility remains
unrevalidated as explained in M16. Publication results are recorded
in the handoff, which must be read first next session.

**Next precise action:** obtain one approved recording containing at least256
consecutive original selected road/wide frames (or exact preprocessed V3 input
tensors), with timestamp/calibration/scalar provenance, then re-enter M17 input
validation. Any new recording configuration change is a separate authorization;
none was made here. Do not start M2 or change RecordRoadCam automatically.
