"""Optional exact native CPU input conversion; preparation compiles/self-tests.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Zeph Leggett. Adapted from tjdgus200/openpilot
third_party/jetlink/jetlink/input_cast.py at a890f6df1bd3eb0478754c68d8b5f92f15e8b722. Full MIT notice is in
the accompanying input_cast.c and the source Jetlink LICENSE.
"""
import ctypes
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import numpy as np


@lru_cache(maxsize=1)
def native_u8_to_f16():
    """Prepare once, before accepting frames; requested failure is fail-closed.

    No call in this module imports GPU runtimes. The returned callable owns the
    loaded library and immutable table. Frame calls only validate and execute.
    """
    compiler = shutil.which('cc') if sys.platform == 'linux' else None
    if compiler is None:
        raise RuntimeError('Explicit input fastpath requires a Linux C compiler at preparation')
    try:
        with tempfile.TemporaryDirectory(prefix='jetlink-input-cast-') as directory:
            library = Path(directory) / 'input_cast.so'
            subprocess.run([compiler, '-std=c99', '-O3', '-fPIC', '-shared', '-fno-fast-math',
                            str(Path(__file__).with_suffix('.c')), '-o', str(library)],
                           check=True, capture_output=True, timeout=10)
            dll = ctypes.CDLL(str(library))
        function = dll.jetlink_u8_f16
        function.argtypes = (ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_size_t)
        function.restype = None
        table = np.arange(256, dtype=np.uint8).astype(np.float16).view(np.uint16)
        table.flags.writeable = False

        def convert(source, dest, _library=dll):
            if (not isinstance(source, np.ndarray) or not isinstance(dest, np.ndarray)
                    or source.dtype != np.uint8 or dest.dtype != np.float16
                    or source.shape != dest.shape or not source.flags.c_contiguous
                    or not dest.flags.c_contiguous or not source.flags.aligned
                    or not dest.flags.aligned or not dest.flags.writeable
                    or np.shares_memory(source, dest)):
                raise ValueError('Invalid native uint8/float16 input buffers')
            function(source.ctypes.data, dest.ctypes.data, table.ctypes.data, source.size)

        for length in (0, 1, 7, 8, 15, 16, 17, 31, 32, 33, 255, 256, 257):
            source = np.arange(length, dtype=np.uint8)
            target = np.empty(length, np.float16)
            convert(source, target)
            if target.tobytes() != source.astype(np.float16).tobytes():
                raise ValueError('Native input conversion self-test failed')
        return convert
    except (OSError, subprocess.SubprocessError, ValueError, AttributeError) as exc:
        raise RuntimeError('Explicit native input conversion preparation failed') from exc
