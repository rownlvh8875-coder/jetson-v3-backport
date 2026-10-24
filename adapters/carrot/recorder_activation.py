"""Offline M19-A -> activation-v2 delta generator. Never deploy or arm a device.

M18 source and its installed patch remain frozen. Only the generated model
footer and generated hook differ; the writer, record format and inference
observer implementation are reused byte for byte.
"""
from __future__ import annotations

import ast
import difflib
import hashlib
import json
from pathlib import Path

from adapters.carrot.recorder import FOOTER, PACKAGE, REPO, recorder_files
from recording.hook import MODEL
from tools.check_comma_dirty_baseline import AFTER as M19A_HASHES

M18_PATCH_SHA = '3a3e19430ab667d204f22fd1e40438a85e1ade1dbab2e6f9dd6e3dd32de4c1ee'
DISCOVERY_PATH = '/dev/shm/carrot-v3-input-capture/arm.ticket'

DISCOVERY_FOOTER = '''

# M18 exact-input observer; default OFF.
# M19-B0: one volatile ticket check at lazy import, never per frame.
try:
  os.lstat('/dev/shm/carrot-v3-input-capture/arm.ticket')
except Exception:
  pass
else:
  try:
    from openpilot.selfdrive.modeld.jetlink.input_recording.hook import install_discovered as _install_input_capture
    _m18_input_capture = _install_input_capture(globals())
  except Exception:
    pass  # Recorder setup must never disable existing inference or fallback.
'''

# Appended to the generated hook only. It reuses arm_ticket/consume_ticket and
# their schema, boot, monotonic, source/spec and capture-ID checks. No Params,
# environment selector, background service, discovery scan or periodic polling.
HOOK_EXTENSION = '''

# M19-B0 activation-v2: /dev/shm is the exact366 Paths.shm_path convention.
DISCOVERY_DIRECTORY = Path('/dev/shm/carrot-v3-input-capture')
CONTEXT_SOURCE_PINS = {
    'openpilot.selfdrive.modeld.modeld': ('main', 'openpilot/selfdrive/modeld/modeld.py',
        '008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594'),
    'openpilot.system.manager.process': ('launcher', 'openpilot/system/manager/process.py',
        'fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752'),
}


def _modeld_import_context(namespace):
    """Require the normal pinned launcher -> modeld.main active call chain.

    jetlink.prepare.main also imports Warp from this module in another
    interpreter. It must never consume the modeld ticket. Process titles,
    environment labels and module presence alone are not authority.
    """
    import sys
    frame = sys._getframe(1)
    matched = set()
    try:
        root = Path(namespace['__file__']).resolve().parents[4]
        for _ in range(64):
            if frame is None:
                break
            name = frame.f_globals.get('__name__')
            if name in CONTEXT_SOURCE_PINS:
                function, relative, expected = CONTEXT_SOURCE_PINS[name]
                method = frame.f_globals.get(function)
                source = root / relative
                if (getattr(method, '__code__', None) is frame.f_code
                        and Path(frame.f_code.co_filename).resolve() == source
                        and Path(frame.f_globals.get('__file__', '')).resolve() == source
                        and not source.is_symlink()
                        and hashlib.sha256(source.read_bytes()).hexdigest() == expected):
                    matched.add(name)
            frame = frame.f_back
        return matched == set(CONTEXT_SOURCE_PINS)
    except (KeyError, IndexError, OSError, TypeError, ValueError):
        return False
    finally:
        del frame


def _require_volatile_parent():
    parent = DISCOVERY_DIRECTORY.parent
    if parent != Path('/dev/shm'):
        raise ValueError('fixed volatile parent required')
    _no_symlinks(parent)
    info = parent.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
            or stat.S_IMODE(info.st_mode) != 0o1777):
        raise ValueError('root-owned sticky shared-memory parent required')
    mounts = Path('/proc/self/mountinfo').read_text().splitlines()
    matches = []
    for row in mounts:
        left, separator, right = row.partition(' - ')
        fields, fs = left.split(), right.split()
        if separator and len(fields) >= 6 and fields[4] == str(parent):
            matches.append(fs[0] if fs else None)
    if matches != ['tmpfs']:
        raise ValueError('exact boot-local tmpfs mount required')


def _discovery_directory(*, create=False):
    _require_volatile_parent()
    directory = _no_symlinks(DISCOVERY_DIRECTORY)
    if create:
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
            or info.st_gid != os.getegid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise ValueError('private owner/group/mode700 directory required')
    return directory


def arm_discovered(*, output_root, source_model_sha, source_spec_sha, offroad,
                   frames=10, depth=4, expires_seconds=60):
    """Explicit future OFF-only action, never called by modeld import.

    Caller supplies a freshly verified genuine OFF assertion exactly as for
    arm_ticket. The import-time consumer intentionally does not query OFF.
    Prior consumption requires separate explicit safe-state cleanup; this
    helper never deletes a ticket, marker, output or claim to make arming pass.
    """
    if offroad is not True or type(expires_seconds) is not int or not 1 <= expires_seconds <= 300:
        raise ValueError('fresh offroad arming and bounded expiry required')
    directory = _discovery_directory(create=True)
    path = directory / 'arm.ticket'
    if os.path.lexists(directory / 'arm.ticket.consumed'):
        raise FileExistsError('previous capture marker requires explicit offroad review')
    value = arm_ticket(path, output_root=output_root, source_model_sha=source_model_sha,
                       source_spec_sha=source_spec_sha, offroad=offroad, frames=frames,
                       depth=depth, expires_seconds=expires_seconds)
    fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return value


def _consume_discovered(path):
    directory = _discovery_directory()
    expected = directory / 'arm.ticket'
    if Path(path) != expected:
        raise ValueError('fixed discovery path required')
    _no_symlinks(expected)
    fd = os.open(expected, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid()
                or info.st_gid != os.getegid() or stat.S_IMODE(info.st_mode) != 0o600
                or info.st_nlink != 1):
            raise ValueError('private single-link regular owner/group/mode600 ticket required')
    finally:
        os.close(fd)
    # Existing consume first removes the original name, retains .consumed,
    # validates canonical schema/boot/expiry/path, and creates the exclusive ID
    # claim. Invalid owned regular tickets are terminal, not retried on restart.
    value = consume_ticket(expected)
    consumed = expected.with_name('arm.ticket.consumed').lstat()
    identity = lambda s: (s.st_dev, s.st_ino, s.st_uid, s.st_gid,
                          stat.S_IMODE(s.st_mode), s.st_size, s.st_mtime_ns)
    if identity(info) != identity(consumed):
        raise ValueError('ticket identity changed while consuming')
    return value


def install_discovered(namespace, *, recorder_factory=None, source_verifier=None):
    """Consume the fixed ticket once, ignoring any old environment selector.

    Unsafe symlinks/FIFOs/foreign ownership are left untouched and cannot arm.
    Any setup error disables only recording. No loop, retry, rearm or process
    startup policy is introduced here.
    """
    try:
        if not _modeld_import_context(namespace):
            return None
        path = _discovery_directory() / 'arm.ticket'
        return install(namespace, recorder_factory=recorder_factory,
                       source_verifier=source_verifier, ticket_loader=_consume_discovered,
                       arm_path=str(path))
    except Exception:
        return None
'''


def _once(source, old, new):
    if source.count(old) != 1:
        raise ValueError('frozen M18 source anchor changed')
    return source.replace(old, new)


def activation_files(reference):
    """Return all six exact candidate files from a validated M19-A profile."""
    patch = (REPO / 'patches/carrot-nav-v3-input-recorder.patch').read_bytes()
    if hashlib.sha256(patch).hexdigest() != M18_PATCH_SHA:
        raise ValueError('installed M18 patch identity changed')
    before = recorder_files(reference)
    if {n: hashlib.sha256(b).hexdigest() for n, b in before.items()} != M19A_HASHES:
        raise ValueError('candidate must start from exact installed M19-A six hashes')
    after = dict(before)
    if not before[MODEL].endswith(FOOTER.encode()):
        raise ValueError('M19-A footer differs')
    after[MODEL] = before[MODEL][:-len(FOOTER.encode())] + DISCOVERY_FOOTER.encode()
    name = PACKAGE + '/hook.py'
    hook = before[name].decode()
    hook = _once(hook, 'source_verifier=None):', 'source_verifier=None, arm_path=None):')
    hook = _once(hook, "    arm = os.getenv('CARROT_V3_INPUT_CAPTURE')",
                 "    arm = os.getenv('CARROT_V3_INPUT_CAPTURE') if arm_path is None else arm_path")
    hook = _once(hook, 'when CARROT_V3_INPUT_CAPTURE names an explicit, prearmed one-shot ticket.',
                 'after the activation-v2 footer discovers the fixed volatile one-shot ticket.\nThe legacy explicit environment API remains available for offline regression.')
    after[name] = (hook + HOOK_EXTENSION).encode()
    for n, b in after.items():
        compile(b, n, 'exec', dont_inherit=True)
    original = before[MODEL][:-len(FOOTER.encode())]
    tree = ast.parse(after[MODEL])
    if ast.dump(ast.Module(body=tree.body[:-1], type_ignores=[])) != ast.dump(ast.parse(original)):
        raise ValueError('original model logic changed')
    return after


def build_activation_candidate(reference, destination):
    """Write a fresh disposable six-file copy and exact forward/reverse delta."""
    reference, destination = Path(reference).resolve(), Path(destination).absolute()
    if (destination.exists() or destination.is_symlink() or destination == reference
            or reference in destination.parents or any(p.is_symlink() for p in destination.parents)):
        raise ValueError('fresh non-symlink candidate outside reference required')
    before, after = recorder_files(reference), activation_files(reference)
    changed = sorted(n for n in before if before[n] != after[n])
    if changed != sorted((MODEL, PACKAGE+'/hook.py')):
        raise ValueError('activation delta must touch only model footer and hook')
    forward, reverse, touched = [], [], []
    for n in changed:
        a, b = before[n], after[n]
        forward.extend(difflib.unified_diff(a.decode().splitlines(True), b.decode().splitlines(True), fromfile='a/'+n, tofile='b/'+n))
        reverse.extend(difflib.unified_diff(b.decode().splitlines(True), a.decode().splitlines(True), fromfile='a/'+n, tofile='b/'+n))
        touched.append(dict(path=n, before_sha256=hashlib.sha256(a).hexdigest(), after_sha256=hashlib.sha256(b).hexdigest()))
    forward, reverse = ''.join(forward).encode(), ''.join(reverse).encode()
    manifest = dict(schema=1, profile='M19A_TO_ACTIVATION_V2_OFFLINE_ONLY',
        actual_deployment='NOT_RUN', base_m18_patch_sha256=M18_PATCH_SHA,
        touched_files=touched, before_profile=dict(M19A_HASHES),
        after_profile={n:hashlib.sha256(b).hexdigest() for n,b in after.items()},
        forward_sha256=hashlib.sha256(forward).hexdigest(), reverse_sha256=hashlib.sha256(reverse).hexdigest(),
        activation='NO_TICKET = OFF; fixed private boot-local tmpfs discovery only at lazy import',
        manager_or_launcher_changed=False, inference_observer_changed=False)
    destination.mkdir(parents=True)
    for n, b in after.items():
        q=destination/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    out=destination/'.activation-v2';out.mkdir()
    (out/'forward.patch').write_bytes(forward);(out/'reverse.patch').write_bytes(reverse)
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    return manifest
