"""Enabled-only exact-input observer for the pinned actual366 nonstate client.

This module has no activation side effects. The model footer imports it only
when CARROT_V3_INPUT_CAPTURE names an explicit, prearmed one-shot ticket.
Arming is a future separately authorized offroad action; it does not select a
model, write Params, or create the capture output directory.
"""
from __future__ import annotations

import functools
import hashlib
import json
import math
import os
from pathlib import Path
import re
import secrets
import stat
import subprocess
import time

import numpy as np

from .format import BASE_SHA, canonical, validate_provenance

MODEL = 'openpilot/selfdrive/modeld/jetlink/model.py'
SOURCE_PINS = {
    MODEL: 'c627644ff2f986883325aaca1b8410f216f45447c6595a123d8c1e53ef8c83da',
    'openpilot/selfdrive/modeld/jetlink/link.py': '9bdb6fb3b9c669fefd0e065e144ceea76068f839cd53eb9d5ccaf3c34c3908c4',
    'openpilot/selfdrive/modeld/camera_gap.py': '7b959fa8bdd740c4bea150c07248a69ea33f08db327110601be3ee17d9bc938a',
    'openpilot/selfdrive/modeld/camera_sync.py': '398980260825757393239796cb4dc10399ef1384f0fd9e23cdad0fd12d0cc0d2',
    'third_party/jetlink/jetlink/spec.py': 'ec844ccaf13ffc1d7c03ad683b0e3f2ce6a1d78f4088067739aaa419af422170',
}
SCALARS = (('desire', (8,)), ('traffic_convention', (1, 2)), ('action_t', (1, 2)))
TICKET_KEYS = {'schema', 'capture_id', 'output_root', 'output', 'frames', 'depth', 'carrot_head',
               'source_model_sha', 'source_spec_sha', 'ticket_path', 'boot_id', 'armed_monotonic_ns',
               'expires_monotonic_ns', 'offroad_armed'}


def _boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def _no_symlinks(path):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('absolute canonical path required')
    for node in (path, *path.parents):
        if node.is_symlink():
            raise ValueError('symlink path forbidden')
    return path


def _output_paths(value):
    root = _no_symlinks(value['output_root'])
    output = _no_symlinks(value['output'])
    if ('realdata' in [part.casefold() for part in output.parts] or not root.is_dir()
            or output.parent != root or output.name != value['capture_id'] or output.exists()):
        raise ValueError('fresh capture directory outside operating routes required')
    return output


def _ticket_contract(value):
    if not isinstance(value, dict) or set(value) != TICKET_KEYS or value['schema'] != 1:
        raise ValueError('arm ticket schema/allowlist')
    if value['carrot_head'] != BASE_SHA or value['offroad_armed'] is not True:
        raise ValueError('source pin/offroad arming proof')
    for key, size in (('capture_id', 32), ('source_model_sha', 64), ('source_spec_sha', 64)):
        if not isinstance(value[key], str) or re.fullmatch('[0-9a-f]{%d}' % size, value[key]) is None:
            raise ValueError('invalid ticket identity')
    if type(value['frames']) is not int or not 1 <= value['frames'] <= 1024:
        raise ValueError('frame cap')
    if type(value['depth']) is not int or value['depth'] not in (4, 8, 16):
        raise ValueError('ring depth')
    for key in ('armed_monotonic_ns', 'expires_monotonic_ns'):
        if type(value[key]) is not int or value[key] < 0:
            raise ValueError('ticket monotonic timestamp')
    if not 0 < value['expires_monotonic_ns'] - value['armed_monotonic_ns'] <= 300_000_000_000:
        raise ValueError('ticket expiry window')
    if not isinstance(value['boot_id'], str) or not value['boot_id']:
        raise ValueError('ticket boot identity')
    _output_paths(value)
    return value


def arm_ticket(path, *, output_root, source_model_sha, source_spec_sha, offroad,
               frames=256, depth=4, expires_seconds=60, boot_id=None, monotonic_ns=None):
    """Prepare, never activate, a future capture after the caller checks offroad.

    The caller must obtain ``offroad`` from a fresh trusted device state during
    the separately approved arming action. This helper does not query or mutate
    Params and is never called by install(). Tests use explicit clock/boot IDs.
    """
    if offroad is not True or type(expires_seconds) is not int or not 1 <= expires_seconds <= 300:
        raise ValueError('offroad arming and bounded expiry required')
    path = _no_symlinks(path)
    root = _no_symlinks(output_root)
    now = time.monotonic_ns() if monotonic_ns is None else monotonic_ns
    capture_id = secrets.token_hex(16)
    value = dict(schema=1, capture_id=capture_id, output_root=str(root), output=str(root / capture_id),
                 frames=frames, depth=depth, carrot_head=BASE_SHA, source_model_sha=source_model_sha,
                 source_spec_sha=source_spec_sha, ticket_path=str(path), boot_id=boot_id or _boot_id(),
                 armed_monotonic_ns=now, expires_monotonic_ns=now + expires_seconds * 1_000_000_000,
                 offroad_armed=True)
    _ticket_contract(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(canonical(value)); stream.flush(); os.fsync(stream.fileno())
    return value


def consume_ticket(path, *, boot_id=None, monotonic_ns=None):
    """Atomically consume once before validating; invalid tickets cannot retry.

    The retained hard link and exclusive ID claim prevent reusing the same
    ticket path/content after a modeld restart. Boot and monotonic expiry deny
    reboot reuse. No current onroad check is made during an authorized capture.
    """
    path = _no_symlinks(path)
    consumed = path.with_name(path.name + '.consumed')
    os.link(path, consumed, follow_symlinks=False)
    path.unlink()
    # O_NONBLOCK is required before fstat: a FIFO can otherwise stall startup
    # indefinitely before we get a chance to reject its non-regular type.
    fd = os.open(consumed, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_size > 8192:
            raise ValueError('regular bounded ticket required')
        raw = stream.read(8193)
        value = json.loads(raw)
    if canonical(value) != raw:
        raise ValueError('noncanonical/duplicate arm ticket JSON')
    _ticket_contract(value)
    if value['ticket_path'] != str(path):
        raise ValueError('ticket moved')
    now = time.monotonic_ns() if monotonic_ns is None else monotonic_ns
    if value['boot_id'] != (boot_id or _boot_id()) or not value['armed_monotonic_ns'] <= now < value['expires_monotonic_ns']:
        raise ValueError('ticket boot/expiry mismatch')
    claim = path.parent / ('.capture-' + value['capture_id'] + '.consumed')
    claim_fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.close(claim_fd)
    return value


def _verify_source(namespace):
    """Startup only: exact tracked HEAD and source bytes, allowing our footer."""
    model = Path(namespace['__file__']).resolve()
    root = model.parents[4]
    head = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], timeout=5).decode().strip()
    if head != BASE_SHA:
        raise ValueError('actual carrot HEAD differs from reviewed366')
    for name, expected in SOURCE_PINS.items():
        raw = (root / name).read_bytes()
        if name == MODEL:
            # The one generated footer starts immediately after the pinned
            # original bytes; no original function body may be modified.
            marker = b'\n\n# M18 exact-input observer; default OFF.\n'
            if raw.count(marker) != 1:
                raise ValueError('recorder footer missing/ambiguous')
            raw = raw.split(marker)[0]
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError('actual source hash changed: ' + name)


def _provenance(value):
    files = {name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
             for name in ('__init__.py', 'format.py', 'recorder.py', 'dataset.py', 'hook.py')}
    return validate_provenance(dict(carrot_head=BASE_SHA, source_kind='existing_jetlink_nonstate',
        source_model_sha=value['source_model_sha'], source_spec_sha=value['source_spec_sha'],
        capture_id=value['capture_id'], source_files=files,
        recorder_source_sha=hashlib.sha256(canonical(files)).hexdigest()))


def _contract(spec, ticket):
    # ClientConnection invokes Client.__init__ on its existing non-realtime
    # connection worker. All digest/layout preparation happens here, never infer.
    if (spec.sha256 != ticket['source_model_sha'] or spec.stateful
            or tuple(spec.warped_shape) != (2, 6, 128, 256)
            or hashlib.sha256(canonical(spec.to_dict())).hexdigest() != ticket['source_spec_sha']):
        raise ValueError('actual nonstate source model/spec mismatch')
    fields = tuple(spec.packed_shapes.items())
    if fields[:3] != SCALARS or not fields or fields[-1][0] != 'prev_feat':
        raise ValueError('actual packed scalar layout mismatch')
    offsets = []
    position = 0
    for name, shape in fields:
        size = math.prod(shape)
        if position < 12:
            offsets.append((position, position + size, shape))
        position += size
    if position != spec.packed_nelem or len(offsets) != 3:
        raise ValueError('actual packed size mismatch')
    snapshots = []
    for name in ('input_shapes', 'output_shapes', 'output_slices'):
        snapshots.append((name, dict(getattr(spec, name))))
    return spec, tuple(offsets), position, tuple(snapshots), (spec.sha256, spec.nbytes, spec.frame_skip, spec.checkpoint)


def _unchanged(spec, contract):
    original, offsets, size, snapshots, scalars = contract
    if spec is not original or (spec.sha256, spec.nbytes, spec.frame_skip, spec.checkpoint) != scalars:
        return False
    for name, expected in snapshots:
        current = getattr(spec, name)
        if len(current) != len(expected) or any(current.get(key) != value for key, value in expected.items()):
            return False
    return True


class _Capture:
    def __init__(self, recorder, ticket):
        self.recorder = recorder
        self.ticket = ticket
        self.disabled = False
        self.pair = None
        self.warped = None
        self.transforms = None

    def stop(self, reason):
        if not self.disabled:
            self.disabled = True
            try:
                self.recorder.stop(reason)
            except Exception:
                pass

    def observe(self, client, image, packed, reset):
        if self.disabled:
            return
        try:
            contract = client._v3_capture_contract
            if not _unchanged(client.spec, contract):
                raise ValueError('source identity/spec changed')
            if (not isinstance(image, np.ndarray) or image.dtype != np.uint8 or image.shape != (2, 6, 128, 256)
                    or not image.flags.c_contiguous or image is not self.warped or self.pair is None):
                raise ValueError('exact warped pair missing or layout changed')
            if (not isinstance(packed, np.ndarray) or packed.dtype != np.float32 or packed.shape != (contract[2],)
                    or not packed.flags.c_contiguous):
                raise ValueError('exact packed scalar layout changed')
            main, extra, selection = self.pair
            transforms = self.transforms
            if transforms is None or any(not isinstance(a, np.ndarray) or a.dtype != np.float32 or a.shape != (3, 3) for a in transforms):
                raise ValueError('actual transforms missing/layout changed')
            metadata = dict(main_frame_id=main.frame_id, extra_frame_id=extra.frame_id,
                model_timestamp_ns=main.timestamp_sof, monotonic_ns=time.monotonic_ns(),
                main_sof_ns=main.timestamp_sof, extra_sof_ns=extra.timestamp_sof,
                selection=selection, transforms=transforms, flags=int(bool(reset)))
            desire, traffic, action = (packed[start:end].reshape(shape) for start, end, shape in contract[1])
            self.recorder.observe(image, desire, traffic, action, metadata)
            # A borrowed warp result belongs to exactly one inference attempt.
            self.warped = None
            if getattr(self.recorder, 'count', 0) >= self.ticket['frames'] or getattr(self.recorder, 'reason', None) is not None:
                # Completed captures must be allowed to finish their private
                # fsync even if a subsequent source transition occurs. A writer
                # failure is already terminal and also needs no further copies.
                self.disabled = True
        except Exception:
            self.stop('exact input observation failed')


def install(namespace, *, recorder_factory=None, ticket_loader=None, source_verifier=None):
    """Install enabled-only wrappers, isolating every setup/observer exception.

    Factory/loader/verifier injection supports CPU fixtures without importing
    openpilot, creating a process, or weakening production source checks.
    Original methods run exactly once with unchanged arguments and exceptions.
    """
    arm = os.getenv('CARROT_V3_INPUT_CAPTURE')
    if not arm:
        return None
    capture = None
    try:
        ticket = (ticket_loader or consume_ticket)(arm)
        (source_verifier or _verify_source)(namespace)
        Client = namespace.get('Client')
        CameraGapTrace = namespace.get('CameraGapTrace')
        if Client is None:
            from openpilot.selfdrive.modeld.jetlink.link import Client
        if CameraGapTrace is None:
            from openpilot.selfdrive.modeld.camera_gap import CameraGapTrace
        Warp = namespace['Warp']
        if any(getattr(cls, '_m18_input_capture_installed', False) for cls in (Client, CameraGapTrace, Warp)):
            raise ValueError('capture hook already installed')
        if recorder_factory is None:
            from .recorder import Recorder
            recorder_factory = Recorder
        # Tests may inject a sink before the rest of the package exists. Real
        # provenance is always complete, strict, and derived at startup.
        provenance = _provenance(ticket)
        recorder = recorder_factory(ticket['output'], provenance, frames=ticket['frames'], depth=ticket['depth'])
        capture = _Capture(recorder, ticket)
        original_receive, original_warp = CameraGapTrace.receive, Warp.__call__
        original_init, original_infer = Client.__init__, Client.infer

        @functools.wraps(original_receive)
        def receive(self, main, extra=None):
            try:
                result = original_receive(self, main, extra)
            except Exception:
                capture.stop('camera receive failed')
                raise
            if not capture.disabled:
                try:
                    capture.pair = None
                    capture.warped = None
                    capture.transforms = None
                    if result is not None:
                        _, main_meta, _, extra_meta = result
                        capture.pair = (main_meta, extra_meta, (0, 0 if extra is None else 1))
                except Exception:
                    capture.stop('camera metadata failed')
            return result

        @functools.wraps(original_warp)
        def warp(self, bufs, transforms, *, prepare=None):
            try:
                result = original_warp(self, bufs, transforms, prepare=prepare)
            except Exception:
                capture.stop('existing warp failed')
                raise
            if not capture.disabled:
                try:
                    capture.warped = result
                    # These float32 matrices are the actual Tinygrad NPY
                    # inputs populated by the original Warp, including its
                    # conversion from any higher-precision caller matrices.
                    capture.transforms = (self.transforms['tfm'], self.transforms['big_tfm'])
                except Exception:
                    capture.stop('warp metadata failed')
            return result

        @functools.wraps(original_init)
        def init(self, *args, **kwargs):
            try:
                original_init(self, *args, **kwargs)
            except Exception:
                capture.stop('existing client setup failed')
                raise
            if not capture.disabled:
                try:
                    self._v3_capture_contract = _contract(self.spec, ticket)
                except Exception:
                    capture.stop('source model/spec/layout mismatch')

        @functools.wraps(original_infer)
        def infer(self, image, packed, frame, reset=False, source_sof=0):
            capture.observe(self, image, packed, reset)
            return original_infer(self, image, packed, frame, reset, source_sof=source_sof)

        CameraGapTrace.receive, Warp.__call__ = receive, warp
        Client.__init__, Client.infer = init, infer
        for cls in (Client, CameraGapTrace, Warp):
            cls._m18_input_capture_installed = True
        return capture
    except Exception:
        if capture is not None:
            capture.stop('capture setup failed')
        return None
