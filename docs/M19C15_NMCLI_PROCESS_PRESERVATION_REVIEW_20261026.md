# M19-C1.5 — offline nmcli/process preservation review

2026-10-26 · **PASS_OFFLINE_REVIEW_ATTRIBUTION_UNRESOLVED**

The failed POST check is reproduced from the retained transaction: the exact
process set grew from 28 to 29. All 28 original identity rows were retained
unchanged, with one additional `nmcli` row. This establishes the failure mechanism;
it does not establish that command's caller, arguments, purpose, lifetime or
relationship to the deployment. The historical result remains **ROLLED_BACK**.

This review used saved private evidence and locally cached exact24c source only.
There was no comma/Jetson connection, deployment, network command, source repair,
storage change, ticket, activation, capture or restart. The process guard and
reviewed C05 recorder candidate are unchanged. Actual current state was not
freshly observed; the last observed state was pure24c + surviving5bb package,
with no recorder footer. Vehicle10 remains NO; parity UNDETERMINED; M2 NO.

## Evidence replay and collector boundary

Read the immutable rollback report and artifact first:

- `docs/M19C15_24C_ACTUAL_OFF_DEPLOYMENT_ROLLBACK_20261026.md`
- `artifacts/m19c15_24c_actual_off_deployment_rollback_20261026.json`

The transaction's frozen expected rows equal its fresh immediate PRE rows. Its
single failed check is exactly:

```python
checks['PROCESS_IDENTITIES'] = ids(post) == EXPECTED['processes']
```

`ids` compares PID, start ticks, cwd, executable, selected resolution environment
and collection errors. Offline replay gives:

| Retained observation | Result |
|---|---|
| PRE / POST rows | 28 / 29 |
| Original rows retained unchanged | 28 |
| Original rows missing or changed | 0 / 0 |
| Added executable / cwd class / errors | nmcli / source root / none |
| Exact process-set equality | FAIL |
| Other POST checks | 9 PASS |
| Separate final restoration process set | 28, equal to PRE |

The final matching set verifies a separate observation. It does not prove that
the additional process did nothing, establish its lifetime, or change the failed
POST result. Snapshots do not establish continuous process or network preservation.

The embedded collector SHA256 is
`3b8f77a388caeb380e78980ba13c02c8e24e8ce4017326f01fbbb7cbf3a90904`.
Its `_processes` function is AST-identical to the current public collector in
`tools/check_comma_dirty_baseline.py:297`. Selection includes source-root cwd,
executable, mapped files or open descriptors, plus argv heuristics. It is not
limited to manager roles. A system executable can therefore be selected solely
because it inherits a source-root cwd.

The collector reads argv for selection but does not retain it. The six retained
fields have no PPID, parent start identity, UID/GID, service/cgroup binding or
launch/exit observation. A row with `errors=[]` does not supply those missing
fields. `/proc` enumeration is a bounded, non-atomic observation. Offline analysis
cannot reconstruct the historical caller from these receipts.

## Exact24c source audit

All source references below refer to
`24c1ba5e4b3428f56fa0e402f5a10097e2e94c32`, read through `git show` in the existing
local reference repository. These modules were not imported or executed.
The companion artifact records review-only hashes and selected line references;
these hashes are not a new recorder activation profile.

There is a concrete background path that can produce a short-lived `nmcli`:

`carrot_server.main` → `make_app` → `features.register_all` → `system.register`
→ application cleanup context → `device_network_context.refresh_loop`
→ `asyncio.to_thread(refresh_device_network)` → Wi-Fi list / IP address query.

`features/system.py:345` starts the refresh loop; registration is at line 369.
It refreshes on startup, then sleeps 15 seconds **after each refresh**. A browser
request is not required for the loop. A network endpoint with `force=1` can also
refresh; the ordinary endpoint uses cached data. Closing a settings page is not
proof the background task stopped and is not a remedy proposed here.

`services/device_info.py` supplies two commands:

- Wi-Fi list: `nmcli -t -f ACTIVE,SSID,SECURITY,SIGNAL dev wifi list`, timeout 3s.
  It appends `ifname wlan0 --rescan no` when `direct_ap_active()` is true, otherwise
  `--rescan auto`. The latter does not support a claim of guaranteed no scan.
- IP query: `nmcli -t -f IP4.ADDRESS dev show wlan0`, timeout 2s.

Neither command is executed by this review. A subprocess timeout is not evidence
of the historical row's runtime. This source path is a plausible explanation,
not attribution of the observed PID.

Other source paths defeat an executable-name-only exemption:

| Source path | Static behavior and attribution limit |
|---|---|
| comma daemon → `WifiPublisher` → `wifi_publisher.py` | Starts a separate worker; ordinary profile queries and `--show-secrets` use the same executable. Its loop also calls AP `ensure`. Historical execution/command unknown. |
| `wifi_direct.py` | A cached `--rescan no` list exists; AP lifecycle has separate side effects. Its filename does not prove which operation occurred. |
| host `wifi_apply.py` | Uses the same `nmcli` wrapper for profile load/delete, radio enable and connection activation. Host-side source example, **not** evidence it ran on comma. |
| `setup_mobile.sh` | Contains a device-managed setter. Installation source example, **not** evidence it ran. |

The audit is not an exhaustive inventory of native/system/external callers.
No NetworkManager output, secrets, SSIDs or network profile identifiers were read.

## Preservation policy decision

**Retain the exact process-set equality guard.** No helper, comparator, recorder,
patch, source pin or runtime behavior was changed. There is no new allowlist and
no deployment retry. This review does not establish a recorder/input defect.

| Observation or proposed shortcut | Current decision |
|---|---|
| Same complete identity rows | Only this process-set comparison can pass; every other gate still applies. |
| All PRE rows retained, with any additional process | FAIL exact-set preservation, including a known query under the current policy. |
| Missing/restarted/changed identity, inaccessible or raced evidence | Do not waive; fail or leave unresolved as appropriate. |
| Exempt every `nmcli`, compare a subset, suppress the background task, or wait/retry until a convenient snapshot | Not approved and not implemented. |

Exact-set comparison is sensitive to normal transient process creation. That
observation explains why a healthy source/profile check can coexist with a failed
preservation check; it does not prove this particular addition was harmless.
Any different preservation contract needs an explicit, separately reviewed design
and evidence. This review does not adopt one.

## Next diagnostic stage — proposal only

Before another deployment attempt, perform a bounded **read-only, fresh-OFF process
lineage diagnosis**. A concrete sampling proposal is 60 seconds with 100ms
intervals, to observe several nominal refresh opportunities without triggering
them. Sampling may miss short subprocesses; no hit means INCONCLUSIVE.

Collect only private diagnostic evidence: boot binding and monotonic sample
brackets; PID/start ticks; PPID/parent start ticks; executable/cwd and UID/GID;
parent role/source identity; cgroup/service if available; argv digest and an exact
non-sensitive command form; collection failures. Bracket each identity read with
start-identity checks. A vanished/changed parent or partial row remains unresolved.

Never retain passwords, command output, SSIDs/profile IDs or arbitrary full process
environments. Unknown or sensitive argv must be hashed/redacted, leaving command
classification unresolved. Do not execute `nmcli`, force-refresh the viewer,
rescan, read secrets, install audit/eBPF facilities, stop/restart processes, change
Params/source/config, arm a ticket or contact Jetson to obtain this evidence.

Future observations can characterize a recurring source path; they cannot prove
which command the historical PID executed. A diagnostic result alone authorizes
neither a process-gate change nor another deployment.

## Validation and repository preservation

Fresh offline evidence reanalysis passed 22 assertions, recorded individually in
the companion artifact. These are evidence checks, **not CPU regression cases**.
One initial checker assertion expected a direct `nm(...)` call in `wifi_apply`;
source inspection showed its `command=nm` callback. The local checker was corrected
to that source form; no runtime or gate code was changed.

The same offline reanalysis confirmed 480 prior evidence/helper/candidate/collector
files byte-preserved. Public changes are only this report, its sanitized artifact
and a prepend to `CODEX_CONTINUATION.md`. Candidate patches and all historical
receipts remain immutable.

Fresh CPU/POSIX regression: NOT_RUN, documentation/evidence review only. The prior
1313 PASS / 0 FAIL / 0 SKIP remains historical and is not recounted. Diagnostics4,
root collection and native-FFmpeg limitations remain separate; no dependency was
installed and no inference/model/GPU work ran.

Development started CLEAN on the exact feature branch at
`3d5b7bdedfa271a4752d3b713fa5c7822d3dad2b`, with local/upstream/remote equal.
Protected refs are unchanged. This stage's commit can be resolved with:

```text
git log -1 --format=%H -- artifacts/m19c15_nmcli_process_preservation_review_20261026.json
```

Next action: bounded fresh-OFF read-only process-lineage diagnosis; no reapply.
