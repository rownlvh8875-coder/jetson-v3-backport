# M19-C1.2 — persistent onroad diagnosis blocked by device access

**BLOCKED_DEVICE_UNREACHABLE. Root cause UNKNOWN. Migration NOT_RUN.**

The known current address and one previously authorized address did not accept
SSH or the existing Carrot web terminal. Four bounded TCP endpoint probes failed;
no network scan or SSH trust bypass was attempted. The first-command helper
received zero terminal frames, so **no actual shell command was delivered**.
Its intended first commands remain only the two IsOffroad/IsOnroad reads.

The user's read-only diagnosis authorization permits observing an onroad device;
this attempt was not stopped by an OFF gate. It was blocked before a device
session existed. Current-address confirmation was requested while the offline
source review proceeded. Network addresses and terminal metadata remain private.
The user subsequently clarified that the comma had been left in the vehicle;
no new address or live power/network evidence was supplied. No immediate trip to
retrieve the device was requested. Continue when the normally powered device is
reachable; this receive-only diagnosis does not require making it offroad first.

## What is current and what is historical

| Item | This stage |
|---|---|
| Fresh IsOffroad / IsOnroad | NOT_OBSERVED / NOT_OBSERVED |
| Actual branch / HEAD | NOT_OBSERVED / NOT_OBSERVED |
| Simultaneous observation requested / completed | at least 10 seconds / 0 seconds |
| deviceState fresh samples | 0; NO_FRESH_DATA |
| pandaStates fresh samples / ignition / harness | 0 / UNKNOWN / UNKNOWN |
| managerState fresh samples / process state | 0 / NOT_OBSERVED |
| hardwared PID/start time/crash evidence | NOT_OBSERVED |
| Bounded hardwared/manager logs | NOT_READ |
| Natural transition / latency | NOT_OBSERVED / unavailable |
| Ticket / writer / capture environment | NOT_CHECKED, not absent/0 assertions |
| Root cause | UNKNOWN |
| Actual changes / migration | NONE / NOT_RUN |

The 0/1 flag pair belongs to **M19-C1.1**, not a successful new read in this
stage. No historical timestamps, process state, known HEAD or Panda values are
substituted for current evidence. Current device access failure does not prove
power-off, an IP change, stale Params or any particular ignition state.

## Exact060de9 source review, off device

Reviewed immutable Git blobs at
`060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c`, using `git show`, without checkout,
fetch on comma, import or execution of hardwared/manager/Panda code. Seven blob
hashes and byte sizes are in the artifact; the six Python files parse as AST.
These are pinned-source facts, **not fresh actual source attestation**.

| Boundary | Reviewed behavior | Source locations |
|---|---|---|
| Panda → hardwared ignition | For a new nonempty pandaStates message, OR ignitionLine/ignitionCan across known Panda types | hardwared.py:235–238 |
| Missing Panda updates | Clear retained ignition when receive age exceeds 5 seconds, logging `panda timed out onroad` | hardwared.py:37,244–247 |
| hardwared → deviceState | should_start requires all onroad conditions; when not started, startup conditions also apply; started is `started_ts is not None` | hardwared.py:344–347,375–393,413–414 |
| Timing | Normal processing at 2 Hz, plus ignition edges | hardwared.py:249–252 |
| deviceState → manager | manager reads deviceState.started and writes onroad flags on transitions | manager.py:209–229 |
| Params values | IsOnroad=started, followed by IsOffroad=not started; two writes | helpers.py:56–58 |
| Startup Params | manager initially calls write_onroad_params(False) | manager.py:197–198 |
| Onroad producers | card/modeld only_onroad; camerad started or driver-view setting | process_config.py:18–19,61–62,128,135,149 |
| Always-run services | hardwared, pandad, jetlinkd | process_config.py:137,155,165 |

An onroad flag alone cannot distinguish a fresh true Panda bit, retained ignition,
a stale deviceState publisher, or a manager discrepancy. The helper's two Params
writes also mean a single instantaneous read pair is not an atomic snapshot.
Repeated time-aligned measurements are needed.

`OnroadCycleRequested` initiates a one-second offroad cycle in the reviewed
hardwared; it does not independently supply persistent true ignition.
`IsDriverViewEnabled` can run camerad offroad and does not directly set
hardwared should_start here. Neither Param's value or existence was read on the
device in this attempt; the diagnosis allows only the two requested flag values.

One **unconfirmed source edge case** deserves checking during the live window:
repeated fresh *empty* pandaStates messages bypass the nonempty ignition
assignment while refreshing SubMaster.recv_time. If an earlier ignition value
was true, the five-second timeout branch need not clear it under that pattern.
Messaging receive-time assignment is at messaging/__init__.py:258–271. No empty
Panda stream was observed here, and this is **not a diagnosis of the current
device or a claim of a stuck Panda**.

## Pending receive-only diagnosis

Once the known device is reachable, first read the two flags, then observe
deviceState/pandaStates/managerState together for at least 10 seconds. Retained
initial queue data must be separated from newly received, valid messages using
their source monotonic timestamps and age. Record zero-length Panda arrays
explicitly; never convert missing data to false ignition.

Collect started/startedMonoTime/thermal status; each Panda's type, both ignition
bits, harness, controlsAllowed/heartbeatLost; manager role/PID/running state and
OS-level hardwared identity. Read only bounded matching log entries. Compare
fresh Panda ignition → device.started → both flags → managed process state.
Only a naturally observed transition permits a measured transition latency.

No source, Params, manager/onroad process, Panda, USB, Jetlink or Jetson change is
authorized by this diagnosis. In particular, do not start the Python pandad
wrapper merely to inspect it: its actual startup includes hardware operations.

## Preservation and next gate

There was no actual session, write, ticket creation, recorder activation, capture,
restart, inference or Jetson access. Operating before/after canaries could not be
read, so preservation is **NOT_ATTESTED**, not a fresh hash PASS. Development
changes are this sanitized report/artifact, README and continuation only.

Local verification checks source blob hashes/AST, JSON integrity, status
consistency, public privacy and Git diff. No production code changed and no CPU
regression was rerun; the previous 543 PASS is historical and is not counted as
a new result.

**Safe to retry M19-C1.1: NO.** First restore the device connection and finish the
receive-only diagnosis. Any separate installation retry still requires fresh
IsOffroad=1, IsOnroad=0, device.started=false, ignitionLine=false,
ignitionCan=false, normal onroad process termination, exact060de9 and every
approved source/package/private-overlay gate. Do not modify/reset/update the
device to obtain those values.

Numerical decision remains PARITY_UNDETERMINED; M2 and vehicle10 readiness NO.
The result commit resolves with
`git log -1 --format=%H -- artifacts/m19c12_persistent_onroad_diagnosis_20261024.json`.
