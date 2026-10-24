# M19-C0.3 — exact5bb deferred NAV / transport review

**RECORDER_LOGIC_CHANGE_REQUIRED. No exact5bb deployment candidate is approved.**
The unchanged a559 infer wrapper rejects the new keyword nav_metadata before
observation or original inference. This happens with default deferred NAV
negotiated for N16, including when metadata is None. A source-pin/footer rebind
alone is unsafe. JoiningModel closes the link and uses its existing local fallback.

Separately, **V3_DATASET_CONTRACT_STILL_SUFFICIENT /
VEHICLE10_FOUR_INPUT_DATASET_SUFFICIENT** for frozen Cinque V3 ONNX
404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4.
Its actual graph has no nav_map/navigation input or dependency. No dataset format
extension is required for this specific V3 replay; a wrapper change is required.

Actual comma access NO; Jetson access NO; device/source/Params/ticket/storage/
capture/restart/updater mutations NONE. All executions are offline CPU/POSIX
fixtures or original-ONNX static metadata inspection. No ORT/TensorRT inference,
model download/build/load, USB or vehicle validation occurred.

## Exact range and preserved history

Development started at 5397ee2b02381569abc2a223ee12fe183b5f3d11 on
feature/jetlink-multimodel-carrot, CLEAN/local=upstream=remote. Main
2519ad0bdbf6e796fa590063fc90d4d6461b6b8d and old feature
26c9c06a5e51ff0e8d3a1e8575eece548e87f3b5 remain protected.
Sources were read from existing Git objects without fetch/checkout/reset.

a559fcd971ccaa5a87befb8ec080f59a2966325b to
5bbbe160822c7cae4245d7a8e96b40d158941ff7 is exactly 10 ahead, 0 behind:
8dc5ced4, 75a2507e, 3983dbed, f05ef7c9, d80eaa15, 907cfc5f, 0fb6c739,
acbe0861, fc2109c4, 5bbbe160. All 22 changed paths, full commits and hashes
are in the artifact.

Read first: continuation, C02 report/artifact, C13 report/artifact and C20
diagnosis report/artifact. Historical366/810/060/a559 files and evidence remain
unchanged. C20 supplies only historical expected PRE: pure5bb model plus five
surviving a559 package files. No current actual attestation is claimed.

## Blocking API regression

Generated a559 hook SHA:
1e82abdfc93ab23f7add69c8f248677538ec2c20b47868b7bc06cb0195a18256.
Its actual nested function is:

    def infer(self, image, packed, frame, reset=False, source_sof=0):
        capture.observe(self, image, packed, reset)
        return original_infer(self, image, packed, frame, reset, source_sof=source_sof)

Exact5bb model.py:257-258 creates map_options containing nav_metadata whenever
client.deferred_nav is true. The new link.Client.infer accepts it; the historical
wrapper does not. Python raises TypeError before entering the wrapper body.
Capture readiness, map validity and matching tensor bytes cannot prevent this.

Direct regressions execute the exact generated FunctionDef with spies. Valid
metadata and None both fail with zero observe/original calls and unchanged input
sentinels. The no-keyword control observes then forwards once. functools.wraps
can conceal the incompatible closure in inspect.signature; follow_wrapped=False
and actual calls expose it.

The full fixture runs exact JoiningModel, Warp control flow, link.Client, daemon,
remote JetlinkClient, framing, CarrotSession, Session and EngineHost. Its unchanged
hook matrix reproduces failure. JoiningModel catches the TypeError, closes its
client and enters existing fallback with zero remote inference/captured frames.

Historical a559 source verification would already reject5bb HEAD/pins. This
fail-closed policy is correct; the API regression shows why simply rebinding
verification/footer cannot be accepted.

The fixture injects a synthetic ticket and source verifier to isolate that
pin-only-rebind hypothesis. Its generated package/dataset still uses the a559
binding. It is not a validated exact5bb capture or an approved activation path.

A separately labelled boundary_probe accepts/forwards kwargs and invokes the
historical _Capture.observe at the intended location. It proves source data
semantics only. It is not an installable hook, reviewed fix or compatibility PASS.

## Logical input, wire representation and frame semantics

Exact source ordering:

    MapInput.update -> JoiningModel.run
    overlap ON: Warp submit -> fill_inputs callback -> Warp read -> infer
    overlap OFF: fill_inputs -> Warp submit/read -> infer
    intended observation -> original local Client.infer
    -> current logical shared/socket IPC plus metadata
    -> daemon -> remote infer_begin -> Sender.prepare -> INFER_REQ submission
    -> phase notification -> flush_map -> infer_end -> reply

Sender.prepare runs inside remote infer_begin, downstream of the intended local
observer. It creates returned serialized bytes, without overwriting source
packed, first12, current navigation47 or camera image. Source packed remains
current full logical input; the dataset deliberately saves only its first12.

Eligible wire requests replace only the map region with a sequence/route
reference. CarrotSession resolves cache before normal packed decoding/EngineHost
staging. Full packed equality is **INTENTIONALLY_DIFFERENT_MAP** when staged and
current map pixels differ. Current first12, navigation47 and image remain exact.
Inline fallback has full packed equality after lossless decoding.

Assume a new valid map image per cycle and successful staging:

| Field/stage | Frame N, initial/reset | Frame N+1 |
|---|---|---|
| Source and host camera | I_N | I_N+1 |
| Desire/traffic/action | S_N | S_N+1 |
| Navigation vector | V_N | V_N+1 |
| Logical source map | M_N | M_N+1 |
| Wire map | inline M_N | reference to staged M_N |
| EngineHost map | M_N | M_N |
| Map staged after local request submission | M_N | M_N+1 |
| Recurrent generation | reset/current successful step | previous validated feedback/current step |
| Four fields with a compatible observer | I_N + S_N | I_N+1 + S_N+1 |

Map age is not invariably one frame. Image timestamps can span several camera
cycles; expiry, route changes and frame gaps trigger inline fallback. Navigation
is recomputed from the current valid instruction and is not staged with the map.
Cache invalidation does not itself clear recurrent history; explicit RESET does.

Local request submission before flush is proven. Deferred completion does not
prove host GPU execution began before map conversion/staging.

## Freshness, ownership and failure gates

Metadata carries route and monotonic image/expiry timestamps. Missing/invalid
context becomes inactive; source map freshness remains500ms. Staging TTL caps
at350ms, subtracts150ms transit reserve and requires more than50ms use/flush
reserve. Reset, nonconsecutive/repeated frame ID, route change, timestamp rollback,
cancellation or unavailable cache prevent prior-map use. Same-generation reuse
does not refresh TTL. Receiver checks key/route/size/TTL/CRC and owns copied pixels.
Missing/expired references return BAD_SHAPE rather than silently choosing a map.

Receiver expiry is arrival-local time plus TTL; source timestamps are not in
updates. Reserves are policy margins, not measured transit bounds or a guarantee
of original-source age at eventual GPU use. No gate/deadline was relaxed.
Noncanonical pixels are not silently quantized; pending conversion errors abandon
the link. Shared input retains generation/ownership until matching reply or
connection failure. No extra fill/reservation/infer retry is introduced.

Writer.send joins caller packets; C copies into owned pending slots before
returning. Deferred capacity is128x8192 or32x32768; synchronous16x32768. Slots are
not reused before validated completion. send/recv poll late errors; partial
submission and wrong completion identity remain sticky. Cleanup unbinds first;
failure retains buffers/context and blocks rebind. Arbitrary io_destroy duration
is not proven bounded.

Chunks preserve whole-message length/order/CRC/age and same-session sequence
suppression. Duplicate complete envelopes/requests execute once. Missing,
interleaved and corrupt streams fail closed. Arbitrary replayed8KiB fragments
are rejected by parser/CRC, not transparently recovered.

The integration fixture relays byte-checked regular-file AIO results over
loopback sockets and duplicates complete logical envelopes. Native batch counts
are not physical USB write counts. One nonblocking poll is not a completion-drain
claim. Separate native/fake-syscall fixtures check8K/32K per-iocb ownership,
submission/completion/cleanup faults. No physical USB timing is inferred.

## Frozen V3 and N16 contracts

The original frozen V3 ONNX was verified before/after reading:
766,354,845 bytes; SHA404a18cf...f1e1aa4. Actual seven external inputs:

| Input | dtype | shape |
|---|---|---|
| new_img | uint8 | (2,6,128,256) |
| desire | float32 | (8,) |
| traffic_convention | float32 | (1,2) |
| action_t | float32 | (1,2) |
| state_img_q | uint8 | (2,5,6,128,256) |
| state_desire_q | float32 | (132,1,8) |
| state_feat_q | float32 | (128,1,16384) |

837 nodes,610 embedded initializers, zero external initializers/nested graphs/
unresolved tensors. One local function is exactly Identity. No nav_map/navigation
tensor appears anywhere. outputs/next_state_feat_q depend on all seven inputs;
next_state_img_q on image/image-state; next_state_desire_q on desire/desire-state.
Frozen spec and adapter agree; nav fields are not hidden V3 preprocessing inputs.

Four per-frame fields (393,264B) suffice for V3 replay with separately matched
initial/reset state, all three feedback pairs, continuity and session boundaries.
They do not reconstruct arbitrary pre-capture history or full N16/nav/state input.
This is not numerical parity or an N16 replay claim.

N16 model remains
01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a;
canonical spec remains
63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71.
Stateful=true, five state pairs, image(2,6,128,256), packed65595, first12=8+2+2.

## Selectors, diagnostics, host and USB lease

| Selector | Exact5bb absent/default behavior |
|---|---|
| JETLINK_CPU_OVERLAP | 1; exact0 prepares before Warp |
| JETLINK_REQUEST_CHUNKS | 1, subject to protocol2/exact Jetson negotiation |
| JETLINK_COMPACT_REPLY | 1; exact0 or SEND_RAW_PRED disables eligible projection |
| JETLINK_RAM_INPUT | 1, subject to capability |
| JETLINK_DEFER_NAV | exact1 plus exact N16/spec/deferred capability |
| JETLINK_DEFER_COMPLETIONS | exact1 |
| JETLINK_AIO_WRITE_BYTES | 8192 if deferred; otherwise32768 |
| CARROT_USB_LPM_OFF | exact1, scoped Linux Jetson claimed USB bulk peer |

Switches changed only inside isolated fixture processes. No actual environment,
Params or runtime setting was read/changed.

RuntimeDiagnostics source is unchanged. New map timing/bytes/used metrics are
observation only; one infer_begin and infer_end, no prep/sequence edit/retry.
Emit failures are caught; malformed internal types may still raise as previously
characterized. Four standalone diagnostics tests remain collection-blocked by
missing zstandard and excluded from passing totals.

REPOSITORY_EXPECTED_HOST changes69c46427892e0fd2279ce37e8a35ceeefd379b0d to
0fb6c73926ef8d54f8434108bd060d47de011cbe; expected bundle SHA
2f51b10b2d6a356d39e0d923e66633a3e80c5b92096603713b39fa540db40162,
size64748504. This is source JSON identity, not downloaded/signed/installed bundle
attestation. ACTUAL_JETSON_HOST=NOT_RUN.

Power lease is transport/runtime policy. Exact USB3 peer VID/PID/bus/address/
port identity and original permit are checked. A fixed nonblocking heartbeat
does not carry model/input data. Root helper owns restoration/journal recovery;
no tensor or model/frame sequence change. Restore may outlive the parent's3s
wait; fake sysfs does not prove physical restoration timing.

## Fresh test ledger

The artifact contains commands, unique case IDs and JUnit hashes. Historical runs
and superseded fixture failures are not added twice.

**1021 unique PASS / 0 FAIL / 0 SKIP** in this scoped CPU/POSIX ledger. PASS
includes assertions of the known API incompatibility; compatibility itself fails.

| Scope | Cases |
|---|---:|
| Specified project regression, fresh | 533 |
| Exact5bb writer/chunks/lease upstream | 108 |
| Exact5bb deferred-map upstream | 43 |
| Host queue/USB/shared/daemon/overlap/projection/nav upstream | 203 |
| Supplementary transport ownership/fault/lease | 34 |
| Supplementary map/order/freshness/recurrence/API negatives | 25 |
| Historical32 + boundary_probe32 + AIO partitions4 | 68 |
| Direct hook API/range/source regressions | 7 |

The previous627 baseline is preserved by fresh533 project cases and current
versions of every former94 upstream case in these larger target suites.
It is not added again.

Of the previous94 upstream IDs,93 are unchanged; the remaining native ordering
case is now parametrized into synchronous32K, deferred32K and deferred8K cases.

Historical hook: NAV OFF16 successful five-frame cases; NAV ON16 expected API
failures with zero observation/original-infer/engine calls. Boundary probe:
all32 switch cases pass five-frame identity. Extra partitions cover deferred32K
and synchronous32K with shared/deferredNAV or socket/inline. Synchronous8K is
unsupported and not accepted.

Successful sequences have five distinct scalar hashes and desire inputs
0/rising/held/falling/rising -> packed0/1/0/0/1. Saved hashes equal original infer
and EngineHost four-field hashes. Image object identity, same camera pair/
transforms/reset, single reservation, current navigation and recurrent
generations0..4 pass. Source packed remains unchanged through response.
Compact/full outputs change returned width only. Equivalent saved bytes are
independent of transport/output selectors. Probe PASS does not fix the old hook.

Retained receipts confirm all52 successful sequences have byte-identical four
field hashes for equivalent inputs,260 synthetic records in total.16 additional
cases stop with the expected API rejection and zero observations/inference.

Root-wide tests/test_backport.py collection/SystemExit blocker remains separate;
root suite is not claimed. Four zstandard-blocked cases are neither PASS nor SKIP.
Initial missing fixture dependencies and instrumentation errors were corrected
without editing exact target sources; superseded runs remain private/excluded.

## Candidate decision and next gate

RECORDER_A559_LOGIC_REUSABLE is rejected. New profile NOT_CREATED; forward/reverse
NOT_READY; approved disposable roundtrip NOT_RUN. No deployable5bb patch, reader
or manifest is delivered. A tentative binding-only experiment was rejected after
API failure; its checks are excluded from the authoritative ledger.

A future offline wrapper review must accept/forward exact nav_metadata once,
keep observe immediately before original infer, and prove exceptions/call order.
Then review33 relevant source pins, package/footer binding, a559-surviving PRE,
strict reader and reversible roundtrip. Do not disable deferred NAV, loosen
verification, automatically repatch or retarget after updater movement.

Exact5bb OFF deployment NO; storage preparation NO; Vehicle10 capture NO.
PARITY_UNDETERMINED; M2 NO.
Next: separately implement/review metadata forwarding offline, then repeat
exact5bb compatibility gates before generating a candidate.

Result commit: git log -1 --format=%H --
artifacts/m19c03_5bb_deferred_nav_20261024.json
