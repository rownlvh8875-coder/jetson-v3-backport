# M19-A — detached comma recorder installed, default OFF

2026-10-24. **M19A_DETACHED_INSTALL_OFF_PASS / PATCH_LEFT_INSTALLED_OFF.**
The user's M19-A authorization covered this installation. The recorder was never
armed or activated. No capture, vehicle operation, Jetson access, model execution,
Protocol3/USB change, model selection, Params write or package installation occurred.
**PARITY_UNDETERMINED / M2 NO** remain unchanged.

Machine evidence: [m19a_detached_install_20261024.json](../artifacts/m19a_detached_install_20261024.json).
Development started clean, local/remote equal at
`3aa545d83154e8bc0e489321c5cd6ebb10f40ae2` on
`feature/jetlink-multimodel-carrot`. Resolve the result commit with
`git log -1 --format=%H -- artifacts/m19a_detached_install_20261024.json`.
The actual source HEAD remains `366d6eae9aa9962104391e1d997fe956dea8f64d`,
branch `carrot-nav`; there was no checkout, pull, source commit or branch change.

## Safety evidence and PRE attestation

The first actual shell commands were only the two requested flag reads:
IsOffroad=1 / IsOnroad=0. Fresh checks retained those values. Multiple receive-only
Panda/manager/device windows established **DEVICE_DETACHED_EVIDENCE_PASS**.
After installation, three further windows retained the following evidence:

| Window | Seconds | Panda samples | Manager samples | Device samples |
|---|---:|---:|---:|---:|
| 1 | 3.057204014 | 28 | 5 | 5 |
| 2 | 3.055786995 | 28 | 5 | 5 |
| 3 | 3.037552748 | 28 | 5 | 5 |

Every Panda sample had a known Panda type, ignitionLine=false,
ignitionCan=false and harnessStatus=notConnected. Every manager window agreed
with card/modeld/camerad inactive and jetlinkd active; deviceState.started=false.
OS process observations also found those three onroad processes absent.
These are detached-device observations, **not a VEHICLE_STATIONARY assertion**.
No carState default or historical value substituted for live evidence.

Only existing telemetry queues were subscribed to. The native subscriber performs
ordinary shared-queue reader/cursor bookkeeping, including writable mappings;
this is receive-only at the messaging-authority level, not a claim of zero OS
writes. No publisher, CAN reader or process producing vehicle inputs was started.
The requested queues existed before subscription; no atomic guarantee against
an unrelated concurrent queue deletion is claimed.

PRE **M193_ATTESTED_BASELINE_PASS** retained all original private path identities:
tracked modifications0, untracked entries48, regular files2006, bytes417208589,
canonical digest
`8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5`.
Runtime-required26 and generated/backup20 remained in place. U46 remains
SAFE_GENERATED_LEGACY. U32 remains **U32_UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION**;
its current runtime use is UNKNOWN, not unused.

The frozen M192 checker and private expected manifest were unchanged. Its legacy
PARTIAL-only-U32 verdict was retained; the separately reviewed M193 scoped policy
and a freshly bound proof/bundle supplied the PASS. Execution authority came from
the human M19-A instruction, not from the checker. Source boundary hashes, model
hashes, process identities/resolution environment, and route metadata matched.
Recorder namespace/target paths were absent and collision checks remained NO.
The actual installer repeated a fresh full collection and detached gate before
creating the private backup or applying anything.

## Disposable validation, backup and exact apply

The private development parent was verified writable and separate from source,
operating routes and the proposed capture root. Observed free space was
28,431,130,624 bytes. Python was the existing 3.12.3 venv invocation; no dependency
was installed or upgraded. No capture directory was created.

A private tracked-only disposable layout used nine pinned source/package files;
the operational overlay was neither moved nor copied. Forward apply produced the
six expected hashes, in-memory syntax compilation passed, the original source
AST was unchanged, and an OFF-footer import trap preserved the original objects.
All five new modules imported in two controlled environments: observed startup
parent and operator. Each environment preserved its own original dependency
resolution. The startup environment retained U48 precedence; the operator already
used venv packages. Live manager-child sys.path/modules were not inspected or
injected. U32 was not imported by these fixtures.

Real reverse apply restored all nine original file hashes and removed the new
disposable package. This PASS is a verified phase aggregation from the same pinned
copy, not a claim of one uninterrupted harness run. Resolved harness stops are
documented below.

Before actual source mutation, the single original tracked file was backed up
exclusively outside the source tree, with private permissions and verified SHA:
`c627644ff2f986883325aaca1b8410f216f45447c6595a123d8c1e53ef8c83da`.
The five new modules were originally ABSENT. Backup verification also passed in
two later read-only observations; no existing backup was overwritten.

Exact patch SHA256:
`3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee`.
Actual `git apply --check` preceded `git apply` without index modification.
One existing tracked file changed and five modules were added. Syntax and all
six after hashes passed; original target owner/group and mode0644 were preserved.

| Target relative to `openpilot/selfdrive/modeld/jetlink/` | After SHA256 |
|---|---|
| model.py | 4813e215b13b447a234ca78839d4cac605f69a9ec2b1a6263ed9ffa063204f0d |
| input_recording/__init__.py | e70246cd5900e93d9c6176443895b9fd5e0487b1d416b861b63b34ff482292ca |
| input_recording/format.py | 9deff26ba3ba9b66642f7a471b10c637272003029866ce47fe82f80ff702acdf |
| input_recording/recorder.py | d6004d0934a87fd23adb82e8873b44ec710935c1e7bd5ec8f1806a46513aeada |
| input_recording/dataset.py | 25af73e6de65116cbb8050c7da2c89e1c2d1f7e275cfeaf54bd939ed9529e0f7 |
| input_recording/hook.py | e8196e46df04a0ca99dd1ba4d009d5a683bd8e8a7a91b05a8b81bec3731f5bd1 |

## OFF health, restart decision and limits

**Restart NOT_NEEDED; none performed.** Actual366 lazily imports JoiningModel in
modeld.main; modeld is only_onroad and absent in the detached OFF state. Manager
preparation imports the modeld module, but does not execute that main path.
An OFF manager restart would not exercise this hook and would add an unnecessary
lifecycle change. No unsupported partial start or forced onroad producer was used.

The installed actual file's AST, six hashes and OFF footer were verified. Only
the appended footer was executed with dummy original objects and an import trap;
the real absent activation environment caused no recorder import/object change.
This is an actual-device CPU **FIXTURE**, not execution of full modeld.
Full patched modeld import, a patched manager reboot, onroad health, model timing,
camera cadence and recorder hot-path overhead remain **NOT_RUN / NOT_AVAILABLE_OFFROAD**.

Bounded current-runtime health observations passed: the manager/jetlink roles
remained healthy under OFF policy and all31 selected process identities and
resolution environments matched PRE without a restart. Three health windows
retained the detached evidence above. No lifecycle fault was observed in that
scope; this does not certify every service or future onroad model behavior.

All31 inspected processes lacked CARROT_V3_INPUT_CAPTURE. Writer count0;
capture memfd matches0 in their FD/maps coverage; the proposed capture output
root remained absent; the installed package held only its five files, with no new
pycache. No ticket or activation was created, so no invalidation/capture cleanup
test is claimed. No dataset exists. A global search for every possible unrelated
ticket/output was not performed.

## POST profile and operating preservation

Two fresh read-only POST collections independently matched. The frozen collector
hashed every original file and metadata tree. The comparison used original private
paths and their complete tree commitments, ignoring only newly shifted anonymous
status IDs. It did not treat the new status ordering as the old U-number mapping.
All48 original commitments matched the original baseline digest above.

Expected POST: tracked modification1, untracked short entries49 (one new package),
regular untracked files2011, untracked bytes417259473. The six recorder targets
match exactly; only the five new regular files are included in those untracked
totals. New module modes0644 / directory0755 and target ownership passed.

POST untracked aggregate digest:
`6857b161fe10363ae9bb58b505195a40a031872e3ef1746917d7e7f89fba50ba`.
This expected new aggregate does not replace the original48 baseline digest.
Future checks must verify **original48 + exact recorder POST profile**, not run
the old tracked0/namespace-absent PRE requirement against the installed source.

Preserved: U32/U46 exact bytes/metadata, all original overlay trees, other seven
source pins, model hashes15, process identities31, and three extra Git-index/native/
bytecode canaries. Route metadata4497 remained at digest
`4bf474e52edc1b6ad250ed125b23a87a34ecd781799fa47040247aebef499c24`.
Route preservation here is metadata comparison, not a full-content route rehash.
No route/model write was performed. Atime is excluded because reads may update it;
the collection is a guarded observation window, not an atomic whole-device image.

**Final source state: PATCH_LEFT_INSTALLED_OFF.** Exact POST, healthy current OFF
policy, no activation and a verified backup favor avoiding another reverse/reapply
cycle. The original48 were never moved/deleted/ignored. Any future rollback must
first obtain fresh safe-state evidence, verify this exact six-file POST and backup,
then reverse only this patch and verify original source hash/new-package absence.
Never reset, clean or remove the runtime overlay. No actual rollback was performed
in M19-A; the disposable reverse was tested.

## Validation history and unresolved boundaries

Fresh unique software regression: **258 PASS / 0 FAIL / 0 SKIP**, 30.31s, WSL
Python3.12.3. This is recorder131 + checker68 + layout1 + U32 provenance58.

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 python -m pytest -q -p no:cacheprovider tests/test_u32_provenance.py tests/test_comma_dirty_baseline.py tests/test_comma_dirty_layout.py tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py --tb=short
```

Separate private metadata POST fixtures:9 PASS, including original hash/mode drift,
new module hash/absence, unexpected tracked change, source hash, PID/start drift
and namespace failure. They are not added to the258 count. A private timestamp
boundary fixture also verified the observer window starts before subscriber
construction, includes publications during construction and rejects older ones.
Validity/age/harness/ignition requirements were not relaxed.

Five disposable device-harness stops were resolved before actual installation:
unequal observed manager environments; rewritten argv0 not executable; invoking
the canonical binary lost the existing venv context; an overbroad requirement
incorrectly demanded U48 for an operator environment originally using venv; reverse
apply had already pruned the empty package directory. These were fixture/tooling
errors, not production runtime crashes. A local source-generator SyntaxError was
caught before device execution. No package or source gate was relaxed to fix them.

An auxiliary read-only restore check returned DETACHED_STATE_UNCONFIRMED without
retaining its detailed failed-window subchecks. No actual source write occurred
in that invocation. Its exact cause is unknown. Later diagnostics retained fresh
positive windows, and the actual installer independently repeated all final gates
before mutation. The later observer-window correction is not asserted as proof of
that earlier failure's cause.

After the installer emitted verified backup/six-hash/POST progress, transfer of its
large private JSON exceeded the transport deadline. **The patch was not reapplied.**
Two compact fresh read-only receipts recovered/confirmed the exact installed state,
backup and full original48 commitments. Their content hashes and the final
observation commitment are recorded in the public artifact; raw observations stay
in ignored private evidence. The frozen M18 patch, recorder implementation and
M192 checker were not changed. Capture capability/performance tests are not
inferred from successful imports.

One independent final read-only local review found no Critical, Important or Minor
issues in the four public files and their receipt/POST consistency. The reviewer
did not access devices/network, execute private scripts or rerun the258 tests.

## M19-B requires activation-order review

**Ready for M19-B parked onroad10: NO, pending an offline launch/arming review.**
M19-A installation itself passed. The proposed next-stage order, ignition ON then
arm, conflicts with the existing arm_ticket requirement for a fresh trusted OFF
state. Additionally, the footer reads the activation environment at module import;
changing another terminal environment after the normal stack has started cannot
activate an already imported OFF module.

Before separately authorized M19-B, review a supported temporary normal-launch
inheritance procedure: arm while genuinely OFF, bind source/spec/boot/expiry, make
the temporary environment available before the normal lazy import, then use normal
ignition/onroad transitions and live stationary verification. No fake OFF proof,
Param/ignition manipulation, manual modeld/card/camerad, persistent service env or
unreviewed restart is acceptable. No such procedure was executed here.
Do not arm now. Existing V2/Nav Protocol2 selection remains unchanged. Even a future
successful10-frame capture would prove recorder operation only, not V3 parity.

Next action: **offline source-backed review of M19-B offroad arming and temporary
supported launch-environment ordering, keeping this installed recorder OFF.**

## Upstream and Git boundaries

Start/end observations were unchanged; actual366 was never advanced:

| Repository/ref | Full HEAD |
|---|---|
| ajouatom/openpilot carrot-nav | 810e14aaf51176f1a50a113939dc2e70907b394b |
| ajouatom/openpilot carrot-wip | dfab65d03fcd7100f572fe9e6908f4c6d1e988f6 |
| ajouatom/carrot-jetson main | d0dc96fa32410403dfb2fefff3e2909c11ec109b |
| zoompilot/jetlink main | d24328d849b0e5154b55f149dc18c5dfe8bd79cc |
| tjdgus200/openpilot codex/jetson-review | a890f6df1bd3eb0478754c68d8b5f92f15e8b722 |

Protected main2519ad0b… / old feature26c9c06a… stay unchanged. Only sanitized
documentation/evidence is committed to the required development feature branch.
Private device paths, mappings, terminal data, argv/env, backup/source contents,
network addresses and visual tensors are excluded from Git.

COMMA_REAL_CAPTURE / VEHICLE_PARKED / ROAD_TEST / Jetson / USB_REAL: **NOT_RUN**.
TRT_REAL: **NOT_RUN_THIS_STAGE**. No ORT model execution. Existing M1 plan stays
DO_NOT_INSTALL. Numerical decision **PARITY_UNDETERMINED**, M2 readiness **NO**.
