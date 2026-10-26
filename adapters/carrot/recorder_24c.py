"""Offline exact24c recorder: unchanged5bb logic, distinct HUD/host binding.

Builds a candidate only; never connects to a device, starts capture or runs a model.
The expected PRE is pure24c plus the surviving5bb-bound recorder package.
"""
from __future__ import annotations

import difflib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import types

from adapters.carrot import recorder_5bb as previous
from adapters.carrot.recorder_060de9 import _assignment

BASE_SHA='24c1ba5e4b3428f56fa0e402f5a10097e2e94c32'
PROFILE='RECORDER_24C_HUD_HOST_V1'
MODEL,SPEC_FILE=previous.MODEL,previous.SPEC_FILE
PACKAGE,PACKAGE_FILES,REPO=previous.PACKAGE,previous.PACKAGE_FILES,previous.REPO
NAV_MODEL_SHA,NAV_SPEC_SHA=previous.NAV_MODEL_SHA,previous.NAV_SPEC_SHA
SOURCE_KIND=previous.SOURCE_KIND
canonical=previous.canonical
# Recomputed from exact24c Git bytes, including HUD ownership boundaries.
SOURCE_PINS = {'openpilot/common/runtime_diagnostics.py': 'f5e6c161a5d7c99aebfdfa89c132b86e519980abe6a5b6d787dc2dd8dd3ac1ea', 'openpilot/selfdrive/carrot/cluster/cluster_h264_pipeline.py': '0c5de22e32c5f0e5fa77a5c5c620e94615d2ad1fefed9cab2edff47569a0c6b5', 'openpilot/selfdrive/carrot/cluster/cluster_renderer.py': '4e6aaff840ed7795baab528269a925bd96f650a17a025ff5d04bee17ffc5d2fd', 'openpilot/selfdrive/carrot/cluster/main.py': '86adf1360250168e363b2d447877511728e2569b3a0d7fb5481db0d27cf36342', 'openpilot/selfdrive/modeld/camera_gap.py': '7b959fa8bdd740c4bea150c07248a69ea33f08db327110601be3ee17d9bc938a', 'openpilot/selfdrive/modeld/camera_sync.py': '398980260825757393239796cb4dc10399ef1384f0fd9e23cdad0fd12d0cc0d2', 'openpilot/selfdrive/modeld/jetlink/contracts.py': '100f92e154b9540ddfe8b8b5ca6c3e2973cce14428fb3442ad98701c976f9ca2', 'openpilot/selfdrive/modeld/jetlink/daemon.py': 'f7038e4f417fdc093c4bd086c0d8184d6e8f2b235c11b519215a7aab4cad0670', 'openpilot/selfdrive/modeld/jetlink/host_release.json': '9b7d72f5f875edfb2a43a8c5695c617671bbcd4e6add78acef9c50163a85a2ee', 'openpilot/selfdrive/modeld/jetlink/inputs.py': 'c737e30ff8c1b170ebc2179394ee0ce63180e257ddb64ce0967aae7161398f8e', 'openpilot/selfdrive/modeld/jetlink/jetson_model.json': 'ceb07d1a502966f10cb1afc33c6d686a418b3f204320685cf5e36bbf44c62f6d', 'openpilot/selfdrive/modeld/jetlink/link.py': '3be648e18f899ffbcbba08d0cf10de318f5b57a140157d3ceba1cddd96dc7df5', 'openpilot/selfdrive/modeld/jetlink/model.py': '6e04d29bca6b1802ecc012f8f8ea154f28ec7854961dbf4fd4b6b963328eccee', 'openpilot/selfdrive/modeld/jetlink/prepare.py': 'c6a9e9fc1fe122b655ea3a6fbbd3b0fff9ad7d3f918e720e9401fd19e0afb4e7', 'openpilot/selfdrive/modeld/jetlink/shared_input.py': 'dc36519c3dc6fad49047fe35a24c5b33f439364c2e4a2559d0f357dfb8e0921e', 'openpilot/selfdrive/modeld/modeld.py': '008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594', 'openpilot/selfdrive/navigation/map_client.py': '6fb6e19701ecd22c3dd2cec2de00bb0c8748daedeea5183847c4ea151b0e1cfc', 'openpilot/system/manager/process.py': 'fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752', 'third_party/jetlink/jetlink/block_codec.py': 'a42299bd1fccdf53022afd50066909caa5740f4790cec1a88eec9665f8e7ad5e', 'third_party/jetlink/jetlink/client.py': 'cda14a04353f87a99b143c5e16ba9c8db69e6bd80a89143e845fde6ffe33ea1c', 'third_party/jetlink/jetlink/deferred_map.py': '69e47a2a26b4c71a64d9b4de8fd4dd9f38ad2c92c4bc6e7a1c7f760573c38c86', 'third_party/jetlink/jetlink/output_projection.py': 'd76547e3426c488c6f8ab341a2b1f0613c183a02c6b6710c9871af8a94d3a534', 'third_party/jetlink/jetlink/packed_codec.py': '8d67a94951e6188d811c8ad7072e5db1b40ff9ef24ec28049634b07cb26c9004', 'third_party/jetlink/jetlink/protocol.py': '27921d6cbac744f28db9f3c3487e42bdf405ac184db41322352f91aad9e3fb51', 'third_party/jetlink/jetlink/queues.py': 'c251eecc45e38704c15b2a10f0969c270cd9fa11603ebdaae88c1b1187112ea8', 'third_party/jetlink/jetlink/request_chunks.py': 'f97d2b3310e2e049d20c2c2526ffb93068cb1b17aa5214a826ebe95bed670a73', 'third_party/jetlink/jetlink/server/session.py': 'a4a5c08f917294806395b1e0fa9c359d747fbc6ced7842dbc3c32d924af2847d', 'third_party/jetlink/jetlink/spec.py': 'ec844ccaf13ffc1d7c03ad683b0e3f2ce6a1d78f4088067739aaa419af422170', 'third_party/jetlink/jetlink/transport/base.py': '1861db5ec506b274f940797a6d2b181f075e94a928326d699c34cfd6b0c93a3b', 'third_party/jetlink/jetlink/transport/ffs.py': '01a7561451a7194b8ac840a29c78784d8a63731860d146299d43cbf97c852dbd', 'third_party/jetlink/jetlink/transport/request_writer.c': '1161ddd29a8ac6852e14832dd94af0bd2c7c1d8fe009a74d83f423fb57d58b89', 'third_party/jetlink/jetlink/transport/request_writer.py': '1fd5ba1a4e446187e41b8c6c73aaff6436ba0b33d6a159c1d6aa1b497ffe1e1e', 'tools/jetlink/host_lpm.py': '36d2d2de86cb6fe585c80fe262802bb1e31aedddca37c0ff9d98621ab5aa1139', 'tools/jetlink/host_reader.py': '991b975dfb4c65c93f82711da25818981b71ef01281a65bc94a28946246b319a', 'tools/jetlink/host_usb.py': '49609ee4a4179369d6e6e3e048ff1669854de9ec42d92ac5f764eb23c50dcba4', 'tools/jetlink/hud.py': '2c76ae0cf4a80385e9e0033c2fc2b1019affa9c6ecdcb2669135ee1c73570a89', 'tools/jetlink/hud_camera.py': '6b2947c85735e5e287a7d0647a137e8b260115b2a30fcb010ce009bd75ea4bd4', 'tools/jetlink/hud_nav_map.py': 'e8a4bdaeb30baca3fdbe57f4c771602890ea94be3acd1804e292c75f5cc5d999', 'tools/jetlink/hud_navi.py': '3656842d21612fd07ea1825679115b57f343ce2ba1f3f3b4f7c70b8297734a32', 'tools/jetlink/hud_protocol.py': '86daaa1cb7a857637c6fbe76dfc0cac0bf67c8c8d7595977b924e69f84ea729a', 'tools/jetlink/server.py': '4fedc5455adccf09c45980ff4de132d6027249dcffaf622fa6353d69452bd0c7'}

FOOTER=previous.FOOTER.replace(previous.PROFILE,PROFILE)


def sources(reference):
    archive=subprocess.check_output(['git','-C',str(reference),'archive','--format=tar',BASE_SHA,*SOURCE_PINS])
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        result={m.name:stream.extractfile(m).read() for m in stream if m.isfile() and m.name in SOURCE_PINS}
    if set(result)!=set(SOURCE_PINS) or any(hashlib.sha256(result[n]).hexdigest()!=h for n,h in SOURCE_PINS.items()):
        raise ValueError('exact reviewed24c sources required')
    if hashlib.sha256(canonical(json.loads(result[SPEC_FILE]))).hexdigest()!=NAV_SPEC_SHA:
        raise ValueError('N16 semantic spec drift')
    return result


def recorder_footer(files):
    return FOOTER.replace('@HOOK_SHA256@',hashlib.sha256(files[PACKAGE+'/hook.py']).hexdigest())


def recorder_files(reference):
    source=sources(reference);old=previous.recorder_files(reference);files=dict(old)
    files[PACKAGE+'/format.py']=_assignment(old[PACKAGE+'/format.py'].decode(),'BASE_SHA',previous.BASE_SHA,BASE_SHA).encode()
    hook=_assignment(old[PACKAGE+'/hook.py'].decode(),'SOURCE_PINS',previous.SOURCE_PINS,SOURCE_PINS)
    old_pins={n:hashlib.sha256(old[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    new_pins={n:hashlib.sha256(files[PACKAGE+'/'+n]).hexdigest() for n in PACKAGE_FILES if n!='hook.py'}
    hook=_assignment(hook,'PACKAGE_PINS',old_pins,new_pins)
    hook=_assignment(hook,'FOOTER_TEMPLATE',previous.FOOTER,FOOTER)
    files[PACKAGE+'/hook.py']=hook.encode()
    files[MODEL]=source[MODEL]+recorder_footer(files).encode()
    for name,raw in files.items():compile(raw,name,'exec',dont_inherit=True)
    return files


def before_files(reference,layout):
    if layout!='surviving5bb':
        raise ValueError('explicit pure24c + surviving5bb PRE layout required')
    result={n:raw for n,raw in previous.recorder_files(reference).items() if n!=MODEL}
    result[MODEL]=sources(reference)[MODEL]
    return result


def build_candidate(reference,destination,*,layout='surviving5bb'):
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
        nav_model_sha=NAV_MODEL_SHA,nav_spec_sha=NAV_SPEC_SHA,
        before_profile={n:hashlib.sha256(b).hexdigest() for n,b in before.items()},
        after_profile={n:hashlib.sha256(b).hexdigest() for n,b in after.items()},touched_files=touched,
        forward_sha256=hashlib.sha256(forward).hexdigest(),reverse_sha256=hashlib.sha256(reverse).hexdigest())
    destination.mkdir(parents=True)
    for name,raw in after.items():
        p=destination/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
    out=destination/'.recorder24c';out.mkdir()
    (out/'forward.patch').write_bytes(forward);(out/'reverse.patch').write_bytes(reverse)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    return manifest


def dataset_class(reference):
    files=recorder_files(reference)
    name='_recorder24c_'+hashlib.sha256(files[PACKAGE+'/format.py']).hexdigest()[:16]
    if name+'.dataset' in sys.modules:return sys.modules[name+'.dataset'].Dataset
    package=types.ModuleType(name);package.__path__=[];sys.modules[name]=package
    for child in ('format','dataset'):
        module=types.ModuleType(name+'.'+child);module.__package__=name;sys.modules[module.__name__]=module
        exec(compile(files[PACKAGE+'/'+child+'.py'],'<trusted-24c-'+child+'>','exec'),module.__dict__)
        setattr(package,child,module)
    return package.dataset.Dataset
