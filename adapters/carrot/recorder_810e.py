"""Offline 810e recorder profile generator; never accesses a device or arms it.

Historical366 templates and deployment profiles are immutable. This profile
reuses their binary writer/reader and ticket security, with a separately audited
N16 contract and the exact810e Warp signature. Git blobs are read by object ID;
the reference checkout and its HEAD are never changed.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import types

from adapters.carrot import recorder_activation as historical
from adapters.carrot.recorder import PACKAGE, PACKAGE_FILES, REPO

BASE_SHA = '810e14aaf51176f1a50a113939dc2e70907b394b'
PROFILE = 'RECORDER_810E_SHARED_INPUT_V1'
MODEL = 'openpilot/selfdrive/modeld/jetlink/model.py'
SPEC_FILE = 'openpilot/selfdrive/modeld/jetlink/jetson_model.json'
NAV_MODEL_SHA = '01effc679eb46d6036ce0302673a87fe2dcfcc95a679daeeb929679e53c3647a'
NAV_SPEC_SHA = '63b2097c114bade03c5ec7ded978d73032a93bb525c03f9b78eddf49809f8b71'
SOURCE_KIND = 'existing_jetlink_n16_nonstate_payload'
# Recomputed from exact810e, including unchanged import/actor boundaries.
SOURCE_PINS = {
    MODEL: '103dc0c7eb1b4998ddbf0a498be55ffd02fd51b195ce20cb7ea44ba3dbce6c42',
    'openpilot/selfdrive/modeld/jetlink/link.py': '3143bc6788132435d6dbeb108f1c68582f702df7913e76f262569f099316ca35',
    'openpilot/selfdrive/modeld/jetlink/shared_input.py': 'dc36519c3dc6fad49047fe35a24c5b33f439364c2e4a2559d0f357dfb8e0921e',
    'openpilot/selfdrive/modeld/jetlink/contracts.py': '100f92e154b9540ddfe8b8b5ca6c3e2973cce14428fb3442ad98701c976f9ca2',
    'openpilot/selfdrive/modeld/jetlink/daemon.py': 'd95e7f44597f150f642f70432143ee9cba8c395bb0513a9e475bc4f597859980',
    'openpilot/selfdrive/modeld/jetlink/inputs.py': 'c737e30ff8c1b170ebc2179394ee0ce63180e257ddb64ce0967aae7161398f8e',
    'openpilot/selfdrive/modeld/jetlink/prepare.py': 'c6a9e9fc1fe122b655ea3a6fbbd3b0fff9ad7d3f918e720e9401fd19e0afb4e7',
    SPEC_FILE: 'ceb07d1a502966f10cb1afc33c6d686a418b3f204320685cf5e36bbf44c62f6d',
    'openpilot/selfdrive/modeld/camera_gap.py': '7b959fa8bdd740c4bea150c07248a69ea33f08db327110601be3ee17d9bc938a',
    'openpilot/selfdrive/modeld/camera_sync.py': '398980260825757393239796cb4dc10399ef1384f0fd9e23cdad0fd12d0cc0d2',
    'openpilot/selfdrive/modeld/modeld.py': '008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594',
    'openpilot/system/manager/process.py': 'fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752',
    'third_party/jetlink/jetlink/spec.py': 'ec844ccaf13ffc1d7c03ad683b0e3f2ce6a1d78f4088067739aaa419af422170',
    'third_party/jetlink/jetlink/server/session.py': 'a4a5c08f917294806395b1e0fa9c359d747fbc6ced7842dbc3c32d924af2847d',
    'third_party/jetlink/jetlink/queues.py': 'c251eecc45e38704c15b2a10f0969c270cd9fa11603ebdaae88c1b1187112ea8',
}

FOOTER = historical.DISCOVERY_FOOTER.replace(
    '# M18 exact-input observer; default OFF.\n# M19-B0: one volatile ticket check at lazy import, never per frame.',
    '# RECORDER_810E_SHARED_INPUT_V1; default OFF.\n# One volatile ticket check at lazy import; no environment activation.')
FOOTER = FOOTER.replace('# One volatile ticket check',
    '# Reviewed hook SHA256: @HOOK_SHA256@\n# One volatile ticket check')


def recorder_footer(files):
    """Bind the reviewed hook to the model footer without a hash fixed point."""
    return FOOTER.replace('@HOOK_SHA256@', hashlib.sha256(files[PACKAGE+'/hook.py']).hexdigest())


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()


def _git(reference, *args):
    return subprocess.check_output(['git', '-C', str(reference), *args])


def sources(reference):
    # One read-only Git object archive; never materialize a checkout or honor
    # local smudge filters. Only reviewed regular members are accepted.
    archive = _git(reference, 'archive', '--format=tar', BASE_SHA, *SOURCE_PINS)
    with tarfile.open(fileobj=io.BytesIO(archive)) as stream:
        result = {member.name: stream.extractfile(member).read()
                  for member in stream if member.isfile() and member.name in SOURCE_PINS}
    if set(result) != set(SOURCE_PINS):
        raise ValueError('incomplete reviewed810e source archive')
    for name, expected in SOURCE_PINS.items():
        raw = result[name]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('exact810e source mismatch: ' + name)
        result[name] = raw
    if hashlib.sha256(canonical(json.loads(result[SPEC_FILE]))).hexdigest() != NAV_SPEC_SHA:
        raise ValueError('N16 contract identity changed')
    signature = next(n for n in ast.walk(ast.parse(result[MODEL]))
                     if isinstance(n, ast.FunctionDef) and n.name == '__call__')
    if [a.arg for a in signature.args.kwonlyargs] != ['prepare', 'output_buffer']:
        raise ValueError('unreviewed Warp API')
    return result


def _replace_node(source, name, replacement):
    node, = [n for n in ast.parse(source).body if getattr(n, 'name', None) == name]
    lines = source.splitlines(True)
    return ''.join(lines[:node.lineno-1]) + replacement.rstrip() + '\n' + ''.join(lines[node.end_lineno:])


VERIFY_SOURCE = '''
def _verify_source(namespace):
    """Startup/arming only: exact HEAD and full patched profile, no footer stripping."""
    model = Path(namespace['__file__']).absolute()
    root = model.parents[4]
    _no_symlinks(model)
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], timeout=5).decode().strip()
    if head != BASE_SHA:
        raise ValueError('reviewed810e HEAD required')
    package = model.parent / 'input_recording'
    for name, expected in PACKAGE_PINS.items():
        path = _no_symlinks(package / name)
        if not stat.S_ISREG(path.lstat().st_mode) or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError('810e recorder package drift: ' + name)
    hook = _no_symlinks(package / 'hook.py')
    if not stat.S_ISREG(hook.lstat().st_mode):
        raise ValueError('regular reviewed hook required')
    hook_sha = hashlib.sha256(hook.read_bytes()).hexdigest()
    footer = FOOTER_TEMPLATE.replace('@HOOK_SHA256@', hook_sha).encode()
    for name, expected in SOURCE_PINS.items():
        path = _no_symlinks(root / name)
        if not stat.S_ISREG(path.lstat().st_mode):
            raise ValueError('regular source required')
        raw = path.read_bytes()
        if name == MODEL:
            if not raw.endswith(footer):
                raise ValueError('reviewed recorder footer/hook binding changed')
            raw = raw[:-len(footer)]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('810e source/profile drift: ' + name)
'''

CONTRACT = '''
def _contract(spec, ticket):
    """Exact N16 server-owned five-pair recurrence, not the old V2 prev_feat gate.

    Only the nonstate payload's first12 floats belong to the V3 dataset.
    nav_map/navigation and every recurrent tensor remain outside the dataset.
    """
    if (not spec.stateful or spec.sha256 != NAV_MODEL_SHA
            or ticket['source_model_sha'] != NAV_MODEL_SHA
            or ticket['source_spec_sha'] != NAV_SPEC_SHA
            or hashlib.sha256(canonical(spec.to_dict())).hexdigest() != NAV_SPEC_SHA
            or tuple(spec.warped_shape) != (2, 6, 128, 256)):
        raise ValueError('exact810e N16 model/spec required')
    fields = tuple(spec.packed_shapes.items())
    expected = SCALARS + (('nav_map', (1, 1, 256, 256)), ('navigation', (1, 47)))
    pairs = tuple(spec.state_pairs.items())
    if (fields != expected or spec.packed_nelem != 65595 or len(pairs) != 5
            or {a: b for a, b in pairs} != EXPECTED_STATE_PAIRS):
        raise ValueError('N16 nonstate payload or server recurrence contract changed')
    snapshots = tuple((name, dict(getattr(spec, name))) for name in
                      ('input_shapes', 'output_shapes', 'output_slices', 'packed_shapes'))
    return spec, ((0, 8, (8,)), (8, 10, (1, 2)), (10, 12, (1, 2))), 65595, snapshots, (
        spec.sha256, spec.nbytes, spec.frame_skip, spec.checkpoint)
'''


def recorder_files(reference):
    source = sources(reference)
    result = {MODEL: source[MODEL]}
    for name in PACKAGE_FILES:
        result[PACKAGE + '/' + name] = (REPO / 'recording' / name).read_bytes()
    # Explicit semantic transformations of a frozen template, never a blanket
    # SHA substitution. The reader and writer are reused without modification.
    fmt = result[PACKAGE + '/format.py'].decode()
    fmt = historical._once(fmt, "BASE_SHA='366d6eae9aa9962104391e1d997fe956dea8f64d'", 'BASE_SHA=' + repr(BASE_SHA))
    fmt = historical._once(fmt, "value['source_kind']!='existing_jetlink_nonstate'",
                          "value['source_kind']!=" + repr(SOURCE_KIND))
    fmt = historical._once(fmt, "    for n in ('recorder_source_sha','source_model_sha','source_spec_sha'):",
        "    if value['source_model_sha']!="+repr(NAV_MODEL_SHA)+" or value['source_spec_sha']!="+repr(NAV_SPEC_SHA)+":\n"
        "        raise ValueError('exact N16 source provenance required')\n"
        "    for n in ('recorder_source_sha','source_model_sha','source_spec_sha'):")
    result[PACKAGE + '/format.py'] = fmt.encode()
    hook = result[PACKAGE + '/hook.py'].decode()
    # AST assignment replacement retains all remaining audited ticket logic.
    assignment = next(n for n in ast.parse(hook).body if isinstance(n, ast.Assign)
                      and any(isinstance(t, ast.Name) and t.id == 'SOURCE_PINS' for t in n.targets))
    pins = dict(SOURCE_PINS)
    lines = hook.splitlines(True)
    hook = ''.join(lines[:assignment.lineno-1]) + 'SOURCE_PINS = ' + repr(pins) + '\n' + ''.join(lines[assignment.end_lineno:])
    spec = json.loads(source[SPEC_FILE])
    pairs = {name: 'next_' + name for name in spec['input_shapes'] if name.startswith('state_')}
    hook += '\nNAV_MODEL_SHA = ' + repr(NAV_MODEL_SHA) + '\nNAV_SPEC_SHA = ' + repr(NAV_SPEC_SHA)
    hook += '\nEXPECTED_STATE_PAIRS = ' + repr(pairs) + '\n'
    # The hook pins the other four modules; the model footer pins the complete
    # hook. The hook validates the exact footer template plus original model
    # body, so neither contains its own final hash or a circular model hash.
    package_pins = {name: hashlib.sha256(result[PACKAGE+'/'+name]).hexdigest()
                    for name in PACKAGE_FILES if name != 'hook.py'}
    hook += '\nPACKAGE_PINS = ' + repr(package_pins) + '\nFOOTER_TEMPLATE = ' + repr(FOOTER) + '\n'
    hook = _replace_node(hook, '_verify_source', VERIFY_SOURCE)
    hook = _replace_node(hook, '_contract', CONTRACT)
    hook = historical._once(hook, "    for key, size in (('capture_id', 32)",
        "    if value['source_model_sha'] != NAV_MODEL_SHA or value['source_spec_sha'] != NAV_SPEC_SHA:\n"
        "        raise ValueError('exact N16 ticket model/spec required')\n"
        "    for key, size in (('capture_id', 32)")
    arm = next(n for n in ast.parse(hook).body if isinstance(n, ast.FunctionDef) and n.name == 'arm_ticket')
    arm_source = ast.get_source_segment(hook, arm)
    checked_arm = historical._once(arm_source, '    path = _no_symlinks(path)',
        "    _verify_source({'__file__': str(Path(__file__).parents[1] / 'model.py')})\n"
        '    path = _no_symlinks(path)')
    hook = _replace_node(hook, 'arm_ticket', checked_arm)
    hook = historical._once(hook, "source_kind='existing_jetlink_nonstate'", 'source_kind=' + repr(SOURCE_KIND))
    hook = historical._once(hook, 'def warp(self, bufs, transforms, *, prepare=None):',
                            'def warp(self, bufs, transforms, *, prepare=None, output_buffer=None):')
    hook = historical._once(hook, 'original_warp(self, bufs, transforms, prepare=prepare)',
                            'original_warp(self, bufs, transforms, prepare=prepare, output_buffer=output_buffer)')
    hook = historical._once(hook, 'source_verifier=None):', 'source_verifier=None, arm_path=None):')
    hook = historical._once(hook, "    arm = os.getenv('CARROT_V3_INPUT_CAPTURE')", '    arm = arm_path')
    hook = historical._once(hook, '    def stop(self, reason):\n',
                            '    def stop(self, reason):\n        self.warped = self.pair = self.transforms = None\n')
    hook = historical._once(hook, '    return True\n\n\nclass _Capture:',
        "    return tuple(spec.packed_shapes.items()) == tuple(contract[3][-1][1].items())\n\n\nclass _Capture:")
    extension = historical.HOOK_EXTENSION.replace('exact366 Paths.shm_path', 'exact810e Paths.shm_path')
    extension = historical._once(extension, "    directory = _discovery_directory(create=True)",
        "    _verify_source({'__file__': str(Path(__file__).parents[1] / 'model.py')})\n"
        "    if source_model_sha != NAV_MODEL_SHA or source_spec_sha != NAV_SPEC_SHA:\n"
        "        raise ValueError('exact N16 model/spec arming required')\n"
        "    directory = _discovery_directory(create=True)")
    hook = hook + extension
    # Accurate profile description; no effect on runtime control/inference.
    hook = _replace_docstring(hook)
    result[PACKAGE + '/hook.py'] = hook.encode()
    result[MODEL] = source[MODEL] + recorder_footer(result).encode()
    tree = ast.parse(result[MODEL])
    if ast.dump(ast.Module(body=tree.body[:-1], type_ignores=[])) != ast.dump(ast.parse(source[MODEL])):
        raise ValueError('inference logic changed')
    for name, raw in result.items():
        compile(raw, name, 'exec', dont_inherit=True)
    return result


def _replace_docstring(hook):
    node = ast.parse(hook).body[0]
    lines = hook.splitlines(True)
    return ('"""Exact810e N16 input observer; fixed volatile discovery, default OFF.\n'
            'Server-owned recurrence and ram_input_v1 ownership are never modified.\n'
            'No module-import activation, Params or persistent environment settings.\n"""\n'
            + ''.join(lines[node.end_lineno:]))


def before_files(reference, layout):
    original = {MODEL: sources(reference)[MODEL]}
    if layout == 'surviving366':
        # Generate historical bytes from their immutable patch, not the current
        # reference working tree/HEAD or an assumed device filesystem state.
        old = {PACKAGE + '/' + n: (REPO / 'recording' / n).read_bytes() for n in PACKAGE_FILES}
        hook = old[PACKAGE + '/hook.py'].decode()
        hook = historical._once(hook, 'source_verifier=None):', 'source_verifier=None, arm_path=None):')
        hook = historical._once(hook, "    arm = os.getenv('CARROT_V3_INPUT_CAPTURE')",
            "    arm = os.getenv('CARROT_V3_INPUT_CAPTURE') if arm_path is None else arm_path")
        hook = historical._once(hook, 'when CARROT_V3_INPUT_CAPTURE names an explicit, prearmed one-shot ticket.',
            'after the activation-v2 footer discovers the fixed volatile one-shot ticket.\nThe legacy explicit environment API remains available for offline regression.')
        old[PACKAGE + '/hook.py'] = (hook + historical.HOOK_EXTENSION).encode()
        expected = json.loads((REPO / 'artifacts/m19b0_activation_v2_validation_20261024.json').read_text())['after_profile']
        if any(hashlib.sha256(raw).hexdigest() != expected[name] for name, raw in old.items()):
            raise ValueError('surviving366 profile changed')
        original.update(old)
    elif layout != 'clean810e':
        raise ValueError('explicit source layout required')
    return original


def build_candidate(reference, destination, *, layout='surviving366'):
    reference, destination = Path(reference).resolve(), Path(destination).absolute()
    if (destination.exists() or destination.is_symlink() or reference == destination
            or reference in destination.parents or any(p.is_symlink() for p in destination.parents)):
        raise ValueError('fresh non-symlink destination outside reference required')
    before, after = before_files(reference, layout), recorder_files(reference)
    forward, reverse, touched = [], [], []
    for name in sorted(after):
        a, b = before.get(name), after[name]
        if a == b:
            continue
        forward.extend(difflib.unified_diff((a or b'').decode().splitlines(True), b.decode().splitlines(True),
            fromfile='a/'+name if a is not None else '/dev/null', tofile='b/'+name))
        reverse.extend(difflib.unified_diff(b.decode().splitlines(True), (a or b'').decode().splitlines(True),
            fromfile='a/'+name, tofile='b/'+name if a is not None else '/dev/null'))
        touched.append(dict(path=name, before_sha256=hashlib.sha256(a).hexdigest() if a is not None else None,
                            after_sha256=hashlib.sha256(b).hexdigest()))
    forward, reverse = ''.join(forward).encode(), ''.join(reverse).encode()
    manifest = dict(schema=1, profile=PROFILE, base_sha=BASE_SHA, layout=layout,
        actual_deployment='NOT_RUN', source_pins=SOURCE_PINS, nav_model_sha=NAV_MODEL_SHA, nav_spec_sha=NAV_SPEC_SHA,
        before_profile={n: hashlib.sha256(b).hexdigest() for n,b in before.items()},
        after_profile={n: hashlib.sha256(b).hexdigest() for n,b in after.items()}, touched_files=touched,
        forward_sha256=hashlib.sha256(forward).hexdigest(), reverse_sha256=hashlib.sha256(reverse).hexdigest())
    destination.mkdir(parents=True)
    for name, raw in after.items():
        path = destination / name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(raw)
    out = destination / '.recorder810'; out.mkdir()
    (out/'forward.patch').write_bytes(forward); (out/'reverse.patch').write_bytes(reverse)
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
    return manifest


def dataset_class(reference):
    """Load only trusted generated codec bytes, never code from a dataset.

    The explicit810e reader cannot silently reinterpret historical366 evidence.
    No deployment/package installation or filesystem cache is created.
    """
    files = recorder_files(reference)
    name = '_recorder810_' + hashlib.sha256(files[PACKAGE+'/format.py']).hexdigest()[:16]
    if name+'.dataset' in sys.modules:
        return sys.modules[name+'.dataset'].Dataset
    package = types.ModuleType(name);package.__path__=[];sys.modules[name]=package
    for child in ('format', 'dataset'):
        module = types.ModuleType(name+'.'+child)
        module.__package__ = name
        sys.modules[module.__name__] = module
        exec(compile(files[PACKAGE+'/'+child+'.py'], '<trusted810e-'+child+'>', 'exec'), module.__dict__)
        setattr(package,child,module)
    return package.dataset.Dataset
