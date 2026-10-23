# M0 read-only checkpoint — 2026-10-23

**Authenticated SSH and core inventory: PASS.** Eleven inventory gates passed;
two privileged queries remain BLOCKED. These are read-only observations, not
TensorRT execution, recurrent inference, USB throughput or vehicle acceptance.
No install/build/load/restart, GPU initialization, Params, power/clock or model
selection change was performed. Existing models, engines and releases remain.

## Access diagnosis

The official SSD setup worked: Jetson returned `Server accepts key` for the
existing PC public key. The private key was encrypted; unattended BatchMode
could not sign. This corrects the earlier inference that Jetson registration
had failed. After the user unlocked the key locally, authenticated SSH and the
inventory succeeded. No key was re-enrolled and no authorized_keys was changed.

The current PC key is absent from comma's four configured GitHub keys. Comma's
existing standard web terminal instead provided a temporary, one-client TCP
relay to the Jetson USB-network SSH endpoint. The private key stayed on the PC;
the temporary local agent signed without agent forwarding. The relay bound the
known comma home interface, accepted only the known PC and connected only to the
observed Jetson endpoint; no subnet scan, routes, firewall or services changed.
Temporary terminal sessions disabled history and exited. Existing known_hosts
were preserved; separate ignored host-key files pinned the observed endpoints.

The first local helper failed because WSL lacked a persistent signing agent,
then lacked an input TTY. Both were corrected before success: foreground agent,
explicit PTY, key lifetime20 minutes, passphrase entered only by the user locally.
No passphrase was requested in chat, stored in helper files or captured by the
agent. The temporary agent's keys were cleared and its process stopped after
the read-only session; a final TCP check confirmed the one-use relay was closed.

Official source reviewed: historical R2 `docs/JETSON-SSH.md` and current
`tools/jetlink/protected_first_boot.py`. The setup key list replaces existing
authorized_keys, so never blindly re-enroll one key or reboot as a workaround.
No provisioning script or credential/Wi-Fi setup file was run or printed.

## Actual device evidence

| Item | Observed result | Evidence / limit |
|---|---|---|
| comma | carrot-nav `366d6eae9aa9962104391e1d997fe956dea8f64d`, aarch64 | COMMA_REAL read-only shell |
| Road flags | IsOffroad1 / IsOnroad0 | Params read only; no vehicle test |
| Jetson OS | Ubuntu22.04.5, L4T36.4.7, kernel5.15.148-tegra | JETSON_REAL read-only |
| Boot/root | `/dev/nvme0n1p1`, ext4 `ro,relatime,norecovery` | NVMe confirmed; protected root |
| Runtime/data | p17 CARROTDATA, mounted `/run/carrot-data`; `/runtime` bound at `/opt/carrot-jetlink`, rw | No remount/write |
| TensorRT | dpkg `10.3.0.30-1+cuda12.5`, Python metadata10.3.0 | No TensorRT import/build/load |
| CUDA toolkit |12.6.11-1; absolute nvcc12.6.68, cudart12.6.68-1 | nvcc absent from default PATH; no fix applied |
| Runtime Python |3.10.12; venv numpy1.26.4, onnx1.23.0 | Metadata queries only |
| CUDA Python | system metadata absent; runtime venv cuda-python12.9.0 / cuda-bindings12.9.9 | Distinct from toolkit version; GPU use untested |
| Power | MAXN_SUPER mode2 | nvpmodel query only |
| Clock lock state | BLOCKED: jetson_clocks --show requires root | No sudo/clock change |
| Current release | `/opt/carrot-jetlink/current` → `releases/54e706fa0573e91dc3b4a0d4f625b9d81a6b68cc` | Release ID plus HELLO source field; no .git/full-tree attestation |
| Runtime cache | `/opt/carrot-jetlink/cache` | Existing files listed/hashed only |
| USB topology | CDC and vendor-specific interfaces at5000M | USB_REAL enumeration; no throughput/inference claim |
| Setup result | BLOCKED: provisioned.json root-only; setup result not mounted | No mount/permission change; key acceptance independently proven |

`carrot-jetlink.service`, Wi-Fi, HUD and boot-display units are loaded/active.
Main service user is `jetlink`, WorkingDirectory `/opt/carrot-jetlink/current`:

```text
/opt/carrot-jetlink/venv/bin/python /opt/carrot-jetlink/current/tools/jetlink/server.py --backend trt --transport usb --cache /opt/carrot-jetlink/cache --control-socket /run/carrot-jetlink/control.sock
```

Root had5,471,490,048 bytes available; runtime/data12,482,035,712 at the sample.
No resize or allocation occurred. Five existing release directories remain.
No environment dump, credential material, hardware serial or private address is
included in this document or committed evidence.

## Preserved model/engine identity

CPU SHA256 reads on actual Jetson, with matching pre/post stat checks:

| Existing file | Bytes | SHA256 |
|---|---:|---|
| V2 ONNX |766040736| `09d080f36965bb2a0790500452bd328aa03c484d0222aa79d1ad9f021a522aec` |
| V2 TRT plan |771100700| `5d7a4a40ad3830fb4406694dddc1b13f1c05a8d47360586c6891bfce8f1f3ca2` |
| Current Nav ONNX |814591107| `01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a` |
| Current Nav TRT plan |795042044| `2c5c5a5e0c736b4d60a6c56569539df219c9e5b32aee8fde26be6d446c96caa2` |

V2 ONNX matches the exact project identity/size. V2 plan matches the existing
sidecar imported_plan_sha256. Current Nav ONNX agrees with saved HELLO and its
sidecar; its spec has five recurrent state pairs plus navigation/map inputs.
No engine was deserialized or run, so these checks do not prove inference or a
working rollback. Cinque V3 was not present in the enumerated cache. V2, Nav
assets, timing cache, last-loaded selection and old releases were preserved.

Fresh comma diagnostics were ready/inactive with one52.562°C sample; saved
HELLO reported protocol2 / Orin-sm87 / TRT10.3 / stateful_v2 / Nav-u8 / N16 and
engine_state none. Do not equate advertised loaded SHA with a resident engine.

## Commands and test evidence

The first Jetson command streamed the reviewed existing inventory on stdin:

```text
env PYTHONDONTWRITEBYTECODE=1 GIT_OPTIONAL_LOCKS=0 python3 - --pretty
```

Only the inventory's `nvidia_smi` entry was omitted; no target file was copied.
Read-only follow-ups used stat/readlink, systemctl show, dpkg-query,
importlib.metadata in the actual venv, findmnt --target, df, lsusb -t and bounded
cache enumeration. hashlib read existing ONNX/plan/JSON bytes; nvcc --version
used its absolute path. Initial multi-target findmnt syntax returned1; separate
--target queries corrected it without mount changes. Non-root jetson_clocks
and root-only setup result remained explicit BLOCKED queries.

Actual command helpers/raw output remain in ignored `.reports/m0-20261023/`.
Sanitized public evidence: `artifacts/m0_20261023_summary.json`.

Project start HEAD `254cd09106d6d01bc40010437416d227c389fd2b`; correct feature
branch, initially clean. No adapter/product implementation changed this session.

| Upstream | Latest observed HEAD |
|---|---|
| ajouatom/openpilot carrot-wip | `813369b0c53bb9c997b7ffbe17fca90222a755b8` |
| ajouatom/carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |

From ba1869151:5 relevant additions/11 modifications reviewed: startup
grace/handoff, USB-completion priority lifecycle, modeld camera-gap telemetry,
new helper tests and Web model status. Stateful spec/server/TRT seams unchanged.

```sh
PYTHONDONTWRITEBYTECODE=1 ~/.venvs/cinque-v3-stage3/bin/python tools/check_latest_carrot_compat.py --work-dir .candidate/m0-carrot-20261023-813369b0 --report .reports/m0-20261023-carrot-compat.json --update-baseline
```

ONLINE rolling: **PASS288 / FAIL0 / SKIP0**, CPU_FAKE/FIXTURE, heads unchanged
before/after and freshly re-queried after M0 with the same checker ref resolver.
Additionally isolated current candidate startup, USB-priority and
write-watchdog tests: **PASS103 / FAIL0 / SKIP0**. The checker's
execute_pytest_suite harness ran `test_connection_startup.py`,
`test_usb_priority.py`, `test_write_watchdog.py`; scheduler/trace/time boundaries
were faked. Current distinct CPU pytest cases391; prior469 remains historical.
These tests did not change kernel scheduling or test actual USB/GPU inference.
M0 metadata gates separately: **PASS11 / FAIL0 / BLOCKED2**.

## Next stage

M0 core inventory is available. Reconcile actual carrot-nav/Protocol2/Nav/N16
runtime with our carrot-wip/Protocol3 managed candidate **before** choosing the
host patch or any runtime write. The current candidate is not directly approved
for the installed branch. Start later development in a separate writable copy;
do not replace current, cache, V2 engines or existing releases.

Keep sequence: M0 → baseline V3 TensorRT build → recurrent inference → USB
protocol3 → latency/fallback → only then optional DeviceState/InputFastpath A/B;
AIO only if measured tail latency warrants it. No optimization was activated.
TRT_REAL build/load, recurrent parity/timing, USB inference, fallback and vehicle
acceptance remain NOT_RUN. Device presence does not convert historical blocked
hardware checks into PASS. Privileged clock/setup questions can be resolved
later with appropriate read-only access; do not elevate or remount by inference.
