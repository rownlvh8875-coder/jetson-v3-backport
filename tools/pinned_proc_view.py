"""Offline acquisition candidate. All returned process data is PRIVATE/UNSANITIZED.

No runtime policy provider, public emitter, process control or device dispatcher.
"""
import ctypes
import copy
from collections import deque
from contextlib import contextmanager, ExitStack
import fcntl
import hashlib
import functools
import os
import platform
import secrets
import stat
import sys
import threading
import time

from tools.proc_view_scope_model import _mount, _Reject


_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FILE = os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC | os.O_NONBLOCK
_LIMIT = 262144


def _require(value, reason):
    if not value:
        raise AcquisitionError(reason)


def _pid(value):
    if type(value) is not int or not 0 < value <= 2**31-1:
        raise ValueError('PID')
    return str(value)


def _stat(raw, pid):
    left, right = raw.find(b'('), raw.rfind(b')')
    fields = raw[right+2:].split()
    _require(left > 0 and right > left and raw[right+1:right+2] == b' ' and
             len(fields) >= 20 and raw[:left].strip() == str(pid).encode(), 'STAT_LAYOUT')
    try:
        parent, start = int(fields[1]), int(fields[19])
    except ValueError as error:
        raise AcquisitionError('STAT_LAYOUT') from error
    _require(parent >= 0 and start >= 0, 'STAT_LAYOUT')
    return {'pid': pid, 'ppid': parent, 'start_ticks': start}


def _credentials():
    return (os.getresuid(), os.getresgid(), tuple(sorted(os.getgroups())))


def _now():
    return time.clock_gettime_ns(time.CLOCK_BOOTTIME)


def _semantic(name):
    """Record the closed semantic API, not a trace of every native syscall."""
    def decorate(function):
        @functools.wraps(function)
        def call(self,*args,**kwargs):
            view=getattr(self,'_view',self)
            if view._audit_sink is None:return function(self,*args,**kwargs)
            view._emit('CALL_BEGIN',{'method':name})
            try:
                value=function(self,*args,**kwargs)
            except BaseException as error:
                view._emit('CALL_FAILED',{'method':name,'error':_error(error),
                    'partial':getattr(error,'private_partial',None)},primary=error)
                raise
            view._emit('CALL_RESULT',{'method':name,'value':value})
            return value
        return call
    return decorate


class AcquisitionError(RuntimeError):
    pass


class _TargetNotFound(FileNotFoundError):
    """Only the fresh target's own numeric directory/stat open raised ENOENT."""


class _LinkNotFound(FileNotFoundError):
    """Only opening this exact symlink entry raised ENOENT."""


class NativeLinux:
    """Reviewed glibc LP64 layouts only; no syscall-number or fdinfo fallback."""
    def __init__(self):
        _require(sys.platform == 'linux' and platform.machine() in {'x86_64', 'aarch64'}
                 and sys.byteorder == 'little' and ctypes.sizeof(ctypes.c_long) == 8
                 and ctypes.sizeof(ctypes.c_void_p) == 8
                 and platform.libc_ver()[0] == 'glibc', 'UNSUPPORTED_ABI')

        class Statfs(ctypes.Structure):
            _fields_ = [('words', ctypes.c_long * 7), ('fsid', ctypes.c_int * 2),
                        ('tail', ctypes.c_long * 7)]

        class Statx(ctypes.Structure):
            _fields_ = [('mask', ctypes.c_uint32), ('prefix', ctypes.c_ubyte * 140),
                        ('mount_id', ctypes.c_uint64), ('tail', ctypes.c_ubyte * 104)]

        _require(ctypes.sizeof(Statfs) == 120 and ctypes.sizeof(Statx) == 256 and
                 Statx.mount_id.offset == 144, 'UNSUPPORTED_ABI')
        self._statfs, self._statx = Statfs, Statx
        library = ctypes.CDLL(None, use_errno=True)
        _require(hasattr(library, 'fstatfs') and hasattr(library, 'statx'), 'UNSUPPORTED_NATIVE')
        self._fs = library.fstatfs
        self._fs.argtypes = [ctypes.c_int, ctypes.POINTER(Statfs)]
        self._fs.restype = ctypes.c_int
        self._sx = library.statx
        self._sx.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int,
                             ctypes.c_uint, ctypes.POINTER(Statx)]
        self._sx.restype = ctypes.c_int
        self._rl = library.readlinkat
        self._rl.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_size_t]
        self._rl.restype = ctypes.c_ssize_t

    def describe(self, fd):
        fs, sx = self._statfs(), self._statx()
        if self._fs(fd, ctypes.byref(fs)) != 0 or self._sx(fd, b'', 0x1000, 0x1000, ctypes.byref(sx)) != 0:
            raise OSError(ctypes.get_errno(), 'NATIVE_DESCRIPTOR_QUERY')
        _require(sx.mask & 0x1000 and sx.mount_id > 0, 'UNSUPPORTED_MOUNT_ID')
        return {'fs_magic': fs.words[0], 'mount_id': sx.mount_id}

    def link(self, fd):
        buffer = ctypes.create_string_buffer(16385)
        count = self._rl(fd, b'', buffer, len(buffer))
        if count < 0:
            raise OSError(ctypes.get_errno(), 'READLINK_QUERY')
        _require(count < len(buffer) and count <= 16384, 'READLINK_LIMIT')
        return os.fsdecode(buffer.raw[:count])


class ProcView:
    def __init__(self, root='/proc', *, native=None, audit_sink=None):
        self._fds, self._identities, self._closed = set(), {}, False
        _require(audit_sink is None or callable(audit_sink),'STREAM_CALLBACK')
        self._audit_sink=audit_sink
        self._stream_failed=False;self._stream_busy=False;self._stream_errors=[]
        self._stream_session=secrets.token_hex(16);self._stream_events=0
        self._backend = 'INJECTED_TEST_BACKEND' if native is not None else 'NATIVE_GLIBC_LP64_STATX'
        self._operations = deque(maxlen=512)
        self._operation_count = 0
        self.cleanup_errors = []
        self._root = None
        try:
            self._emit('VIEW_BEGIN',{'backend':self._backend})
            _require(threading.get_native_id() == os.getpid() and threading.active_count() == 1,
                     'THREAD_PROFILE')
            self._owner = (os.getpid(), threading.get_ident(), _credentials())
            self._native = native or NativeLinux()
            root = os.fspath(root)
            _require(isinstance(root, str) and root.startswith('/') and
                     all(p not in {'', '.', '..'} for p in root.split('/')[1:]), 'ROOT_PATH')
            _require(root == '/proc' or native is not None, 'FIXTURE_NATIVE_REQUIRED')
            # Hold the named-root parent too; subsequent validation is relative.
            current = os.open('/', _DIR)
            self._fds.add(current)
            parts = root.split('/')[1:]
            for part in parts[:-1]:
                child = os.open(part, _DIR, dir_fd=current)
                self._fds.add(child)
                self._release(current)
                current = child
            self._anchor, self._root_name = current, parts[-1]
            self._root = os.open(self._root_name, _DIR, dir_fd=self._anchor)
            self._fds.add(self._root)
            self._root_identity = self._describe(self._root)
            _require(self._root_identity['fs_magic'] == 0x9FA0, 'NOT_PROCFS')
            self._identities[self._root] = self._root_identity
            self._mapped_pid = int(self._link(self._root, 'self'))
            _require(self._mapped_pid == os.getpid(), 'SELF_MAPPING_UNSUPPORTED')
            self._self = self._open(self._root, _pid(self._mapped_pid), directory=True)
            self._self_identity = self._stat_at(self._self, self._mapped_pid)
            self._status_identity = self._owner_status()
            self._emit('VIEW_READY',{'root':self._root_identity,'owner':self._self_identity})
        except BaseException as error:
            self._emit('VIEW_FAILED',{'error':_error(error)},primary=error)
            self.close(error)
            error.private_cleanup_errors = copy.deepcopy(self.cleanup_errors)
            raise

    def __enter__(self):
        try:
            self._guard()
            return self
        except BaseException as error:
            self.close(error)
            error.private_cleanup_errors = copy.deepcopy(self.cleanup_errors)
            raise

    def __exit__(self, kind, error, traceback):
        self.close(error)
        if self.cleanup_errors:
            if error is None:
                error = AcquisitionError('CLEANUP_FAILED')
                error.private_cleanup_errors = copy.deepcopy(self.cleanup_errors)
                raise error
            error.private_cleanup_errors = copy.deepcopy(self.cleanup_errors)

    def _close(self, fd):
        if fd in self._fds:
            self._fds.remove(fd)
            self._identities.pop(fd, None)
            os.close(fd)

    def _release(self, fd, primary=None):
        try:
            self._close(fd)
        except OSError as error:
            self.cleanup_errors.append(_error(error))
            if primary is not None:
                primary.private_cleanup_errors = copy.deepcopy(self.cleanup_errors)
            else:
                failure = AcquisitionError('CLEANUP_FAILED')
                failure.private_cleanup_errors = copy.deepcopy(self.cleanup_errors)
                raise failure from error

    @contextmanager
    def _managed(self, fd):
        try:
            yield fd
        except BaseException as error:
            self._release(fd, error)
            raise
        else:
            self._release(fd)

    def close(self,primary=None):
        if self._closed:return
        self._closed = True
        for fd in list(self._fds):
            try:
                self._close(fd)
            except OSError as error:
                self.cleanup_errors.append(_error(error))
        if not self._stream_failed:
            self._emit('VIEW_CLOSED',{'cleanup_errors':self.cleanup_errors,
                'remaining_fds':len(self._fds),'attempts':self._operation_count},primary=primary)

    def detach_in_child(self):
        _require(os.getpid()!=self._owner[0],'NOT_CHILD')
        self._audit_sink=None
        self.close()
        _require(not self.cleanup_errors,'INHERITED_CLEANUP_FAILED')

    def _emit(self,event,details,primary=None):
        if self._audit_sink is None:return
        try:
            _require(not self._stream_failed and not self._stream_busy,'STREAM_FAILED')
            self._stream_busy=True;self._stream_events+=1
            self._audit_sink(copy.deepcopy({'schema':1,'session':self._stream_session,
                'sequence':self._stream_events,'timestamp_ns':_now(),
                'event':event,'details':details}))
            _require(not self._stream_failed,'STREAM_FAILED')
        except BaseException as error:
            self._stream_failed=True;self._stream_errors.append(_error(error))
            if primary is not None:
                primary.private_stream_errors=copy.deepcopy(self._stream_errors)
            else:raise AcquisitionError('STREAM_FAILED') from error
        finally:self._stream_busy=False

    @contextmanager
    def _attempt(self, operation, field):
        value = {'operation': operation, 'field': field, 'scheme': 'DIRFD',
                 'start_ns': _now(), 'status': 'OK'}
        primary=None
        try:
            yield value
        except BaseException as error:
            primary=error
            value.update(status='FAILED', error=_error(error))
            raise
        finally:
            value['end_ns'] = _now()
            self._operation_count += 1
            value['sequence'] = self._operation_count
            self._operations.append(value)
            self._emit('ATTEMPT',value,primary=primary)

    def audit(self):
        """Private bounded diagnostic tail, explicitly incomplete after eviction."""
        dropped = self._operation_count - len(self._operations)
        return {'operations': copy.deepcopy(list(self._operations)),
                'dropped_operations': dropped, 'complete': dropped == 0,
                'cleanup_errors': copy.deepcopy(self.cleanup_errors),
                'stream_enabled':self._audit_sink is not None,'stream_failed':self._stream_failed,
                'stream_events':self._stream_events,
                'acquisition_backend': self._backend, 'policy_acceptance': False}

    def _describe(self, fd):
        node = os.fstat(fd)
        result = self._native.describe(fd)
        _require(type(result['mount_id']) is int and result['mount_id'] > 0, 'MOUNT_ID')
        return {**result, 'device': node.st_dev, 'inode': node.st_ino,
                'kind': stat.S_IFMT(node.st_mode),
                'flags': fcntl.fcntl(fd, fcntl.F_GETFL), 'inheritable': os.get_inheritable(fd)}

    def _check(self, fd):
        _require(fd in self._fds and self._describe(fd) == self._identities[fd], 'FD_IDENTITY_CHANGED')

    def _guard(self):
        _require(not self._closed, 'VIEW_CLOSED')
        if self._stream_busy:self._stream_failed=True
        _require(not self._stream_failed,'STREAM_FAILED')
        _require(not self.cleanup_errors, 'CLEANUP_FAILED')
        _require(self._owner == (os.getpid(), threading.get_ident(), _credentials()), 'OWNER_CHANGED')
        _require(threading.get_native_id() == os.getpid() and threading.active_count() == 1,
                 'THREAD_PROFILE')
        self._check(self._root)
        named = os.open(self._root_name, _DIR, dir_fd=self._anchor)
        self._fds.add(named)
        with self._managed(named):
            _require(self._describe(named) == self._root_identity, 'NAMED_ROOT_CHANGED')
        _require(self._stat_at(self._self, self._mapped_pid) == self._self_identity, 'OWNER_GENERATION_CHANGED')
        _require(self._owner_status() == self._status_identity, 'OWNER_STATUS_CHANGED')

    def _owner_status(self):
        raw = self._read(self._self, 'status').decode('ascii', 'strict')
        result = {}
        for key in ('Uid', 'Gid', 'Groups'):
            rows = [line.split(':',1)[1].split() for line in raw.splitlines() if line.startswith(key+':')]
            _require(len(rows) == 1 and all(v.isascii() and v.isdecimal() for v in rows[0]), 'OWNER_STATUS')
            result[key] = tuple(int(v) for v in rows[0])
        _require(len(result['Uid']) == len(result['Gid']) == 4 and
                 result['Uid'][:3] == os.getresuid() and result['Gid'][:3] == os.getresgid() and
                 sorted(result['Groups']) == sorted(os.getgroups()), 'OWNER_STATUS')
        return result

    def _open(self, parent, name, *, directory=False, target_lookup=False):
        with self._attempt('OPEN_DIRECTORY' if directory else 'OPEN_FILE', name) as attempt:
            fd = self._acquire(parent, name, directory=directory, target_lookup=target_lookup)
            attempt['fd_identity'] = dict(self._identities[fd])
            return fd

    def _acquire(self, parent, name, *, directory=False, target_lookup=False):
        _require(type(name) is str and name not in {'', '..'} and '/' not in name, 'RELATIVE_COMPONENT')
        self._check(parent)
        try:
            fd = os.open(name, _DIR if directory else _FILE, dir_fd=parent)
        except FileNotFoundError as error:
            if target_lookup:
                raise _TargetNotFound(error.errno, 'TARGET_PROC_ENTRY') from error
            raise
        self._fds.add(fd)
        try:
            identity = self._describe(fd)
            _require(identity['fs_magic'] == 0x9FA0, 'NOT_PROCFS')
            _require(identity['mount_id'] == self._root_identity['mount_id'] and
                     identity['device'] == self._root_identity['device'], 'CROSS_MOUNT')
            _require(identity['kind'] == (stat.S_IFDIR if directory else stat.S_IFREG), 'FILE_KIND')
            _require(not os.get_inheritable(fd), 'FD_INHERITABLE')
            self._identities[fd] = identity
            return fd
        except BaseException as error:
            self._release(fd, error)
            raise

    def _read(self, parent, field, *, limit=_LIMIT, target_lookup=False):
        with self._attempt('READ', field) as attempt:
            fd = self._open(parent, field, target_lookup=target_lookup)
            with self._managed(fd):
                attempt['fd_identity'] = dict(self._identities[fd])
                raw = bytearray()
                while len(raw) <= limit:
                    part = os.read(fd, min(65536, limit + 1 - len(raw)))
                    if not part:
                        break
                    raw.extend(part)
                _require(len(raw) <= limit, 'READ_LIMIT')
                self._check(fd)
                return bytes(raw)

    def _stat_at(self, fd, pid, *, target_lookup=False):
        return _stat(self._read(fd, 'stat', limit=16384, target_lookup=target_lookup), pid)

    def _link(self, parent, field):
        """Read the held symlink itself, not an unchecked intermediate path."""
        with self._attempt('READLINK', field) as attempt:
            self._check(parent)
            try:
                fd = os.open(field, os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
            except FileNotFoundError as error:
                raise _LinkNotFound(error.errno, 'LINK_ENTRY') from error
            self._fds.add(fd)
            with self._managed(fd):
                identity = self._describe(fd)
                _require(identity['kind'] == stat.S_IFLNK and identity['fs_magic'] == 0x9FA0 and
                         identity['mount_id'] == self._root_identity['mount_id'] and
                         identity['device'] == self._root_identity['device'], 'LINK_CROSS_MOUNT')
                self._identities[fd] = identity
                attempt['fd_identity'] = dict(identity)
                result = self._native.link(fd)
                self._check(fd)
                _require(len(os.fsencode(result)) <= 16384, 'LINK_LIMIT')
                return result

    def _path_read(self, components):
        current = self._root
        with ExitStack() as stack:
            for name in components[:-1]:
                current = self._open(current, name, directory=True)
                stack.enter_context(self._managed(current))
            return self._read(current, components[-1])

    @_semantic('scope')
    def scope(self):
        """Endpoint acquisition only: no temporal-visibility/operating approval."""
        begin = _now()
        self._guard()
        value = {'kind': 'PROC_VIEW_ACQUISITION_V1', 'clock_id': 'CLOCK_BOOTTIME',
                 'acquisition_backend': self._backend,
                 'start_ns': begin, 'root': dict(self._root_identity),
                 'endpoint_checks_pass': False, 'errors': {},
                 'runtime_scope_confirmed': False, 'namespace_equality_proven': False,
                 'full_host_visibility_proven': False, 'temporal_visibility_proven': False,
                 'negative_pid_witness_allowed': False, 'policy_acceptance': False,
                 'legacy_fallback_allowed': False,
                 'admissibility': 'ACQUISITION_ONLY_NOT_POLICY_ADMISSIBLE',
                 'trust_assumptions': ['TRUSTED_SAME_PROCESS_FD_OWNERSHIP',
                    'NO_UNOBSERVED_PRIVILEGED_FILTER_OR_MOUNT_MUTATION',
                    'SUPPORTED_NATIVE_ABI', 'NO_ATOMIC_PROCESS_METADATA_ASSUMPTION']}
        try:
            value['owner'] = dict(self._self_identity)
            value['credentials'] = _credentials()
            value['owner_status'] = dict(self._status_identity)
            value['boot_sha256'] = hashlib.sha256(self._path_read(('sys','kernel','random','boot_id'))).hexdigest()
            value['uptime'] = self._read(self._root, 'uptime').decode('ascii').strip()
            namespace = self._open(self._self, 'ns', directory=True)
            with self._managed(namespace):
                value['mount_namespace'] = self._link(namespace, 'mnt')
                try:
                    value['pid_namespace'] = {'status': 'PRESENT', 'link': self._link(namespace, 'pid')}
                except _LinkNotFound as error:
                    value['pid_namespace'] = {'status': 'ENOENT', 'errno': error.errno}
                mount_namespace_end = self._link(namespace, 'mnt')
                try:
                    pid_namespace_end = {'status': 'PRESENT', 'link': self._link(namespace, 'pid')}
                except _LinkNotFound as error:
                    pid_namespace_end = {'status': 'ENOENT', 'errno': error.errno}
                _require(mount_namespace_end == value['mount_namespace'] and
                         pid_namespace_end == value['pid_namespace'], 'NAMESPACE_ENDPOINT_CHANGED')
            mountinfo = self._read(self._self, 'mountinfo').decode('utf-8', 'strict')
            value['mount'] = _mount(mountinfo, self._root_identity['mount_id'],
                [os.major(self._root_identity['device']), os.minor(self._root_identity['device'])])
            _require(self._read(self._self, 'mountinfo').decode('utf-8','strict') == mountinfo,
                     'MOUNT_ENDPOINT_CHANGED')
            _require(hashlib.sha256(self._path_read(('sys','kernel','random','boot_id'))).hexdigest() ==
                     value['boot_sha256'], 'BOOT_ENDPOINT_CHANGED')
            self._guard()
            value['endpoint_checks_pass'] = True
        except (OSError, ValueError, AcquisitionError) as error:
            value['errors']['scope'] = _error(error)
        value['end_ns'] = _now()
        return value

    @_semantic('mapping_identity')
    def mapping_identity(self):
        """Child-side record, private until carried by a separately owned pipe."""
        value = self.scope()
        _require(value['endpoint_checks_pass'], 'MAPPING_SCOPE_UNAVAILABLE')
        return {**self._self_identity, 'mount_id': self._root_identity['mount_id'],
                'root_device': self._root_identity['device'], 'root_inode': self._root_identity['inode'],
                'boot_sha256': value['boot_sha256'], 'mount_namespace': value['mount_namespace']}

    @_semantic('compare_child_mapping')
    def compare_child_mapping(self, child):
        """Compare mapping only. Never grants origin, ownership, wait or signal rights."""
        current = self.mapping_identity()
        value = {'mapping_matches': False, 'owned_child': False, 'signal_authority': False,
                 'record_origin_authenticated': False}
        if type(child) is not dict or set(child) != set(current):
            return value
        try:
            _pid(child['pid'])
            if (type(child['start_ticks']) is not int or child['start_ticks'] < 0 or
                type(child['ppid']) is not int or child['ppid'] != self._mapped_pid):
                return value
            fixed = set(current) - {'pid', 'ppid', 'start_ticks'}
            if any(type(child[k]) is not type(current[k]) or child[k] != current[k] for k in fixed):
                return value
            with self.generation(child['pid']) as actor:
                actual = actor.identity()
                value['mapping_matches'] = actual == {k: child[k] for k in ('pid','ppid','start_ticks')}
            self._guard()
        except (OSError, ValueError, AcquisitionError):
            value['mapping_matches'] = False
        return value

    @_semantic('enumerate')
    def enumerate(self):
        begin = _now()
        self._guard()
        with self._attempt('LIST', 'pid_list') as attempt:
            fd = self._open(self._root, '.', directory=True)
            with self._managed(fd):
                attempt['fd_identity'] = dict(self._identities[fd])
                names = os.listdir(fd)
                self._check(fd)
                pids = sorted(int(n) for n in names if n.isascii() and n.isdecimal() and int(n) > 0)
        self._guard()
        return {'pids': pids, 'start_ns': begin, 'end_ns': _now(),
                'pid_list_read': True, 'negative_pid_witness_allowed': False}

    def generation(self, pid):
        _pid(pid)
        self._guard()
        return Generation(self, pid)

    @_semantic('probe')
    def probe(self, pid):
        _pid(pid)
        begin = _now()
        self._guard()
        value = {'pid': pid, 'start_ns': begin, 'negative_pid_witness_allowed': False}
        try:
            with self.generation(pid) as actor:
                value.update(actor.identity(), status='PRESENT')
        except _TargetNotFound as error:
            value.update(status='NOT_FOUND', errno=error.errno)
        except (OSError, AcquisitionError) as error:
            value.update(status='UNREADABLE', errno=getattr(error, 'errno', None), error=type(error).__name__)
        self._guard()
        value['end_ns'] = _now()
        return value


class Generation:
    def __init__(self, view, pid):
        self._view, self._pid = view, pid
        self._closed = False
        self._fd = view._open(view._root, _pid(pid), directory=True, target_lookup=True)
        try:
            self._identity = view._stat_at(self._fd, pid, target_lookup=True)
        except BaseException as error:
            self.close(error)
            error.private_cleanup_errors = copy.deepcopy(view.cleanup_errors)
            raise

    def __enter__(self):
        try:
            self.identity()
            return self
        except BaseException as error:
            self.close(error)
            error.private_cleanup_errors = copy.deepcopy(self._view.cleanup_errors)
            raise

    def __exit__(self, kind, error, traceback):
        self.close(error)

    def close(self, primary=None):
        if not self._closed:
            self._closed = True
            self._view._release(self._fd, primary)

    @_semantic('identity')
    def identity(self):
        _require(not self._closed, 'GENERATION_CLOSED')
        self._view._guard()
        self._view._check(self._fd)
        value = self._view._stat_at(self._fd, self._pid)
        _require(value == self._identity, 'GENERATION_CHANGED')
        return dict(value)

    @_semantic('read')
    def read(self, field):
        if field not in {'stat', 'status', 'cmdline', 'cgroup'}:
            raise ValueError('FIELD')
        self.identity()
        raw = self._view._read(self._fd, field, limit=16384 if field == 'stat' else _LIMIT)
        self.identity()
        return raw

    @_semantic('link')
    def link(self, field):
        if field not in {'exe', 'cwd'}:
            raise ValueError('FIELD')
        self.identity()
        value = self._view._link(self._fd, field)
        self.identity()
        return value

    def _exe_target(self):
        before = self.link('exe')
        # Deliberate cross-filesystem exception: fixed exe only; O_PATH, no read.
        fd = os.open('exe', os.O_PATH | os.O_CLOEXEC, dir_fd=self._fd)
        self._view._fds.add(fd)
        with self._view._managed(fd):
            node = os.fstat(fd)
            value = {'link': before, 'device': node.st_dev, 'inode': node.st_ino,
                     'mode': node.st_mode, 'size': node.st_size}
        _require(self.link('exe') == before, 'EXECUTABLE_CHANGED')
        return value

    def _parent(self, pid):
        if pid == 0:
            return {'status': 'NO_PARENT_IN_VIEW'}
        with self._view.generation(pid) as parent:
            return parent.identity()

    @_semantic('metadata')
    def metadata(self):
        self._partial_metadata = {}
        try:
            return self._metadata()
        except (OSError, AcquisitionError) as error:
            error.private_partial = self._partial_metadata
            raise

    def _metadata(self):
        begin = _now()
        before = self.identity()
        value = {'identity': before, 'fields': {}, 'errors': {}, 'atomic_snapshot': False,
                 'acquisition_backend': self._view._backend,
                 'scheme': 'DIRFD', 'root': dict(self._view._root_identity),
                 'parent': {}, 'start_ns': begin}
        self._partial_metadata = value
        def attempt(name, callback):
            try:
                return callback()
            except OSError as error:
                value['errors'][name] = _error(error)
                return None
        value['parent']['before'] = attempt('parent_before', lambda: self._parent(before['ppid']))
        executable = attempt('exe_before', self._exe_target)
        command = attempt('cmdline_before', lambda: self.read('cmdline'))
        value['fields']['cmdline'] = command
        for field in ('status', 'cgroup'):
            value['fields'][field] = attempt(field, lambda f=field: self.read(f))
        value['fields']['cwd'] = attempt('cwd', lambda: self.link('cwd'))
        command_after = attempt('cmdline_after', lambda: self.read('cmdline'))
        _require(command == command_after, 'CMDLINE_CHANGED')
        value['command_stable_endpoints'] = command is not None and not any(k.startswith('cmdline_') for k in value['errors'])
        after_exe = attempt('exe_after', self._exe_target)
        _require(executable == after_exe, 'EXECUTABLE_CHANGED')
        value['exe_target'] = {'observation': executable,
                               'stable_endpoints': executable is not None and not any(k.startswith('exe_') for k in value['errors'])}
        value['parent']['after'] = attempt('parent_after', lambda: self._parent(before['ppid']))
        _require(value['parent']['before'] == value['parent']['after'], 'PARENT_GENERATION_CHANGED')
        value['parent_generation_bracket_pass'] = (before['ppid'] > 0 and value['parent']['before'] is not None and
            not any(k.startswith('parent_') for k in value['errors']))
        self.identity()
        value['end_ns'] = _now()
        return value


def _error(error):
    value = {'type': type(error).__name__, 'errno': getattr(error, 'errno', None)}
    if isinstance(error, (AcquisitionError, _Reject)):
        value['reason'] = str(error)
    return value
