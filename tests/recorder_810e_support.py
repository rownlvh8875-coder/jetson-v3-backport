"""Pinned source-backed CPU fixtures. No device, CUDA/QCOM or model execution."""
import ast
from functools import lru_cache
import importlib
import json
import math
from pathlib import Path
import subprocess
import sys
import types
from dataclasses import dataclass

import numpy as np

from adapters.carrot import recorder_810e as r

REFERENCE = Path(__file__).resolve().parents[1] / '.reference/m15-carrot-nav-366d6eae'


@lru_cache(maxsize=None)
def blob(name):
    return subprocess.check_output(['git', '-C', str(REFERENCE), 'show', r.BASE_SHA+':'+name])


def selected(name, names, namespace):
    """Execute unchanged selected source nodes; native imports are not executed."""
    tree = ast.parse(blob(name))
    nodes = [n for n in tree.body if isinstance(n, (ast.ClassDef, ast.FunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    tree = ast.Module(body=[ast.ImportFrom(module='__future__', names=[ast.alias(name='annotations')], level=0), *nodes], type_ignores=[])
    exec(compile(ast.fix_missing_locations(tree), name, 'exec'), namespace)
    return namespace


@lru_cache(maxsize=1)
def nav_spec():
    module = types.ModuleType('_exact810_spec')
    sys.modules[module.__name__] = module
    module.__dict__.update(dataclass=dataclass, math=math, STATEFUL_FRAME='new_img', DEFAULT_FRAME_SKIP=4)
    selected('third_party/jetlink/jetlink/spec.py', ['ModelSpec'], module.__dict__)
    return module.ModelSpec.from_dict(json.loads(blob(r.SPEC_FILE)))


def package(tmp_path, monkeypatch):
    # A private package name keeps current and historical366 imports separate.
    folder = tmp_path/'capture810'; folder.mkdir()
    files = r.recorder_files(REFERENCE)
    for n in r.PACKAGE_FILES:
        (folder/n).write_bytes(files[r.PACKAGE+'/'+n])
    monkeypatch.syspath_prepend(str(tmp_path))
    for n in list(sys.modules):
        if n == 'capture810' or n.startswith('capture810.'):
            del sys.modules[n]
    return importlib.import_module('capture810.hook')


def ticket(hook, tmp_path, frames=10):
    out = tmp_path/'outputs';out.mkdir(exist_ok=True)
    return dict(schema=1, capture_id='b'*32, output_root=str(out), output=str(out/('b'*32)),
                frames=frames, depth=4, carrot_head=r.BASE_SHA,
                source_model_sha=r.NAV_MODEL_SHA, source_spec_sha=r.NAV_SPEC_SHA)


class Sink:
    count = 0
    reason = None
    def __init__(self):
        self.records = []; self.identities = []
    def observe(self, image, desire, traffic, action, metadata):
        self.identities.append(id(image))
        self.records.append((image.copy(), desire.copy(), traffic.copy(), action.copy(), metadata))
        self.count += 1
    def stop(self, reason):
        self.reason = reason


def fake_namespace(spec=None):
    class CameraGapTrace:
        def receive(self, main, extra=None):
            return self.result
    class Warp:
        def __call__(self, bufs, transforms, *, prepare=None, output_buffer=None):
            if prepare: prepare()
            self.transforms = {'tfm': transforms['img'], 'big_tfm': transforms['big_img']}
            if output_buffer is None: return bufs
            np.copyto(output_buffer, bufs)
            return output_buffer
    class Client:
        def __init__(self):
            self.spec = spec or nav_spec()
            self.calls = []
        def infer(self, image, packed, frame, reset=False, source_sof=0):
            self.calls.append((image, packed, frame, reset, source_sof))
            if getattr(self, 'failure', None): raise self.failure
            return self
    return dict(CameraGapTrace=CameraGapTrace, Warp=Warp, Client=Client)


def receive_frame(ns, fid=1):
    meta = types.SimpleNamespace(frame_id=fid, timestamp_sof=1_000_000_000+fid*50_000_000)
    camera = ns['CameraGapTrace']()
    camera.result = (object(), meta, object(), meta)
    camera.receive(object())
    return {'img':np.eye(3, dtype=np.float32), 'big_img':np.eye(3, dtype=np.float32)}
