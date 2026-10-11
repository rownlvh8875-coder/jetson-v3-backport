#!/usr/bin/env python3
"""Development-copy patch verification only. No devices, services or activation."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

PACKAGE = Path(__file__).resolve().parents[1]

def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git(root, *args):
    return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.STDOUT)

def execute(root, record, action):
    root = Path(root).resolve()
    if action not in ('preflight', 'apply', 'reverse'):
        raise ValueError('unknown experimental action')
    if Path(git(root, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != root:
        raise ValueError('root must be the exact development checkout root')
    if git(root, 'rev-parse', 'HEAD').decode().strip() != record['base_sha']:
        raise ValueError('wrong fixed source SHA; preserve this checkout')
    patch = PACKAGE / record['patch']
    if sha256(patch) != record['patch_sha256']:
        raise ValueError('patch hash mismatch')
    # Staged user work is never an acceptable applied experiment state.
    if git(root, 'diff', '--cached', '--name-only'):
        raise ValueError('staged changes present')
    status = git(root, 'status', '--porcelain=v1', '--untracked-files=all', '-z')
    if action != 'reverse' and status:
        raise ValueError('dirty or already applied checkout; preserve changes')
    if action == 'reverse':
        for entry in status.split(b'\0'):
            if entry and (entry[:2] not in (b' M', b'??', b' D') or entry[3:].decode() not in record['files']):
                raise ValueError('changes outside the verified experiment')
    side = 'after_sha256' if action == 'reverse' else 'before_sha256'
    for name, hashes in record['files'].items():
        path = root / name
        if Path(name).is_absolute() or not path.resolve().is_relative_to(root) or path.is_symlink():
            raise ValueError('unsafe target path')
        expected = hashes[side]
        if expected is None:
            if path.exists(): raise ValueError('unexpected existing file: ' + name)
        elif not path.is_file() or sha256(path) != expected:
            raise ValueError('file content mismatch (LF checkout required): ' + name)
    args = ['apply'] + (['--reverse'] if action == 'reverse' else [])
    git(root, *args, '--check', str(patch.resolve()))
    if action != 'preflight':
        git(root, *args, str(patch.resolve()))
        target_side = 'before_sha256' if action == 'reverse' else 'after_sha256'
        for name, hashes in record['files'].items():
            path = root / name
            expected = hashes[target_side]
            if (path.exists() if expected is None else not path.is_file() or sha256(path) != expected):
                raise ValueError('post-application content mismatch: ' + name)
        if action == 'reverse' and git(root, 'status', '--porcelain'):
            raise ValueError('reverse did not restore a clean checkout')
    return 'PASS ' + action

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('preflight','apply','reverse'))
    parser.add_argument('target', choices=('jetson','comma'))
    parser.add_argument('root', type=Path, help='isolated development checkout, never a device installation')
    args = parser.parse_args()
    manifest = json.loads((PACKAGE/'patches/experimental-v3-manifest.json').read_text())
    try:
        print(execute(args.root, manifest['targets'][args.target], args.action))
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        parser.exit(1, 'REFUSED: ' + str(e) + '\n')

if __name__ == '__main__':
    main()
