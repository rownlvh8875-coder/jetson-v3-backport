# M19-C1.5A — Phase A attribution gate

2026-10-26 · **BLOCKED_PHASE_A_INSUFFICIENT_EVIDENCE**

Phase A is complete. The retained evidence cannot classify the historical added
process as SELF_INDUCED_OBSERVER_PROCESS or KNOWN_BOUNDED_EXTERNAL_HELPER.
The user's Phase B entry gate therefore blocks policy implementation and Phases
C–E. No actual connection, sampler deployment, recorder apply, physical-action
prompt, ticket, activation or capture occurred. Phase F records the blocked result.

## Development and discovered inputs

Fresh initial branch was `feature/jetlink-multimodel-carrot`, CLEAN, with HEAD,
upstream and remote equal at `2634d857fb30b16c0d4442f941bcfa6fbd82485c`.
The expected `3d5b7bdedfa271a4752d3b713fa5c7822d3dad2b` is its direct parent.
The sole intervening commit is this chat's prior offline review: three documentation
and artifact changes, no runtime/checker/patch change. This is an explained
development history delta, not a retarget of the actual source.

`git show --format= --name-only 3d5b7bd...` discovered the immutable rollback inputs:

- `docs/M19C15_24C_ACTUAL_OFF_DEPLOYMENT_ROLLBACK_20261026.md`
- `artifacts/m19c15_24c_actual_off_deployment_rollback_20261026.json`

The C05 commit discovered the exact24c compatibility report/artifact and
`artifacts/m19c05_24c_surviving5bb_deployment_manifest_20261026.json`. Continuation,
the latest offline review, public collector/tests, saved actual helpers/command
receipts and exact24c Git objects were read. Input hashes are in the new artifact.
No historical receipt was edited. Main and the old feature ref remain protected.

## A3 — caller investigation

Fresh offline structural replay searched 31 top-level private JSON receipts for
the added numeric PID. Exactly one matching process row was found. It contains
only PID, start ticks, cwd, executable, selected resolution environment and errors.
No retained matching argv/PPID/UID/cgroup/lifetime row supplies the missing proof.
The independent process reviewer additionally checked saved transport records;
their retained output does not recover that attribution.

The original 28 source-related identity rows match PRE exactly; POST has 29 rows.
The single added executable basename is `nmcli`, cwd is source-root, errors are
empty. The later restoration snapshot matches 28 again. These facts do not prove
the full lifetime, operation or parent of the historical process.

| Candidate cause | Evidence and conclusion |
|---|---|
| Collector itself launched nmcli | Reviewed `_processes` reads `/proc` directly. Its enclosing Git probes use explicit Git arguments; no nmcli/ps/pgrep launch was identified. Static source does not attribute the observed PID. |
| Parent orchestration launched it | Seven retained transport-wrapper files have no literal nmcli or NetworkManager token. Actual helper/embedded collector calls were parsed as source only. No recorded process ancestry proves or excludes indirect causation. |
| cweb/network observer launched it | Exact24c has a registered background network refresh, sleeping 15s after each refresh; forced network requests can refresh too. Queries include both `--rescan no` and conditional `--rescan auto`. Plausible caller, not historical attribution. |
| Another operating component launched it | comma Wi-Fi publisher has ordinary and secret queries; setup/test/host paths include setters. UI also uses NetworkManager via D-Bus. No matching lineage identifies any of them. |
| Existing evidence establishes a permitted benign class | No. Required fields and effect coverage are incomplete. **INSUFFICIENT_EVIDENCE**. |

Exact24c tracked-text search found six nmcli-containing files and seven literal
launch sites, including test/setup paths; NetworkManager appears in 23 tracked
text files. Hashes and launch-site locations are retained. Native binaries,
submodule contents and system/external callers are not exhaustively attributed
by this search. No source module was imported or run. No NetworkManager command,
profile, secret, SSID, device address or runtime network output was read.

## A4 — existing checker audit

The public tool's `verify` remains the historical exact366/48-entry verifier.
The actual24c attempt reused its collector but compared a transaction-local
`ids(post) == EXPECTED['processes']`. Editing the old public verifier alone would
not repair the actual transaction. Neither was changed in this stage.

| Requested audit point | Finding |
|---|---|
| Observer's own identity | Self and ancestors are excluded and their PIDs recorded. Descendant ancestry is not tracked/excluded. No excluded PID overlaps the separately selected manager/hardwared/pandad/jetlinkd roles in the saved PRE/POST. Excluded ancestor hosting of cweb is not established. |
| Transient tool mistaken for operating daemon | Source-root cwd/maps/fd/argv heuristics select helpers as well as daemons. No lifetime or critical-role separation exists. |
| PID-only identity / PID reuse | Start ticks are retained and compared; this is not PID-only. There is no per-row before/after start-identity bracket or parent-generation binding. |
| Parent/argv/UID/cgroup preservation | argv is read for selection then discarded; required added-process fields were not saved. Richer selected-role rows do not include the added process or cover NetworkManager/system critical roles fully. |
| Snapshot race / process exit | One non-atomic `/proc` enumeration. A cmdline read error skips a process; other read errors may become row errors or an inaccessible count. An exit/selection disappearance is not a proven bounded lifetime. |
| Critical roles vs generic helper | Full selected-row equality treats them alike. No complete role-aware critical baseline with UID/cgroup/ancestry is established. |
| Existing tests | Start-tick drift, different boot, environment drift, privacy and collector read-only behavior are covered. The requested new transient/ancestry policy cases are not an existing complete sampler-policy suite. Phase B tests were not implemented or run. |

The collector has real observation limits. They do not establish that this
historical addition was observer-owned, harmless or noncritical. No blanket
allowlist, subset comparison or retry-until-equal was introduced.

## A5 and the hard phase gate

The user requires parent/ancestry, executable **and cmdline**, UID/cgroup,
first/last-seen, bounded lifetime, exclusion of recorder spawning, a complete
critical baseline and source/index/Params/service/USB preservation evidence.
The original 28 retained rows and source/index/storage/flag-binding checks provide
partial preservation evidence, but not all of these proofs. In particular,
Params binding/flags are not complete Params-content or service/USB preservation.
Default-OFF/static spawn analysis is not a replacement for the missing lineage.

The operative user instructions are explicit:

> 각 Phase의 하드 게이트가 실패하면 다음 Phase로 넘어가지 않는다.

> Phase A 결과가 아래 중 하나일 때만 진행한다.

The listed permitted results are SELF_INDUCED_OBSERVER_PROCESS and
KNOWN_BOUNDED_EXTERNAL_HELPER. The actual Phase A result is neither. Consequently:

| Phase | Result |
|---|---|
| A | COMPLETE — INSUFFICIENT_EVIDENCE |
| B policy/sampler/tests | NOT_RUN_PHASE_A_GATE |
| C actual characterization | NOT_RUN_PHASE_A_GATE; reachability not tested |
| D redeployment / rollback | NOT_RUN_PHASE_A_GATE; no new apply to reverse |
| E physical checkpoint / arm / capture | NOT_RUN_PHASE_A_GATE |
| F | Sanitized blocked receipts and continuation only |

C cannot be moved before B within this ordered request. Fresh future sampling
can characterize a recurring current helper, but cannot retroactively attribute
the historical PID. No physical ACTION_REQUIRED or extra approval question was
issued. This stop follows the user's gate, not an inferred skill approval rule.

## Independent reviews and future constraints

Three independent reviewers agree with the Phase A classification and gate.
Their new private notes are hash-committed in the sanitized artifact. No reviewer
ran an operation helper, connected to a device or changed public/runtime code.

Rollback review confirms that the previous exact inverse was guarded by own apply,
still-exact24c/OFF/index/boot and known six AFTER bytes twice, then exact PRE restore.
It remains a historical ROLLED_BACK result. A future inverse must not be forced
after HEAD drift or against an unknown footprint; if ownership/identity cannot
be proved, preserve evidence and stop with rollback blocked.

Future lifetime handling must account for left/right censoring, polling gaps and
PID reuse. first_seen-to-last_seen duration alone is not full lifetime, and
disappearance from a source-related selection is not confirmed process exit.

Capture review found that the old5bb monitor lacks `canValid` and an explicit
finite-vEgo predicate; it cannot be directly reused for the new E6. The recorder
observer itself is not a carState stationary interlock. A future capture needs
independent fresh, valid, finite stationary telemetry throughout its bounded
capture interval. These findings were recorded, not implemented behind a failed gate.

## Validation and final state

Fresh offline evidence audit: 17 assertions PASS, distinct from CPU regression
cases. Three independent source/evidence reviews completed. No fresh 1313-case
regression was run because Phase B was not entered and no production code or
tests changed. Historical 1313/0/0 is not counted anew; the diagnostics4/root/native
FFmpeg limitations remain separate. No dependency, GPU, model or ORT/TRT work ran.

Actual current state: NOT_OBSERVED_THIS_STAGE. Last recorded state: exact24c,
pure model + surviving5bb package, footer absent, restored index/source/storage.
No current OFF/source/storage/ticket/process claim is borrowed from that history.
No actual or Jetson mutation, no ticket, no activation, no frames or dataset
were created by this stage. Vehicle10 NOT_RUN; parity UNDETERMINED; M2 NO.

Next action: a separately ordered fresh-OFF read-only attribution diagnostic
before Phase B, with no deployment or capture, resolving the prerequisite order.

Result commit lookup:
`git log -1 --format=%H -- artifacts/m19c15a_process_attribution_gate_20261026.json`
