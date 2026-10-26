# M19-C0.5 — exact24c HUD / host-release recorder review

2026-10-26 · **PASS (OFFLINE CPU_FAKE/POSIX/source review)**

The exact24c future OFF-deployment candidate is ready. Recorder logic is
**RECORDER_LOGIC_REUSABLE** and the dataset remains **FOUR_INPUT_SUFFICIENT**.
No actual comma/Jetson connection, deployment, storage change, ticket, capture,
restart, Params/updater operation, model execution or model switch occurred.
Vehicle10 remains NOT_RUN; PARITY_UNDETERMINED; M2=NO.

Development started at `7f327c2ecf44ea372bdc38d5e8aa3b6754983294` on `feature/jetlink-multimodel-carrot`,
equal to upstream/remote. Initial status contained only app-managed private image
attachments; their bytes were preserved and excluded using local `.git/info/exclude`.
The subsequent start gate was CLEAN/equal. No public ignore rule or historical
evidence was changed. Result commit is resolved without a circular self hash:
`git log -1 --format=%H -- artifacts/m19c05_24c_hud_host_compatibility_20261026.json`.

## Exact public comparison

`5bbbe160822c7cae4245d7a8e96b40d158941ff7` → `24c1ba5e4b3428f56fa0e402f5a10097e2e94c32` is **5 ahead /0 behind /5 commits**,
with exactly8 changed paths,190 additions and7 deletions. Local Git object
comparison independently verifies the expected chain:

- `708adb3fa6f5adde9fba68dda98a56513d0df2f1` — Bound Jetson HUD software encoder concurrency
- `9de4c1e03814a0cf594651b806093564a5db3428` — Install scheduler test dependency in HUD CI
- `c3f2aeebf6acc645da9b499724e902dbc80401a5` — Include hardware imports for Linux scheduler coverage
- `e5abf9928f441e16af3e5bb7a704473af2a7cf1f` — Publish measured Jetson HUD encoder runtime
- `24c1ba5e4b3428f56fa0e402f5a10097e2e94c32` — Record final Jetson HUD encoder validation

All eight changed files were reviewed:

- `.github/workflows/jetlink-checks.yaml`
- `AGENTS.md`
- `docs/jetson_regression_isolation_20261024.md`
- `openpilot/selfdrive/carrot/cluster/cluster_h264_pipeline.py`
- `openpilot/selfdrive/carrot/cluster/main.py`
- `openpilot/selfdrive/carrot/tests/test_cluster_ffmpeg_threads.py`
- `openpilot/selfdrive/modeld/jetlink/host_release.json`
- `tools/jetlink/hud.py`

CI changes add scheduler dependencies/import coverage and encoder tests; upstream
AGENTS/docs record historical measured results. These are reviewed source data,
not newly measured hardware results or permission to run their operations.

All14 required inference/transport hot-path files are byte-identical; Python AST
also matches, and the C writer bytes match. All prior33 source pins were recomputed.
The only changed existing pin is `openpilot/selfdrive/modeld/jetlink/host_release.json`:
`2f36e9a081ea0591e937b8631208652365eadf3dca559157d7a4c8e03a639516` →
`9b7d72f5f875edfb2a43a8c5695c617671bbcd4e6add78acef9c50163a85a2ee`.
The artifact contains every old/new hash, AST result and all41 new pins.

## Recorder semantics and frozen dataset

The local `link.py:Client.infer` API and generated wrapper remain:

```python
@functools.wraps(original_infer)
def infer(self, image, packed, frame, reset=False, source_sof=0, nav_metadata=None):
    capture.observe(self, image, packed, reset)
    return original_infer(self, image, packed, frame, reset,
                          source_sof=source_sof, nav_metadata=nav_metadata)
```

Successful observation occurs once immediately before one original call; downstream deferred
map preparation occurs inside that original path. Metadata is passed as the same
object once, without normalization, validation or retry. `None`, invalid metadata,
observer/original/transport/shared-input exceptions and `functools.wraps` behavior
retain their source ordering. If the observer raises, original infer is not called;
if original infer raises, that one call propagates without retry. Unsupported
keyword rejection remains covered.

Both CPU-overlap orders still finalize same-frame scalars before infer; fill runs
once. Warp callback/None/output-buffer forwarding, shared image object identity,
socket byte identity, camera-pair/reset association and first12 exactness are
unchanged. Five deliberately distinct sequential scalar hashes and the actual
desire pulse0/rise/held/fall/rise=0/1/0/0/1 are verified; no reconstruction or lag.

Deferred NAV behavior is unchanged: source image/first12/navigation are CURRENT;
source full packed map is current. A valid host cache hit can intentionally use
prior staged map pixels after wire substitution. Whole EngineHost packed equality
is therefore not claimed on cache hits. Route/timestamp/expiry/reset/gap/fallback,
flush and request lifetime behavior retain the exact5bb source semantics.

The frozen V3 ONNX SHA
`404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`
graph proof from C03/C04 is reused as historical static evidence; no ONNX was read,
built, loaded or executed anew. It has four stored inputs plus three recurrent
queues, with no nav_map/navigation graph dependency. Stored fields stay exactly:

| Field | Dtype | Shape |
|---|---|---|
| new_img | uint8 | (2,6,128,256) |
| desire | float32 | (8,) |
| traffic_convention | float32 | (1,2) |
| action_t | float32 | (1,2) |

The prompt's traffic label retains canonical stored name `traffic_convention`.
No nav_metadata/nav_map/navigation/recurrent/HUD/encoder data is added. Parity
replay still needs matched initial reset/state, ordered feedback and gap/session
continuity; arbitrary mid-session images plus zero state cannot recreate history.

N16 model `01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a` and canonical spec `63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`
are unchanged: stateful=true, five server-owned state pairs, packed65595,
warped(2,6,128,256), first12 desire8/traffic2/action2.

## HUD content boundary and limits

Classification: **HUD_DISPLAY_PATH_ONLY; no new model-buffer mutation/alias path**.
The common encoder defaults to automatic0; Jetson HUD prepends1 and a trailing
user0 overrides it. Valid range0..16 applies only to libx264 filter/encoder pool
options. Format, dimensions, FPS, bitrate, GOP, protocol and deadlines are unchanged.

Camera preview reads an alias of camera data without writing it, then uses advanced-index/allocated
preview buffers and JPEG/base64 bytes. A separate publisher serializes events.
The host handles HUD snapshot bytes and returns before inference dispatch; the
renderer reads fresh bytes/JSON and renderer-local cereal builders. NAV preview
PNG files are distinct from inference deferred-map packed data.

Raylib renders a local display texture and borrows its RGBA buffer until context
unload. `main.py` submits that display buffer synchronously within the context.
The pipeline uses display RGBA or its own padding allocation; synchronous
`os.write` copies bytes into a separate FFmpeg process pipe. Encoded stdout sends
display chunks. The modified pool receives no model image, packed ndarray,
camera Warp result, shared slot or shared-memory descriptor. Model Warp fencing
and connection nonce/generation/busy/completion ownership remain separate.

Exact source anchors: hud_camera37–50/93–101; hud_protocol29–48/145–176/203–221;
server163–208; hud99–127/140–171/227–235; cluster_renderer2336–2365/2639–2703;
main1823–1839; pipeline988–1049/1291–1317/2224–2260. These named source files
are pinned where relevant. The new41-pin set is old33 plus HUD pipeline/main,
hud/protocol/camera/navi/nav_map and cluster_renderer; no volatile docs/test pins.

Eight focused cases run the full pinned H264UsbPipeline start/submit/write/stdout/
close path with worker0/1 and four transport/model partitions. A bounded pipe
child and independent source thread progress across all five model observations
per case. Inactive/active model hashes match an independent input oracle:
recorded image/scalars == original infer == EngineHost four-field hashes.
All40 active model frames retain exact identity and no frame lag/alias mutation.

This is CPU_FAKE pipe evidence: the child hashes RGBA and emits AUD marker bytes;
it does not encode H264. Native FFmpeg is unavailable, so native codec/visual
validation is BLOCKED and excluded. The source separation does not promise
scheduling isolation: CPU/cache/GPU/USB contention, backpressure, arrivals,
drops/fallback/map TTL timing and lossy encoded output can differ. No20Hz,
hard50ms, physical USB/GPU or latency improvement is claimed.

## Repository host release

Expected source changes `0fb6c73926ef8d54f8434108bd060d47de011cbe` → `c3f2aeebf6acc645da9b499724e902dbc80401a5`.
Bundle SHA changes `2f51b10b2d6a356d39e0d923e66633a3e80c5b92096603713b39fa540db40162` → `2e784fcd8ade8d0242ca585395d973e6b7f39152cebf8683d5098312e633c973`;
size64748504 →64749015 (+511). URL/signature change; both complete metadata
records are preserved in the artifact. Both declared runtime tags remain
aarch64/L4T36.4.7/TRT10.3.0; N16 model URL/SHA/size814591107 are identical.
This is repository metadata comparison. Bundle download/hash/authenticity,
signature verification and binary ABI load validation were NOT_RUN.
**ACTUAL_JETSON_HOST=NOT_RUN**, separate from REPOSITORY_EXPECTED_HOST.

## Distinct candidate and reversible migration

Profile **RECORDER_24C_HUD_HOST_V1**, exact base `24c1ba5e4b3428f56fa0e402f5a10097e2e94c32`,41 source pins.
All generated recorder function/class ASTs equal5bb. Only format.BASE_SHA and
hook.SOURCE_PINS/PACKAGE_PINS/FOOTER_TEMPLATE change. init/recorder/dataset bytes
are identical. The model is pure24c plus exactly one hook-SHA-bound footer.

Future PRE is pure24c tracked model plus surviving5bb-bound package, with no
footer. Earlier private drift evidence supports this expected layout only;
future actual verification must freshly check it. This is not an a559/old366 PRE.
The forward patch touches exactly model.py/format.py/hook.py; the reverse restores
that complete PRE byte-for-byte, without reset/clean or index mutation.

- Forward: `patches/carrot-nav-24c-v3-input-recorder.patch`
  SHA256 `28e68ced23a9ca9f0bea33c430346801272ae17532a73ffacf7c33ed5099162d`
- Reverse: `patches/carrot-nav-24c-v3-input-recorder.reverse.patch`
  SHA256 `643eaa68f5c579d8874032817279a59c0754b6c98aa694fcc76949d569489d40`
- Full PRE/AFTER/source gate manifest:
  `artifacts/m19c05_24c_surviving5bb_deployment_manifest_20261026.json`
- Strict profile reader: `tools/v3_input_dataset_24c.py`; wrong5bb binding rejects.

Expected AFTER six hashes:

| File | SHA256 |
|---|---|
| model.py | `71abe14b79c0336b67d58ba3ef8bb3bd4b82458915aada29ec4127dba0bab4f9` |
| __init__.py | `e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca` |
| format.py | `72978fd31a4e58081ce7e570ca527d50a7a403d51278f4c8122a0ae64ee1f31e` |
| recorder.py | `d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada` |
| dataset.py | `25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7` |
| hook.py | `fec2efd042475952a9e4c81a84f8d58c3bd3610437bfd6e17d7c70663c8663f5` |

Disposable Git apply-check/forward/hash/syntax/footer/reverse/byte-restoration
roundtrip PASS; touched set exactly3 and index unchanged. No-ticket path returns
before recorder imports/tensor copies/process creation: writer0/frames0/datasetNONE.
Every41-pin drift plus HEAD/footer/package drift rejects activation; updater
footer removal remains OFF. No auto-retarget/repatch/install.

Output rules are unchanged and statically compatible with `/data/v3_input_capture`.
Existing storage is **YES_EXPECTED reusable**, without storage migration. No
current actual path/owner/free-space/uploader attestation was performed here.

## Fresh regression and preservation

**1313 unique PASS /0 FAIL /0 ERROR /0 SKIP** in selected authoritative results:

| Domain | Unique cases |
|---|---:|
| Fresh historical5bb control groups, exact C04 IDs | 1165 |
| exact24c profile/wrapper/wire/paired/HUD/HUD controls | 148 |
| Total | 1313 |

New148 breakdown:56 profile,13 wrapper,36 actual-source wire,25 paired-source,
8 concurrent HUD,10 encoder/CLI controls. Wire covers all32 combinations of
CPU overlap/chunks/compact/shared/deferred NAV and four32KiB completion partitions;
8KiB paths are in the32-case matrix. Cache hit/miss/expiry/route/reset/gap,
replay/partial/interleaved/cleanup and exception paths remain covered by the
fresh historical controls and target paired tests. Real source JoiningModel,
daemon/transport/Session/EngineHost execute with CPU_FAKE Warp/model and POSIX
socket/memfd/native regular-file AIO. No physical device/model execution claim.

The first1165 run retained1121 PASS/44 AF_UNIX bind failures from overlong private
temporary paths (8 in203 cases,36 in119 cases; initial socket names110 bytes).
Source/tests were unchanged. Both complete affected groups203+119 were freshly
rerun with short unique basetemps. The authoritative selection uses the other
8 original PASS groups plus those two retries once; all1165 IDs equal C04 exactly.
Failed attempt evidence is preserved; retries and preliminary RED/oracle checks
are not added to the unique total. Target148 has a separate fresh JUnit and IDs.

Diagnostics4 remain BLOCKED by missing zstandard; root collection's known
import-time network/SystemExit blocker remains separate; native encoder checks
are BLOCKED by missing FFmpeg. None is reported as PASS or counted as SKIP.
No packages were installed. Existing WSL Ubuntu24.04/Python3.12.3/pytest/numpy/C
toolchain was used; plugin autoload disabled, bytecode writes off, BLAS threads1.
The artifact records groups/IDs/hashes, source commitments and execution limits.
Exact-target tests require the existing local Git reference with the reviewed
commit objects; historical controls use the immutable C04 source/support extract.
No fetch/checkout is implicit. The private runners retain full executed commands,
environment, JUnit, collected IDs and every retained receipt; public evidence
uses source-relative case IDs and digests with private paths redacted.

Independent whole-candidate review has zero actionable findings. Historical
reports/private evidence, tested sources/fixtures/patches and app attachment
bytes are preserved. Continuation is prepend-only; protected refs and reference
checkout remain unchanged. Actual access/mutation, storage, ticket, capture,
restart, Jetson and numerical parity work are all NOT_RUN in this stage.

Next action: separately authorize exact24c OFF deployment and repeat fresh
genuine-OFF, HEAD/PRE six/41pins/N16/namespace/index/overlay gates. The previously
raised power-retention issue is unresolved; this offline PASS does not bypass
OFF gates or authorize an onroad source patch. Ready for Vehicle10=NO.
