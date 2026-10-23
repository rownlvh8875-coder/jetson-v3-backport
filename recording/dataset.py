"""Strict offline reader for complete logical inputs, without model/device imports.

Construction validates every record before exposing any inputs. The Linux reader
opens each path component without following symlinks, keeps a read-only mapping,
and checks file identity on access. Returned records own immutable byte snapshots.
Recurrent state is always owned by the caller's independent replay harness.
"""
from __future__ import annotations

import copy
import hashlib
import json
import mmap
import os
from pathlib import Path
import re
import stat

import numpy as np

from . import format as f


_FILES = {'frames.bin', 'manifest.json', 'COMPLETE'}
_MANIFEST_KEYS = {
    'schema', 'kind', 'status', 'expected_frames', 'frames', 'continuity',
    'spec_digest', 'target_sha256', 'provenance', 'inputs', 'files',
    'capture_start_ns', 'capture_end_ns', 'interval_diagnostic',
    'no_gps_raw_camera', 'state_tensors_stored', 'dataset_digest',
}
_DIAGNOSTIC_KEYS = {'expected_ns', 'min_ns', 'max_ns', 'p50_ns', 'p95_ns', 'p99_ns'}


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate JSON key')
        result[key] = value
    return result


def _reject_constant(_value):
    raise ValueError('nonfinite JSON constant')


def _json(raw):
    try:
        value = json.loads(raw, object_pairs_hook=_json_object, parse_constant=_reject_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError('invalid JSON') from exc
    if type(value) is not dict:
        raise ValueError('expected JSON object')
    return value


def _signature(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_size, info.st_mtime_ns, info.st_ctime_ns)


def _open_directory(path):
    # dir_fd + O_NOFOLLOW prevents a component replacement from redirecting an
    # open between lstat and open. Refuse platforms lacking this guarantee.
    if os.open not in os.supports_dir_fd or not hasattr(os, 'O_NOFOLLOW'):
        raise ValueError('safe directory-relative opens require a supported POSIX platform')
    path = Path(path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    if '..' in path.parts:
        raise ValueError('parent traversal is not a dataset path')
    flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)
    directory = os.open(path.anchor, flags)
    try:
        for name in path.parts[1:]:
            child = os.open(name, flags, dir_fd=directory)
            os.close(directory)
            directory = child
        return directory
    except BaseException:
        os.close(directory)
        raise


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError('invalid integer: ' + name)


def _sha(value):
    return type(value) is str and re.fullmatch('[0-9a-f]{64}', value) is not None


class Dataset:
    """Validated, read-only random access. This class does not execute a model.

    ``spec`` is optional and used only by ``trt_into``. It must be the complete
    authoritative spec dictionary, or an exactly round-tripping ModelSpec.
    When omitted the repository's pinned Cinque spec is read lazily.
    """

    def __init__(self, path, spec=None):
        self.path = Path(path).expanduser().absolute()
        self._spec_source = spec
        self._directory = None
        self._fds = {}
        self._snapshots = {}
        self._mapping = None
        self._validated = False
        try:
            self._directory = _open_directory(self.path)
            if set(os.listdir(self._directory)) != _FILES:
                raise ValueError('complete dataset must contain exactly frames.bin, manifest.json, COMPLETE')
            self._directory_snapshot = _signature(os.fstat(self._directory))
            for name in sorted(_FILES):
                descriptor = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK
                                     | getattr(os, 'O_CLOEXEC', 0), dir_fd=self._directory)
                self._fds[name] = descriptor
                info = os.fstat(descriptor)
                if not stat.S_ISREG(info.st_mode):
                    raise ValueError('dataset member is not a regular file')
                self._snapshots[name] = _signature(info)
            manifest_raw = self._small_file('manifest.json')
            if self._small_file('COMPLETE') != manifest_raw:
                raise ValueError('COMPLETE must exactly match manifest bytes')
            self._manifest = _json(manifest_raw)
            self._validate_manifest()
            self._mapping = mmap.mmap(self._fds['frames.bin'], 0, access=mmap.ACCESS_READ)
            self._validate_frames()
            self._check_unchanged()
            self._validated = True
        except BaseException as exc:
            self.close()
            if isinstance(exc, (OSError, KeyError, TypeError, OverflowError)):
                raise ValueError('invalid or inaccessible dataset') from exc
            raise

    def _small_file(self, name):
        descriptor = self._fds[name]
        size = os.fstat(descriptor).st_size
        if not 0 < size <= 65_536:
            raise ValueError('invalid manifest/marker size')
        with os.fdopen(os.dup(descriptor), 'rb') as stream:
            raw = stream.read(size + 1)
        if len(raw) != size:
            raise ValueError('manifest/marker changed while reading')
        return raw

    def _validate_manifest(self):
        manifest = self._manifest
        if set(manifest) != _MANIFEST_KEYS:
            raise ValueError('manifest allowlist')
        constants = {'schema': 1, 'kind': 'v3-logical-input-dataset', 'status': 'COMPLETE',
                     'continuity': 'CONTIGUOUS', 'spec_digest': f.SPEC_DIGEST,
                     'target_sha256': f.TARGET_SHA, 'no_gps_raw_camera': True,
                     'state_tensors_stored': False}
        for key, expected in constants.items():
            if type(manifest[key]) is not type(expected) or manifest[key] != expected:
                raise ValueError('manifest contract: ' + key)
        _integer(manifest['expected_frames'], 'expected_frames', 1)
        _integer(manifest['frames'], 'frames', 1)
        self._count = manifest['frames']
        size = f.expected_size(manifest['expected_frames'])
        if self._count != manifest['expected_frames']:
            raise ValueError('incomplete frame count')
        f.validate_provenance(manifest['provenance'])
        inputs = {name: {'shape': list(shape), 'dtype': dtype} for name, (shape, dtype) in f.INPUTS.items()}
        if f.canonical(manifest['inputs']) != f.canonical(inputs):
            raise ValueError('logical input contract')
        files = manifest['files']
        if type(files) is not dict or set(files) != {'frames.bin'}:
            raise ValueError('file allowlist')
        item = files['frames.bin']
        if type(item) is not dict or set(item) != {'bytes', 'sha256'}:
            raise ValueError('file metadata allowlist')
        _integer(item['bytes'], 'frames.bin bytes', 1)
        if item['bytes'] != size or self._snapshots['frames.bin'][3] != size or not _sha(item['sha256']):
            raise ValueError('frames size/hash contract')
        for key in ('capture_start_ns', 'capture_end_ns'):
            _integer(manifest[key], key, 1)
        diagnostic = manifest['interval_diagnostic']
        if type(diagnostic) is not dict or set(diagnostic) != _DIAGNOSTIC_KEYS:
            raise ValueError('interval diagnostic allowlist')
        for key in ('expected_ns', 'min_ns', 'max_ns'):
            _integer(diagnostic[key], key)
        for key in ('p50_ns', 'p95_ns', 'p99_ns'):
            if type(diagnostic[key]) is not float or not np.isfinite(diagnostic[key]) or diagnostic[key] < 0:
                raise ValueError('invalid interval percentile')
        if diagnostic['expected_ns'] != f.EXPECTED_INTERVAL_NS:
            raise ValueError('expected interval')
        if not _sha(manifest['dataset_digest']) or manifest['dataset_digest'] != f.dataset_digest(manifest):
            raise ValueError('dataset digest')

    def _validate_frames(self):
        manifest = self._manifest
        header = f.parse_header(self._mapping[:f.HEADER_BYTES])
        if header['capacity'] != self._count or header['provenance'] != manifest['provenance']:
            raise ValueError('header/manifest mismatch')
        if hashlib.sha256(self._mapping).hexdigest() != manifest['files']['frames.bin']['sha256']:
            raise ValueError('frames SHA mismatch')
        values = np.ndarray((self._count,), f.RECORD_DTYPE, buffer=self._mapping, offset=f.HEADER_BYTES)
        previous = None
        intervals = []
        for value in values:
            f.validate_record(value, previous)
            if previous is not None:
                intervals.append(int(value['model_timestamp_ns']) - int(previous['model_timestamp_ns']))
            previous = value
        if (manifest['capture_start_ns'] != int(values[0]['monotonic_ns'])
                or manifest['capture_end_ns'] != int(values[-1]['monotonic_ns'])):
            raise ValueError('capture timestamps mismatch')
        actual = {'expected_ns': f.EXPECTED_INTERVAL_NS,
                  'min_ns': min(intervals, default=0), 'max_ns': max(intervals, default=0)}
        for percentile in (50, 95, 99):
            actual[f'p{percentile}_ns'] = float(np.percentile(intervals, percentile)) if intervals else 0.0
        if manifest['interval_diagnostic'] != actual:
            raise ValueError('interval diagnostics mismatch')

    def _check_unchanged(self):
        try:
            directory = _open_directory(self.path)
            try:
                if (_signature(os.fstat(directory)) != self._directory_snapshot
                        or set(os.listdir(directory)) != _FILES):
                    raise ValueError('dataset directory changed after validation')
                for name, expected in self._snapshots.items():
                    if (_signature(os.stat(name, dir_fd=directory, follow_symlinks=False)) != expected
                            or _signature(os.fstat(self._fds[name])) != expected):
                        raise ValueError('dataset member changed after validation')
            finally:
                os.close(directory)
        except OSError as exc:
            raise ValueError('dataset path changed after validation') from exc

    @property
    def manifest(self):
        return copy.deepcopy(self._manifest)

    def __len__(self):
        return self._count

    def record(self, index):
        if not self._validated:
            raise ValueError('dataset is not open and validated')
        if type(index) is not int:
            raise TypeError('frame index must be an integer')
        if not 0 <= index < self._count:
            raise IndexError('frame index outside dataset')
        self._check_unchanged()
        offset = f.HEADER_BYTES + index * f.RECORD_BYTES
        raw = self._mapping[offset:offset + f.RECORD_BYTES]
        self._check_unchanged()
        return np.frombuffer(raw, dtype=f.RECORD_DTYPE, count=1)[0]

    def __iter__(self):
        for index in range(len(self)):
            yield self.record(index)

    def ort_feeds(self, index):
        """Only four logical arrays; caller supplies and advances its ORT state."""
        value = self.record(index)
        return {name: value[name] for name in f.INPUTS}

    def trt_into(self, index, dest):
        """Fill caller buffers via the existing conversion; never create state."""
        value = self.record(index)
        source = self._spec_source
        if source is None:
            source = _json((Path(__file__).resolve().parents[1] / 'artifacts/cinque_v3.json').read_bytes())
        elif not isinstance(source, dict):
            source = source.to_dict()
        if hashlib.sha256(f.canonical(source)).hexdigest() != f.SPEC_DIGEST:
            raise ValueError('replay spec identity mismatch')
        from jetlink.spec import ModelSpec
        from jetlink.queues import StatefulState
        spec = ModelSpec.from_dict(source)
        if type(dest) is not dict or set(dest) != set(spec.input_shapes):
            raise ValueError('complete caller-owned TRT inputs required')
        for name, shape in spec.input_shapes.items():
            array = dest[name]
            expected_dtype = np.dtype('float16' if name in ('new_img', 'state_img_q') else 'float32')
            if (not isinstance(array, np.ndarray) or array.shape != shape or array.dtype != expected_dtype
                    or not array.flags.c_contiguous):
                raise ValueError('TRT destination shape/dtype/layout: ' + name)
            if name in f.INPUTS and not array.flags.writeable:
                raise ValueError('TRT destination is read-only: ' + name)
        for name in f.INPUTS:
            for other in dest:
                if name != other and np.shares_memory(dest[name], dest[other]):
                    raise ValueError('TRT logical/state destinations must not alias')
        packed = np.concatenate([value[name].reshape(-1) for name in ('desire', 'traffic_convention', 'action_t')])
        StatefulState(spec).step_into(value['new_img'], packed, dest)

    def close(self):
        self._validated = False
        if self._mapping is not None:
            self._mapping.close()
            self._mapping = None
        for descriptor in self._fds.values():
            os.close(descriptor)
        self._fds.clear()
        if self._directory is not None:
            os.close(self._directory)
            self._directory = None

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def __del__(self):
        try:
            self.close()
        except Exception:
            pass
