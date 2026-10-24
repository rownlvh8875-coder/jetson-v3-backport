# M19-C0.4 — exact5bb nav_metadata wrapper fix / offline review

**PASS. Blocking API issue RESOLVED. RECORDER_5BB_DEFERRED_NAV_V1 is a ready
offline candidate for exact5bb OFF deployment.** Recorder logic is
REUSABLE_WITH_WRAPPER_FIX; the frozen V3 four-input dataset remains sufficient.
Actual deployment, storage preparation and Vehicle10 were not performed.

Target: `5bbbe160822c7cae4245d7a8e96b40d158941ff7`. Development started at
`f05a7ffaa7ad9e89630e3e925000090c374f6c02`, exact feature branch,
CLEAN and local=upstream=remote. Protected refs remain unchanged. Historical
366/810/060/a559 profiles and C03/C13/C20 evidence are immutable.

Read first: continuation, C03 report/artifact, C02 report/artifact and C13
report/artifact. C20 supplies historical expected PRE only. There was no actual
comma or Jetson access, source/Params/updater change, ticket, storage directory,
activation, capture, restart, model load/build or ORT/TensorRT inference.

## Minimal explicit API change

The new generated hook has this exact function signature and body:

```python
@functools.wraps(original_infer)
def infer(self, image, packed, frame, reset=False, source_sof=0, nav_metadata=None):
    capture.observe(self, image, packed, reset)
    return original_infer(self, image, packed, frame, reset,
                         source_sof=source_sof, nav_metadata=nav_metadata)
```

Relative to the a559 hook, the only function/class AST differences are the
explicit argument and its one forwarding keyword. No generic kwargs, metadata
copy/normalization/validation, alternate infer, close, fallback or retry is added.
The tuple sentinel passes as the **same object**, once. Both default
inspect.signature and follow_wrapped=False match the real local source signature;
__wrapped__ points to the original method. All supported positional/keyword forms
pass, including omitted/None metadata; unsupported keywords still reject before
observer or original. Historical negative tests remain intact.

The exact source AST call scan retained all48 infer/infer_begin sites, including
tests. Non-test sites classify as follows; the unrelated lane API is excluded.

| Path:line | API / metadata |
| --- | --- |
| model.py:258 | Local Client.infer; negotiated deferred NAV supplies nav_metadata, including None |
| tools/jetlink/bench.py:27 | Local Client.infer; omitted metadata |
| daemon.py:366 | Remote infer_begin; negotiated map_options, outside recorder wrapping |
| daemon.py:634 | Remote infer warmup; omitted metadata |
| third_party/jetlink/jetlink/client.py:587 | Remote infer facade to infer_begin; no nav_metadata argument in remote infer API |
| tools/jetlink/validate_nav_rl_cpu.py:191,220 | Remote infer; omitted metadata |
| xiaoge/v_asm_server.py:671 | Unrelated lane inference |

Local None is forwarded unchanged. Original deferred ON serializes zero metadata
through IPC; deferred OFF ignores metadata. Direct remote None clears sender,
whereas zero tuple enters Sender.prepare and cancels cache/pending. Recorder
does not collapse those distinct source semantics. Invalid negotiated metadata
is rejected by the original path after original image/packed finite/layout
checks; unnegotiated source behavior continues to ignore it. Source exceptions,
close order and JoiningModel local fallback are preserved, with no retry.

Actual _Capture.observe isolates a sink exception, disables recorder once and
allows one original inference. A deliberately injected raw observe exception
retains propagation and calls original zero times, as the existing wrapper did.
Original, transport, shared ownership/generation/completion and map-stage failures
retain their original error type/order and do not duplicate inference.

## Exact observation and unchanged dataset

Ordering remains observe -> original local infer -> remote infer_begin /
Sender.prepare -> wire/cache reconstruction -> EngineHost. Warp prepare callback
or None and output_buffer are forwarded once. Both CPU-overlap orders finalize
same-frame scalars first. Shared Warp output is the very ndarray passed to the
original infer; socket fallback preserves its bytes. One shared reservation,
camera pair/transforms/reset association and original call ordering remain.

All32 switch combinations (CPU overlap, chunks, compact reply, shared input,
deferred NAV) and4 supported writer partitions pass with the **actual generated
fixed hook**. There is no boundary_probe substitute in these36 cases. Each writes
five synthetic frames: five distinct scalar12 hashes, desire pulse sequence
0/rise/held/fall/rise => 0/1/0/0/1. Recorder hashes equal original infer and engine
image/first12 hashes, frame by frame; no lag. Equivalent source inputs give the
same four stored byte sequences across switches and 8KiB/32KiB completion modes.
Navigation stays current. Sender.prepare/flush_map/infer_end sentinels remain
unchanged. Replay does not execute the fake engine twice.

The paired suite additionally compares25 wrapped/unwrapped source scenarios
(50 executions) with fixed clock/inputs. Traces after removing observer events
match for cache hit/miss, expiry, route change, reset, gap/repeat, timestamp
rollback, None, same generation without TTL refresh, noncanonical inline input,
stage/transport/reply/shared errors and sink failure. Source sequence allocation,
pending/cache state, request flags, shared generation and flush order match.
The paired harness mirrors daemon IPC parsing/order; the separate36-case matrix
executes the whole JoiningModel/daemon/Session/EngineHost fixture pipeline.

Full packed equality is intentionally **not** claimed on a deferred map hit:
EngineHost map pixels may come from the preceding staged source map. Source
packed/current first12/current navigation remain intact. This wrapper changes
none of the map freshness/TTL/route/reset/gap/inline fallback gates or flush timing.
The observed request-send-before-flush order does not prove GPU execution began.

Stored fields remain exactly new_img uint8(2,6,128,256), desire float32(8,),
traffic_convention float32(1,2), action_t float32(1,2). No nav_metadata, nav_map,
navigation or recurrent tensors are added. Canonical manifest/records and strict
5bb reader are checked, including wrong-profile rejection. Only source binding
changes; record schema and init/recorder/dataset module bytes are unchanged.

FOUR_INPUT_SUFFICIENT remains frozen for ONNX
404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4.
The immutable C03 original-graph inspection proved7 actual inputs: four fields
plus3 recurrent queues, with no nav_map/navigation dependency. This stage reuses
that identified static proof; it does not claim a fresh graph read. Replay still
requires matched initial/reset state, feedback and continuity, and cannot
reconstruct pre-capture history or full N16 inference. Numerical parity remains
undetermined. N16 model/spec remain unchanged:

- model: `01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a`
- canonical spec: `63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`
- stateful five server-owned pairs; packed65595; first12=desire8/traffic2/action2.

## Distinct source binding and reversible candidates

All33 exact source pins include deferred_map, map_client, client, request chunks,
native writer, ffs, host_lpm/release, diagnostics/projection, modeld/manager and
N16 contract sources. Tests reject each pin drift before ticket discovery, plus
HEAD/footer/package drift. Pure5bb model body is unchanged with exactly one
fixed volatile-discovery footer and hook SHA binding. No environment activation,
auto-retarget/repatch or updater control is introduced.

Expected future actual PRE is **pure5bb model without footer plus surviving
a559-bound package**, verified historically in C20; a fresh actual PRE remains a
future gate. Surviving migration touches exactly model.py, format.py and hook.py.
Reverse restores exact PRE, including a559-bound format/hook. Clean5bb is a
separate alternative for a layout with no surviving package; it must not be used
for the expected surviving layout. It produces the same AFTER profile.

| AFTER file | SHA256 |
| --- | --- |
| model.py | `65b9006aba819376344e72114b2de55330aa76cd358f30c7e80488f0dd9e799a` |
| __init__.py | `e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca` |
| format.py | `838cbb11d254132f55ff808ef59e3010a18f0f0a0d157e7a215635229950810a` |
| recorder.py | `d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada` |
| dataset.py | `25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7` |
| hook.py | `1b0331426cc13c3f1ec27910f69eea4c4bc210af339acdf63bebf5098e041f83` |

Surviving forward: patches/carrot-nav-5bb-v3-input-recorder.patch
`8840e15e873526774d9c6f0ce1b2442dc1a3ee91cbf77326371bf643d79c6217`

Surviving reverse: patches/carrot-nav-5bb-v3-input-recorder.reverse.patch
`96e2232d00fcecdfc2fd9a7adfaa646d9719903bf69315c4a42355b28173aee3`

Clean forward/reverse SHAs are `fb01880627f8a88cdab7fb46e6da243a501e1d7984abc43a532a2c7148f623a8` /
`738212281753aa9040f181c196fb322bc1cd6ba932fbb82e70e7bbaa02c850ea`. Full PRE/AFTER hashes,33 pins and touched paths are in
the two deployment manifests. All four public patch bytes match generated diffs.

Disposable POSIX tests and separate isolated Windows Git copies pass forward
check/apply, six exact AFTER hashes, syntax/footer/hook binding, reverse
check/apply and byte-exact PRE restoration. Supplementary Windows checks first
exposed parent Git-prefix skipping and system core.autocrlf conversion; the
final check used its own Git root and per-command core.autocrlf=false. These were
evidence-harness issues, did not modify development or actual source, and are
excluded from test totals.
No global Git setting changed; the development index remained stable.

No-ticket footer returns before package import: no tensor copy, writer, process
or dataset. Lazy normal-modeld import path and updater footer removal fail closed.
No synthetic fixture ticket or dataset is a real vehicle capture.

## Fresh verification and limits

**1,165 unique PASS /0FAIL /0ERROR /0SKIP**: prior authoritative1021 run once,
new fixed-profile/API/matrix/gates/migration119, new paired-source25. Baseline IDs
match C03 exactly; no historical case is counted twice. The baseline includes its
historical expected API-failure negative test; new positive tests prove the fix.
Private API20 and initial private paired25 checks, red5FAIL/3PASS and preliminary
runs are not added to the authoritative total. Artifact retains all unique IDs,
JUnit hashes, fixture matrix hashes and private command/evidence commitments.

WSL Ubuntu24.04 Python3.12.3/NumPy2.5.4/pytest9.1.1/cc13.3; regular-file native AIO
and fake engine only. No USB, GPU, ORT, TRT, model performance or vehicle evidence.
Four diagnostics tests remain collection-blocked by missing zstandard, separately
excluded. Known root test_backport SystemExit collection blocker remains separate;
its live top-level network code was not executed. No dependency installs.

Independent code review verified minimal AST delta,33 pins, exact patch bytes,
source/packaged footer binding and fail-closed boundaries. Final review receipt
and command/source manifests remain private. Public artifact contains synthetic
hashes and sanitized outcomes only, no device address, vehicle data or raw inputs.

Ready for exact5bb OFF deployment: YES, as a candidate requiring separately
authorized fresh actual gates. Ready for storage preparation: NO. Ready for
Vehicle10: NO. Actual Jetson host: NOT_RUN. Repository expected host/bundle remain
the C03 exact5bb identity, separately recorded. PARITY_UNDETERMINED; M2NO.

Next action: separately authorize exact5bb OFF deployment with fresh actual
identity, genuine-OFF, surviving-package and overlay gates. Result commit:
git log -1 --format=%H -- artifacts/m19c04_5bb_nav_metadata_wrapper_20261024.json
