# M19.2 — exact attestation of the actual366 runtime overlay

Later [M19.3](M193_U32_PROVENANCE_20261024.md) adds a separately versioned,
reviewed scoped-isolation policy under the user's newer criteria. It preserves
the exact M192 checker and its PARTIAL result below, without inventing runtime
non-use or changing the original48 manifest. Consult M193 for current retry gates.

2026-10-24. **ATTESTED_DIRTY_BASELINE_PARTIAL / Ready to retry M19: NO.**
All measured preservation checks pass. U46 is resolved by byte-exact PC
regeneration; U32 remains `POSSIBLY_DYNAMIC_REFERENCED`, without an accepted-unknown
exception. No actual source/file/configuration mutation, cleanup, installation,
restart, ticket, capture, Jetson or USB operation was performed.

The user explicitly replaced the earlier clean-tree requirement with exact
attestation. The 26 runtime dependencies and 20 generated/backup entries stay in
place. Neither unknown entry is removed. A count whitelist, ignore rule or clean-up
is not a substitute for the private path/content/metadata manifest.

## Baseline and preservation

Actual branch **carrot-nav**, HEAD
**366d6eae9aa9962104391e1d997fe956dea8f64d**, Offroad/Onroad **1/0**, tracked
modifications **0**, collapsed untracked entries **48**. Recursive inventory:
**2,006 regular files / 417,208,589 bytes / 283 directories / 0 symlinks**.

Original on-device canonical inventory digest, unchanged:

```text
8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5
```

All 48 canonical tree digests recompute exactly. Private manifests bind real paths,
regular-file SHA256, node type, size, mode, UID/GID and exact mtime/ctime integers.
The public [artifact](../artifacts/m192_attested_dirty_baseline_20261024.json)
publishes anonymous IDs, content/tree commitments and summaries; no actual paths,
source text, private argv/environment, route names, addresses or credentials.

Before/final comparison also matches eight selected source hashes, 15 model-file
hashes, 31 process identities and their allowlisted source-resolution environment,
boot identity, flags and Params path binding. Route metadata covers 4,497 files,
digest `4bf474e52edc1b6ad250ed125b23a87a34ecd781799fa47040247aebef499c24`.
This is names/mode/size/mtime metadata, not all-route content hashing. Three extra
canaries (Git index, current native library and U32 bytecode cache) match. Owned
audit helper shells are gone; production processes were not interrupted.

These are observation-window checks, not an atomic whole-device image or proof
about every ignored file and live Python module. Ordinary reads can update atime;
atime is excluded. No operational mutation was requested or performed.

## Correction to historical metadata transport

The old PC terminal receiver parsed JSON into JavaScript Number and serialized
it again. **4,574 of 4,578 saved node nanosecond time fields lost integer
precision.** Derived time displays are also approximate. File/hash strings,
counts, bytes, mode and UID/GID survived. The strict new verifier rejected these
rounded snapshots; that was transport corruption, not device baseline drift.

The receiver now saves verified decompressed JSON bytes directly. A local Node VM
regression reproduced the rounding before the fix and passed afterward, without
filesystem/network operations. Fresh raw observations preserve Python integers
and recompute every original tree digest and the same original inventory digest.
There is no rebaseline, time-rounding tolerance or gate relaxation. M191's public
records remain with an explicit correction; do not use their old numeric times
or the old receiver to construct an exact private policy.

## U32: observer semantics; current dynamic use not established

**11,831 bytes**, SHA256
`07e2bd4cdac1479f85447c1f96182c8f24603a9184b11045086d7433b68e5b70`.
Classification: **POSSIBLY_DYNAMIC_REFERENCED**. Runtime reference: **UNKNOWN**.
General import/use risk: **UNKNOWN**. Recorder-specific shadow/overlap: none
observed in the audited namespace.

Static AST analysis found snapshot/configuration/loop observability helpers,
stdlib and messaging imports, definitions/constants and a dataclass decorator.
No direct actuator/CAN authority, Params access, filesystem/process/network-write
API was found. Functions can publish two dedicated telemetry message types and
perform allocation/hashing/serialization; they can raise exceptions. This is
observer-oriented code, not a claim that importing/calling it is side-effect-free
or has no scheduling cost. Dynamic caller objects and imported libraries limit
static conclusions. The source was never imported or executed.

The scoped reference scan read 4,795 files / 87,537,788 bytes in 24.74 seconds.
Exact module/class references occur only in U32 itself. Generic method-name
matches in 1,178 files are not callers. The 206 files with dynamic import,
eval/plugin sites contained no literal U32 module reference. Three large or
nonregular candidates were excluded and are recorded privately. This is complete
within the declared extension/size scope, not proof against arbitrary dynamic
construction. No U32 open-FD/mmap/cwd/executable reference was observed in the 31
audited processes. Another 37 inaccessible processes and Python's closed source
files prevent a whole-runtime absence claim. No module-table injection or attach.

The CPython 3.12 timestamp-based cache has source size and whole-second mtime
matching U32. Cache SHA256:
`8cb1ccbaae6cbda662145a50671ede87103baf61edd7e165381412b5d68c48c3`.
This header match is a compilation/import candidate, not hash-based source
equivalence or current-runtime activity proof. No marshal payload was executed.

The index has no U32 entry. Its exact Git blob is absent from 19,113 existing
local blobs, including available unreachable objects. Available path history
across 30 refs and 337 reflog records contains no U32 attribution. Two bounded
known history/startup-log files had no filename mention; no broad personal
history collection or raw commands are published. UID/GID ownership cannot name
the creator. **No `UNKNOWN_ACCEPTABLE_FOR_PATCH_ISOLATION` decision is granted:**
namespace separation passes, but the stronger runtime-reference-absence condition
has not been established.

## U46: legacy generated C, reproduced byte for byte

**1,056,482 bytes**, SHA256
`21ac37949a83dcb5b2799007c8ebc93909efaff7bf6d6481fb49a8eb2a43314e`.
Classification: **SAFE_GENERATED_LEGACY**. The C source itself has no observed
runtime OS reference in the audited scope. Keep it in place.

U46 and U47 identify the same source/module and Cython 3.2.9, but their generated
function-name sets contain 42 and 87 names respectively. They are not merely the
same source emitted as C versus C++. The older tracked source available at
`1cd1b2c6748c6603ad97c9357858a2447c36a3d2` is 2,163 bytes, SHA256
`d2246a1562cc751db585977bc33563c64263f88a30e2c0cf6f33c4d35e16c9b2`.

On the PC, Python 3.12.3 and isolated Cython 3.2.9 regenerated C from that source,
using its original relative layout, module identity and observed embedded build
metadata. **Raw output size and SHA256 match U46 exactly**, without normalizing
or rewriting generated output. Initial layout/source variants did not match and
are retained privately. A C-mode warning about unused C++ declarations is retained.
No source execution, native compilation/linking or actual-comma build occurred.
The official wheel was checked against HTTPS package metadata and SHA256
`a2b0e87f6b80790c929308ca0831d686f7a180feab684fe8cd4a4380bd96aaca`;
it was extracted into an isolated PC report area, with no shared/device package
installation. [Official package provenance](https://pypi.org/project/Cython/3.2.9/).

All 12 inspected available historical build recipes select C++ output. Therefore
the original creating command/person is still unknown; byte-exact content
reconstruction establishes generated legacy provenance, not that a particular
historical build invocation ran. The current native library has C++ source/debug
labels, newer symbols, and is mapped by 15 processes. That derivative is a runtime
dependency; it does not make this older C intermediate a current build target.

## Exact installation gate

The original M191 classification map is immutable: generated19, backup1,
runtime-required26, original unknown2. A separate provenance policy resolves U46,
leaving **one unresolved entry**. No original classification or digest is silently
rewritten. U48's dependency overlay is actively mapped by 23 processes, across 18
distinct files and 2,179 map segments. All 26 runtime entries are operational
baseline, never clean-up targets. The earlier 20 MOVE proposals are not executed
and are unnecessary for this attestation approach.

| Gate | Actual result |
|---|---|
| carrot-nav / exact366 / fresh flags1/0 | PASS |
| tracked changes0 and ordinary index flags | PASS |
| expected48, exact private paths/content/metadata and aggregate digest | PASS |
| all runtime-required hashes | PASS |
| U32 resolved or strongly reviewed accepted-unknown policy | **HOLD** |
| U46 resolved | PASS: exact legacy regeneration |
| frozen recorder patch identity and six before/after profiles | PASS |
| recorder path/parent/backup collision | NO observed |
| physical recorder namespace, including ignored/empty paths | ABSENT |
| reviewed static import/OFF layout isolation | PASS within fixture scope |
| source/model pins and process/boot/resolution identity | PASS |
| route inventory and protected canaries | PASS |

The M18 patch remains
`3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee`:
one existing file and five new modules. Dynamic U32 use remains unknown even
though the recorder-specific namespace is separate. **Partial is intentional;
the current CLI exits 1 and never authorizes installation.**

## Read-only checker and disposable validation

[`tools/check_comma_dirty_baseline.py`](../tools/check_comma_dirty_baseline.py)
has two separate modes: Linux stdlib-only `collect-private` consumes a private
configuration on stdin and emits private raw JSON on stdout; `verify` compares
trusted observations against an independently pinned expected-file byte SHA256.
The [schema](../artifacts/comma366_dirty_baseline_schema.json) documents structure;
runtime code additionally recomputes all node/tree/inventory commitments.

The collector imports no vehicle module and provides no write/cleanup operation.
Regular files use nofollow/nonblocking read descriptors with stability checks;
symlinks/special inventory nodes fail closed. Params' existing directory alias is
accepted only with its explicitly bound physical root; alias/leaf drift, symlink
leaf, FIFO, oversized or invalid flag contents are rejected. Git operations use
ephemeral fsmonitor/untracked-cache disable flags, optional locks off and lazy
fetch off. Before each status call, effective clean/process drivers are matched
against the filter attributes of every indexed path, without running a filter.
Any applicable external driver or gitlink is refused; status is not delegated to
submodules. Actual366 has one registered but inapplicable driver across 6,160
indexed paths and no gitlinks. No filter/attribute/configuration is disabled or
rewritten to hide dirty files. Tests isolate host Git configuration and explicitly
exercise local/global filter cases. Concurrent hostile configuration writers are
outside the observation-window guarantee. Git does not edit configuration or
refresh the index. Assume-unchanged
and skip-worktree index states are rejected. Physical namespace checks catch
empty or ignored recorder directories that Git short status would omit.

Private policy byte SHA256:
`59d952de8a7b4f6530473c5fda392238bc500f25d490d71044b53f9bc2c2f328`.
It binds exact paths, classifications, source profiles and reviewed isolation
evidence. A fresh 32-hex challenge correlates acquisition/result; it is not
authentication or cryptographic anti-replay proof. Hashes commit to bytes, not
author identity. A trusted collection channel and reviewed policy remain required.

On a disposable PC actual366 source copy, a 48-role layout fixture plus the frozen
patch passed forward/reverse application, six after hashes, original AST/function
identity and disabled-footer checks. PathFinder in a subprocess resolved the
recorder to its expected root and retained dependency-overlay precedence for four
representative packages, without importing vehicle packages. This is
**CPU_FAKE / FIXTURE**, not a copy of actual overlay contents or live module table.

## Executed verification

**200 PASS / 0 FAIL / 0 SKIP in 27.61 seconds**: checker68, disposable layout1,
unchanged recorder131. The separate raw-JSON transport VM regression passed and
is not added to the pytest count. CI includes the checker CPU fixtures, with no
device collector or private manifest in CI.

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_comma_dirty_baseline.py tests/test_comma_dirty_layout.py tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py --tb=short
```

Tests cover missing/extra/hash/metadata/identity drift, immutable classifications,
source/patch pins, malformed/duplicate JSON, unresolved policy, private/public
separation, exact large integers, read-only Git including a hostile fsmonitor
fixture, bound Params alias, index flags, ignored/empty namespace collisions and
filesystem immutability. Synthetic accepted-unknown PASS tests do not accept U32
on the actual device. The actual comparison remains PARTIAL on U32 alone.

One fresh independent static review found one Important issue: status could
invoke external clean/process filters despite optional locks being off. Same-size
modified-file and submodule fixtures reproduced actual marker writes (three RED
cases). The guard above makes all three GREEN, and an inapplicable global-driver
case verifies that tracked modifications remain visible. Full suite200/200 passes.
No second review was dispatched. The reviewer independently recomputed all48
tree/inventory commitments and checked public/privacy/policy evidence, but did
not contact devices, execute tests/regeneration or certify live imports,
installation/capture, numerical parity or hardware/vehicle readiness.

## Future retry boundary

Current readiness is **NO**. Next action: review a concrete creator/caller or
deployment record for U32, or obtain the strong explicitly reviewed isolation
evidence required by the policy. Lack of an observed FD is insufficient. Do not
attach/inject into a runtime to force this proof. No filesystem cleanup is needed.

After resolving that hold, a separately authorized M19 must obtain fresh parked
and stationary evidence and rerun the exact PRE-install attestation. A stored
snapshot is not a future preflight. The PRE checker requires tracked0 and the
original48. After an authorized patch, use a distinct POST profile: six exact
after hashes and the original48 by **private path**, without reassigning IDs when
new status entries sort differently. Do not weaken PRE gates or assume five new
modules imply five new collapsed status entries. Rollback must restore the exact
original file and absence of the added package. The M18 builder's clean-reference
rule still applies to disposable offline references, not the attested actual tree.
Use in-memory syntax compilation for read-only checks; `-B` alone does not prevent
an explicit `py_compile` call from writing a cache.

Actual recorder installation/activation/capture, VEHICLE_PARKED, ROAD_TEST,
Jetson, USB, ORT and TRT are **NOT_RUN**. Actual source-read-only checks are
**COMMA_REAL_READ_ONLY**. M15 adapter, M18 recorder core and M16/M17 tools remain
frozen. Numerical status is **PARITY_UNDETERMINED / M2 NO**, existing M1 plan
**DO_NOT_INSTALL**; it was not accessed or re-hashed this stage.

Development started at `377e37653423d69cb5a6a7153da93c60fd9af313`.
Checker commits: `2bb91ff1562694328bf1fe1d038b644afed7bf00` and
`25dc746a476fcb1ee35b7acaf35d16ffe4795a76`; final review fix
`efa65e669bc51f9edd392a30af50a217613244a6`. Result commit resolves with
`git log -1 --format=%H -- artifacts/m192_attested_dirty_baseline_20261024.json`;
current development HEAD with `git rev-parse HEAD`. Only the required feature
branch is committed/pushed; protected main and the original feature stay unchanged.

All upstream refs were re-queried at start/end without changing the actual pin:

| Upstream | HEAD |
|---|---|
| carrot-nav | `810e14aaf51176f1a50a113939dc2e70907b394b` |
| carrot-wip | `dfab65d03fcd7100f572fe9e6908f4c6d1e988f6` |
| carrot-jetson main | `d0dc96fa32410403dfb2fefff3e2909c11ec109b` |
| zoompilot/jetlink main | `d24328d849b0e5154b55f149dc18c5dfe8bd79cc` |
| external review | `a890f6df1bd3eb0478754c68d8b5f92f15e8b722` |

Protected remote main is `2519ad0bdbf6e796fa590063fc90d4d6461b6b8d` and
original feature is `26c9c06a5e51ff0e8d3a1e8575eece548e87f3b5`, unchanged.
