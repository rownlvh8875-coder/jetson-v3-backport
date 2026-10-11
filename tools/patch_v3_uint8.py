#!/usr/bin/env python3
"""Offline entry point for the same V3 graph transform used in production."""
import sys
from pathlib import Path

_saved_path = sys.path[:]
try:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from jetlink.cinque_v3 import (V3_IMG_INPUTS, V3_IMG_OUTPUT, needs_patch_v3,
                                 patch_v3_uint8_inputs, patch_file_v3)
finally:
    sys.path[:] = _saved_path


def main():
    if len(sys.argv) < 3:
        print(f'usage: {sys.argv[0]} in.onnx out.onnx [retypes.json]', file=sys.stderr)
        raise SystemExit(2)
    print('patched; retypes:', patch_file_v3(sys.argv[1], sys.argv[2],
          sys.argv[3] if len(sys.argv) > 3 else None))


if __name__ == '__main__':
    main()
