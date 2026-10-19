# Current Carrot candidate validation and rollback

This is a software candidate for current carrot-wip, not an installed Carrot R2
release. See CODEX_CONTINUATION.md for the final checked SHAs/counts.

## Maintained source

- `adapters/carrot/integration.py`: read-only reference → new disposable
  candidate, patch, before/after SHA256 manifest. Existing destinations rejected.
- `adapters/carrot/server.py`: reviewed source body guards, current spec/state,
  protocol 2/3 session, current TRT builder/cache, host control provisioning gate.
- `adapters/carrot/peer_policy.py` and existing `jetlink/multimodel_policy.py`:
  explicit USB/TRT/Jetson capability, resident-only adoption, current Carrot
  offroad approval and exact approved spec comparison.
- `tools/check_latest_carrot_compat.py`: online remote HEAD lookup before/after
  tests, relevant Git blob comparison, isolated reference/candidate, source
  provenance freeze, required behavioral suites. Any required failure/skip/xfail/
  empty collection prevents compatible status and baseline update.

Current `model.py`, `link.py`, parser and JetlinkClient are preserved. The V2
protocol 2 path retains its wire/queued behavior. Protocol 3 queued clients omit
prev_feat; the candidate retains that state on the server. Protocol 3 stateful
inference checks every physical output before next-state commit; bad results
return error headers, invalidate the resident generation and require reload.
Partial copy failure does not claim rollback. Valid protocol 3 HELLO resets state;
invalid generations cannot be revived by HELLO or RESET.

## Offroad provisioning boundary

Managed ENGINE_REQ adopts only the same resident generation and full spec seen
at HELLO. It cannot build, upload, select an alternative engine or download.
First adoption is offroad; exact approved model reconnection may occur onroad.
Current daemon identity checks and JoiningModel internal fallback remain active.

The host's local prepare/import/download APIs are also guarded. In managed mode,
an injected trusted `offroad` callback must return exactly True and no protocol 3
session may be attached. Unknown/False/raising providers deny setup. Workers
recheck before expensive work, cache publication and loaded-engine publication,
including after warm. A running TensorRT compilation is not claimed cancellable;
authorization loss prevents publication/adoption afterward.

Candidate `--managed-jetson` selects protocol 3 and enables this default-deny
gate at startup; ordinary legacy startup stays unchanged. No actual installed
offroad provider is invented. M0 must identify the real runtime/vehicle-state
source before wiring it. Thus this flag alone does not produce a deployable
model-selection service, and no installed service was started or changed.

## Reproduce current software verification

Linux Python requires numpy, pytest and onnx; no TRT/GPU package is imported by
the CPU substitutes. Use an isolated development environment.

```sh
python tools/check_latest_carrot_compat.py --report .reports/carrot-compat.json --update-baseline
```

The default command always checks latest upstream. `--reference PATH` explicitly
means OFFLINE_REFERENCE; it cannot update a latest-validated baseline. Use
`--work-dir NEW_PATH` to retain the separate clean reference/candidate.

For a manually built candidate:

```sh
python -m adapters.carrot.integration REFERENCE NEW_DEVELOPMENT_CANDIDATE
CARROT_CANDIDATE_ROOT=NEW_DEVELOPMENT_CANDIDATE CARROT_REFERENCE_ROOT=REFERENCE \
  python -m pytest -q tests/test_current_carrot_adapter.py tests/test_current_carrot_server.py tests/test_current_carrot_loopback.py tests/test_current_carrot_integration.py
```

The full repository's pytest tests also include historical protocol-2 V3 assets.
They require separate copies at the old manifest's SHAs with the old patches
applied; do not point them at an unpatched reference or the current candidate.
Source paths of comma and Jetson remain isolated in separate subprocesses.

```sh
CINQUE_PRODUCTION_ROOT=OLD_PATCHED_JETSON_COPY CINQUE_COMMA_ROOT=OLD_PATCHED_COMMA_COPY \
CARROT_CANDIDATE_ROOT=CURRENT_CANDIDATE \
  python -m pytest tests --ignore=tests/test_backport.py --ignore=tests/test_stateful_safety.py -q
python tests/test_backport.py
python tests/test_stateful_safety.py
```

The last two are existing standalone scripts with `sys.exit` at import. Bare
pytest tries to collect them and aborts; they are run separately, not rewritten.
Their fixed-path real-model sections skip when that workspace has no ONNX/ORT.
That is distinct from the actual-model measurement below.

## Actual ONNX measurement (ORT_REAL_MODEL)

The pre-existing V3 file was reused read only and whole-file identity checked.
Current generated `jetlink.onnx_patch.patch_file(src, dst, spec=canonical)` was
executed, including its exact source/spec/graph gate and current tinygrad-op
stripping. The local legacy patch function was not substituted for it.

- Original: 766354845 bytes,
  `404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4`.
- Current patched graph: 766352690 bytes,
  `38f8664e65da3c8140674df0b56c8fc444be86ff41a1e54c13d9d9cc96273037`.
- ORT 1.31.0 CPUExecutionProvider only; seed 73.
- Recurrent and same-state each 5 frames; outputs + next_state image/desire/
  feature all finite, every max/mean absolute error 0.
- No new tolerance was selected. Numerical acceptance remains UNDETERMINED,
  exit 3; both acceptance gates are SKIP. This is actual-model CPU measurement,
  not TensorRT, model quality, Jetson timing or vehicle evidence.
- Original identity was unchanged afterward. No model/engine is committed.

Actual run: Windows isolated Python executed `.reports/current_real_model.py`;
ignored logs `.reports/current-real-model.log` and JSON preserve measurements.
Portable evidence is `artifacts/current_carrot_real_model_evidence.json`.
Equivalent reproducible Python (set paths to the actual model and a fresh output):

```python
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(candidate) / 'third_party/jetlink'))
from jetlink.onnx_patch import patch_file
spec = json.loads(Path('artifacts/cinque_v3.json').read_text())
patch_file(str(original), str(patched), spec=spec)
sys.path.insert(0, 'tools')
from build_trt_v3 import verify_onnx_pair, VerificationIncomplete
for mode in ('recurrent', 'same-state'):
    try:
        verify_onnx_pair(original, patched, spec, frames=5, mode=mode, seed=73)
    except VerificationIncomplete as error:
        print(error)  # preserve acceptance UNDETERMINED; do not report PASS
```

## Candidate manifest / rollback

`patches/current-carrot-multimodel.patch` and
`artifacts/current_carrot_candidate_manifest.json` identify one checked upstream
SHA, every touched file's before/after hash, patch hash and software evidence.
The rolling adapters/tests, rather than this fixed patch, are the maintenance
entrypoint. An upstream source-body change intentionally requires review.

In a separate development copy at that exact base SHA, compare all before hashes
and use `git apply --check` before applying the candidate. To reverse, compare
all after hashes, then run:

```sh
git apply --reverse --check /path/to/current-carrot-multimodel.patch
git apply --reverse /path/to/current-carrot-multimodel.patch
```

Verify restored before hashes and absence of candidate-added files. The current
integration test performs reverse/apply and hash checks for every touched file.
No engine/cache deletion belongs to rollback. Runtime settings/services require
actual inventory first; this is not an operating-image installation command.

## CI and remaining device gates

The workflow runs on feature-branch pushes, and declares manual + daily schedule
events with contents:read. It never pushes upstream, fixes failures or merges.
GitHub requires default-branch registration for both workflow_dispatch and
schedule; main was not changed. Those two triggers remain BLOCKED pending that
repository administration decision. Feature push execution is verified separately
when GitHub exposes a run, and is never inferred from local tests.
The feature push at `4c07d018e468ccf2ba94a0c675aef8d5f372fd65` produced
[successful run 39208594966](https://github.com/rownlvh8875-coder/jetson-v3-backport/actions/runs/39208594966).
GitHub documents default-branch restrictions for
[manual dispatch](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow)
and [scheduled events](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

The stale-connection test rejects different sequence/frame tuples on the actual
current client. Existing protocol 3 has no authenticated connection epoch for an
artificially replayed identical tuple; no anti-replay/authentication guarantee is
claimed. Actual USB buffering/re-enumeration still requires USB_REAL.

First Jetson action remains read-only M0:

```sh
python3 tools/jetson_runtime_inventory.py --pretty
```

No build, restart, overwrite, Params changes or USB inference during M0.
The blocked-gate ledger and immediate next steps are in CODEX_CONTINUATION.md.
