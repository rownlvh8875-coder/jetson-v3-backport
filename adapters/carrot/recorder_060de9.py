"""Offline exact060de9 binding of the audited810e recorder behavior.

No device access, activation or historical module mutation. The logical-input
path is identical; reviewed request construction, framing and host reassembly
sources are additionally pinned for this separate deployment profile.
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

from adapters.carrot import recorder_810e as previous

BASE_SHA = '060de9c8e59f0e1c0f75d8da3a1ca0ba6058b46c'
PROFILE = 'RECORDER_060DE9_REQUEST_CHUNKS_V1'
MODEL, SPEC_FILE = previous.MODEL, previous.SPEC_FILE
PACKAGE, PACKAGE_FILES, REPO = previous.PACKAGE, previous.PACKAGE_FILES, previous.REPO
NAV_MODEL_SHA, NAV_SPEC_SHA = previous.NAV_MODEL_SHA, previous.NAV_SPEC_SHA
SOURCE_KIND = previous.SOURCE_KIND  # Same logical input provenance, transport independent.
canonical = previous.canonical
TRANSPORT_PINS = {'third_party/jetlink/jetlink/client.py': '05d500179dd3e49d8875d8cfc370a59dd692839eb6b1b939efee5fb72b9092b9', 'third_party/jetlink/jetlink/protocol.py': '27921d6cbac744f28db9f3c3487e42bdf405ac184db41322352f91aad9e3fb51', 'third_party/jetlink/jetlink/request_chunks.py': 'a4ac4bcf467b09df3b703e05a59e757ce2ebb8e016898eb1808ad0031a1905e1', 'third_party/jetlink/jetlink/packed_codec.py': '8d67a94951e6188d811c8ad7072e5db1b40ff9ef24ec28049634b07cb26c9004', 'third_party/jetlink/jetlink/block_codec.py': 'a42299bd1fccdf53022afd50066909caa5740f4790cec1a88eec9665f8e7ad5e', 'third_party/jetlink/jetlink/transport/base.py': '1861db5ec506b274f940797a6d2b181f075e94a928326d699c34cfd6b0c93a3b', 'third_party/jetlink/jetlink/transport/ffs.py': '41580e2d6ae5c4533e5c089375a1788920f3480f59b80fbb7d0eabe2f8b7fd50', 'third_party/jetlink/jetlink/transport/request_writer.py': '7d6846fdeebfafdffb849b17c7771f39ea6f352211ee879f61acdf3e71029d53', 'third_party/jetlink/jetlink/transport/request_writer.c': 'a05f1c9bf1d875625cbb46c5c5d402537c22cb1c625f0aa413db906cbc882bc9', 'tools/jetlink/host_reader.py': '991b975dfb4c65c93f82711da25818981b71ef01281a65bc94a28946246b319a', 'tools/jetlink/host_usb.py': '49609ee4a4179369d6e6e3e048ff1669854de9ec42d92ac5f764eb23c50dcba4', 'tools/jetlink/server.py': '10298c588d517c6aad2c5223b1bc0506fb1a5b89c6f965f5d0b5a7a16b839e87', 'openpilot/selfdrive/modeld/jetlink/host_release.json': 'c113776620f9644bd899bc719a3ded13be3ef851c501d0f323bede7c6181a242'}
SOURCE_PINS = {**previous.SOURCE_PINS, **TRANSPORT_PINS}
FOOTER = previous.FOOTER.replace(previous.PROFILE, PROFILE)


def sources(reference):
    archive = subprocess.check_output(['git','-C',str(reference),'archive','--format=tar',BASE_SHA,*SOURCE_PINS])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        result = {m.name:stream.extractfile(m).read() for m in stream if m.isfile() and m.name in SOURCE_PINS}
    if set(result) != set(SOURCE_PINS) or any(hashlib.sha256(result[n]).hexdigest()!=h for n,h in SOURCE_PINS.items()):
        raise ValueError('exact060de9 reviewed source required')
    # Reuse is conditional on byte equality, not an assumed compatible label.
    before = previous.sources(reference)
    if any(result[n] != before[n] for n in previous.SOURCE_PINS):
        raise ValueError('HOT_PATH_CHANGED; new recorder contract review required')
    if hashlib.sha256(canonical(json.loads(result[SPEC_FILE]))).hexdigest()!=NAV_SPEC_SHA:
        raise ValueError('N16 semantic spec drift')
    return result


def _assignment(source, name, expected, replacement):
    nodes = [n for n in ast.parse(source).body if isinstance(n,ast.Assign)
             and any(isinstance(t,ast.Name) and t.id==name for t in n.targets)]
    node, = nodes
    if ast.literal_eval(node.value) != expected:
        raise ValueError('unreviewed810e constant: '+name)
    lines = source.splitlines(True)
    return ''.join(lines[:node.lineno-1])+name+' = '+repr(replacement)+'\n'+''.join(lines[node.end_lineno:])


def recorder_footer(files):
    return FOOTER.replace('@HOOK_SHA256@',hashlib.sha256(files[PACKAGE+'/hook.py']).hexdigest())


def recorder_files(reference):
    source = sources(reference)
    old_files = previous.recorder_files(reference)
    files = dict(old_files)
    fmt = files[PACKAGE+'/format.py'].decode()
    files[PACKAGE+'/format.py'] = _assignment(fmt,'BASE_SHA',previous.BASE_SHA,BASE_SHA).encode()
    old_hook = files[PACKAGE+'/hook.py'].decode()
    hook = _assignment(old_hook,'SOURCE_PINS',previous.SOURCE_PINS,SOURCE_PINS)
    old_pins = {n:hashlib.sha256(old_files[PACKAGE+'/'+n]).hexdigest()
                for n in PACKAGE_FILES if n!='hook.py'}
    pins = {n:hashlib.sha256(files[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    hook = _assignment(hook,'PACKAGE_PINS',old_pins,pins)
    hook = _assignment(hook,'FOOTER_TEMPLATE',previous.FOOTER,FOOTER)
    # Function/class AST stays identical to the reviewed810e behavior. Diagnostic
    # error wording inherited from810e is historical, not a different runtime pin.
    def behavior(value):
        return [ast.dump(n) for n in ast.parse(value).body if isinstance(n,(ast.ClassDef,ast.FunctionDef))]
    if behavior(hook)!=behavior(old_hook):
        raise ValueError('unexpected recorder behavior change')
    files[PACKAGE+'/hook.py'] = hook.encode()
    files[MODEL] = source[MODEL]+recorder_footer(files).encode()
    for name,raw in files.items():compile(raw,name,'exec',dont_inherit=True)
    return files


def before_files(reference, layout):
    if layout not in ('surviving366','clean060de9'):
        raise ValueError('explicit060de9 source layout required')
    value = previous.before_files(reference,'surviving366' if layout=='surviving366' else 'clean810e')
    if value[MODEL]!=sources(reference)[MODEL]:
        raise ValueError('pure060de9 model differs from audited810e')
    return value


def build_candidate(reference,destination,*,layout='surviving366'):
    reference,destination=Path(reference).resolve(),Path(destination).absolute()
    if (destination.exists() or destination.is_symlink() or reference==destination
        or reference in destination.parents or any(p.is_symlink() for p in destination.parents)):
        raise ValueError('fresh non-symlink destination outside reference required')
    before,after=before_files(reference,layout),recorder_files(reference)
    forward,reverse,touched=[],[],[]
    for name,b in sorted(after.items()):
        a=before.get(name)
        if a==b:continue
        forward.extend(difflib.unified_diff((a or b'').decode().splitlines(True),b.decode().splitlines(True),
                       fromfile='a/'+name if a is not None else '/dev/null',tofile='b/'+name))
        reverse.extend(difflib.unified_diff(b.decode().splitlines(True),(a or b'').decode().splitlines(True),
                       fromfile='a/'+name,tofile='b/'+name if a is not None else '/dev/null'))
        touched.append(dict(path=name,before_sha256=hashlib.sha256(a).hexdigest() if a is not None else None,
                            after_sha256=hashlib.sha256(b).hexdigest()))
    forward,reverse=''.join(forward).encode(),''.join(reverse).encode()
    manifest=dict(schema=1,profile=PROFILE,base_sha=BASE_SHA,layout=layout,actual_deployment='NOT_RUN',
                  source_pins=SOURCE_PINS,nav_model_sha=NAV_MODEL_SHA,nav_spec_sha=NAV_SPEC_SHA,
                  before_profile={n:hashlib.sha256(b).hexdigest() for n,b in before.items()},
                  after_profile={n:hashlib.sha256(b).hexdigest() for n,b in after.items()},touched_files=touched,
                  forward_sha256=hashlib.sha256(forward).hexdigest(),reverse_sha256=hashlib.sha256(reverse).hexdigest())
    destination.mkdir(parents=True)
    for name,raw in after.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    out=destination/'.recorder060';out.mkdir()
    (out/'forward.patch').write_bytes(forward);(out/'reverse.patch').write_bytes(reverse)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest


def dataset_class(reference):
    files=recorder_files(reference)
    name='_recorder060_'+hashlib.sha256(files[PACKAGE+'/format.py']).hexdigest()[:16]
    if name+'.dataset' in sys.modules:return sys.modules[name+'.dataset'].Dataset
    package=types.ModuleType(name);package.__path__=[];sys.modules[name]=package
    for child in ('format','dataset'):
        module=types.ModuleType(name+'.'+child);module.__package__=name;sys.modules[module.__name__]=module
        exec(compile(files[PACKAGE+'/'+child+'.py'],'<trusted060de9-'+child+'>','exec'),module.__dict__)
        setattr(package,child,module)
    return package.dataset.Dataset
