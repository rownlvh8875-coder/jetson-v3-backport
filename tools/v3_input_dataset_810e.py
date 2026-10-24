#!/usr/bin/env python3
"""Strict offline810e dataset reader. No inference, device access or arming."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys

sys.dont_write_bytecode=True
if __package__ in (None,''):
    sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adapters.carrot.recorder_810e import PROFILE, dataset_class


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('validate','inspect'))
    parser.add_argument('path',type=Path)
    parser.add_argument('--reference',type=Path,required=True,help='Local Git object store containing exact810e')
    args=parser.parse_args(argv)
    try:
        with dataset_class(args.reference)(args.path) as dataset:
            result=dict(status='PASS',profile=PROFILE,frames=len(dataset),
                        dataset_digest=dataset.manifest['dataset_digest'],state_tensors_stored=False)
            if args.command=='inspect':result['manifest']=dataset.manifest
    except (ValueError,OSError) as error:
        print(json.dumps(dict(status='FAIL',error=str(error))));return 1
    print(json.dumps(result,sort_keys=True,allow_nan=False));return 0


if __name__=='__main__':raise SystemExit(main())
