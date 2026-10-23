"""Prepare an offline, default-OFF M18 candidate; never deploy or activate."""
from __future__ import annotations

import argparse
import ast
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

from recording.hook import BASE_SHA, MODEL, SOURCE_PINS

REPO = Path(__file__).resolve().parents[2]
PACKAGE = 'openpilot/selfdrive/modeld/jetlink/input_recording'
PACKAGE_FILES = ('__init__.py', 'format.py', 'recorder.py', 'dataset.py', 'hook.py')
FOOTER = '''

# M18 exact-input observer; default OFF.
if os.getenv('CARROT_V3_INPUT_CAPTURE'):
  try:
    from openpilot.selfdrive.modeld.jetlink.input_recording.hook import install as _install_input_capture
    _m18_input_capture = _install_input_capture(globals())
  except Exception:
    pass  # Recorder setup must never disable existing inference or fallback.
'''


def _git(reference, *args):
    return subprocess.check_output(['git', '-C', str(reference), *args])


def recorder_files(reference):
    """Validate exact source blobs and return one footer plus the new package."""
    reference = Path(reference).resolve()
    if _git(reference, 'rev-parse', 'HEAD').decode().strip() != BASE_SHA:
        raise ValueError('actual366 source HEAD required; no automatic rebase')
    if _git(reference, 'status', '--porcelain', '--untracked-files=all', '--ignore-submodules=all').strip():
        raise ValueError('clean tracked/untracked reference required')
    originals = {}
    for name, expected in SOURCE_PINS.items():
        raw = _git(reference, 'show', 'HEAD:' + name)
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('reviewed actual366 source hash changed: ' + name)
        originals[name] = raw
    original = originals[MODEL]
    after = original + FOOTER.encode()
    # Check structure independently of textual anchors. Every original node,
    # including class/method bodies, must remain untouched and in order.
    tree = ast.parse(after)
    if ast.dump(ast.Module(body=tree.body[:-1], type_ignores=[])) != ast.dump(ast.parse(original)):
        raise ValueError('original model AST changed')
    changes = {MODEL: after}
    for name in PACKAGE_FILES:
        if _git(reference, 'ls-files', '--', PACKAGE + '/' + name).strip():
            raise ValueError('new recorder package collides with upstream source')
        changes[PACKAGE + '/' + name] = (REPO / 'recording' / name).read_bytes()
    return changes


def build_recorder_candidate(reference, destination):
    """Create a fresh disposable development copy and reversible patch evidence.

    Only tracked regular sparse-checkout files are copied. Git repositories,
    ignored assets, devices, and the source reference are never changed.
    """
    reference, destination = Path(reference).resolve(), Path(destination).absolute()
    if (destination.exists() or destination.is_symlink() or destination == reference
            or reference in destination.parents or any(p.is_symlink() for p in destination.parents)):
        raise ValueError('fresh non-symlink candidate outside reference required')
    changes = recorder_files(reference)
    tracked = _git(reference, 'ls-files', '-t', '-z').decode().split('\0')
    names = [value[2:] for value in tracked if value.startswith('H ')]
    destination.mkdir(parents=True)
    for name in names:
        source = reference / name
        if source.is_file() and not source.is_symlink():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            # Read-only tracked files only. The five runtime identity sources
            # are copied from their pinned Git blobs, independent of local
            # clean smudge/line-ending filters.
            if name in SOURCE_PINS:
                target.write_bytes(_git(reference, 'show', 'HEAD:' + name))
            else:
                shutil.copyfile(source, target)
    touched = []
    hunks = []
    for name, after in sorted(changes.items()):
        before = _git(reference, 'show', 'HEAD:' + name) if name == MODEL else None
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(after)
        touched.append({'path': name, 'before_sha256': hashlib.sha256(before).hexdigest() if before is not None else None,
                        'after_sha256': hashlib.sha256(after).hexdigest()})
        hunks.extend(difflib.unified_diff((before or b'').decode().splitlines(True), after.decode().splitlines(True),
                     fromfile='a/' + name if before is not None else '/dev/null', tofile='b/' + name))
    patch = ''.join(hunks).encode()
    source_files = {name: hashlib.sha256(changes[PACKAGE + '/' + name]).hexdigest() for name in PACKAGE_FILES}
    manifest = dict(schema=1, base_sha=BASE_SHA, branch='carrot-nav',
        repository='https://github.com/ajouatom/openpilot', status='CANDIDATE_UNVERIFIED',
        evidence='CPU_FAKE/FIXTURE and disposable actual366 source only', installation='DO_NOT_INSTALL',
        activation='OFF; explicit boot-bound expiring one-shot offroad arm ticket required',
        source_kind='existing_jetlink_nonstate', source_model_sha='runtime arm ticket + exact Client.spec gate',
        source_spec_sha='runtime arm ticket + canonical actual Client.spec.to_dict SHA256 gate',
        source_pins=dict(SOURCE_PINS), recorder_source_files=source_files,
        touched_files=touched, patch_sha256=hashlib.sha256(patch).hexdigest(),
        limitations=['No actual capture, device, USB, GPU, stationary overhead or vehicle validation',
                     'No V3 execution/selection; exact logical inputs borrowed from existing nonstate source',
                     'Internal-only fallback produces zero captured frames and no COMPLETE dataset',
                     'Camera binding exposes main/extra roles; physical camera stream enum is unavailable',
                     'Fixed record stores exact SOF timestamps; EOF remains available only in borrowed FrameMeta'],
        rollback='In a disposable development copy only: verify all after hashes, reverse patch, verify before hashes; no operating runtime/cache/V2 files changed.')
    out = destination / '.jetlink-recorder'; out.mkdir()
    (out / 'candidate.patch').write_bytes(patch)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(build_recorder_candidate(args.reference, args.destination), indent=2))


if __name__ == '__main__':
    main()
