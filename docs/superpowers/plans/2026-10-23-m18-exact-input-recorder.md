# M18 exact logical V3 input recorder plan

> **For agentic workers:** Execute with TDD. Independent reader and hook work uses dispatching-parallel-agents after the format contract is fixed; a fresh final reviewer checks the integrated candidate. No agent may access or change devices.

**Goal:** Prepare a default-OFF, failure-isolated observer and exact offline reader for future256/512-frame representative input capture, without deploying or activating it.

**Architecture:** A single conditional footer in actual366 jetlink/model.py installs enabled-only wrappers. Capture immediately before existing Client.infer using its uint8 warped array and packed scalar views, plus camera metadata from CameraGapTrace.receive and existing Warp transforms. OFF leaves original function bodies/code objects and IPC untouched. A four-slot preallocated memfd SPSC ring carries fixed little-endian records to a standalone low-priority writer process; nonblocking socket credits provide ownership. Reader rejects incomplete/corrupt/gapped datasets and exposes four logical inputs, leaving recurrent state to the parity harness.

**Tech Stack:** Existing NumPy, Python3.10+ Linux memfd/mmap/socketpair/subprocess, existing StatefulState.step_into conversion, WSL CPU tests/benchmark; no dependency install.

**Spec:** User M18 request2026-10-23; AGENTS.md; M17/M16 numerical holds; artifacts/cinque_v3.json; exact actual366 source. M19 actual capture is a separate approval boundary.

## Global constraints

- Work only feature/jetlink-multimodel-carrot, clean initial remote/localaa30f9ea70a3e62538bcbc0a7d8c083f1dbfad52. Preserve main/old feature, no reset/force/user deletion.
- No actual comma/Jetson writes, install, activation, Params, output-directory creation, restart, inference/control/USB/road activity. Optional read-only actual checks only. Numerical pair unchanged and DO_NOT_INSTALL.
- Freeze existing M15 adapter and M16/M17 tools. New recording package, reader/bench tools, candidate generator/patch/tests/docs only. Reference366 read-only; never auto-rebase to moving latest Nav.
- Observer never selects/builds/downloads/executes V3. Existing V2/Nav nonstate preprocessing is compatible only after exact runtime layout gates; manifest identifies actual source model. Internal-only fallback exposes no borrowed Jetlink array, so no extra warp/force join; capture remains incomplete.
- Logical four arrays: new_img uint8[2,6,128,256], desire float32[8], traffic_convention/action_t float32[1,2]. No recurrent tensors, raw camera/GPS/route/cabin data.
- Startup explicit one-shot boot-bound expiring arm ticket, created only by a future offroad arming action and selected by an explicit environment variable. Consume atomically; same ticket/reboot cannot auto-rearm. Begin collecting may occur onroad under separate authorization; no control authority.
- Hot path only bounded metadata/type/shape checks, fixed memcpy and nonblocking credit/slot messages. No hashes/finite scan/JSON/compression/file operations/writer wait. First overflow/contention/shape failure aborts recorder only; no silent internal sequence drop.
- Defaults cap256, test512, hard1024; queue4 (bench4/8/16 memory/throughput). Record metadata144bytes+logical393264bytes=393408bytes/frame;4096-byte header. Reserve payload+64MiB before starting; no operating route path output.
- Writer validates every complete record/scalar finite/ID+timestamp continuity. No arbitrary jitter cutoff: expected50ms is diagnostic; actual camera source permits23/77ms intervals. Source-ID gaps/reset after start invalidate recurrence.
- Outputs exclusively fresh directory, preallocated frames.bin.partial. All data/manifest hashes and fsync before atomic COMPLETE hard-link publication; crash/truncation/no marker rejects. No output overwrite.

## Review focus

- Model input is copied at actual Client.infer boundary, not reconstructed from published desire/logs; original inputs/results/exceptions unchanged. Disabled install must leave original hot methods identical.
- Ring slot cannot be reused until writer ACK; producer never waits for credit or child. Writer slow/crash/EAGAIN cannot block model thread. Child drops inherited realtime scheduling and never imports GPU libraries.
- Source frame IDs/main-extra roles/SOF/transform matrices and reset flags must come from actual objects; model timestamp means main SOF. EOF is not stored. No inferred physical camera stream name where binding lacks it.
- COMPLETE must imply all exact expected records, finite/scalar contracts, source/frame continuity and file/hash/provenance consistency. Corruption, symlinks, collision, short write/fsync/manifest failure must reject.
- Host benchmark is CPU_HOST_BENCH only. No COMMA_REAL_CAPTURE/RT claim; M19 requires actual stationary overhead/observer-OFF/rollback approval before road recording.

## Task1 — fixed format and schema

Files recording/__init__.py, recording/format.py, tests/test_v3_input_format.py.

- [x] RED tests: authoritative spec/dtypes, fixed sizes/endian offsets/header magic, exact four-array bits and structural record validation; implement minimal format helpers.
- [x] Export interfaces: BASE_SHA, TARGET_SHA, SPEC_DIGEST, INPUTS mapping(name→shape,dtype), RECORD_DTYPE, RECORD_BYTES393408, HEADER_BYTES4096, expected_size(cap), header_bytes(provenance), parse_header(bytes), validate_record(record,previous), canonical(value), file_sha(path), dataset_digest(manifest).

## Task2 — recorder producer and isolated writer

Files recording/recorder.py, tests/test_v3_input_recorder.py; root implementer.

- [x] RED→GREEN Recorder(output,provenance,frames=256,depth=4, fault=None). Construction prepares fixed shared buffers and starts exec-only writer; observe(new_img,desire,traffic_convention,action_t,metadata) never raises/waits. stop(reason) nonblocking; close(timeout) only off hot path. Metadata fields index/IDs/model_timestamp/monotonic/SOFs/gap flags/selection/expected interval/transforms exact format.
- [x] Real process failure injection: insufficient/unwritable storage, slow/full queue, exception/crash, short write, fsync/manifest error, collisions, missing/dead child, invalid shape/dtype/finite/gap. Only own outputs/processes; model callback remains unchanged.
- [x] Writer stores frames and completion manifest with allowlisted provenance and full spec/source/dataset hashes. Four-slot bounded memory and credit ownership checked.

## Task3 — reader and replay compatibility (independent after format contract)

Files recording/dataset.py, tools/v3_input_dataset.py, tests/test_v3_input_dataset.py.

- [x] RED→GREEN validate/inspect/hash/strict complete-size/continuity reader, read-only random frame access. Reject incomplete/tamper/symlink/object/unknown privacy metadata/collision markers. Four-array ORT feed only; no state generation.
- [x] TRT input fill reuses existing jetlink.queues.StatefulState.step_into with supplied buffers; no new physical conversion, no recurrent state reset/write. Exact all256 uint8→FP16 bits and scalar signed-zero bits.

## Task4 — enabled-only actual366 observer and candidate patch (independent)

Files recording/hook.py, adapters/carrot/recorder.py, tests/test_v3_input_hook.py; generated patches/carrot-nav-v3-input-recorder.patch and manifest.

- [x] TDD runtime one-shot boot/expiry/offroad arm-ticket checks; consume once outside hot path, no automatic rearm/reboot/selection. Install only on explicit flag; exceptions contained.
- [x] Wrappers preserve base CameraGapTrace.receive/Warp.__call__/Client.__init__/infer behavior and exceptions; data comes immediately before infer. No original method replacement when OFF, no file/queue/process/copy. Runtime layout/spec/source identity gates, same-frame metadata/reset/gaps and existing source V2/Nav provenance.
- [x] Fresh disposable candidate from actual366,1 existing footer+new package. AST/code-object guard, byte inputs/results/exceptions OFF, enabled exact callback fixture. Reverse patch/forward restoration actually executed only disposable copies; full before/after/patch hashes.

## Task5 — benchmark, documentation, preservation and publication

- [x] CPU_HOST_BENCH copy/queue p50/p95/p99, writer throughput, ring/child memory,512-frame20Hz simulation/high-water; queue4/8/16 comparison. No real-time comma claim.
- [x] Write M18 design/report and sanitized artifact, M19 future approval/install/10stationary/256–512road/disable/rollback plan. Exact logical versus actual source model distinction and internal fallback capture limitation explicit.
- [x] New+frozen CPU smoke and independent integrated review. Frozen hashes/patch rollback/public privacy/diff/upstream checks, continuation update and same-feature normal commit/push; clean/remote/protected refs verification.

Execution ruling: detailed autonomous scope and prior no-extra-question preference supply implementation choices without another approval prompt. Separate deployment/vehicle authorization remains mandatory. Existing feature plus exclusive candidate/output paths provide isolation; no actual activation this session.

Execution evidence: code milestone 920a3f8fe7e5324466af9990dd93d2ed4fc10017; finalCPU218PASS, hostbench51220HzPASS, independent131PASS, no device actions. Publication/clean/remote/protected refs are final postcommit checks recorded in the final task response.
