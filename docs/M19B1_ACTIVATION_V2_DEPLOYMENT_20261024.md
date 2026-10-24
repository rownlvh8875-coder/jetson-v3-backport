# M19-B1 — activation-v2 installed, OFF validation (2026-10-24)

**PASS / PATCH_LEFT_INSTALLED_OFF_V2.** The explicitly approved two-file delta
was installed on actual carrot-nav
`366d6eae9aa9962104391e1d997fe956dea8f64d`. No ticket was created. No activation,
capture, restart, ignition transition, Params/model selection change, Jetson
access, USB inference or vehicle operation occurred. The original M18 patch was
not reapplied. Numerical status remains **PARITY_UNDETERMINED / M2 NO**.

Development started clean, on `feature/jetlink-multimodel-carrot`, with local and
remote HEAD `7c38054aae7bead13fc9d4bf34453f5b985a78a9`. Main and the old feature
branch are preserved. Actual comma has no new Git commit or branch change.

## Fresh gates and deployment

The first actual shell commands were only the two IsOffroad/IsOnroad reads,
returning **1 / 0**. Fresh frozen collection then verified installed M19-A,
rather than requiring tracked0 or an absent recorder package. Requirements were:

- Original48 private path/tree commitments exact: 2,006 regular files,
  417,208,589 bytes, digest
  `8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5`.
- M19-A six source hashes exact, one expected tracked modification, 49 collapsed
  untracked entries / 2,011 regular files / 417,259,473 bytes; POST digest
  `6857b161fe10363ae9bb58b505195a40a031872e3ef1746917d7e7f89fba50ba`.
- Context source pins exact, source/model/route commitments and original31 process
  identities unchanged. Original anonymous IDs were never reassigned from new
  status ordering. Index bytes and extra source/native/bytecode canaries preserved.
- U32 remains **U32_UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION**, runtime use UNKNOWN,
  exact hash unchanged. U46 remains SAFE_GENERATED_LEGACY, unchanged. No original48
  file was removed, moved, copied or renamed.
- Fixed discovery namespace absent. Its parent was verified read-only as an exact
  tmpfs mount, root-owned/group, mode1777, without symlink. No discovery directory
  was created. Capture environment, writer, capture memfd and output root absent.

Three fresh receive-only telemetry windows before deployment showed known
`cuatro` Panda, ignitionLine=false, ignitionCan=false, harnessStatus=notConnected,
deviceState.started=false, normal OFF card/modeld/camerad inactivity and healthy
manager/jetlinkd. This is **DEVICE_DETACHED_EVIDENCE_PASS**, not a vehicle stationary
assertion. Only existing queues were opened; no publisher, CAN reader or onroad
producer was started. Native subscriber reader/cursor bookkeeping is not a claim
of zero OS writes.

A fresh exclusive private disposable tree outside source/routes contained only
the six recorder sources, context pins and tracked package markers. Actual48
overlay content was not copied. Forward check/apply, six after hashes, syntax,
unchanged inference AST, one missing-ticket footer check, dependency resolution
and reverse check/apply all passed. Reverse restored the exact M19-A copy.
Controlled recorder-module imports started no writer and imported no U32. Observed
startup-parent and operator resolution environments retained their respective
dependency precedence, including U48. Live manager-child sys.path/module state
was not injected or inferred from these fixtures.

Immediately before actual application, the full PRE gate and fresh detached
telemetry were repeated. Two exclusive mode0600 private backups outside source
were written and fsynced, with M19-A hashes verified. No existing backup was
overwritten. Actual `git apply --check` preceded `git apply`, without index writes.
Both changed sources have exact V2 hashes and unchanged file owner/group/mode.
Other four recorder sources and both context pins remained exact. No restart was
needed or performed. Actual366 `restart.sh` remains unsuitable because it pulls
Git updates; it was not used.

## Exact source profiles

Only these two existing installed files changed:

| Source | M19-A BEFORE SHA256 | Activation-v2 AFTER SHA256 |
|---|---|---|
| `openpilot/selfdrive/modeld/jetlink/model.py` | `4813e215b13b447a234ca78839d4cac605f69a9ec2b1a6263ed9ffa063204f0d` | `0fbcba80a84fa6ffd22a6463cb75f111c95cd939697ce357e44ec45909109c91` |
| `openpilot/selfdrive/modeld/jetlink/input_recording/hook.py` | `e8196e46df04a0ca99dd1ba4d009d5a683bd8e8a7a91b05a8b81bec3731f5bd1` | `9e688299d4fcefeea3a5ebc1460ee8fd72afd1c15c9f2d1a1fd3f58b1a5ca7de` |

All six hashes, the unchanged four and the context hashes are in the sanitized
artifact. The context pins are process.py
`fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752`
and modeld.py
`008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594`.

Forward delta SHA256:
`ea18f2c2849e09e577882599a6374c13d09779ebbef5909d2d73934ed41ad6cb`.
Reverse delta SHA256:
`0593e4a283d3ceec85c37367d0a3776ba0c80340ac857122bfe90f37ee36cf4a`.
Both were freshly checked before use. Original M18/checker/activation generator,
patches, protocol adapter and numerical tools remain frozen.

## Final OFF health and attestation

Fresh three-window POST health passed, with Panda samples **29 / 28 / 28**,
managerState **6 / 6 / 6**, deviceState **6 / 6 / 6**. All validity, source-time
freshness and frequency deadline gates remained enabled. Original31 selected
processes had no capture environment or observer memfd; no recorder writer was
found. Detached state persisted, namespace/output root remained absent, source
pins and extra canaries were exact. Ticket/activation/capture/frames = **none /
none / NOT_RUN / 0**. No full real-modeld activation footer import occurred:
modeld is correctly absent offroad. Syntax/static footer and missing-ticket fixture
checks are distinguished from real onroad execution. Modeld timing and camera
cadence are **NOT_AVAILABLE_OFFROAD**.

Final isolated full POST collection passed every check:

| Profile | Collapsed untracked | Regular files | Bytes | Aggregate digest |
|---|---:|---:|---:|---|
| Original48, unchanged | 48 | 2006 | 417208589 | `8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5` |
| M19-A PRE, retained historical profile | 49 | 2011 | 417259473 | `6857b161fe10363ae9bb58b505195a40a031872e3ef1746917d7e7f89fba50ba` |
| Activation-v2 POST, new profile | 49 | 2011 | 417266269 | `a4980220b3fd14af9149c01d6643cdd2ee97388c1d90e4ccf65853b89d85304c` |

The new aggregate is metadata-sensitive, not a replacement for the old profiles.
All original48 private path/tree checks, exact six hashes, source/model/route
commitments, process identities, context pins, owner/mode and namespace checks
were checked separately. The result is a guarded collection, not a globally
atomic device snapshot. Route preservation is a metadata inventory comparison,
not a new full content hash of every route file.

One initial POST collection overlapped the receive-only health helper and rejected
the process identity comparison. That sample was **not** counted PASS. The frozen
collector selects source-root cwd processes, so another audit helper can enter
coverage. Its exact extra PID was not retained in the rejected compact result;
this cause is therefore an observer-overlap diagnosis, not proof of a particular
PID. Source mutations and activation remained stopped. An identical isolated
read, after the helper exited, passed exact original31 identities and every other
gate. No checker/allowlist/timeout was weakened. The failed transcript remains
private. Final evidence required no rollback. Future full identity collections
must run sequentially with telemetry helpers.

## Offline receipt regression

The added checker `tools/check_recorder_activation_deployment.py` is a pure
**offline receipt consistency** validator. It does not collect or authenticate a
device, patch source, import vehicle modules or arm a ticket. Actual private
collector evidence remains authoritative. The actual sanitized receipt passed
this validator. Fixtures reject wrong PRE/POST source profile, counts, unknown
entries, original ID/hash commitments, context drift, metadata/index failures,
health/ticket/env/writer/capture/restart and missing evidence.

Fresh final GREEN scopes, unique **339 PASS / 0 FAIL / 0 SKIP**:

- Existing B0 complete regression: **310 PASS**, 69.54s.
- New POST metadata/isolation receipt fixtures: **29 PASS**, 0.29s.

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -m pytest -q -p no:cacheprovider tests/test_recorder_activation_v2.py tests/test_u32_provenance.py tests/test_comma_dirty_baseline.py tests/test_comma_dirty_layout.py tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py --tb=short
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_recorder_activation_deployment.py --tb=short
```

Host runtime: WSL Ubuntu24.04/Python3.12.3. JUnit files and complete private
receipts are retained in ignored development evidence. The expected TDD RED
collection error from the absent new checker preceded implementation; it is
separate from the final GREEN counts. No actual device performance acceptance
is inferred from CPU_FAKE/FIXTURE tests.

## End boundary and next action

**PATCH_LEFT_INSTALLED_OFF_V2** is retained: exact after profile, OFF health,
no ticket/env/writer/output, preserved overlay and no need for an unnecessary
reverse/reapply or restart. Exact reverse delta was tested in the disposable copy
and remains available for a verified failure; the whole M18 patch is not the
activation-v2 rollback unit.

**Ready for M19-B vehicle10: YES, future execution readiness only.** This stage
does not authorize capture. Next action is a separately approved vehicle10
preflight using existing Nav/V2 Protocol2, fresh V2 POST/source/spec checks and
genuine OFF arming proof. The vehicle must remain physically stopped; live
stationary evidence must cover the actual capture timestamps, because automatic
lazy-import activation can precede a later external check. Unknown/moving coverage
must invalidate the dataset. No forced onroad producer, V3/P3 selection or road
capture is allowed as a workaround. M2 remains NO.

Result artifact: `artifacts/m19b1_activation_v2_deployment_20261024.json`.
Resolve the final development result commit with:
`git log -1 --format=%H -- artifacts/m19b1_activation_v2_deployment_20261024.json`.
Public evidence contains source contract paths/hashes, anonymous original IDs,
counts and commitments. Private actual paths/argv/env/U32 content/network details,
credentials and any tensor data are excluded.

One fresh independent local read-only final review approved the five publication
files with Critical0 / Important0 / Minor0 / Declined[]. It verified all eight
evidence commitments and both saved JUnit scopes without rerunning tests or
contacting devices/network. Validation code commit: 6cab5b5227c4676397478b61524bae6c0956d414.
Start/end upstream HEADs matched those in the artifact; actual366 was not advanced.
Protected remote main/old-feature refs also matched their original values.
