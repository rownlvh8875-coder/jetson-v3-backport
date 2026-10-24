# M19-C1.2 — live diagnosis resumed: current OFF, historical cause unknown

**Current genuine OFF observed; persistent Onroad=1 not reproduced.**
**Root-cause classification UNKNOWN for the earlier report. No migration.**

The user brought the comma home and supplied its current address. In a fresh
private terminal, the first actual commands were again only the two flag reads:
IsOffroad=1 / IsOnroad=0. This resumed the receive-only diagnosis, not the
previously blocked installation. The earlier inaccessible attempt and its
artifact remain unchanged as historical evidence.

Observed branch is **carrot-nav**, actual HEAD
**a559fcd971ccaa5a87befb8ec080f59a2966325b**. This differs from the approved
exact060de9 recorder target. Tracked modifications0; untracked short entries49.
No checkout/reset/pull, patch, restart or updater manipulation was performed.

## Same-window fresh evidence

The local observation started at **2026-10-24 17:59:45 +09:00**. Its receive-only
window was **12.094330398 seconds**, monotonic468959524110–481053854508ns.
All three services span more than ten seconds in their own fresh source
timestamps. Source timestamps, validity and receive age were checked for each
sample; retained/default data were not substituted for fresh evidence.

| Service | Fresh samples | Source span | Maximum receive age | Age at window end |
|---|---:|---:|---:|---:|
| deviceState |22 |11.308725s |23.889ms |314.024ms |
| pandaStates |112 |11.960442s |18.712ms |113.934ms |
| managerState |22 |11.306677s |27.020ms |295.272ms |

These are subscriber samples, not a claim to have captured every publisher
message. Expected publisher frequencies are2/10/2Hz respectively. Every received
sample in this successful window was valid and fresh.

**deviceState:** started=false throughout, startedMonoTime=0, thermal green.
Classification **FALSE_STABLE**. The zero timestamp is an actual field in fresh
messages, not a default used for unavailable data.

**Panda1:** type **cuatro**; ignitionLine=false, ignitionCan=false,
harnessStatus=notConnected, controlsAllowed=false, heartbeatLost=false,
faultStatus=none throughout. Panda uptime advances424→436 seconds. No empty Panda
arrays or ignition-bit changes occurred. **IGNITION_SOURCE=NONE** and harness
**NOT_CONNECTED**. A currently stale/absent Panda publisher is not supported by
these fresh packets. Detached evidence is not a vehicle-stationary assertion.

## Manager and OS process evidence

| Role | Running throughout | shouldBeRunning | Observed managed PID |
|---|---|---|---:|
| hardwared |true |true |48364 |
| pandad |true |true |48362 |
| card |false |false |0 |
| camerad |false |false |0 |
| modeld |false |false |0 |
| controlsd |false |false |0 |
| selfdrived |false |false |0 |
| jetlinkd |true |true |48357 |

**ONROAD_PROCESSES_RUNNING=NO.** The actual controls process is named controlsd.
Hardwared starts46.57 seconds after boot; its PID/start identity is unchanged in
the window. No restart/crash loop was observed in that interval. The schema does
not expose a cumulative restart counter, so no lifetime count is asserted.

OS manager PIDs48300→48304 form the expected parent/child chain. This matches
the reviewed `unblock_stdout()` forkpty parent proxy and child manager loop;
it is not evidence of two independent managers. The pandad Python wrapper and
native child are likewise recorded privately. No code was injected or attached
to a running Python process.

## Time correlation and source semantics

The public artifact retains first/last source timestamps on the same monotonic
axis. The first fresh Panda packet at468979478629ns has false/false ignition;
the first fresh deviceState at469431105741ns has started=false; managerState at
469451905529ns reports normal OFF process policy. The last fresh packets keep
the same relationship through the end of the window. Repeated flag reads retain
1/0, with no observed flag transition.

Seven actual source blobs are byte-identical to the already reviewed exact060de9
hardwared/manager/helpers/process_config/messaging/services/schema blobs despite
the newer overall Git HEAD. This supports applying the earlier *state-machine
explanation*, not installing an old source-bound recorder:

- Known-Panda line/can OR supplies hardwared ignition.
- Missing Panda receipt for five seconds clears retained ignition.
- hardwared publishes started from started_ts; manager consumes device.started.
- On a started transition manager writes IsOnroad then inverse IsOffroad.
- card/modeld are only_onroad; camerad also permits the driver-view policy.

OnroadCycleRequested was absent and IsDriverViewEnabled existed; only existence
was checked, **neither value was read**. Their source semantics remain as in the
earlier report. The source edge case involving repeated *empty* Panda arrays did
not occur in this window and is not claimed as the earlier cause.

The newest three source-defined swaglog tails were read, bounded to64KiB each.
196 JSON records parsed; no matching hardwared/manager ignition/Startup/started/
panda-timeout/onroad/offroad event was recovered in that scope. Typed msg$s and
msg.event$s file formatting was considered. This is not an absence proof across
all logs and does not recover the earlier0/1 interval.

**No natural true→false transition was observed.** The device was already OFF
when first contacted. Neither the transition time nor its cause can be inferred
from the user's move/power history or from this later snapshot. Historical root
cause therefore remains **UNKNOWN**, rather than a claim of stuck ignition,
publisher staleness, a hardwared delay or manager inconsistency.

## Recorder, preservation and limitations

Ticket discovery namespace absent; arm.ticket absent; writer0; no recorder memfd
in the inspected runtime roles; no capture selector in their environments;
recorder output root absent. Ticket/activation/capture/migration NOT_RUN. No
Params, source, service, Panda, USB, CAN/control or Jetson mutation. No ORT/TRT or
USB inference was requested. There is no dataset.

Before/after branch/HEAD, Git status, index SHA,12source canary hashes and every
inspected runtime role's PID/start identity are unchanged. This is a **scoped
preservation PASS**. No fresh full route/model/runtime-overlay inventory was
performed in this diagnosis; the historical48-entry attestation is not extended
to the new HEAD or current49-entry short status.

Collector limitations are explicit: two initial source-in-memory responses
exceeded the terminal screen transport capacity. A smaller paced response then
revealed an observer guard that incorrectly required one OS manager process.
Source and OS parent/child evidence explained forkpty; only the off-device
observer context selection changed. The successful receipt above is a complete
fresh12-second observation, not a combination of truncated attempts. No runtime
or recorder gate was relaxed. Private scripts/evidence remain ignored locally;
the public artifact contains hashes/metrics only, without addresses/raw process
arguments/environment/route names/source contents or raw logs.

Local receipt/source/privacy consistency is validated. No production code or
recorder patch changed; the previous543CPU PASS is not recounted as a new run.

## Retry decision

**Safe to retry M19-C1.1: NO — BLOCKED_HEAD_DRIFT.** The genuine-OFF diagnostic
conditions passed in this observation, but actuala559fcd is outside the approved
exact060de9 source target. Old package/full overlay/install pins were not
validated as a deployment profile. Do not reset/update/checkout actual to fit it.

Next recommended step is an **offline comparison of actuala559fcd against the
reviewed060de9 recorder profile**, before proposing any distinct deployment.
No automatic port, installation, restart, ticket or capture follows this result.
Numerical status PARITY_UNDETERMINED and M2 readiness NO remain unchanged.

Result commit resolves with
`git log -1 --format=%H -- artifacts/m19c12_live_onroad_diagnosis_20261024.json`.
