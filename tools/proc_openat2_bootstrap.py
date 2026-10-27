"""Bounded PRIVATE local origin experiment; no provider, dispatcher or policy API.

The independent premise is kernel-enforced noncrossing for *every* component
below a held procfs root. fdinfo bytes do not authenticate their own reader.
Requires trusted native bindings, exclusive same-process FD ownership and no
unobserved privileged mount/filter ABA or native-thread interference. A closed
bootstrap lease proves neither a complete view nor subsequent observations.
"""
import ctypes
import fcntl
import os
import stat
import threading

from tools.pinned_proc_view import NativeLinux, _credentials, _stat
from tools.proc_view_scope_model import _fd_mount_id, _fd_value


RESOLVE_GUARDS = 0x01 | 0x02 | 0x04 | 0x08
_DIR = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
_FLAGS = {'directory': _DIR, 'file': os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC,
          'link': os.O_PATH | os.O_NOFOLLOW | os.O_CLOEXEC}
_KINDS = {'directory': stat.S_IFDIR, 'file': stat.S_IFREG, 'link': stat.S_IFLNK}
_READ_LIMIT = 16384
_OPEN_LIMIT = 64
_READ_CALL_LIMIT = 4096


class BootstrapError(RuntimeError):
    pass


def _require(condition, reason):
    if not condition:
        raise BootstrapError(reason)


class _OpenHow(ctypes.Structure):
    _fields_ = [('flags', ctypes.c_uint64), ('mode', ctypes.c_uint64),
                ('resolve', ctypes.c_uint64)]


class NativeOpenat2:
    """Linux glibc LP64 little-endian x86_64/aarch64 only; no weaker fallback.

    NativeLinux checks that ABI and supplies fstatfs/readlinkat. Its statx symbol
    is still a constructor dependency, but describe/statx is never called here.
    Number 437 and open_how24 are pinned to Linux v5.6 UAPI for these ABIs.
    """
    def __init__(self):
        self._legacy = NativeLinux()
        _require(ctypes.sizeof(_OpenHow) == 24 and _OpenHow.mode.offset == 8 and
                 _OpenHow.resolve.offset == 16, 'UNSUPPORTED_OPEN_HOW')
        self._library = ctypes.CDLL(None, use_errno=True)
        self._syscall = self._library.syscall
        self._syscall.restype = ctypes.c_long

    def open_component(self, parent, name, kind):
        _require(type(parent) is int and 0 <= parent <= 2**31 - 1, 'PARENT_FD')
        _require(type(name) is str and name not in {'', '.', '..'} and
                 '/' not in name and '\0' not in name and name.isascii(), 'COMPONENT')
        _require(kind in _FLAGS, 'OPEN_KIND')
        how = _OpenHow(_FLAGS[kind], 0, RESOLVE_GUARDS)
        fd = self._syscall(ctypes.c_long(437), ctypes.c_int(parent),
                           ctypes.c_char_p(name.encode('ascii')), ctypes.byref(how),
                           ctypes.c_size_t(ctypes.sizeof(how)))
        if fd < 0:
            raise OSError(ctypes.get_errno(), 'OPENAT2_COMPONENT')
        return int(fd)

    def filesystem_magic(self, fd):
        fs = self._legacy._statfs()
        if self._legacy._fs(fd, ctypes.byref(fs)) != 0:
            raise OSError(ctypes.get_errno(), 'FSTATFS')
        return fs.words[0]

    def link(self, fd):
        return self._legacy.link(fd)


def _identity(fd):
    node = os.fstat(fd)
    return {'device': node.st_dev, 'inode': node.st_ino, 'kind': stat.S_IFMT(node.st_mode),
            'flags': fcntl.fcntl(fd, fcntl.F_GETFL),
            'descriptor_flags': fcntl.fcntl(fd, fcntl.F_GETFD)}


def _owner():
    _require(threading.get_native_id() == os.getpid() and threading.active_count() == 1,
             'THREAD_PROFILE')
    return os.getpid(), threading.get_ident(), _credentials()


class _Lease:
    def __init__(self, native, injected):
        self.native, self.injected = native, injected
        self.fds, self.identities, self.origins = [], {}, []
        self.open_count, self.read_count = 0, 0
        self.owner = _owner()
        self.root_device = None

    def guard(self):
        _require(_owner() == self.owner, 'OWNER_CHANGED')

    def retain(self, fd, kind, proc=True):
        # Register ownership before any operation that can reject this new FD.
        _require(type(fd) is int and fd >= 0 and fd not in self.identities, 'FD_OWNERSHIP')
        self.fds.append(fd)
        identity = _identity(fd)
        self.identities[fd] = identity
        _require(identity['kind'] == _KINDS[kind], 'FD_KIND')
        expected = _FLAGS[kind] & ~os.O_CLOEXEC
        _require(identity['flags'] & expected == expected and
                 identity['flags'] & ~(expected | 0o100000) == 0 and
                 identity['descriptor_flags'] == fcntl.FD_CLOEXEC, 'FD_FLAGS')
        if proc:
            _require(self.native.filesystem_magic(fd) == 0x9FA0, 'NOT_PROCFS')
            if self.root_device is not None:
                _require(identity['device'] == self.root_device, 'PROC_DEVICE')
        return fd

    def check(self, fd):
        self.guard()
        _require(fd in self.identities and _identity(fd) == self.identities[fd],
                 'FD_IDENTITY_CHANGED')

    def opened(self, parent, name, kind):
        self.check(parent)
        _require(self.open_count < _OPEN_LIMIT, 'OPEN_LIMIT')
        self.open_count += 1
        fd = self.native.open_component(parent, name, kind)
        self.retain(fd, kind)
        self.check(parent)
        self.origins.append({'parent_fd': parent, 'name': name, 'fd': fd,
                             'identity': dict(self.identities[fd]),
                             'resolve': RESOLVE_GUARDS, 'native_origin': not self.injected})
        return fd

    def release(self, fd):
        # close is attempted once: retry after EINTR can close a reused FD.
        self.fds.remove(fd)
        # fstat/fcntl can fail after ownership registration but before identity
        # insertion. That FD still needs its single close attempt.
        self.identities.pop(fd, None)
        try:
            os.close(fd)
        except OSError as error:
            failure = BootstrapError('CLEANUP_FAILED')
            failure.private_cleanup_errors = [{'reason': 'CLOSE', 'errno': error.errno}]
            raise failure from error

    def read(self, parent, name):
        fd = self.opened(parent, name, 'file')
        raw = bytearray()
        # On failure the outer finally attempts this and every other owned FD.
        while True:
            self.check(fd)
            _require(self.read_count < _READ_CALL_LIMIT, 'READ_CALL_LIMIT')
            self.read_count += 1
            part = os.read(fd, min(4096, _READ_LIMIT + 1 - len(raw)))
            self.check(fd)
            raw.extend(part)
            _require(len(raw) <= _READ_LIMIT, 'READ_LIMIT')
            if not part:
                break
        self.release(fd)
        return bytes(raw)

    def status(self, owner_fd):
        text = self.read(owner_fd, 'status').decode('ascii', 'strict')
        result = {}
        for key in ('Uid', 'Gid', 'Groups'):
            rows = [line.split(':', 1)[1].split() for line in text.splitlines()
                    if line.startswith(key + ':')]
            _require(len(rows) == 1 and all(x.isascii() and x.isdecimal() for x in rows[0]),
                     'OWNER_STATUS')
            result[key] = tuple(map(int, rows[0]))
        uid, gid, groups = self.owner[2]
        _require(len(result['Uid']) == len(result['Gid']) == 4 and
                 result['Uid'][:3] == uid and result['Gid'][:3] == gid and
                 sorted(result['Groups']) == list(groups), 'OWNER_STATUS')
        return result

    def mount_id(self, directory, target):
        self.check(target)
        raw = self.read(directory, str(target)).decode('ascii', 'strict')
        lines = raw.splitlines()
        _require(lines and all(line.count(':') == 1 and line.split(':')[0] in
                              {'pos', 'flags', 'mnt_id', 'ino'} for line in lines), 'FDINFO_FIELDS')
        position = _fd_value(raw, 'pos')
        _require(position.isascii() and position.isdecimal(), 'FDINFO_POSITION')
        flags = _fd_value(raw, 'flags')
        _require(flags and all(c in '01234567' for c in flags), 'FDINFO_FLAGS')
        self.check(target)
        actual = self.identities[target]
        _require(int(flags, 8) == actual['flags'] | os.O_CLOEXEC, 'FDINFO_FLAGS')
        inode = _fd_value(raw, 'ino', required=False)
        if inode is not None:
            _require(inode.isascii() and inode.isdecimal() and
                     int(inode) == actual['inode'], 'FDINFO_INODE')
        return _fd_mount_id(raw)

    def close(self):
        errors = []
        for fd in reversed(self.fds[:]):
            try:
                self.release(fd)
            except BootstrapError as error:
                errors.extend(error.private_cleanup_errors)
        return errors


def bootstrap_procfs_origin(root='/proc', *, _native=None):
    """Return PRIVATE closed-lease origin evidence; never operational acceptance.

    _native/custom root are controlled local fixture injection, not a native
    proof. All errors reject without retry or weaker opens. No subprocesses,
    journal, filesystem writer, device connection or existing provider changes.
    """
    injected = _native is not None
    root = os.fspath(root)
    _require(root == '/proc' or injected, 'FIXTURE_ROOT')
    _require(type(root) is str and root.startswith('/') and
             all(p not in {'', '.', '..'} for p in root.split('/')[1:]), 'ROOT_PATH')
    lease = _Lease(_native if injected else NativeOpenat2(), injected)
    primary = None
    try:
        # Only named-root acquisition may cross a mount. Fixture parents are
        # ordinary local paths and never labelled native proc-origin evidence.
        anchor = lease.retain(os.open('/', _DIR), 'directory', proc=False)
        parts = root.split('/')[1:]
        for part in parts[:-1]:
            child = lease.retain(os.open(part, _DIR, dir_fd=anchor), 'directory', proc=False)
            lease.release(anchor)
            anchor = child
        proc = lease.retain(os.open(parts[-1], _DIR, dir_fd=anchor), 'directory')
        lease.root_device = lease.identities[proc]['device']
        self_link = lease.opened(proc, 'self', 'link')
        _require(lease.native.link(self_link) == str(lease.owner[0]), 'OWNER_MAPPING')
        lease.check(self_link)
        owner = lease.opened(proc, str(lease.owner[0]), 'directory')
        fdinfo = lease.opened(owner, 'fdinfo', 'directory')
        before_stat = _stat(lease.read(owner, 'stat'), lease.owner[0])
        before_status = lease.status(owner)
        targets = [proc, self_link, owner, fdinfo]
        mount_id = lease.mount_id(fdinfo, proc)
        _require(all(lease.mount_id(fdinfo, fd) == mount_id for fd in targets[1:]), 'MOUNT_ID_CHANGED')
        lease.check(anchor)
        named = lease.retain(os.open(parts[-1], _DIR, dir_fd=anchor), 'directory')
        _require(lease.identities[named] == lease.identities[proc] and
                 lease.mount_id(fdinfo, named) == mount_id, 'NAMED_ROOT_CHANGED')
        _require(_stat(lease.read(owner, 'stat'), lease.owner[0]) == before_stat,
                 'OWNER_GENERATION_CHANGED')
        _require(lease.status(owner) == before_status, 'OWNER_STATUS_CHANGED')
        for fd in lease.fds:
            lease.check(fd)
        result = {'origin_supported': True,
                  'evidence_kind': 'INJECTED_FIXTURE' if injected else 'NATIVE_LOCAL_PROCFS',
                  'root': {**lease.identities[proc], 'mount_id': mount_id},
                  'named_root_verified': True, 'restricted_open_count': lease.open_count,
                  'read_call_count': lease.read_count, 'reader_origins': lease.origins,
                  'root_lease_closed': True, 'full_scope_checked': False,
                  'runtime_scope_confirmed': False, 'namespace_equality_proven': False,
                  'full_host_visibility_proven': False, 'temporal_visibility_proven': False,
                  'negative_pid_witness_allowed': False, 'policy_acceptance': False,
                  'legacy_fallback_allowed': False}
    except BaseException as error:
        primary = error
        raise
    finally:
        errors = lease.close()
        if errors:
            if primary is not None:
                primary.private_cleanup_errors = getattr(primary, 'private_cleanup_errors', []) + errors
            else:
                failure = BootstrapError('CLEANUP_FAILED')
                failure.private_cleanup_errors = errors
                raise failure
    return result
