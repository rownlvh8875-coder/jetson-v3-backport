# M19-C0.1 — exact060de9 request-chunk compatibility

**RECORDER_810E_LOGIC_REUSABLE.** New distinct profile:
`RECORDER_060DE9_REQUEST_CHUNKS_V1`, base
`060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c`.

**543 unique CPU_FAKE/FIXTURE PASS /0FAIL/0SKIP:**449 authoritative scoped
(415 historical once +34 new060), plus94 separate upstream transport cases.
Implementation commit: `9722b3702cf0bde6b2866416c236674c8c0b4a34`.

This is OFFLINE ONLY. No comma/Jetson connection, source/config/Params write,
ticket, activation, capture, restart, GPU initialization, USB operation or updater
change occurred. Supplied actual060de9/OFF1/ON0/tracked0 is historical evidence;
it was not refreshed here. Future deployment must reject a different actual HEAD.
Numerical decision remains PARITY_UNDETERMINED, M2 and M19-B2 capture readiness NO.

## Exact range and unchanged input contract

Immutable local Git objects were read without checkout or modifying the reference
HEAD366. Its pre-existing submodule status was preserved. The range810e..060de9
contains12 commits and13 changed files. Every commit's full SHA/subject/file list,
every changed file's before/after SHA256, and all28 profile pins are in
`artifacts/m19c01_060de9_request_chunks_20261024.json`.

| Commit | Change |
|---|---|
|83e2d8d8ed01613eb726f7db253d46a0692bdf9f |negotiate bounded replay-safe envelopes |
|c95a92e2d4054e1e8377f06642f7177b450c62c2 |select signed bounded-request runtime |
|4f02cb40b3975a41f6e5acaf5240ba9a4591b382 |raw signal masks |
|cb4df37d2092e6d3aaeda320e70df8c533c5ee73 |same-request bounded write queue |
|6e51d136131b4537b0f003236eab1dd1d32c3529 |mirrored FunctionFS completion lengths |
|58fc9d41aa78327fa6624782fe3d253b6b60dfa6 |bounded-request USB prefetch |
|f62f0edae3fbc92df2ea425cf609f549136395ee |deploy prefetch runtime |
|234d167db3cafc78e0fd9bbbd2391508010e4d4c |prepare exact frames, fill request queue |
|99888e4a77554ca46fee6422810cb370a328d14e |request cleanup check |
|69c46427892e0fd2279ce37e8a35ceeefd379b0d |assemble before logical queue |
|61622ebee853ec9094a76eb8b49b9b38883059fa |deploy logical queue runtime |
|060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c |display-window queue verification |

Changed paths, exhaustively: `openpilot/selfdrive/modeld/jetlink/host_release.json`;
`third_party/jetlink/jetlink/client.py`, `request_chunks.py`,
`transport/ffs.py`, `transport/request_writer.py`, `transport/request_writer.c`;
`tools/jetlink/host_reader.py`, `host_usb.py`, `server.py`,
`test_host_request_queue.py`, `test_host_usb.py`, `test_request_chunks.py`,
`test_request_writer.py`.

All15 old recorder source pins are byte-identical, including model/link/shared
input/contracts/daemon/inputs/prepare/N16 sidecar/camera gap+sync/modeld/manager
process/vendored spec/session/queues. The requested eight hot-path sources are
therefore **UNCHANGED**. Pure060de9 model.py remains SHA256
`103dc0c7eb1b4998ddbf0a498be55ffd02fd51b195ce20cb7ea44ba3dbce6c42`.

N16 model remains
`01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`,
814591107bytes; exact semantic spec digest
`63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`.
It is a stateful graph with five server-owned state pairs, warped uint8 shape
2×6×128×256, packed65595float32 values ordered desire8, traffic2, action2,
nav_map65536, navigation47. No prev_feat is added. Recorder still saves only
logical new_img/desire/traffic_convention/action_t, without Nav extras/state.

## Request construction, negotiation and ownership

Exact source chain:

`Warp(output_buffer=Client.image_buffer()) → recorder copy → Client.infer →
local shared token/socket IPC → daemon._serve_local → JetlinkClient.infer_begin →
FfsTransport.send → bounded envelopes/native writer → host ReadAheadTransport →
Receiver → CarrotSession.handle → Session._infer → EngineHost/queues`.

The original810e single reservation/Warp/return identity and shared-buffer
lifetime remain unchanged. No recorder wrapper calls begin/complete/release or
mutates generation/nonce/packed context. Chunking occurs in the comma daemon
after the recorder has copied the attempted inference input. The hook's borrowed
reference is cleared before original infer; it cannot keep a shared slot busy.

`JetlinkClient.hello` resets chunk state before each handshake. Enable requires:
client opt-in (default True), selected protocol2, host identity `jetson`, exact
`carrot_request_chunks_v1` descriptor with integer fields version1,
wire_bytes32768/max_bytes1048576, and successful native writer preparation on the
FFS layer. Unsupported descriptor, another host, client opt-out, protocol3 or
preparation failure leaves original framing. HELLO/spec identity and selected
Protocol2 are not promoted to Protocol3.

`infer_begin` first validates image/context lengths and makes one logical request
from the existing frame header/image/packed context. Existing `carrot_nav_u8_v1`
compact map packing is bit-preserving; fractional/noncanonical values, including
negative zero, use full floats. First12 scalars and image bytes are preserved.
Optional full-block compression remains disabled in this candidate's tests.

`request_chunks.packets` joins the logical request once, computes CRC32, and
slices32720 data bytes per envelope:32-byte P2 wire header +16-byte
`<HHIII>` original kind/flags/total/offset/checksum header, padded using the
unchanged gadget alignment. Total request limit1MiB, age/deadline cap0.5s.
No per-chunk recorder work or second logical input construction is introduced.

Receiver requires offset0 first, strict contiguous offsets/exact body lengths,
stable seq/kind/flags/total/checksum and a nonexpired clock window. Same-offset
identical duplicates return None; changed duplicates, missing/out-of-order chunks,
CRC corruption and interleaving raise LinkError and clear the partial assembly.
An incomplete idle request cannot enter inference; its bounded buffer can remain
until another checked arrival, HELLO or close. The age check runs on arrivals.

ReadAheadTransport reassembles **before** its two-logical-message queue, owns a
bytes copy before another recv, and advances last_received_seq before queueing.
CarrotSession/Session also reject seq≤last_seq; a completed same-sequence request
cannot run recurrent inference twice. HELLO clears receiver/sequence state.
These are same-session sequence guarantees. Nonce is logging/client identity;
CRC32 is integrity checking, not authentication. Cross-HELLO freshness,
cross-session replay defense and sequence-wrap behavior are not established.

## Bounded native writer

060de9 request_writer is part of the existing reviewed upstream transport, not
the external optimization candidate and not a new opt-in performance deployment.
It transports already-serialized packets. DEPTH16, each≤32768bytes, at most34
packets/request. A pending slot is never reused before its matching completion;
logical send returns only after every completion. res/sequence/object validation
rejects short/bad completions. Partial submission, timeout or write error latches
failure; no raw partial stream retransmission is introduced. Cleanup retains
kernel-owned context if io_destroy fails; FFS failure close unbinds first.

CPU native tests execute the exact C writer on regular files for order/bytes and
repeated requests, plus fault syscall fixtures for reversed completions, partial
submission, timeout, invalid/mirrored completion and cleanup refusal. BulkInput
uses a fake libusb transfer for cancellation/ownership/prefetch tests. These do
not establish real FunctionFS kernel behavior, USB speed or realtime timing.

## Byte-identity evidence

Eight separate server/comma process cases exercise all four required paths,
each with exact compact Nav and noncanonical full-float fallback:

| Local input | USB framing fixture | Strict dataset/Session/EngineHost identity |
|---|---|---|
| shared memfd | request chunks |PASS |
| shared memfd | original request |PASS |
| socket ndarray | request chunks |PASS |
| socket ndarray | original request |PASS |

Each case records3 synthetic attempts. Actual060 Client/Warp/shared ownership,
daemon, JetlinkClient, FfsTransport serializer/bounded-send, chunk packets,
ReadAheadTransport, unchanged CarrotSession.handle, Session parser and EngineHost
run. Native regular-file AIO packets are relayed over POSIX sockets. Host identity
metadata, OS diagnostics/Params/phase reporting, QCOM execution and GPU engine
are explicit fixture boundaries; unrelated HUD/Wi-Fi workers never start.
No entire client/server inference function is replaced.

For every attempt, recorder strict-reader image/scalar SHA equals Client's input
and EngineHost's logical tensor SHA. Full packed SHA equals engine fields joined
in spec order. Pre-framing logical request SHA equals Session parser input SHA.
Every physical envelope is repeated, then the entire request is replayed after
the reply; engine invocation count remains3. Existing framing is compared using
whole-frame replay, not a claim that its raw partial-write replay is safe.
Artifacts contain all8 synthetic receipts/24attempts; no actual recorded frames.

## Expected host release, not actual Jetson evidence

| Field |810e repository |060de9 repository |
|---|---|---|
|source_commit |54e706fa0573e91dc3b4a0d4f625b9d81a6b68cc |69c46427892e0fd2279ce37e8a35ceeefd379b0d |
|bundle SHA256 |42c2951e92bd47029ff22fb058f577a0a3d334eeca62c92aa7b6ef479227787c |f254316cf1b347cf561712f9018079ff7ad4b540e803f8a7ff27120ad4540d63 |
|bundle bytes |64707580 |64733965 |
|runtime |aarch64/L4T36.4.7/TRT10.3.0 |unchanged |

No standalone runtime semantic-version field is declared. Source commit and
signed bundle identity distinguish releases. The model entry is unchanged.
Declared69c464 runtime code matches060de9 for reviewed transport files; only
host_release metadata and a queue test changed afterward. Bundle bytes/signature
were not downloaded/reverified. **ACTUAL_JETSON_HOST=NOT_RUN/UNKNOWN**. Future
live preflight must query actual host identity/capabilities; repository metadata
does not prove an installed release. Old hosts retain negotiated framing fallback.

## Minimal distinct profile and rollback

`adapters/carrot/recorder_060de9.py` reuses frozen810 generation with checked AST
constant rebinding. format BASE_SHA, hook SOURCE_PINS/PACKAGE_PINS/FOOTER_TEMPLATE
and footer profile/hook digest change. Hook functions/classes retain identical
AST, including inherited810 diagnostic wording; that wording does not define
the accepted HEAD. SOURCE_KIND remains the same logical N16 input provenance.
Writer/dataset/__init__ bytes are unchanged; no control/inference changes.

The15 input/spec/actor/recurrence pins are retained;13 additional pins cover
client/protocol/packed+block codec/StreamTransport/chunker/FFS/native writer,
host reader/prefetch/session wrapper and expected host release. Documentation,
unrelated build scripts and test sources are not deployment pins. The full
package/footer coupling rejects drift before creating the volatile discovery
namespace. Boot/expiry/O_EXCL/owner/mode/no-symlink/role/one-shot rules are unchanged.

Main migration patches:
`patches/carrot-nav-060de9-v3-input-recorder.patch` and `.reverse.patch`.
They target pure060 model + exact surviving366/B1 five-file package and touch
only model.py/format.py/hook.py. Separate `-clean` patches support clean060.
Both disposable forward→after→reverse roundtrips restore exact original bytes
and absence. All six before/after hashes and patch SHA are in the artifact.
Historical366/810 patches and evidence are untouched. No device migration ran.

| Migration asset | SHA256 |
|---|---|
|surviving366 forward |2b09f9753d5cf3e717b126898445ed2e33a44ad6871c0b64062aa2a24044e099 |
|surviving366 reverse |cd07d062c5fbd06e49d5581b908ea5108b633b69442cb15f548079daaa88d473 |
|clean060 forward |e63591a2f40c680873c2b578635124e26de699292128d17300c790ede3673a61 |
|clean060 reverse |8872acedb662d73b293d44fada872ab6fa9c1648e310dadac9434041afbba0e9 |

Updater removal of footer or HEAD movement fails source attestation; no automatic
repatch, version rollback, updater disable, launcher/manager change or activation
environment is added. Future arming must verify actual HEAD and all six source
hashes plus fresh private runtime-overlay/physical-state evidence. No historical
original48 digest is a current060 attestation.

## Reproduction, results and boundaries

Generate only into a fresh destination:

```sh
PYTHONPATH=. python -B -c "from adapters.carrot.recorder_060de9 import build_candidate; build_candidate('.reference/m15-carrot-nav-366d6eae', '.candidate/fresh-recorder060', layout='surviving366')"
PYTHONPATH=. python -B tools/v3_input_dataset_060de9.py validate PRIVATE_DATASET --reference .reference/m15-carrot-nav-366d6eae
```

Exact fresh commands, unique counts/JUnit hashes and limits are in the artifact.
The authoritative project scope includes the historical415 cases once, new060
tests and the two reviewed reader CLI error cases. Upstream transport94 runs in a
separate import namespace/process; those cases are not counted again as project
cases. Root collection was checked separately: existing tests/test_backport.py
calls sys.exit during import, producing SystemExit0 / pytest exit3 / no tests
collected. That blocker is not a scoped test failure or a full-repository PASS.

Private RED/setup runs remain distinguishable: absent profile/reader RED,
fixture import/class/backend setup errors, and an incorrectly partial old-frame
replay fixture were corrected without changing upstream transport or gates.
Independent final review found no blocking issue; a minor reader bad-reference
traceback was reproduced with2RED cases and changed to JSON FAIL, then verified.

During work public Nav was710da0d285cd21c25c2ea143450de94196690884; WIP moved
from9fa59128bdff6b6c0b9501aec2898205492b389f to
deb63e276d95d3e0fc2234ad4b312b4c4d075269. The GitHub compare adds UI/EGL shutdown
changes and extends the Jetlink CI workflow trigger/test list; no Jetlink runtime
file changed in that WIP increment. Metadata is recorded separately and does not
retarget this exact060 review or prove latest-Nav compatibility. Actual HEAD was
not queried. End refs and source comparison URL are in the artifact.

CPU_FAKE/FIXTURE only. No numerical output approval or current comma overhead
claim; no actual USB/QCOM/GPU/Jetson/vehicle test. New candidate is for a separately
approved **fresh exact060 OFF deployment**, not capture. Before device mutation,
refresh actual HEAD/package/overlay and genuine-OFF evidence; a different HEAD
must STOP. Ticket/capture/restart/Jetson changes remain unauthorized here.
