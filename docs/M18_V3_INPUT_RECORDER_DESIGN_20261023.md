# M18 — exact logical input recorder, offline candidate

2026-10-23. **Offline candidate PASS; default OFF; DO_NOT_INSTALL without
separate M19 authorization.** No actual device access, installation, activation,
capture, GPU execution, USB inference or vehicle operation occurred in M18.
Numerical decision remains **PARITY_UNDETERMINED / M2 NO**. This prepares the
missing representative inputs; it does not resolve numerical acceptance.

## Source and exact hook

The patch base is actual carrot-nav
`366d6eae9aa9962104391e1d997fe956dea8f64d`, not latest Nav. Source was read from
pinned Git objects in the existing reference, with no source checkout changes.
The generated patch changes **one existing file**, appending an activation footer
to `openpilot/selfdrive/modeld/jetlink/model.py`, and adds five modules under
`openpilot/selfdrive/modeld/jetlink/input_recording/`. No original function or
class body is changed. Disposable tests compare original AST and compiled code
objects and execute the OFF footer with an import trap.

Actual366 `JoiningModel.run` calls `Warp(..., prepare=fill_inputs)` before
`Client.infer(images, packed, frame, reset, source_sof=...)`. Native `Warp`
returns the already materialized uint8 array after the same-frame scalar fill.
With activation only, wrappers observe CameraGapTrace.receive, Warp.__call__,
Client.__init__ and Client.infer. The capture copies that exact borrowed image
and packed scalar views immediately before the unchanged infer call. No second
warp, synthetic replacement or subsequent-log scalar reconstruction occurs.
Successful remote output is not required: these are inference-attempt inputs.

The currently executing source can be existing V2 or Nav. It is **not selected
or replaced by V3**. The startup source/spec gate accepts only the reviewed
nonstate client layout: image uint8[2,6,128,256], first packed fields desire,
traffic_convention, action_t, with prev_feat last. Exact source SHA/spec digest
must match the arm ticket. Existing Nav extra packed fields are left alone.
The manifest identifies `existing_jetlink_nonstate`, the actual source model
SHA and exact source spec digest separately from the V3 replay target.

This is an exact shared logical input tuple compatible with the V3 contract,
not evidence that V3 was running on comma. Internal-small-only fallback lacks
the borrowed Jetlink array and yields no complete capture. The recorder never
forces joining, warp preparation, model selection, USB activation or a restart
to obtain frames. M19 must first establish that an existing authorized path
actually supplies the tuple; if not, stop and design a separately reviewed hook.

Actual source evidence also includes `camera_gap.py`, `camera_sync.py`,
`compile_modeld.py`, `inputs.py`, `link.py` and native VisionIPC bindings.
Camera metadata comes from actual FrameMeta objects. The recorded model timestamp
is main SOF; both SOFs, both frame IDs, monotonic capture time, same/extra-source
roles, reset flag and the exact float32 Warp transform matrices are retained.
EOF is not stored. The binding does not expose the physical camera stream enum;
no road/wide label is guessed. Transforms are the actual converted Warp inputs,
not possibly higher-precision caller matrices. Their byte hashes can be computed
offline; no transform hash is calculated in the model thread.

## Contract and replay

Authoritative `artifacts/cinque_v3.json` canonical SHA256:
`6905b3d4efd18caf3df8c02898e9f3003a5adb11813a277f627b1decea8304e0`.

| Logical input | Shape | Stored dtype | Bytes/frame |
|---|---|---|---:|
| new_img | 2,6,128,256 | uint8 | 393216 |
| desire | 8 | little-endian float32 | 32 |
| traffic_convention | 1,2 | little-endian float32 | 8 |
| action_t | 1,2 | little-endian float32 | 8 |
| Total logical payload | | | 393264 |

Original V3 ONNX remains
`404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`.
M1 plan remains
`8f831b5af400a10aa35128ceeceac74595df1363bdcd6fd230957415f7e540aa`,
DO_NOT_INSTALL. Neither was loaded, rebuilt, moved or published in M18.

No recurrent arrays or state hashes are captured. An acceptance harness starts
each runtime from validated zero state and owns its recurrence. `Dataset.ort_feeds`
returns only the four exact logical arrays. `Dataset.trt_into` validates the exact
target spec/buffers, then reuses existing `StatefulState.step_into`; new_img can
enter the reviewed M1 FP16 physical buffer, while scalars remain FP32 and all
recurrent destination buffers stay untouched. All256 uint8 values, signed-zero
scalar bits and recurrent buffer sentinels are tested. No general uint8/FP16
rewrite or new conversion path was added. Real ORT/TRT replay is NOT_RUN.

## Activation and isolation

Default OFF means the footer makes one startup environment lookup. It imports
no recorder code and starts no thread/process/queue/copy/file. Original hot method
code objects, inputs, IPC, results and exceptions stay unchanged in fixtures.
Actual timing equivalence still requires stationary M19 measurement.

Activation candidate: `CARROT_V3_INPUT_CAPTURE` points to an explicitly prepared,
one-shot ticket. There is no Param and no persistent enable setting. Future
arming must occur offroad after fresh trusted state checks; the helper requires
that explicit proof and never reads/writes Params itself. The ticket expires
within60s by default (hard300s), is boot-bound, and is consumed before startup
validation. A retained exclusive consumption claim prevents modeld restart from
reusing it; reboot invalidates it. No ticket was armed in M18. Recreating or
copying tokens is not an authorization mechanism; tickets/hashes assume trusted
local operator ownership, not adversarial authentication.

Once separately authorized, observation may continue onroad to collect driving
inputs. Recorder has no CAN/control authority and does not alter controls,
selection, Jetson, USB or fallback. Any recorder setup/validation/I/O exception
disables only capture. Original method exceptions retain their original behavior.

| Design | Main benefit | Cost/risk | Decision |
|---|---|---|---|
| Writer thread in modeld | Simple queue/API | Python writer validation/hashing shares GIL and crash domain | Not chosen |
| Shared-memory producer + exec writer | Writer failures isolated; no writer GIL/disk wait in modeld | One process, bounded ring and credit protocol | Chosen |

The enabled startup preallocates/touches a memfd ring with four fixed slots and
uses a nonblocking UNIX datagram socket for slot ownership credits. ACK follows
validation and full write; a slot cannot be reused earlier. Model observation
does only structural checks, scalar views/metadata and fixed copies, plus bounded
nonblocking credit receive/send. There is no disk access, hash, finite scan,
compression, JSON, fsync, video codec or wait for a writer/slot in that path.
The first full queue or send failure terminates recording, never drops inference
or silently removes a frame from a complete sequence.

The child uses Python `-S`; it drops inherited realtime scheduling to SCHED_OTHER
and sets nice10 **before site, runpy or NumPy imports**. BLAS/OMP/MKL thread caps
are1. It retains inherited CPU affinity deliberately; no hardware-specific core
assignment is invented. Strict gates and synthetic benchmarks do not certify
actual comma scheduling. A recording is a bounded singleton: shared mapping/socket
remain until explicit off-hot close or modeld exit, and after terminal hook disable
an exited child can remain unreaped until then. This bounded lifecycle limitation
must be checked in M19; no cleanup wait is put in the model hot path.

The writer has a30s first-frame deadline, then nominal capture duration+10s for
frames, and polls cancellation every100ms. These govern only recorder abandonment;
no existing inference or transport timeout was changed. Before READY, capture
has not started. Thereafter any index/frame ID gap, nonmonotonic timestamp,
camera-role change or second reset invalidates the sequence. Nominal cadence is
20Hz (`DT_MDL=.05`); actual camera pairing permits alternating23/77ms intervals,
so timing percentiles are diagnostics, not an invented jitter rejection threshold.

## Storage, integrity and privacy

Fixed layout:4096-byte canonical header followed by393408-byte little-endian
records (144 metadata bytes +393264 logical bytes). Random access needs no ZIP,
per-frame files or pickle. Caps: default256, benchmark512, hard1024. Depth4 uses
1577728 bytes including control; depths8/16 use3151360/6298624. Each cap is exact,
not a silent maximum followed by accepted early truncation.

| Frames | Nominal20Hz span | frames.bin bytes | Minimum free-space gate |
|---:|---:|---:|---:|
| 256 | 12.8s | 100716544 | 167825408 |
| 512 | 25.6s | 201428992 | 268537856 |
| 1024 | 51.2s | 402853888 | 469962752 |

The binary size includes its header and record metadata, excluding the final
manifest and filesystem overhead. Reader caps manifest size at64KiB; COMPLETE
hard-links that same manifest inode. The additional64MiB reserve covers bounded
manifest/metadata and margin. Existing directory, symlink ancestors, unavailable
space, allocation or permission failures refuse only recorder startup. No old
output or route is removed to recover space.

Writer creates a fresh exclusive0700 output directory, `frames.bin.partial` and
`status.partial`. It validates finite scalars/transforms, exact records and full
continuity off-thread, then flushes/fsyncs the full binary, calculates SHA256 and
writes/fsyncs a canonical manifest. No-overwrite hard links publish binary and
manifest; directory fsync precedes the final COMPLETE hard link. No fallible
recording work follows that last publication. Failure/crash leaves no valid
COMPLETE; even if final filenames exist they are not an accepted dataset.
Power loss may lose the last marker, producing a safe false negative.

Reader requires exactly frames.bin, manifest.json and COMPLETE, equal complete
manifest bytes, exact full size/hash/header/spec/provenance and every record.
It rejects partial/truncated/mutated/symlink/nonregular inputs, duplicate/unknown
JSON metadata and privacy fields, and opens directory components without following
symlinks. Frame snapshots are immutable and survive reader close. Source aggregate
digest binds its file-hash mapping. SHA integrity is not proof of camera provenance;
future acceptance also needs trusted capture/transfer records.

No route name, GPS, address, raw camera buffer, cabin image, identity, full rlog or
recurrent tensor is stored. Preprocessed visual tensors still contain sensitive
scene information: keep privately in a separately approved directory, not Git.
Recommended future root `/data/media/0/v3_input_capture/` is **only a proposal**;
M19 must inspect the actual mount/permissions/free space before creating it.
Operating realdata/runtime/cache remain separate. Local offline `.captures/`,
`.candidate/` and `.reports/` are ignored. Public evidence includes only anonymous
IDs/hashes/counts/code/test metrics; all benchmark datasets were temporary fixtures.

## Validation and reproducible commands

Fresh final WSL Python3.12.3 suite: **PASS218 / FAIL0 / SKIP0**. New M18:131
(format8, recorder20, reader74, hook29); frozen prior smoke87. Repeated runs and
old708 are not added. CPU_FAKE/FIXTURE only. Failure tests include unavailable
output, space refusal, full/slow queue, writer exception/process crash, short write,
fsync/manifest failure, collisions, gaps, wrong shape/dtype, nonfinite scalar,
disabled import/copy invariant, source drift, FIFO ticket and replay tampering.
Real subprocess writer/reader and actual366 camera-sync/Warp/Client method bodies
run with only camera/GPU/IPC boundaries substituted. No COMMA_REAL inference claim.

Independent review found and fixed inherited realtime import priority, FIFO ticket
blocking and inconsistent aggregate source digest. Its final independent131-test
run passed with no remaining blocker. One initial smoke invocation omitted the
three required reference/candidate variables:18 setup failures,187 passes; rerun
with the correct frozen roots passed218. Bare whole-repository pytest collection
remains unsupported because legacy `test_backport.py` calls sys.exit during import;
this is not reported as a full-suite PASS. No existing test/tool was altered to
hide those conditions.

From the repository root, with PY pointing to the existing reviewed WSL Python:

```sh
export PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1
export CARROT_NAV_REFERENCE_ROOT=.reference/m15-carrot-nav-366d6eae
export CARROT_NAV_CANDIDATE_ROOT=.candidate/m15-carrot-nav-complete-366d6eae
export CARROT_HOST_CANDIDATE_ROOT=.candidate/m1-carrot-20261023-frozen/candidate
"$PY" -m pytest -q -p no:cacheprovider tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py tests/test_recorded_driving_gate.py tests/test_jetson_m16_acceptance.py tests/test_jetson_m16_analysis.py tests/test_jetson_m15_semantic.py tests/test_carrot_nav_adapter.py tests/test_carrot_nav_wire.py tests/test_carrot_nav_loopback.py
"$PY" -m tools.benchmark_v3_input_recorder --output .reports/m18-20261023/host-benchmark-new.json
"$PY" -m adapters.carrot.recorder .reference/m15-carrot-nav-366d6eae .candidate/m18-recorder-new
"$PY" tools/v3_input_dataset.py validate /path/to/private/complete-dataset
```

All candidate/output destinations must be fresh. These are offline commands;
none deploy, arm a ticket or load an engine. `Dataset` and memfd writer require
supported POSIX/Linux APIs; Windows host tests run under WSL, not native Windows.

Final CPU_HOST_BENCH (x86_64 WSL, NumPy2.5.4, synthetic inputs, temporary filesystem):

| Component | p50 µs | p95 µs | p99 µs |
|---|---:|---:|---:|
| Fixed copies + metadata | 55.077 | 80.995 | 108.648 |
| Nonblocking socket send + measurement | 29.825 | 38.321 | 50.372 |
| Whole observer incl polling/checks | 146.792 | 197.011 | 242.069 |

512 frames20Hz completed and strict reader validation PASS; elapsed26.416s includes
writer finalization. Queue high-water1/4, effective7.272MiB/s at paced source.
Unpaced128-frame writer+finalization throughput: depth4/8/16 respectively
154.615/115.477/131.826MiB/s; one host run, not a robust ordering of disk speed.
Four slots are adequate for this tested fixture and minimize resident ring space;
larger queues only delay invalidation when the writer cannot keep up.
Sampled writer RSS35,304KiB sustained; peak parent232,512KiB includes offline
reader mapping201MB. Lifetime child RSS also includes pre-exec inheritance and
must not be interpreted as live writer-only memory. None is COMMA_REAL performance.

## Patch, rollback and moving upstream

Patch: `patches/carrot-nav-v3-input-recorder.patch`; hash
`3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee`.
Full before/after hashes and source pins are in the M18 JSON artifact. The actual
disposable-copy test runs reverse-check, reverse-apply, verifies original bytes,
then forward-check/apply and verifies all six after hashes. No actual comma patch
or rollback ran. M15 adapter/numerical tools remain frozen.

Start→end upstream observations:

| Source | Start | End |
|---|---|---|
| carrot-nav | 3da803836786acdd9f6699ce75ef1134d1aabc6e | 810e14aaf51176f1a50a113939dc2e70907b394b |
| carrot-wip | 3fdf82b268d69db31c1bf6d4137198d65cd548fe | dfab65d03fcd7100f572fe9e6908f4c6d1e988f6 |
| carrot-jetson | d0dc96fa32410403dfb2fefff3e2909c11ec109b | same |
| zoompilot/jetlink | d24328d849b0e5154b55f149dc18c5dfe8bd79cc | same |
| external review | a890f6df1bd3eb0478754c68d8b5f92f15e8b722 | same |

Relevant end drift was fetched/diffed in a local reference without changing its
checkout. Runtime/tool scope excludes AGENTS.md and two documentation files:
Nav9files,+659/-7 (whole diff12files,+827/-7), with parser full-output precedence for N16-size collisions,
ADB handoff, mobile DHCP cleanup race and USB power/setup tests. WIP7files,+641/-6:
same tooling changes (whole WIP diff10files,+809/-6). No additional modeld/Warp/inputs/camera-sync hook change
appeared in this start→end range; earlier latest-Nav shared-input drift remains.
No tooling/USB setup was executed or imported into this feature. Actual366 remains
the explicit pin; latest Nav/WIP recorder compatibility is NOT_VALIDATED and the
runtime HEAD gate rejects them. Existing full rolling-adapter baseline was not
advanced by this recorder-only session.

M18 operating preservation is by scope: no comma/Jetson connection or device write
was made. Actual live HEAD/flags/processes/hashes were **not freshly re-observed**;
the earlier M17 checkpoint is historical evidence only. Ready for **M19 separately
authorized parked preflight: YES**. Actual capture and road use remain NOT_RUN;
M19 must apply every preflight/measurement/rollback gate in its own plan.
