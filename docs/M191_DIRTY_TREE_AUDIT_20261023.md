# M19.1 — read-only dirty-tree audit

**2026-10-24 precision correction:** the old PC terminal receiver parsed and
re-serialized JSON through JavaScript Number. Its saved numeric nanosecond fields
lost precision (4,574 of4,578 node time fields); derived time displays are also
approximate. The on-device computed file/tree/inventory SHA256 strings, bytes,
mode/UID/GID and counts were preserved. Do not use those old numeric times as an
exact private attestation manifest. M19.2 preserves original JSON bytes, re-collects
exact integers and recomputes all48 original tree digests and the same8b0cbfc9…
inventory digest. No device metadata changed or gate was relaxed. See
[M19.2](M192_ATTESTED_DIRTY_BASELINE_20261024.md). Original records remain below
with this correction, rather than being silently replaced.

2026-10-23. **Audit complete with stated unknowns; M19 remains BLOCKED_DIRTY_TREE.**
Actual carrot-nav **366d6eae9aa9962104391e1d997fe956dea8f64d**, fresh Offroad1/Onroad0, tracked modifications0,
untracked short entries48. No cleanup, ignore change, source patch, restart,
Params write, recorder installation/activation/capture, Jetson or USB operation.
The 48 entries contain **2,006 regular files / 417,208,589bytes**, 283 directories,
and no symlinks. M18 candidate/adapter/numerical code is frozen.

## Acquisition and coverage

Used the existing Carrot web terminal, fresh owned shells with history/bytecode
persistence disabled; compressed audit source existed only in shell/Python memory.
No probe file was uploaded. First device commands were exactly the two requested
flag reads, branch, HEAD and short status, in that order. All later preflights
also required1/0 and exact366. Untracked entries were the investigation target;
no tracked change appeared. Git optional writes and lazy missing-object fetches
were disabled in subsequent audit subprocesses. No package initializer or
vehicle/control source module was imported; only standard-library static analysis.

Each short entry was expanded recursively with lstat; no symlink traversal.
Every regular file was hashed through an O_RDONLY/O_NOFOLLOW descriptor with
before/after inode/stat checks. Mode, UID/GID, size, mtime/ctime nanoseconds,
SHA256/Git blob ID and tree digest were recorded. All nodes are UID/GID1000/1000;
this identifies filesystem ownership, not the creating person. Mtime is not
creation time. Actual creator/invocation remains unknown unless separately proven.

The public JSON gives anonymous entry/node IDs, all regular-file SHA256 values,
counts, sizes, modes, UID/GID, timestamps and tree digests. The private mapping,
full source/reference matrix, raw process evidence and tracked candidate paths
stay in the ignored PC report area. No raw paths, source contents, argv,
environment values, addresses, credentials or route names are committed.

## Classification and recommendations

|Classification|Entries|
|---|---:|
|SAFE_GENERATED|19|
|SAFE_BACKUP_NOT_REFERENCED|1|
|CUSTOM_SOURCE_REFERENCED|0|
|CUSTOM_SOURCE_NOT_REFERENCED|0|
|RUNTIME_REQUIRED|26|
|UNKNOWN_USER_OWNED|2|

`SAFE` means the audited producer/consumer/resolution evidence supports the
classification. It is neither removal permission nor a whole-system proof of
non-use. Every recommendation is **proposal only**. No DELETE_CANDIDATE is needed.

|ID|Anonymous role|Regular files|Bytes|Classification|Recommendation|
|---|---|---:|---:|---|---|
|U01|CAN Cython C++ intermediate|1|600,952|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U02|controller backup|1|43,702|SAFE_BACKUP_NOT_REFERENCED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U03|radar DBC generator output|1|53,886|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U04|schema-generated C++/headers/objects|12|7,688,342|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U05|messaging bridge executable|1|1,896,688|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U06|generated service header|1|6,418|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U07|font pair 01 descriptor|1|25,050|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U08|font pair 01 atlas|1|406,015|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U09|font pair 02 descriptor|1|25,048|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U10|font pair 02 atlas|1|416,743|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U11|font pair 03 descriptor|1|25,058|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U12|font pair 03 atlas|1|413,006|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U13|font pair 04 descriptor|1|25,060|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U14|font pair 04 atlas|1|440,652|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U15|font pair 05 descriptor|1|25,050|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U16|font pair 05 atlas|1|435,239|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U17|font pair 06 descriptor|1|25,052|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U18|font pair 06 atlas|1|428,080|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U19|font pair 07 descriptor|1|25,054|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U20|font pair 07 atlas|1|427,473|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U21|font pair 08 descriptor|1|25,056|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U22|font pair 08 atlas|1|423,313|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U23|font pair 09 descriptor|1|25,048|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U24|font pair 09 atlas|1|439,049|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U25|font pair 10 descriptor|1|24,617|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U26|font pair 10 atlas|1|369,483|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U27|font pair 11 descriptor|1|1,415,130|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U28|font pair 11 atlas|1|6,449,929|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U29|font pair 12 descriptor|1|1,422,455|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U30|font pair 12 atlas|1|587,778|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U31|radar-motion Cython C++ intermediate|1|431,784|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U32|custom controls observability module|1|11,831|UNKNOWN_USER_OWNED|REQUIRES_USER_REVIEW|
|U33|model build stamp|1|123|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U34|driver-monitoring warp artifact A|1|1,406,645|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U35|driver-monitoring warp artifact B|1|1,406,475|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U36|driver-monitoring metadata|1|818|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U37|driver-monitoring chunk|1|29,315,473|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U38|driver-monitoring chunk manifest|1|1|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U39|driving-model chunk 1|1|47,185,920|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U40|driving-model chunk 2|1|37,378,400|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U41|driving-model declared empty chunk 3|1|0|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U42|driving-model chunk manifest|1|1|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U43|model input-device configuration|1|224|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U44|navigation Cython C++ intermediate|1|1,048,690|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U45|camera executable|1|6,125,944|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|
|U46|Cython C intermediate with unconfirmed current producer|1|1,056,482|UNKNOWN_USER_OWNED|REQUIRES_USER_REVIEW|
|U47|UI Cython C++ intermediate|1|1,912,633|SAFE_GENERATED|MOVE_OUTSIDE_REPO_CANDIDATE|
|U48|runtime Python dependency overlay|1948|265,312,719|RUNTIME_REQUIRED|RUNTIME_DEPENDENCY_DO_NOT_TOUCH|

Build-source intermediates U01/U04/U06/U31/U44/U47 have explicit current producer
recipes and generated metadata; their compiled runtime libraries are distinct
files. U03 matches its pinned tracked generator byte-for-byte when evaluated
**on the PC in memory only**, with writes redirected to StringIO:53,886bytes,
SHA2566252667dc3e5f24152a955035b054e7a66d636f633c3657ad644197787d29daf.
The generator was not run on comma. The final runtime DBC is distinct.

The font recipe declares descriptor/atlas pairs from tracked font inputs. Six
pairs are used by the UI enum and loader; those12 entries are runtime dependencies
even though textures can outlive closed file descriptors. The other six pairs
have no generated-asset consumer in the audited tracked source/current OS paths.
References to original TTFs were not miscounted as references to generated atlases.
No font rebuild or performance test was performed.

U05/U45 are process-config executable targets. Offroad absence does not make them
removable. U33–U43 are builder/loader contracts, not disposable caches. In
particular **U41 is0bytes but explicitly declared by the three-chunk manifest**;
the loader opens all declared chunks. Keep it. U48 is the launcher-created
dependency overlay:31 pip distribution metadata records, plus live mmap evidence.

## Controller backup and custom source

**U02:** byte-identical to its tracked sibling at actual366 and the last available
path-changing historical commit4205086b8cc1a2c6e7146bad8220c56443258a60.
Both SHA256285fea414f09d7d09c9984ca33e7d80a2495247ba81da1d5fa8b50aad4d42179;
diff is empty. Backup suffix is not a Python source suffix. No audited tracked
static reference or selected-process OS reference appeared. Creation attribution
is unknown. Moving it outside the repository is a **future approval candidate**.

**U32:** additional custom Python controls/observability code, not a copy of a
tracked same-basename module. SHA256
07e2bd4cdac1479f85447c1f96182c8f24603a9184b11045086d7433b68e5b70.
Static AST exposes snapshot/publication helpers; it was never executed. The path
is importable, but no audited tracked static caller or OS file reference appeared.
It is absent from actual366 and the available1800-ancestor path-history search.
This is not proof it was never imported or created by a user. Current Python
module tables and arbitrary dynamic callers are unknown: **UNKNOWN_USER_OWNED**,
not an assertion of runtime non-use or removal safety.

**U46:** generated C header identifies Cython3.2.9, but the current pinned build
recipe selects C++ output. The matching C++ entry is U47. The invocation producing
the C variant is unproven, so a generated-looking header alone does not establish
SAFE_GENERATED. **UNKNOWN_USER_OWNED / REQUIRES_USER_REVIEW.**

949 source/config-like files (including Python typing/Cython declarations and
C++ headers, not just executable Python) were compared against actual tracked same-basename
candidates:147 have candidates,13 have at least one byte-identical candidate;
only U02 has an established logical counterpart. Other basename matches were
not invented into semantic diff pairs. Candidate SHA256/index IDs and the full
comparison matrix are private; anonymized candidate hashes are public.

The actual shallow local object store contains19,113 blobs;33 source/config-like files
match existing blobs (U02:1, U04:2, U48:30). Membership alone does not attribute
a commit/path/creator. PC reference exposes1800 ancestor commits; an exhaustive
object traversal was **PARTIAL** because historical objects were missing while
lazy fetch was disabled. No absent object was fetched on comma, and no complete
historical-absence claim is made. U02's exact base/historical match was separately
verified with available objects. U32 origin remains unknown.

## Runtime and import resolution

31 selected repository-related processes had readable cwd, argv, executable,
maps, fd and allowlisted source-resolution environment fields. **23 processes
mapped18 distinct U48 files**, represented by2,179 mmap-segment records. There
were no untracked cwd/executable/open-FD matches; other47 entries had no observed
OS reference. This does not inspect closed Python source objects or GPU font
textures. Another37 inaccessible processes had no readable repository argv marker;
their inaccessible fields prevent a whole-system non-use proof.

The audit shell's interpreter path differs from the manager launch path. The
manager's actual cwd/executable and resolution environment were read, then startup
search order was reconstructed and checked with `PathFinder.find_spec` and explicit
parent paths, without importing source packages. **Import shadowing YES:** U48
takes precedence over installed `cffi`, `cryptography`, `idna`, `pycparser`.
This is a required dependency-overlay mechanism, not observed shadowing of a
tracked controls or recorder module. Live manager sys.path/module objects were
not extracted or injected into; runtime path mutations remain possible. U32 is
an importable extra module, not an established tracked-module replacement.

## Recorder patch collision

**RECORDER_PATCH_CONFLICT = NO**, for all observed node paths and audited static
search roots: exact0, untracked-directory-parent0, backup0, recorder import0.
The new recorder package does not currently resolve. Sharing a tracked ancestor
package with an unrelated untracked descendant is not a package collision.
U48 does not supply that parent package; its dependency precedence is documented
separately. This is not an assertion about arbitrary live dynamic import hooks.
M18 patchSHA **3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee** is unchanged. No apply or import test on actual source.

## Preservation and tests

Fresh full before/after inventory digest, including all untracked content and
mtime/ctime/mode/UID/GID metadata:
**8b0cbfc9df6194fa1607ce8bdc02bc06158b1bd3496a0a4f8de20fdffacfd9d5** — identical.
Original M18 source5 + manager/config/modeld3 SHA256:8/8 unchanged. All15 model
regular-file hashes unchanged. Observed31 process identities unchanged by PID,
start tick, executable and cwd. Fifteen relevant producer/consumer source hashes
also match pinned366. The recorder source pin and patch remain original.

Existing route inventory4,497files digest
**4bf474e52edc1b6ad250ed125b23a87a34ecd781799fa47040247aebef499c24** — identical. This is names/mode/size/mtime
metadata, not a hash of all route contents. No route content or model payload
was executed. Reads can update atime; atime was not compared. These claims cover
the observation window, not a full-device image attestation.
Final flags1/0, branch/HEAD/status unchanged; no other owned audit shell remained
at the last probe (current helper exits itself). No controls/CAN subscriber or
current-stationary inference was needed or run for this read-only audit.

Unchanged M18 CPU_FAKE/FIXTURE regression: **131PASS /0FAIL /0SKIP,26.66s**:

```sh
PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 OPENBLAS_NUM_THREADS=1 "$PY" -m pytest -q -p no:cacheprovider tests/test_v3_input_format.py tests/test_v3_input_recorder.py tests/test_v3_input_dataset.py tests/test_v3_input_hook.py
```

No packages installed. No new production code/test implementation was required.
Fresh independent local read-only review found no Critical/Important/Minor issue:
all2,289 anonymous node records and2,006 hashes matched private evidence, and
classification/coverage/privacy/collision/stop-boundary claims agreed. The reviewer
did not rerun device operations or the CPU suite; the fresh test execution above
was performed by the primary agent. No actual cleanup/install safety or whole-
system non-use conclusion was delegated or inferred.
COMMA_REAL_READ_ONLY PASS; COMMA_REAL_CAPTURE, VEHICLE_PARKED, ROAD_TEST, USB_REAL,
JETSON_REAL, ORT and TRT **NOT_RUN**. No model selection/cache/service action.

## Clean-tree resolution boundary

20 entries (19 scoped generated intermediates/assets +1 exact backup) may be
considered for an explicitly approved outside-repository move, not executed here.
**26 runtime dependencies must remain available; U32/U46 require provenance review.**
No approved complete solution currently produces a clean running source tree
while preserving every dependency. Do not move/delete all48, change ignore rules,
stash/reset/clean, or reinterpret the original clean-tree requirement.

**Ready to resolve clean tree: NO. Ready to retry M19 install: NO.** Next step is
review U32/U46 provenance and approve a complete preservation-compatible source
layout/clean-tree resolution. Approval of any actual cleanup must be separate.
No recorder installation/capture is implied by this audit. Numerical status stays
**PARITY_UNDETERMINED / M2 NO**; the unchanged, unaccessed M1 plan remains
DO_NOT_INSTALL (not a fresh Jetson hash measurement).

All5 upstream refs were re-queried at start/end and unchanged; exact actual366
was retained. Their full SHAs and protected main/old-feature refs are in the JSON.
Development started clean/remote-equal at a9bc99e2865f0b2fa44b3b8906765f3bbd38eacb.
The audit result commit resolves with
`git log -1 --format=%H -- artifacts/m191_dirty_tree_audit_20261023.json`.
Normal same-feature commit/push and final clean/ref checks follow; no force,
main merge, old-feature change or automatic cleanup.
