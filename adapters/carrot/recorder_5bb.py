"""Offline exact5bb recorder with explicit nav_metadata forwarding.

Only the nested infer API changes; observation/writer/dataset behavior is retained.
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

from adapters.carrot import recorder_a559 as previous

BASE_SHA='5bbbe160822c7cae4245d7a8e96b40d158941ff7'
PROFILE='RECORDER_5BB_DEFERRED_NAV_V1'
MODEL,SPEC_FILE=previous.MODEL,previous.SPEC_FILE
PACKAGE,PACKAGE_FILES,REPO=previous.PACKAGE,previous.PACKAGE_FILES,previous.REPO
NAV_MODEL_SHA,NAV_SPEC_SHA=previous.NAV_MODEL_SHA,previous.NAV_SPEC_SHA
SOURCE_KIND=previous.SOURCE_KIND
canonical=previous.canonical
# Exact reviewed source, actor, map and transport boundaries; no docs/test pins.
SOURCE_PINS = {'openpilot/selfdrive/modeld/jetlink/model.py': '6e04d29bca6b1802ecc012f8f8ea154f28ec7854961dbf4fd4b6b963328eccee', 'openpilot/selfdrive/modeld/jetlink/link.py': '3be648e18f899ffbcbba08d0cf10de318f5b57a140157d3ceba1cddd96dc7df5', 'openpilot/selfdrive/modeld/jetlink/shared_input.py': 'dc36519c3dc6fad49047fe35a24c5b33f439364c2e4a2559d0f357dfb8e0921e', 'openpilot/selfdrive/modeld/jetlink/contracts.py': '100f92e154b9540ddfe8b8b5ca6c3e2973cce14428fb3442ad98701c976f9ca2', 'openpilot/selfdrive/modeld/jetlink/daemon.py': 'f7038e4f417fdc093c4bd086c0d8184d6e8f2b235c11b519215a7aab4cad0670', 'openpilot/selfdrive/modeld/jetlink/inputs.py': 'c737e30ff8c1b170ebc2179394ee0ce63180e257ddb64ce0967aae7161398f8e', 'openpilot/selfdrive/modeld/jetlink/prepare.py': 'c6a9e9fc1fe122b655ea3a6fbbd3b0fff9ad7d3f918e720e9401fd19e0afb4e7', 'openpilot/selfdrive/modeld/jetlink/jetson_model.json': 'ceb07d1a502966f10cb1afc33c6d686a418b3f204320685cf5e36bbf44c62f6d', 'openpilot/selfdrive/modeld/camera_gap.py': '7b959fa8bdd740c4bea150c07248a69ea33f08db327110601be3ee17d9bc938a', 'openpilot/selfdrive/modeld/camera_sync.py': '398980260825757393239796cb4dc10399ef1384f0fd9e23cdad0fd12d0cc0d2', 'openpilot/selfdrive/modeld/modeld.py': '008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594', 'openpilot/system/manager/process.py': 'fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752', 'third_party/jetlink/jetlink/spec.py': 'ec844ccaf13ffc1d7c03ad683b0e3f2ce6a1d78f4088067739aaa419af422170', 'third_party/jetlink/jetlink/server/session.py': 'a4a5c08f917294806395b1e0fa9c359d747fbc6ced7842dbc3c32d924af2847d', 'third_party/jetlink/jetlink/queues.py': 'c251eecc45e38704c15b2a10f0969c270cd9fa11603ebdaae88c1b1187112ea8', 'third_party/jetlink/jetlink/client.py': 'cda14a04353f87a99b143c5e16ba9c8db69e6bd80a89143e845fde6ffe33ea1c', 'third_party/jetlink/jetlink/protocol.py': '27921d6cbac744f28db9f3c3487e42bdf405ac184db41322352f91aad9e3fb51', 'third_party/jetlink/jetlink/request_chunks.py': 'f97d2b3310e2e049d20c2c2526ffb93068cb1b17aa5214a826ebe95bed670a73', 'third_party/jetlink/jetlink/packed_codec.py': '8d67a94951e6188d811c8ad7072e5db1b40ff9ef24ec28049634b07cb26c9004', 'third_party/jetlink/jetlink/block_codec.py': 'a42299bd1fccdf53022afd50066909caa5740f4790cec1a88eec9665f8e7ad5e', 'third_party/jetlink/jetlink/transport/base.py': '1861db5ec506b274f940797a6d2b181f075e94a928326d699c34cfd6b0c93a3b', 'third_party/jetlink/jetlink/transport/ffs.py': '01a7561451a7194b8ac840a29c78784d8a63731860d146299d43cbf97c852dbd', 'third_party/jetlink/jetlink/transport/request_writer.py': '1fd5ba1a4e446187e41b8c6c73aaff6436ba0b33d6a159c1d6aa1b497ffe1e1e', 'third_party/jetlink/jetlink/transport/request_writer.c': '1161ddd29a8ac6852e14832dd94af0bd2c7c1d8fe009a74d83f423fb57d58b89', 'tools/jetlink/host_reader.py': '991b975dfb4c65c93f82711da25818981b71ef01281a65bc94a28946246b319a', 'tools/jetlink/host_usb.py': '49609ee4a4179369d6e6e3e048ff1669854de9ec42d92ac5f764eb23c50dcba4', 'tools/jetlink/server.py': '4fedc5455adccf09c45980ff4de132d6027249dcffaf622fa6353d69452bd0c7', 'openpilot/selfdrive/modeld/jetlink/host_release.json': '2f36e9a081ea0591e937b8631208652365eadf3dca559157d7a4c8e03a639516', 'openpilot/common/runtime_diagnostics.py': 'f5e6c161a5d7c99aebfdfa89c132b86e519980abe6a5b6d787dc2dd8dd3ac1ea', 'third_party/jetlink/jetlink/output_projection.py': 'd76547e3426c488c6f8ab341a2b1f0613c183a02c6b6710c9871af8a94d3a534', 'third_party/jetlink/jetlink/deferred_map.py': '69e47a2a26b4c71a64d9b4de8fd4dd9f38ad2c92c4bc6e7a1c7f760573c38c86', 'openpilot/selfdrive/navigation/map_client.py': '6fb6e19701ecd22c3dd2cec2de00bb0c8748daedeea5183847c4ea151b0e1cfc', 'tools/jetlink/host_lpm.py': '36d2d2de86cb6fe585c80fe262802bb1e31aedddca37c0ff9d98621ab5aa1139'}
FOOTER=previous.FOOTER.replace(previous.PROFILE,PROFILE)


def sources(reference):
    archive=subprocess.check_output(['git','-C',str(reference),'archive','--format=tar',BASE_SHA,*SOURCE_PINS])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        result={m.name:stream.extractfile(m).read() for m in stream if m.isfile() and m.name in SOURCE_PINS}
    if set(result)!=set(SOURCE_PINS) or any(hashlib.sha256(result[n]).hexdigest()!=h for n,h in SOURCE_PINS.items()):
        raise ValueError('exact reviewed5bb sources required')
    if hashlib.sha256(canonical(json.loads(result[SPEC_FILE]))).hexdigest()!=NAV_SPEC_SHA:
        raise ValueError('N16 semantic spec drift')
    return result


def _metadata_wrapper(hook):
    """Change only accepted metadata argument and its one original forwarding."""
    tree=ast.parse(hook)
    node,=[n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='infer']
    if [a.arg for a in node.args.args]!=['self','image','packed','frame','reset','source_sof']:
        raise ValueError('unreviewed historical infer signature')
    original,=[n for n in ast.walk(node) if isinstance(n,ast.Call)
               and isinstance(n.func,ast.Name) and n.func.id=='original_infer']
    node.args.args.append(ast.arg(arg='nav_metadata'))
    node.args.defaults.append(ast.Constant(value=None))
    original.keywords.append(ast.keyword(arg='nav_metadata',value=ast.Name(id='nav_metadata',ctx=ast.Load())))
    before='def infer(self, image, packed, frame, reset=False, source_sof=0):'
    after='def infer(self, image, packed, frame, reset=False, source_sof=0, nav_metadata=None):'
    old='return original_infer(self, image, packed, frame, reset, source_sof=source_sof)'
    new='return original_infer(self, image, packed, frame, reset, source_sof=source_sof, nav_metadata=nav_metadata)'
    if hook.count(before)!=1 or hook.count(old)!=1:
        raise ValueError('unreviewed infer forwarding body')
    result=hook.replace(before,after).replace(old,new)
    if ast.dump(ast.parse(result))!=ast.dump(tree):
        raise ValueError('unexpected recorder logic change')
    return result


def recorder_footer(files):
    return FOOTER.replace('@HOOK_SHA256@',hashlib.sha256(files[PACKAGE+'/hook.py']).hexdigest())


def recorder_files(reference):
    source=sources(reference);old=previous.recorder_files(reference);files=dict(old)
    assign=previous.previous._assignment
    files[PACKAGE+'/format.py']=assign(old[PACKAGE+'/format.py'].decode(),'BASE_SHA',previous.BASE_SHA,BASE_SHA).encode()
    hook=assign(old[PACKAGE+'/hook.py'].decode(),'SOURCE_PINS',previous.SOURCE_PINS,SOURCE_PINS)
    old_pins={n:hashlib.sha256(old[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    new_pins={n:hashlib.sha256(files[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    hook=assign(hook,'PACKAGE_PINS',old_pins,new_pins)
    hook=assign(hook,'FOOTER_TEMPLATE',previous.FOOTER,FOOTER)
    hook=_metadata_wrapper(hook)
    files[PACKAGE+'/hook.py']=hook.encode()
    files[MODEL]=source[MODEL]+recorder_footer(files).encode()
    for name,raw in files.items():compile(raw,name,'exec',dont_inherit=True)
    return files


def before_files(reference,layout):
    if layout not in ('survivinga559','clean5bb'):
        raise ValueError('explicit exact5bb PRE layout required')
    result=({n:raw for n,raw in previous.recorder_files(reference).items() if n!=MODEL}
            if layout=='survivinga559' else {})
    result[MODEL]=sources(reference)[MODEL]
    return result


def build_candidate(reference,destination,*,layout='survivinga559'):
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
        wrapper_api='infer(self,image,packed,frame,reset=False,source_sof=0,nav_metadata=None)',
        dataset_fields=['new_img','desire','traffic_convention','action_t'],state_tensors_stored=False,
        nav_model_sha=NAV_MODEL_SHA,nav_spec_sha=NAV_SPEC_SHA,before_profile={n:hashlib.sha256(b).hexdigest() for n,b in before.items()},
        after_profile={n:hashlib.sha256(b).hexdigest() for n,b in after.items()},touched_files=touched,
        forward_sha256=hashlib.sha256(forward).hexdigest(),reverse_sha256=hashlib.sha256(reverse).hexdigest())
    destination.mkdir(parents=True)
    for name,raw in after.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    out=destination/'.recorder5bb';out.mkdir()
    (out/'forward.patch').write_bytes(forward);(out/'reverse.patch').write_bytes(reverse)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def dataset_class(reference):
    files=recorder_files(reference)
    name='_recorder5bb_'+hashlib.sha256(files[PACKAGE+'/format.py']).hexdigest()[:16]
    if name+'.dataset' in sys.modules:return sys.modules[name+'.dataset'].Dataset
    package=types.ModuleType(name);package.__path__=[];sys.modules[name]=package
    for child in ('format','dataset'):
        module=types.ModuleType(name+'.'+child);module.__package__=name;sys.modules[module.__name__]=module
        exec(compile(files[PACKAGE+'/'+child+'.py'],'<trusted-5bb-'+child+'>','exec'),module.__dict__)
        setattr(package,child,module)
    return package.dataset.Dataset
