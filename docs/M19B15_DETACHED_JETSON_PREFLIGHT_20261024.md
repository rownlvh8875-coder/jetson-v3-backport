# M19-B1.5 — detached comma + Jetson readiness (2026-10-24)

**DETACHED_JETSON_PREFLIGHT_PASS. Ready for M19-B2 vehicle10: YES**, as readiness
for a separately authorized stage. Existing Nav/V2 Protocol2 is ready, USB is
SuperSpeed, protected assets and runtime identities are unchanged, and recorder
activation-v2 remains **PATCH_LEFT_INSTALLED_OFF_V2**. No ticket, activation,
capture, restart, forced producer, model selection, V3/P3 or configuration change
occurred. **USB_REAL_INFERENCE = NOT_RUN_BY_SCOPE**, capture frames0/dataset NONE.
Numerical decision remains **PARITY_UNDETERMINED / M2 NO**.

Development began clean on `feature/jetlink-multimodel-carrot`, local/remote equal
at `540fbcad790ebc7572a993f8b2269a72b4f9132c`. Actual comma remains carrot-nav
`366d6eae9aa9962104391e1d997fe956dea8f64d`; latest upstream was not installed.

## Comma identity, detached state and recorder

The first actual comma shell commands were the two flag reads, returning **1/0**.
Fresh PRE and final full POST confirmed the exact installed activation-v2 profile,
original48 private path/hash/metadata commitments, U32/U46, context pins and no
unexpected source entries. This was a V2 POST comparison, not the obsolete
tracked0/M19-A BEFORE gate.

| Check | Result |
|---|---|
| Original48 | 48 entries /2006 files /417208589 bytes, unchanged |
| Original48 digest | `8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5` |
| Installed V2 POST | 49 entries /2011 files /417266269 bytes, unchanged |
| V2 POST digest | `a4980220b3fd14af9149c01d6643cdd2ee97388c1d90e4ccf65853b89d85304c` |
| model.py | `0fbcba80a84fa6ffd22a6463cb75f111c95cd939697ce357e44ec45909109c91` |
| hook.py | `9e688299d4fcefeea3a5ebc1460ee8fd72afd1c15c9f2d1a1fd3f58b1a5ca7de` |
| Other4 recorder files / process.py / modeld.py | Exact pinned hashes |
| Sources, models, routes, process identities | Exact before/after; original31 identities retained |
| Ticket namespace / capture output | Absent; no directory or ticket created |
| Recorder / writer / observer memfd / activation env | OFF /0 /0 /absent |

U32 remains **U32_UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION**, runtime use UNKNOWN;
U46 remains SAFE_GENERATED_LEGACY. No original48 content was removed, moved,
copied or renamed. Route preservation covers the metadata inventory, not a fresh
full content hash of all route files. Index/native/bytecode canaries also matched.

Fresh receive-only telemetry showed known `cuatro` Panda, ignitionLine=false,
ignitionCan=false, harnessStatus=notConnected, deviceState.started=false and normal
OFF card/modeld/camerad inactivity. Three accepted final windows contained Panda
**28/28/29**, managerState **6/6/6**, deviceState **6/6/6** samples. All original
validity, source-time freshness and frequency deadline checks remained enabled.
This is **DEVICE_DETACHED_EVIDENCE_PASS**, not a vehicle stationary assertion.
Modeld timing and camera cadence are NOT_AVAILABLE_OFFROAD; no real onroad
activation footer import was executed.

One earlier final health window rejected its initial cached deviceState sample
because its source timestamp preceded that window's start, despite started=false.
It was not counted PASS. An identical new three-window read passed without
changing a timeout or freshness rule. Full process collections and telemetry
helpers ran sequentially. The temporary SSH relay was closed before final comma
identity collection, so its helper did not alter the expected process set.

## Jetson and protected assets

Existing pinned-host SSH authentication was reused; StrictHostKeyChecking=yes and
UpdateHostKeys=no. No new trust, key copying or network scan occurred. Old temporary
mux sockets were closed, so a temporary local signing agent and the previously
reviewed SSH-only relay were reopened and subsequently closed. No persistent
device setup was installed. Private connection data stays in ignored evidence.

| Item | Fresh result |
|---|---|
| Hardware/root | Orin Nano Super, NVMe root, protected root read-only |
| L4T/kernel/Python | 36.4.7 /5.15.148-tegra /3.10.12 |
| Power | MAXN_SUPER, mode2; query only |
| TRT/CUDA package | 10.3.0.30-1+cuda12.5 /CUDA toolkit12.6.11-1 |
| Service | active/running; backend trt, transport usb; NRestarts0 |
| Current release | `54e706fa0573e91dc3b4a0d4f625b9d81a6b68cc` |
| Control socket | Present/listening; audit did not connect to it |
| Service PID/start/argv/cwd/executable | Exact before/after |
| Releases/cache/unit/drop-ins/package inventory | Five releases, eight cache files; exact before/after |

All four required asset identities passed fresh complete SHA256 reads:

| Asset | Bytes | SHA256 |
|---|---:|---|
| V2 ONNX | 766040736 | `09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec` |
| V2 plan | 771100700 | `5d7a4a40ad3830fb4406694dddc1b13f1c05a8d47360586c6891bfce8f1f3ca2` |
| Nav ONNX | 814591107 | `01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a` |
| Nav plan | 795042044 | `2c5c5a5e0c736b4d60a6c56569539df219c9e5b32aee8fde26be6d446c96caa2` |

Sidecars, timing cache and last-loaded selection also matched; these hashes and
release membership match the retained M16 operating evidence. Current last-loaded
selection is **Nav SHA01effc… /frame_skip4 /backend trt**, matching current comma
status and live engine state. No V3 selection or experimental environment flag was
observed. The M1 V3 plan was neither accessed nor loaded. The audit imported no
TensorRT/CUDA module and initialized no GPU context. Existing operating GPU state
and historical Nav CUDA-graph/device-state messages were left unchanged.

Read-only sanity readings showed CPU about54.9°C, GPU55.0°C, TJ55.3°C and live
thermal health OK. About5.76GB RAM was available; swap use was about0.46GB. Root
free space was5.47GB and operating partition free space6.57GB. These are idle
snapshots, not stress/latency/thermal acceptance tests. Three other thermal zones
returned no usable temperature; values were not fabricated. The first collector
failed on that sysfs TypeError before returning a receipt; the local collector
was corrected to record unavailability and full fresh reads then succeeded.

## USB and existing P2 readiness

Jetson USB topology and sysfs identify the `1209:0001` jetlink peer at **5000M**,
vendor interface usbfs and network interface cdc_ncm. Its running service owns
the matching USB device handle. Comma reports **a600000.dwc3 /configured /
super-speed**, with ffs.jetlink and ncm.jetlink functions. AdbEnabled is **0**.
The `g1` gadget is **absent**, rather than a present gadget with blank UDC; no
blank read was fabricated and no competing gadget owns the UDC. This is an
exclusive healthy Jetlink binding, so it passes the ownership check without any
gadget/ADB change. Before/after state matched; no USB2 fallback was observed.

**P2_SERVER_READY** is supported by the existing daemon's published HELLO metadata,
fresh live STATE telemetry, exact asset/source identity, service/socket/FD and USB
evidence. Three passive status samples reported ready /protocol2 /engine ready /
Nav loaded /health ok. Status ages were0.18–0.34s and live telemetry ages0.45–0.61s.
The pre-existing server frame counter was **10 throughout**, not a new audit or
recorder frame count. No client, INFER request or manual producer was created.
The normal daemon already maintains its own HELLO/state keepalive while modeld
is absent, consistent with actual366 daemon.py:249–280.

Actual runtime protocol.py declares VERSION2 and supported versions(2,3);
session.py:674–700 advertises the legacy stateful_v2/Nav contract. P3 source
support does not mean an active P3 session. **Current P3/V3: NOT_ENABLED**.
Actual366 daemon.py publishes the original `peer` HELLO separately from refreshed
`client.last_state`: the peer snapshot retains startup engine_state=none/frames0
and an old protocol error, while current live telemetry is engine ready/frames10/
health ok. These snapshots were not conflated.

Bounded journal reads used at most80 recent lines over15minutes and60 boot-tail
lines. Unprivileged journal access was denied; existing `sudo -n` read-only access
worked without changing groups/permissions. Recent queries returned no entries.
Boot tail retains an earlier boot-update wait interruption before the current
successful start, one unknown_message type16387, one USB transfer-status5
disconnect, an engine portability warning, then successful reconnect/HELLO and
Nav engine-ready. These historical events are disclosed; no repeated current
disconnect/error, crash loop, load failure or device memory error was observed.
No error was cleared and no service was restarted.

## Preservation, checks and handoff

Jetson before/after comparison passed14 checks. The service/unit/drop-ins, package
inventory, all eight stable cache files, timing/selection, current symlink, release
membership and source hashes matched. Its new metadata-inclusive preservation
digest is `02c247700e66e674764ff2a21c7e1f5e762fecedcfa1cb9caeb062b64b82d3f2`;
it is not a replacement for older schemas' digests. Comma final full attestation
matched the original48 and V2 POST exactly, with no unexpected source entry.

Normal SSH/sudo logging and native receive-only queue cursor bookkeeping can
update OS runtime records. No command wrote source, Params, packages, service or
USB configuration, model selection, operating cache or route content. Owned SSH
master, relay and signing agent were closed; personal keys were unchanged.

Fresh unchanged offline receipt regression: **CPU_FAKE/FIXTURE29 PASS /0 FAIL /
0 SKIP**, 0.30s. This is not a new339-case run or a hardware inference test.

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 python -m pytest -q -p no:cacheprovider tests/test_recorder_activation_deployment.py --tb=short
```

No production code or patch changed. Public evidence contains anonymous original
IDs, source contract hashes, counts and sanitized metrics; no private paths,
addresses, argv/environment payloads, raw logs, credentials, route names/GPS or
tensor binary is committed. The artifact records private receipt commitments.

Next action: **separately authorized vehicle-mounted M19-B2 read-only OFF/source/
USB preflight**, with a continuously stationary observation plan before one-shot10
arming. Automatic lazy-import activation can precede a later external stationary
check; stationary coverage must span capture timestamps. Missing proof invalidates
the dataset. No ticket, onroad transition, road capture or M2 authorization is
inherited from this readiness result.

Result commit: `git log -1 --format=%H -- artifacts/m19b15_detached_jetson_preflight_20261024.json`.

One fresh independent local read-only final review approved publication with
Critical0 /Important0 /Minor0 /Declined[]. It verified all15 private evidence
commitments and the29-case JUnit without tests, scripts or device/network access.
Start/end upstream HEADs and protected remote main/old-feature refs matched;
actual366 was not advanced. Result documentation only is published on the same
feature branch; final HEAD/local-remote equality is reported after normal push.
