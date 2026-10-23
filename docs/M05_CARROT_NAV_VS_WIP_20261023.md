# M0.5 source comparison: actual carrot-nav vs latest carrot-wip

Date: 2026-10-23. Evidence: SOURCE_ONLY / CPU source transformation and JSON round-trip checks. No Jetson/comma connection, device probe, GPU import, build/load, service action, Params write, commit, product-code edit, or hardware validation was performed by this analysis.

## Decision

**M0.5 result: PASS_RECOMMEND_A.** Actual comma was rechecked read-only and
remains at the supplied Nav SHA, IsOffroad1/IsOnroad0. M1 build is separately
authorized by the user after its identity/storage/isolation gates; this report
does not authorize comma modification or operational host activation.

Recommend **Strategy A: retain actual carrot-nav and port only the reviewed managed protocol-3/Cinque V3 seams later**. For M1, use a separate development host tree based on the existing reviewed WIP candidate; leave actual comma and operational Jetson runtime/cache untouched. Do not replace the full comma checkout merely to gain protocol 3.

This is conditional approval of a development direction, not a deployable Nav patch. Existing source adapters accept the Nav comma anchors but the complete host adapter correctly refuses Nav source drift. A dtype-preserving ModelSpec extension and Nav-specific behavioral verification remain necessary before any later comma port. All comma changes remain outside this stage.

## Fixed inputs and reproducibility

- Workspace branch: `feature/jetlink-multimodel-carrot`; requested implementation HEAD `5aa0bbac095686afd480627eddb627b1d011dc19`.
- Actual/latest carrot-nav input: `ajouatom/openpilot@366d6eae9aa9962104391e1d997fe956dea8f64d`.
- Latest carrot-wip input: `ajouatom/openpilot@813369b0c53bb9c997b7ffbe17fca90222a755b8`.
- Existing WIP reference: `.reference/carrot-wip-20261023-813369b0`; left unchanged.
- New ignored Nav reference: `.reference/m05-carrot-nav-366d6eae`, created with `tools.check_latest_carrot_compat.fetch_reference(...)`, canonical LF configuration and an exact detached Nav commit. WIP SHA fetched only into this new reference's Git object database for tree comparison; no checkout of WIP into it.
- Actual Jetson runtime `54e706fa...` and its protocol-2/Nav five-state-pair classification are supplied M0 evidence. Authenticated read-only M1 preservation inventory rechecked its current symlink, service and cache identities separately; they are distinct from the two openpilot source snapshots.
- Target Cinque V3: `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`, 766,354,845 bytes, three recurrent state pairs, full output width 18,452.

Read `AGENTS.md` and `docs/JETLINK_MULTIMODEL_PLAN_20261019.md` first. Source comparison commands, with `R=.reference/m05-carrot-nav-366d6eae`, `A=366d6eae9aa9962104391e1d997fe956dea8f64d`, `B=813369b0c53bb9c997b7ffbe17fca90222a755b8`:

```text
git -C R diff --shortstat A B
git -C R diff --numstat A B
git -C R diff --name-status A B
git -C R diff A B -- <reviewed path set>
git -C R show A:<source path>
```

The new exact-reference fetch used the repository helper from WSL Python 3. Both references were clean under WSL Git at end. Windows-native Git marks uninitialized/sparse submodule links differently; WSL Git is the clean-reference check used here. Full machine-readable paths, counts, statuses and source smoke evidence are in `artifacts/m05_nav_wip_20261023.json`.

Fresh upstream queries also returned carrot-jetson main
`d0dc96fa32410403dfb2fefff3e2909c11ec109b`, zoompilot/jetlink main
`d24328d849b0e5154b55f149dc18c5dfe8bd79cc`, and external review
`a890f6df1bd3eb0478754c68d8b5f92f15e8b722`. None moved since the previous
checkpoint. The actual/latest Nav and latest WIP SHAs above are observations,
not permanent branch pins.

## Quantified churn

Direction is **Nav -> WIP**: added lines are present in WIP; deleted lines are present in Nav. These are Git snapshot diffs with default rename detection, not chronological claims that one branch is universally newer. Zero binary files in these counts. Groups overlap and must not be summed.

| Scope | Changed files | Added | Deleted |
|---|---:|---:|---:|
| Full tree | 239 | 16,468 | 14,310 |
| Plan checker `RELEVANT_PATHS` | 108 | 204 | 8,625 |
| Broad Jetlink: peer + modeld/jetlink + vendored Jetlink + all tools/jetlink | 108 | 201 | 8,679 |
| modeld/jetlink | 12 | 58 | 590 |
| All modeld | 32 | 122 | 1,344 |
| Vendored Jetlink | 19 | 44 | 964 |
| All tools/jetlink | 77 | 99 | 7,125 |
| Direct selfdrive/controls | 0 | 0 | 0 |
| Hyundai opendbc, including tests | 10 | 14,525 | 15 |
| Carrot radar | 2 | 47 | 1 |
| Carrot route/instruction integration (`carrot_man.py`, `carrot_serv.py`) | 2 | 188 | 45 |
| navigation + navd | 30 | 738 | 2,029 |
| Carrot Web | 7 | 3 | 170 |
| Carrot server | 5 | 2 | 220 |
| cereal | 2 | 1 | 1 |

Most WIP added lines are unrelated Hyundai radar work: `radar_bosch.py` adds 7,325 lines and its tests account for a large remainder. The absence of direct controls-directory changes does not imply whole-vehicle equivalence: radar inputs, navigation inputs, model defaults, manager processes and message schema differ.

## Module/API comparison

Paths below are relative to each pinned openpilot tree.

| Module/scope | Nav -> WIP churn | Behavior and consequence |
|---|---:|---|
| `openpilot/common/jetlink_peer.py` | identical | Conservative Mac/iOS/Android classifier; neither branch has the managed Jetson selector capability. No need to replace this classifier. |
| `modeld/jetlink/contracts.py` | +2/-21 | Nav adds exact `JETSON_SPEC`, Nav map/instruction shape validation and exact negotiated N16 projection parsing. WIP retains generic queued/stateful validation but lacks those Nav contracts. Both can describe non-Nav three-state V3 structurally. |
| `compat.py` | +11/-10 | Nav legacy V3Client validates against V2 or its pinned Nav spec and uses dynamic packed layout. WIP legacy V3Client is exact V2 only and slices its 48-byte scalars. Main daemon uses generic `JetlinkClient`, not this legacy V3Client; do not mistake this adapter for the live daemon model path. |
| `daemon.py` | +16/-103 | Both select per-stream protocol and construct generic JetlinkClient; both keep loaded-identity checks and existing fallback IPC. Nav adds projection negotiation, USB read pipeline diagnostics, more timing counters and display negotiation. WIP removes these Nav-specific paths. |
| `link.py` | +5/-11 | Both validate dynamic model spec, exact IPC sizes, frame identity and finite outputs. Nav optionally requests N16's negotiated 2,066-float driving prefix; WIP always carries full model output. `validate_spec(spec, expected=None)` in Nav versus `validate_spec(spec)` in WIP is a real API difference. |
| `mac.py` | +1/-23 | Nav dispatches `is_jetson(peer)` first to its exact pinned `JETSON_SPEC`; pending load/build requires offroad. WIP has no separate Nav pin and non-App protocol-3 peers select fixed V2. Neither unmodified path selects arbitrary Cinque V3 on Jetson. |
| `model.py` | +10/-26 | Both reallocate packed inputs from the selected spec and use the same local small-model fallback. Nav fills map/commands and overlaps same-frame CPU context preparation with GPU warp while always draining the warp before fallback. WIP removes this Nav fill/overlap. |
| `inputs.py` | deleted, -26 | Nav clears maps/commands every frame, rejects bad shapes/nonfinite maps and enforces 0..255 pixels. Removing it changes Nav behavior. |
| `selection.py` | identical | Offroad-approved spec stored atomically as selected.json; full same-SHA spec equality is checked by prepare; a loaded-SHA change/unload raises ModelChanged. Reuse this. |
| `warp.py`, `prepare.py`, `phase.py`, `power.py`, `scheduling.py`, `mobile.py`, `__init__.py` | identical | Reuse warp parity probes/preparation and existing scheduling/lifecycle modules. |
| `startup.py` | +5/-36 | Nav supports local and SHA-256 USB release selection as well as signed release matching. WIP reverts to signed public release selection. A branch switch changes the installed updater contract, not only inference. |
| `host_release.json`, `jetson_model.json` | +8/-8; Nav pin deleted -165 | Branch-specific release and model selection. Do not copy either over actual runtime selection. |
| vendored `client.py` | +6/-71 | Both have generic protocol-3 packed handling: stateful scalar payload unchanged, queued prev_feat tail removed. Nav additionally negotiates protocol-2 stateful_v2, exact Nav map packing/block compression and driving-output projection. WIP rejects all stateful protocol-2 inference. |
| `protocol.py`, `protocol_v3.py` | identical | Strict v2/v3 framing already exists in Nav. `protocol.py.VERSION` remains 2 for the vendored server; a protocol-version flag alone is not a complete P3 server conversion. |
| `spec.py` | -1 | Nav's extra packed_shapes line carries nav_map/navigation. Neither unpatched ModelSpec serializes dtype declarations. This is a blocking exact-V3-contract gap in both branches. |
| `queues.py` | -146 | Nav has StatefulQueues, DeviceStateQueues and a queue factory in addition to PolicyQueues. WIP only has queued PolicyQueues. Nav stateful recurrence is real existing functionality, not something to discard or duplicate indiscriminately. |
| `server/session.py` | +21/-95 | Nav chooses stateful queues, validates named outputs and feedback, supports negotiated P2 compact maps/projection. WIP `_warm` always constructs PolicyQueues and checks only first output's count. Both raw servers need reviewed P3 resident identity/generation/offroad protections; existing WIP-based candidate supplies these. |
| `server/cache.py`, `server/main.py`, `server/control.py` | identical | Existing cache identity/tagging and host lifecycle can be reused; selecting another openpilot branch does not itself provide a complete managed P3 host. |
| TRT `__init__.py`, `build.py` | identical | Existing TensorRT build entrypoint reused; V3 source/physical dtype/build-record gates are supplied by our candidate adapter. |
| TRT `engine.py`, `cudart.py` | +13/-74; +2/-29 | Nav adds device-owned recurrence/event synchronization, state feedback staging and CUDA helpers. Device state defaults on for Nav stateful feedback. WIP removes this and its device_state/state_buffers modules. Do not enable Nav's performance defaults for new V3 without its own parity/finite validation. |
| transport `ffs.py` | +1/-13 | Nav has read-packet/finalizer hooks for an explicit Park/inactive AIO diagnostic; WIP reads directly. base/tcp/usbbulk/priority/watchdog and transport initialization are identical. StreamTransport lives in base.py; no transport/stream.py exists in either tree. |
| `tools/jetlink/server.py` | +4/-40 | Nav adds optional HUD Wi-Fi negotiation, USB-display capability and source-commit reporting. Both installed entrypoints can run migration/boot-gate behavior; neither is a harmless read-only launcher. |
| `prepare_cache.py`, `verify_model.py` | identical | prepare_cache is a cache writer and imports TRT; verify_model is specifically pinned to Cinque V2. Neither is a generic read-only V3 acceptance tool. Do not run them on the operational cache for analysis. |
| host_reader/host_usb/host_health | +1/-5; identical; identical | Nav host reader forwards protocol-version attributes, so wrapper identity/framing must survive any new managed transport path. |
| `update_host.py`, `install_updates.py`, `boot_update.py` | +14/-60; +3/-41; +10/-63 | Nav supports local/USB release registration, selected model pin compatibility and additional boot-display migration. WIP removes these paths. Both retain runtime ABI/signature/storage gates. |
| `install_server.sh` | identical | Writes systemd/udev, changes groups, enables/starts the service. Not an M0.5 or isolated-source-analysis action. |
| `build_host_bundle.py` | +3/-20 | Nav exports the selected Jetson pin to a legacy filename for bootstrap compatibility; WIP bundles fixed cinque_v2.json. Bulk copying the WIP packaging path would break the separate Nav selection contract. |

## Exact selection and fallback implications

1. In actual Nav `mac.prepare` (line 116), the broad legacy `is_jetson` test takes priority over App selection. It allows `carrot_host=jetson` or TRT/Orin identity and calls ensure_engine for the exact branch `JETSON_SPEC`, then validates exact spec. Changing the host's loaded model alone will not make Cinque V3 selectable.
2. In latest WIP, non-App protocol-3 legacy selection still chooses DEFAULT_SPEC/Cinque V2. Thus switching to WIP alone also does not solve managed multi-model selection. Both require the same small explicit Jetson capability path.
3. Our `prepare_managed` is inserted before the legacy branch, validates protocol=3/backend=trt/carrot_host=jetson/USB plus exact capability fields, asks only for a resident selected SHA, rechecks STATE before and after ENGINE_REQ, and uses a separate managed approval cache. Unknown model/spec first approval remains offroad-only. It never pretends Jetson is a Mac/phone or supplies ONNX for upload.
4. Nav's generic daemon and dynamic IPC/model path already handle a selected three-state V3 layout after the missing dtype serialization is added. Target V3 has no map inputs, so existing MapInput becomes a no-op for it. Preserve Nav's map/input code so reconnecting to the original Nav model does not regress.
5. Nav ModelSpec.from_dict(canonical CinqueV3).to_dict() **loses input_dtypes/output_dtypes**. A CPU JSON smoke check returned equality=false and exactly those two missing keys. Therefore the five-file comma source-anchor transform is insufficient. Port the candidate's optional dtype fields/round-trip behavior into Nav's spec.py while retaining its Nav packed_shapes entry. Omit empty dtype fields when serializing legacy Nav specs so the exact Nav projection contract/hash stays unchanged.
6. Nav's legacy compat.V3Client exact-pin validation also rejects arbitrary V3; if any separate user of that helper is retained, it needs an explicit reviewed contract path or must remain legacy-only. The live daemon uses generic JetlinkClient, so changing compat.py is not a prerequisite merely because its filename exists.
7. Both branches' JoiningModel catch external exceptions, close the client, record the fault marker if external inference was active (existing commIssue/disengagement path), reset the local model and run small.run. They require three local outputs before a new external join. The shared may_join gate requires fresh (<250 ms) state and standstill/near-zero speed OR steeringPressed; it is separate from ignition-off model approval. Do not describe it as a universal offroad-only join gate.
8. Existing per-stream framing changes only after failed HELLO on a fresh transport. Engine/inference errors do not authorize a protocol downgrade or another arbitrary big model. Preserve this and all finite/shape/frame/loaded-identity checks.

## Nav / NOO / Web / vehicle differences

- Nav maps are wired end to end: modeld subscribes navInstructionCarrot and navRoute; MapInput consumes a fresh 256x256 map (<0.5 s), fresh instructions (<2 s), and exact carrotRouteId agreement; missing/expired fields are zeroed by fill_inputs. WIP removes that modeld path, mapsd manager process, navigation package and carrotRouteId schema member. WIP has a different navd renderer implementation, which is not evidence of preserving Nav model inputs.
- carrot_man changes route source ownership/heartbeats to a different navd/carrotNavi sequence implementation. Nav has RouteSource arbitration and preserves route lifetime while computation pauses offroad. WIP changes route retention/reset and external route handling. carrot_serv also changes external-navigation priority and navInstructionCarrot validity handling. These are navigation/NOO integration differences even though controls/ is identical. No claim is made that either branch's NOO is safe or validated by this diff.
- WIP removes the /navigation server feature, navigation.html/map JS, the tools navigation-map link, and Nav-model HUD mode 7; configured HUD screen range changes 7 -> 5. It changes eGPU model display/default provisioning from Nav to Mountain Dew v3. Those are visible product differences unrelated to the V3 Jetson transport goal.
- WIP adds substantial Hyundai Bosch radar implementation/test changes and Carrot radar behavior, so a whole branch switch expands vehicle regression scope beyond protocol/model selection.
- Nav Wi-Fi/HUD coexistence and read-only network listing behavior also differ. Do not replace networking or display paths during managed V3 transport work.

## Strategy comparison and recommended boundary

| Strategy | Concrete work | Risk/rollback scope | Recommendation |
|---|---|---|---|
| A. Keep actual Nav; isolated managed host first; later minimal comma port | Reuse existing WIP-based host candidate in a new writable host source/cache; later add managed peer/prepare modules + V3 seed + optional dtype support, retaining Nav maps/projection/legacy pin/fallback. | Host dev tree/cache rollback now; small independently reviewed comma diff only in a separately authorized later stage. Nav behavior remains available. | **Preferred for this objective.** |
| B. Later move comma to WIP + candidate | Candidate source seams already reviewed on WIP, but must accept/reconcile 239-file snapshot differences, Nav map/route/Web removals, model default and radar changes, updater delivery differences. | Full comma branch/runtime/model/navigation/radar and host-update compatibility rollback; substantially broader stationary and vehicle regression. | Possible future independent migration, not required for M1/P3/V3. |

Read-only source smoke:

- PASS: `comma_files(Nav)` finds its exact anchors and returns 5 candidate file bodies entirely in memory. Existing-file delta is just +1 line in peer.py and +3 lines in mac.py; 3 added files contain 300 lines. This proves anchors only, not execution compatibility. The dtype extension is an additional required vendor-spec change.
- BLOCKED (correct fail-closed guard): `server_files(Nav)` raises `current server source body changed; review required: spec.py`. Do not weaken the hash guard or replace Nav server bodies without review. The Nav packed-map line is the first divergence; queues/session/engine differ much more substantially too.
- FAIL (known missing capability): unpatched Nav V3 JSON round trip drops both dtype maps. This is a concrete port requirement, not a reason to relax the exact-spec check.
- Existing evidence only: `.reports/m0-20261023-carrot-compat.json` reports PASS on WIP 813369b0 at implementation SHA `254cd09106d6d01bc40010437416d227c389fd2b`, 16 candidate touched files and 288 CPU/fake/fixture tests across seven suites. This analysis did not rerun those suites or promote that historical report into hardware evidence/current-HEAD validation.

## Rollback and next-stage constraints

- Actual comma must remain unchanged in this M0.5/M1 stage. No branch checkout, software update, Params change, or managed approval write on comma follows from this report.
- Keep actual runtime `54e706fa...`, its Nav assets, original V2 engine/ONNX, current service ExecStart and operational cache intact. Use distinct development source/cache/control/status paths and retain before hashes. The existing cache pruner can remove old engine entries, so sharing the operational cache is not isolation.
- Do not run install_server, update_host, boot_update or installed tools/jetlink/server.py startup just to exercise private P3 logic. Their entrypoints include real migration/activation/service effects. Any launcher chosen for M1 must explicitly avoid the operational updater and production cache.
- The candidate's managed CLI has no trusted offroad provider wired by default, deliberately disabling provisioning/preload. A real M1 runner must supply a reviewed trusted offroad authorization path before permitted preparation; a fabricated always-true production authorization is not acceptable. No inference/build success is implied here.
- Keep Nav projection restricted to its exact model/spec and negotiated protocol-2 capability. V3 should initially use full finite-validated outputs and independently validated state feedback, without importing Nav device-state defaults or optional AIO/fast-path work.
- Later comma rollback must restore exact pre-port file hashes and isolate the managed approval cache from legacy selection. Reversing a generated source patch is valid only against its verified after hashes; operational V2/Nav engine files must not be deleted.
- Hardware gates remain separate: V2 protocol-3 loopback, Cinque V3 TRT10.3 build/physical contract, recurrent parity, 1000+ finite frames, USB/fallback, latency/thermal and offroad selection. Vehicle driving and any claim about stop/restart improvement remain SKIP until separately validated.

Status: **PASS source comparison**, **BLOCKED unmodified Nav adapter deployment**, **SKIP ORT/TRT/Jetson/USB/vehicle validation**. No install/upgrade or comma modification is authorized or performed by this analysis.
## Navigation source locations (Nav SHA above)

- `openpilot/selfdrive/modeld/jetlink/mac.py:116-224` prepare; exact Nav legacy branch at 118-138.
- `openpilot/selfdrive/modeld/jetlink/contracts.py:34-90` validate_model_spec; `:99-117` parse_outputs.
- `openpilot/selfdrive/modeld/jetlink/model.py:166-176` _reset_small; `:178-272` JoiningModel.run; active-failure fault/reset/local fallback specifically `:252-272`.
- `openpilot/selfdrive/modeld/jetlink/selection.py:14-20` approved_spec; `:23-32` remember_spec; `:35-37` check_loaded.
- `openpilot/selfdrive/modeld/jetlink/daemon.py:245-410` _serve_local; `:541` generic JetlinkClient; `:580` prepare call with real offroad/connected predicates.
- `third_party/jetlink/jetlink/spec.py:91-108` packed_shapes including Nav fields; `:154-163` to_dict and `:166-173` from_dict drop dtype maps.
- `third_party/jetlink/jetlink/client.py:573-588` _protocol3_packed.
- `third_party/jetlink/jetlink/server/session.py:456-477` _warm; `:526-542` _check_shapes; `:674-700` on_hello; `:762-853` _infer.
- Local candidate sources: `adapters/carrot/integration.py::comma_files`, `adapters/carrot/server.py::server_files`, `adapters/carrot/peer_policy.py::prepare_managed`, `jetlink/multimodel_policy.py::is_managed_jetson_peer`.
