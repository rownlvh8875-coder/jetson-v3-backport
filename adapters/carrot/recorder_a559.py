"""Offline a559 binding of the unchanged infer-input recorder observer.

Two source-proven CPU preparation orders precede the same observation boundary.
Historical profiles are immutable; no device, ticket or inference is started.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import types

from adapters.carrot import recorder_060de9 as previous

BASE_SHA='a559fcd971ccaa5a87befb8ec080f59a2966325b'
PROFILE='RECORDER_A559_EXECUTION_SWITCHES_V1'
MODEL,SPEC_FILE=previous.MODEL,previous.SPEC_FILE
PACKAGE,PACKAGE_FILES,REPO=previous.PACKAGE,previous.PACKAGE_FILES,previous.REPO
NAV_MODEL_SHA,NAV_SPEC_SHA=previous.NAV_MODEL_SHA,previous.NAV_SPEC_SHA
SOURCE_KIND=previous.SOURCE_KIND
canonical=previous.canonical
REVIEWED_CHANGED_PINS={
    MODEL:'93c2858e5b981ed01ce39745002d7479d5362cb7265c11f2018ac7f7bb3c4554',
    'openpilot/selfdrive/modeld/jetlink/link.py':'418e063bd10245bc1c26a858173d1488188afe3d062bca8ca898a34a36c0e253',
    'openpilot/selfdrive/modeld/jetlink/daemon.py':'b7fb4898bcf62cfc9d8e9fb4034b3fb342ee7468dba6371fc17a99509e2dc35d',
    'openpilot/common/runtime_diagnostics.py':'f5e6c161a5d7c99aebfdfa89c132b86e519980abe6a5b6d787dc2dd8dd3ac1ea',
    'third_party/jetlink/jetlink/output_projection.py':'d76547e3426c488c6f8ab341a2b1f0613c183a02c6b6710c9871af8a94d3a534',
}
SOURCE_PINS={**previous.SOURCE_PINS,**REVIEWED_CHANGED_PINS}
FOOTER=previous.FOOTER.replace(previous.PROFILE,PROFILE)


def sources(reference):
    archive=subprocess.check_output(['git','-C',str(reference),'archive','--format=tar',BASE_SHA,*SOURCE_PINS])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        result={m.name:stream.extractfile(m).read() for m in stream if m.isfile() and m.name in SOURCE_PINS}
    if set(result)!=set(SOURCE_PINS) or any(hashlib.sha256(result[n]).hexdigest()!=h for n,h in SOURCE_PINS.items()):
        raise ValueError('exact reviewed a559 sources required')
    if hashlib.sha256(canonical(json.loads(result[SPEC_FILE]))).hexdigest()!=NAV_SPEC_SHA:
        raise ValueError('N16 semantic spec drift')
    return result


def recorder_footer(files):
    return FOOTER.replace('@HOOK_SHA256@',hashlib.sha256(files[PACKAGE+'/hook.py']).hexdigest())


def recorder_files(reference):
    source=sources(reference);old=previous.recorder_files(reference);files=dict(old)
    assign=previous._assignment
    files[PACKAGE+'/format.py']=assign(old[PACKAGE+'/format.py'].decode(),'BASE_SHA',previous.BASE_SHA,BASE_SHA).encode()
    hook=assign(old[PACKAGE+'/hook.py'].decode(),'SOURCE_PINS',previous.SOURCE_PINS,SOURCE_PINS)
    old_pins={n:hashlib.sha256(old[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    new_pins={n:hashlib.sha256(files[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    hook=assign(hook,'PACKAGE_PINS',old_pins,new_pins)
    hook=assign(hook,'FOOTER_TEMPLATE',previous.FOOTER,FOOTER)
    behavior=lambda value:[ast.dump(n) for n in ast.parse(value).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
    if behavior(hook)!=behavior(old[PACKAGE+'/hook.py']):
        raise ValueError('unexpected observer behavior change')
    files[PACKAGE+'/hook.py']=hook.encode()
    files[MODEL]=source[MODEL]+recorder_footer(files).encode()
    for name,raw in files.items():compile(raw,name,'exec',dont_inherit=True)
    return files


def before_files(reference,layout):
    if layout not in ('surviving366','cleana559'):
        raise ValueError('explicit a559 layout required')
    result=previous.before_files(reference,'surviving366' if layout=='surviving366' else 'clean060de9')
    result[MODEL]=sources(reference)[MODEL]
    return result


def build_candidate(reference,destination,*,layout='surviving366'):
    reference,destination=Path(reference).resolve(),Path(destination).absolute()
    if (destination.exists() or destination.is_symlink() or reference==destination or reference in destination.parents
            or any(p.is_symlink() for p in destination.parents)):
        raise ValueError('fresh non-symlink destination outside reference required')
    before,after=before_files(reference,layout),recorder_files(reference)
    forward,reverse,touched=[],[],[]
    for name,b in sorted(after.items()):
        a=before.get(name)
        if a==b:continue
        forward.extend(difflib.unified_diff((a or b'').decode().splitlines(True),b.decode().splitlines(True),fromfile='a/'+name if a is not None else '/dev/null',tofile='b/'+name))
        reverse.extend(difflib.unified_diff(b.decode().splitlines(True),(a or b'').decode().splitlines(True),fromfile='a/'+name,tofile='b/'+name if a is not None else '/dev/null'))
        touched.append(dict(path=name,before_sha256=hashlib.sha256(a).hexdigest() if a is not None else None,after_sha256=hashlib.sha256(b).hexdigest()))
    forward,reverse=''.join(forward).encode(),''.join(reverse).encode()
    manifest=dict(schema=1,profile=PROFILE,base_sha=BASE_SHA,layout=layout,actual_deployment='NOT_RUN',source_pins=SOURCE_PINS,
        nav_model_sha=NAV_MODEL_SHA,nav_spec_sha=NAV_SPEC_SHA,before_profile={n:hashlib.sha256(b).hexdigest() for n,b in before.items()},
        after_profile={n:hashlib.sha256(b).hexdigest() for n,b in after.items()},touched_files=touched,
        forward_sha256=hashlib.sha256(forward).hexdigest(),reverse_sha256=hashlib.sha256(reverse).hexdigest())
    destination.mkdir(parents=True)
    for name,raw in after.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    out=destination/'.recordera559';out.mkdir()
    (out/'forward.patch').write_bytes(forward);(out/'reverse.patch').write_bytes(reverse)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def dataset_class(reference):
    files=recorder_files(reference)
    name='_recordera559_'+hashlib.sha256(files[PACKAGE+'/format.py']).hexdigest()[:16]
    if name+'.dataset' in sys.modules:return sys.modules[name+'.dataset'].Dataset
    package=types.ModuleType(name);package.__path__=[];sys.modules[name]=package
    for child in ('format','dataset'):
        module=types.ModuleType(name+'.'+child);module.__package__=name;sys.modules[module.__name__]=module
        exec(compile(files[PACKAGE+'/'+child+'.py'],'<trusted-a559-'+child+'>','exec'),module.__dict__)
        setattr(package,child,module)
    return package.dataset.Dataset
