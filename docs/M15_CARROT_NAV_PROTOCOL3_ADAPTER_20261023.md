# M1.5 minimal carrot-nav managed Protocol3 adapter

Date2026-10-23. **Software candidate PASS — DO_NOT_INSTALL.** Numerical gate
is separately PARITY_UNDETERMINED, with a parsed desire disagreement; M2
readiness is **NO**. No comma source, manager, Params, selected.json, USB
ownership, operating Jetson service/current/cache or packages were changed.

Machine evidence: `artifacts/m15_carrot_nav_adapter_20261023.json`.
Reproducible patch: `patches/carrot-nav-protocol3-managed.patch`.
Numerical report: `docs/M15_ORT_TRT_PARITY_20261023.md`.
Future execution boundary: `docs/M2_PARKED_USB_PLAN_20261023.md`.

## Base, source materialization and scope

Actual comma and upstream carrot-nav were freshly checked at
`366d6eae9aa9962104391e1d997fe956dea8f64d`. Latest WIP remained
`813369b0c53bb9c997b7ffbe17fca90222a755b8`. The adapter uses actual Nav,
not a moving branch checkout or whole WIP merge. M0.5 recommendation A remains.

First reference `.reference/m05-carrot-nav-366d6eae` was sparse and lacked
`openpilot/selfdrive/navigation`, causing NavRL/projection collection errors on
both baseline and candidate. No model or fallback assertion failed. A fresh
reference `.reference/m15-carrot-nav-366d6eae` materialized that exact source
path through the existing fetch helper; neither old reference was modified.
Fresh candidate `.candidate/m15-carrot-nav-complete-366d6eae` has the same
six-file patch SHA as the first candidate. Complete baseline and candidate
upstream suites then passed170/170 each, without source/test gate relaxation.

The generator is `adapters/carrot/nav.py`, alongside the unchanged WIP
generator. It requires exact actual base, a clean reference, fresh external
destination and exact source anchors before copying tracked materialized files;
it excludes .git/untracked assets. Existing WIP host source-hash guards remain
unchanged and correctly refuse a blind Nav server port.

This is a **comma-only** Nav adapter. A separately generated reviewed WIP host
candidate supplies the P3 managed resident-engine/generation/finite/state
contract in another process. No Nav server/device-state implementation was
merged or activated. Nav P3 client wire capability is tested, but arbitrary
Nav engine execution on that WIP host is not claimed.

## Exactly six touched files

| File relative to openpilot root | Change | Reason |
|---|---|---|
| openpilot/common/jetlink_peer.py | Existing; import one managed predicate | Expose explicit USB/TRT/Jetson/P3 capability policy; no App classifier or USB-speed relaxation |
| openpilot/selfdrive/modeld/jetlink/mac.py | Existing; early managed dispatch | Explicit capability is handled before broad legacy is_jetson exact Nav pin; malformed capability fails closed |
| third_party/jetlink/jetlink/spec.py | Existing; optional dtype maps serialization | Preserve explicit V3 input/output dtype declarations through exact JSON approval/spec equality |
| openpilot/common/jetlink_managed.py | New, reused reviewed policy | Exact capability syntax/identity rules; metadata is not authentication |
| openpilot/selfdrive/modeld/jetlink/managed.py | New, reused managed preparation plus Nav exact catalog | Existing validator/offroad approval/reconnect/loaded checks, limited to exact reviewed V2/Nav/V3 seeds |
| openpilot/selfdrive/modeld/jetlink/cinque_v3.json | New, copied exact contract | Full source SHA/size/checkpoint/shapes/dtypes/slices gate |

No edits to model.py, link.py, contracts.py, parser, daemon.py, selection.py,
warp.py, inputs.py, client.py, queues, protocol codecs, updater or navigation
code. Critical bytes were compared with the actual reference. The entire
legacy mac.prepare branch from `if is_jetson(peer):` onward remains byte-identical.
No Carrot Web/NOO or vehicle-control changes.

### Dtype and N16 preservation

ModelSpec adds optional dicts defaulting empty. to_dict emits a dtype map only
when explicitly nonempty, and from_dict retains it. It does not infer dtype
maps for old model metadata or replace Nav's packed_shapes implementation.
Thus canonical legacy Nav/V2 dictionaries remain unchanged, preserving N16
spec hash `63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71`.
Populating empty/inferred maps would have broken projection eligibility.

Actual Nav source spec is SHA01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a,
814591107 bytes, output18580, five state pairs, packed65595 float32 values
(262380 bytes), nav_map[1,1,256,256] and navigation[1,47]. Its exact source pin,
signed release metadata, canonical spec and existing metadata fixture were
used; the older nav_rl_metadata fixture is ABI evidence, not model identity.
No814MB Nav ONNX or TRT engine was committed or inferred in these CPU tests.

### Managed selection contract

Explicit valid P3 USB/TRT/Jetson capability is required. Host loaded must be
an exact catalog SHA for V2, actual Nav or canonical V3. Unsupported models are
rejected before ensure_engine or approval; they never fall into legacy Nav.
First/different selection requires current offroad+connected checks. The
existing model validator and exact catalog equality bind SHA, size, checkpoint,
shapes, slices and any explicit dtype maps. Approval is separate under a
managed-jetson development cache; approved exact spec may reconnect onroad.

State() is checked before and after engine readiness; loaded drift, stale or
corrupt approval, spec/dtype/size mismatch, missing engine and disconnection
reject preparation. Pending provision/build stays offroad-only; no alternate
big model is chosen/downloaded for a missing engine. Existing local small
fallback remains the failure path.

Same-SHA live spec/generation mutation is rejected by the **paired reviewed
host's** prepared Loaded object and exact spec snapshot on inference. Comma
telemetry's loaded SHA alone cannot authenticate a host or independently see
a same-SHA spec change. No stronger security claim is made. Generic App policy
and WIP candidate behavior are not globally restricted by this Nav catalog.

Legacy Nav Jetson P2 still requests the exact Nav JETSON_SPEC. V2 P2 client
support is preserved; changing Nav's legacy default to V2 to satisfy a WIP
test would be a regression and was not done. No may_provision/auto-peer change
was made, because those flags affect App handshakes and USB-speed admission.

## Real source CPU regression evidence

| Target | PASS | FAIL | SKIP | Evidence |
|---|---:|---:|---:|---|
| Latest WIP rolling required suites | 288 | 0 | 0 | CPU_FAKE/FIXTURE, frozen source/online refs |
| Current startup/priority/watchdog | 103 | 0 | 0 | CPU_FAKE/FIXTURE |
| M1 guard/recurrence/parity regression | 85 | 0 | 0 | CPU_FAKE/FIXTURE |
| M15 semantic/cache math/source boundaries | 25 | 0 | 0 | CPU_FAKE/FIXTURE; no fake GPU PASS |
| Nav candidate source/catalog/selection/patch rollback | 8 | 0 | 0 | Actual Nav source + CPU_FAKE preparation |
| Cross-process Nav comma / WIP host | 13 | 0 | 0 | Real client/session/daemon IPC/parser/JoiningModel; CPU fake engine |
| Before/after exact client wire snapshots | 5 | 0 | 0 | Actual V2/Nav specs and real TCP framing |
| Nav existing managed approval suite subset | 11 | 0 | 0 | One WIP-specific legacy-default test deselected; replaced by exact Nav default test |
| Nav upstream on candidate | 170 | 0 | 0 | Same exact five suites as unmodified control |
| Unmodified Nav control | 170 | 0 | 0 | Additional control run, excluded from target total |

Target suite executions **708** count branch/configuration variants separately;
control170 and independent review repeats are not added. Fresh combined local
command passed136 cases (85+25+8+13+5); these are already included above. No
claim that this is a successful bare-pytest aggregate: historical test_backport
top-level SystemExit remains an unrelated collector limitation.

Exact Nav upstream counts: NavRL24, App models53, stateful protocol11, output
projection42, mac40. Both original and candidate passed the same counts. They
cover actual Nav metadata/maps/clear-on-missing/NOO demand/JoiningModel fallback,
P2 stateful_v2 and N16 negotiation/full-output validation, P3 full contracts,
App selection/IPC/parser and unchanged legacy Mac behavior.

### Byte/behavior checks

Five socketpair snapshots use actual original and adapted JetlinkClient,
HELLO/ENGINE_REQ and TCP protocol framing: V2 P2, V2 P3, Nav P2 full, Nav P2 N16
with map codec, Nav P3 full. Inference request/reply sizes, payload SHA, flags,
sequence, resulting output SHA, spec and state-pair metadata were identical.
V2 retains caller prev_feat under P2 and removes it for P3 (393272-byte request).
Nav retains five pairs, packed maps and projection spec pin. These are synthetic
response CPU checks, not actual Nav/V2 model inference or USB tests.

The13 cross-process tests use the actual Nav generic client, mac.prepare,
daemon._serve_local, local IPC, Parser and JoiningModel.run. Only deterministic
full-size GPU engine, native Params/logging/diagnostics and camera/small-engine
hardware seams are substituted. Normal remote parsed results, state continuity,
reconnect stale-response rejection, bad SHA/size/spec, timeout/disconnect/
malformed/nonfinite output, identity drift and state failure close/fallback run.
Active failures preserve the existing fault/reset behavior; first failures
keep the local model. Reload/reset/invalid generation are also covered by the
paired host's existing rolling state suites.

An initial test hardware Camera lacked Nav's `prepare` callback, reproducing
an actual TypeError before inference. Only that camera seam was corrected to
execute the real CPU fill_inputs callback; no model code was changed. A new
stale-response test incorrectly expected <1s; actual _expect intentionally
discards stale sequence until its existing3s deadline. The test now checks
the unchanged3s production deadline with the existing4s harness envelope and
requires rejection/dead connection. No runtime deadline was increased.

## Reproduction, manifest and rollback

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" -m adapters.carrot.nav .reference/m15-carrot-nav-366d6eae .candidate/NEW-NAV-CANDIDATE
```

Reference must contain the exact actual SHA and navigation dependency. The
existing fetch_reference helper was called with SPARSE_PATHS plus
openpilot/selfdrive/navigation into a NEW reference. Future Nav HEAD movement
does not alter the actual-base requirement; investigate before regenerating.
Configure tests with CARROT_NAV_REFERENCE_ROOT, CARROT_NAV_CANDIDATE_ROOT,
CARROT_HOST_CANDIDATE_ROOT; each vendor package stays in its own process.

Local final command used existing WSL test Python and those roots:

```sh
PYTHONDONTWRITEBYTECODE=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_jetson_m1.py tests/test_jetson_m1_recurrent.py tests/test_jetson_m1_parity.py tests/test_jetson_m15_semantic.py tests/test_carrot_nav_adapter.py tests/test_carrot_nav_loopback.py tests/test_carrot_nav_wire.py
PYTHONDONTWRITEBYTECODE=1 "$PY" tools/check_latest_carrot_compat.py --work-dir .candidate/m15-carrot-wip-5812a65 --report .reports/m15-20261023/carrot-compat.json --update-baseline
```

The exact-source upstream harness execute_pytest_suite ran each of the five
Nav test files separately, once on control and once on candidate, with isolated
PYTHONPATH/no plugin autoload. The11 managed tests reused
tests/test_current_carrot_adapter.py except its WIP-specific V2 legacy-default
expectation, explicitly deselected. Raw commands/logs/JUnit stay ignored.

Patch SHA256:
`bfeca1f882cbd12fe4130d17f9358b80472cdecc5a4e0e69af8a26289b535267`.
The artifact lists all six before/after SHA256 values and exact base SHA.
The rollback test copies only touched files into a disposable directory,
reverse-checks/reverses, verifies every before hash/new-file absence, then
forward-checks/reapplies and verifies every after hash. It never modifies the
reference, actual comma or operational host.

No operational rollback is needed now: no installation occurred. A future
separately approved M2 must bind source hashes and service/endpoint ownership
and restore the exact Nav/P2 environment. Do not apply this comma patch to a
host tree or publish the M1 plan into cache. Numerical hold and explicit M2
approval remain prerequisites; software PASS does not grant activation.
