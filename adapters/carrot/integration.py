"""Generate a reviewable, reversible candidate from a clean reference checkout.

No reference edits, repository commits, installed files or service operations.
Source adapters + behavioral compatibility tests are the maintained interface;
the generated patch is evidence for one upstream SHA only.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

REPO = Path(__file__).resolve().parents[2]


def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args])


def replace_once(source: str, before: str, after: str, name: str) -> str:
    if source.count(before) != 1:
        raise ValueError(f'INCOMPATIBLE: {name} source contract changed')
    return source.replace(before, after, 1)


def comma_files(reference: Path) -> dict[str, bytes]:
    reference = Path(reference)
    peer_path = 'openpilot/common/jetlink_peer.py'
    mac_path = 'openpilot/selfdrive/modeld/jetlink/mac.py'
    peer = (reference / peer_path).read_text(encoding='utf-8')
    peer = replace_once(peer, 'import re\n',
                        'import re\nfrom openpilot.common.jetlink_managed import is_managed_jetson_peer\n', peer_path)
    mac = (reference / mac_path).read_text(encoding='utf-8')
    signature = "def prepare(client, peer, offroad, connected, progress, cache=CACHE, mode='usb'):\n"
    replacement = signature + '''  if isinstance(peer, dict) and 'carrot_model_selection_v1' in peer:
    from openpilot.selfdrive.modeld.jetlink.managed import prepare_managed
    return prepare_managed(client, peer, offroad, connected, progress, cache, mode)
'''
    mac = replace_once(mac, signature, replacement, 'mac.prepare signature')
    return {
        peer_path: peer.encode(), mac_path: mac.encode(),
        'openpilot/common/jetlink_managed.py': (REPO / 'jetlink/multimodel_policy.py').read_text(encoding='utf-8').encode(),
        'openpilot/selfdrive/modeld/jetlink/managed.py': (REPO / 'adapters/carrot/peer_policy.py').read_text(encoding='utf-8').encode(),
        'openpilot/selfdrive/modeld/jetlink/cinque_v3.json': (REPO / 'artifacts/cinque_v3.json').read_text(encoding='utf-8').encode(),
    }


def build_candidate(reference: Path, destination: Path) -> dict:
    from adapters.carrot.server import server_files
    reference, destination = Path(reference).resolve(), Path(destination).resolve()
    if destination.exists():
        raise ValueError('Candidate destination must not exist; choose a fresh development directory')
    if destination == reference or reference in destination.parents:
        raise ValueError('Candidate must be outside the reference checkout')
    if git(reference, 'status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('Reference checkout contains tracked changes')
    base = git(reference, 'rev-parse', 'HEAD').decode().strip()
    changes = comma_files(reference)
    host_changes = server_files(reference)
    if changes.keys() & host_changes.keys():
        raise ValueError('Conflicting source adapter ownership')
    changes.update(host_changes)
    # Adapters must succeed before any candidate is copied. Never copy .git,
    # untracked files, ignored model assets, credentials or another candidate.
    records = git(reference, 'ls-files', '-t', '-z').decode().split('\0')
    # Sparse references include thousands of absent skip-worktree paths.
    # Filtering the index avoids stat calls for those paths over /mnt/c.
    names = [record[2:] for record in records if record.startswith('H ')]
    destination.mkdir(parents=True)
    for name in names:
        path = reference / name
        if name and path.is_file():
            target = destination / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
    touched, hunks = [], []
    for name, after in sorted(changes.items()):
        if Path(name).is_absolute() or '..' in Path(name).parts:
            raise ValueError(f'Unsafe candidate path: {name}')
        path = reference / name
        before = path.read_bytes() if path.is_file() else None
        target = destination / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(after)
        touched.append({'path': name,
                        'before_sha256': hashlib.sha256(before).hexdigest() if before is not None else None,
                        'after_sha256': hashlib.sha256(after).hexdigest()})
        hunks.extend(difflib.unified_diff((before or b'').decode().splitlines(True),
                     after.decode().splitlines(True),
                     fromfile='a/' + name if before is not None else '/dev/null', tofile='b/' + name))
    patch = ''.join(hunks).encode()
    manifest = {'schema': 1, 'status': 'CANDIDATE_UNVERIFIED', 'base_sha': base,
                'repository': 'https://github.com/ajouatom/openpilot',
                'branch': 'carrot-wip', 'evidence': 'CPU_FAKE / FIXTURE only until checked',
                'patch_sha256': hashlib.sha256(patch).hexdigest(), 'touched_files': touched,
                'rollback': 'Verify after hashes, git apply --reverse --check candidate.patch, then reverse in development copy only; verify before hashes. Never delete V2 engines.'}
    output = destination / '.jetlink-candidate'
    output.mkdir()
    (output / 'candidate.patch').write_bytes(patch)
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('reference', type=Path)
    parser.add_argument('destination', type=Path)
    args = parser.parse_args()
    print(json.dumps(build_candidate(args.reference, args.destination), indent=2))


if __name__ == '__main__':
    main()
