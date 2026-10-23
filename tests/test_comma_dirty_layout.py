"""Pinned actual366 + representative overlay LAYOUT fixture; no actual overlay data."""
import ast
import builtins
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import types

from tools import check_comma_dirty_baseline as checker

REPO=Path(__file__).resolve().parents[1]
REFERENCE=REPO/'.reference/m15-carrot-nav-366d6eae'
PATCH=REPO/'patches/carrot-nav-v3-input-recorder.patch'


def blob(path):
    return subprocess.check_output(['git','-C',str(REFERENCE),'show',checker.BASE_SHA+':'+path],
                                   env={**os.environ,'GIT_NO_LAZY_FETCH':'1'})


def test_dirty_layout_patch_resolution_OFF_and_exact_reverse(tmp_path,monkeypatch):
    root=tmp_path/'disposable';root.mkdir()
    for name,sha in checker.SOURCE_PINS.items():
        data=blob(name);assert hashlib.sha256(data).hexdigest()==sha
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
    # Actual root package is empty at this pin. Other package markers are fixture
    # layout, deliberately not a reconstruction of the device dependency tree.
    for rel in ('openpilot','openpilot/selfdrive','openpilot/selfdrive/modeld','openpilot/selfdrive/modeld/jetlink',
                'openpilot/selfdrive/controls/lib','openpilot/system/ui/lib'):
        p=root/rel;p.mkdir(parents=True,exist_ok=True);(p/'__init__.py').write_bytes(b'')
    assert blob('openpilot/__init__.py')==b''
    overlay=root/'dependency_overlay';overlay.mkdir()
    role_paths=[]
    for i in range(1,49):
        if i==48:role_paths.append(overlay);continue
        name=('openpilot/selfdrive/controls/lib/observer_fixture.py' if i==32 else
              'openpilot/system/ui/lib/generated_fixture.c' if i==46 else
              f'other_role_layout/U{i:02d}.fixture')
        p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'layout marker only\n');role_paths.append(p)
    assert len(role_paths)==48
    installed=root/'installed_fixture';installed.mkdir()
    for module in ('cffi','cryptography','idna','pycparser'):
        for parent in (overlay,installed):
            p=parent/module;p.mkdir();(p/'__init__.py').write_text('marker="fixture"\n')
    before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    subprocess.run(['git','-C',str(root),'apply','--check',str(PATCH)],check=True)
    subprocess.run(['git','-C',str(root),'apply',str(PATCH)],check=True)
    for name,sha in checker.AFTER.items():assert hashlib.sha256((root/name).read_bytes()).hexdigest()==sha
    for name,data in before.items():
        if name!=checker.MODEL:assert (root/name).read_bytes()==data
    original=before[checker.MODEL];patched=(root/checker.MODEL).read_bytes()
    tree=ast.parse(patched);assert ast.dump(ast.Module(body=tree.body[:-1],type_ignores=[]))==ast.dump(ast.parse(original))
    calls=[]
    def refuse_import(*args,**kwargs):calls.append(args);raise AssertionError('OFF imported recorder')
    functions={name:object() for name in ('JoiningModel','Client','Warp','CameraGapTrace')}
    namespace={**functions,'os':types.SimpleNamespace(getenv=lambda name:None),
               '__builtins__':{**vars(builtins),'__import__':refuse_import}}
    exec(compile(ast.Module(body=[tree.body[-1]],type_ignores=[]),'actual366-OFF-footer','exec'),namespace)
    assert not calls and all(namespace[k] is v for k,v in functions.items())
    script='''import importlib.machinery as m,json,sys
root,overlay,installed=sys.argv[1:];paths=[overlay,root,installed]+sys.path
def resolve(name):
 search=paths;full=[]
 for part in name.split('.'):
  full.append(part);s=m.PathFinder.find_spec('.'.join(full),search)
  assert s is not None,name
  search=list(s.submodule_search_locations or [])
 return s.origin
print(json.dumps({'recorder':resolve('openpilot.selfdrive.modeld.jetlink.input_recording'),
                 'overlay':[resolve(n) for n in ('cffi','cryptography','idna','pycparser')],
                 'vehicle_package_imported':'openpilot' in sys.modules}))
'''
    run=subprocess.run([sys.executable,'-B','-c',script,str(root),str(overlay),str(installed)],capture_output=True,text=True,check=True)
    result=json.loads(run.stdout)
    assert result['recorder']==str(root/checker.PACKAGE/'__init__.py')
    assert all(str(overlay) in p for p in result['overlay']) and not result['vehicle_package_imported']
    subprocess.run(['git','-C',str(root),'apply','--reverse','--check',str(PATCH)],check=True)
    subprocess.run(['git','-C',str(root),'apply','--reverse',str(PATCH)],check=True)
    after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert after==before
