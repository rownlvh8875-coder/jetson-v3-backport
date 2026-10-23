#!/usr/bin/env python3
"""Validate/inspect a completed offline logical-input dataset; no inference."""
from __future__ import annotations

import sys
sys.dont_write_bytecode = True

import argparse
import json
from pathlib import Path

if __package__ in (None, ''):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recording.dataset import Dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('validate', 'inspect'))
    parser.add_argument('path', type=Path)
    args = parser.parse_args(argv)
    try:
        with Dataset(args.path) as dataset:
            manifest = dataset.manifest
            report = {'status': 'PASS', 'evidence': 'OFFLINE_DATASET_VALIDATION',
                      'frames': len(dataset), 'dataset_digest': manifest['dataset_digest'],
                      'spec_digest': manifest['spec_digest'], 'target_sha256': manifest['target_sha256'],
                      'state_tensors_stored': False}
            if args.command == 'inspect':
                report['manifest'] = manifest
    except (ValueError, OSError) as exc:
        print(json.dumps({'status': 'FAIL', 'evidence': 'OFFLINE_DATASET_VALIDATION', 'error': str(exc)}, allow_nan=False))
        return 1
    print(json.dumps(report, sort_keys=True, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
