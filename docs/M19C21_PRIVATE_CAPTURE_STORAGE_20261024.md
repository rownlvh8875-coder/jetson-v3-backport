# M19-C2.1 — private capture storage precheck stopped

**BLOCKED_SOURCE_OR_PROFILE_DRIFT.** The actual read-only source/profile guard
returned this classification. Per instruction2, the operation ended at the
first failed guard. The approved `/data/v3_input_capture` root was not created,
and no probe, ticket, activation, writer, capture or restart was initiated.

This result does not establish the particular drift: the helper returns its
observed branch/HEAD and hash maps only after all source assertions pass. The
failure receipt retained only the generic AssertionError/classification. The
specific predicate and observed values are therefore **NOT_RETAINED**, and a
fresh valid a559 profile is **NOT_ATTESTED**. It would be incorrect to say that
HEAD specifically moved, a particular installed file changed, or all six hashes
failed. No further actual read was made after this STOP.

Sanitized evidence: `artifacts/m19c21_private_capture_storage_20261024.json`.
Historical C2/C13/C02/366/810/060 evidence remains unchanged. Private connection
and terminal receipts stay in the ignored local reports directory.

## Authorization, access and first actual gate

The user explicitly approved one dedicated private storage root plus private
mode/owner setup and one minimal exclusive write/fsync/read/delete probe. Ticket,
arm_discovered, capture, restart, Jetson access, Params/source/Git/updater changes
were excluded. The current approved candidate is `/data/v3_input_capture`;
the historical proposed root from M18/C2 was not substituted or created.

Development started CLEAN/local=remote on feature/jetlink-multimodel-carrot at
`df705b42ecf0818c4c796999b9bf221430c0a369`. Protected refs were unchanged.
The continuation/C2 report and relevant source/ticket/path design were read.

The prior device connection initially timed out. Bounded probes checked only the
known web-terminal and SSH endpoints; no address scan or actual shell command
was delivered. The user reconfirmed the same address, after which a newly owned
web-terminal session connected. No IP/address is published here.

The in-memory read-only guard's first actual Git observations were:

```sh
git -C /data/openpilot branch --show-current
git -C /data/openpilot rev-parse HEAD
```

The guard requires carrot-nav/a559, then exact installed six-file hashes, the
exact bound footer, all30 normalized source pins, nine additional source hashes
used for ownership/uploader/storage-boundary review, and only the previously
installed model footer as tracked diff. Git reads use GIT_OPTIONAL_LOCKS=0 and
GIT_NO_LAZY_FETCH=1; source reads use read-only/no-follow file descriptors and
Python -B. No actual helper file was installed.

The guard failed before returning its result. The surrounding operation caught
that assertion, emitted BLOCKED_SOURCE_OR_PROFILE_DRIFT/actual_mutation=NONE and
exited. No ticket/process inventory, parent/mount/space/config inspection, mkdir,
chmod/chown, storage probe or hook dry check followed it.

The required identity/profile remain the expected contract, not a fresh actual
identity claim. All current ticket/writer/root/mount/owner/free-space states are
NOT_CHECKED. Historical ticket-absent/writer0/C2 OFF values were not reused.

## Local review and its limits

Exact a559 manager PythonProcess/launcher source starts modeld without a UID/GID
override; the generated reviewed writer Popen also supplies no user/group
override. Exact uploader source iterates Paths.log_root(), while hw.Paths defines
the native route root and honors LOG_ROOT. The modeld and writer source has no
credential-changing call in the reviewed startup path. These facts identify what
fresh process identity, environment and path configuration must verify; they do
not prove the current device owner or uploader separation.

A local fixture replay passed the ordinary exact-source guard, including the
leading Git status space, and rejected47 deliberate branch/HEAD/status/source
mutations. An AST check found no filesystem mutation/activation/process-start API
in the actual executed helper. This is **LOCAL_FIXTURE_ONLY** verification, not
device storage validation and not a source-drift diagnosis.

The first local fixture attempt needed Windows Path output normalized to POSIX
keys. That local test-only fix was not executed on comma and did not alter the
actual guard or its failed receipt. No production reader/tool or pytest test was
changed. The previous C2 authoritative627 PASS/0FAIL/0SKIP remains historical;
it was not rerun or recounted in this docs-only stage. Diagnostics4 dependency
blockers and the root collection blocker remain separate.

## Final state and next action

Actual mutation NONE. Storage created NO; fsync probe NOT_RUN. Root type, owner,
mode, emptiness, writeability, free space and route/Git/uploader separation are
UNKNOWN/NOT_CHECKED. No claim of PASS_STORAGE_READY or STORAGE_ROOT_ALREADY_VALID
is made. Source/index stability and updater movement are NOT_ATTESTED because
the source gate did not return a successful initial snapshot.

Ticket NOT_CREATED_BY_WORKFLOW/current namespace NOT_CHECKED; activation NOT_RUN;
writer NOT_STARTED_BY_WORKFLOW/current count NOT_CHECKED; frames0 from this
workflow; dataset NONE_CREATED. Vehicle transition NOT_RUN; Jetson access and
mutation NONE. No updater manipulation, Git repair, auto-retarget or source patch
was attempted.

Ready to retry M19-C2 **NO**. Numerical PARITY_UNDETERMINED/M2 NO remain unchanged.
Next action: a separate read-only source/profile diagnosis must retain the first
failing predicate and observed identity before any storage retry. Do not run
mkdir or arm a ticket based on the historical a559 result.

Resolve the containing development commit with:
`git log -1 --format=%H -- artifacts/m19c21_private_capture_storage_20261024.json`.
