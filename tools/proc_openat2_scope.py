"""PRIVATE offline endpoint scope candidate, never a ProcView/policy provider.

One continuously held local lease covers bootstrap and all endpoint reads.
No previous closed bootstrap certificate can authenticate this inspection.
The fixed native opener, lifetime helpers and strict validators are reused
unchanged. Broader process/namespace/temporal authority is never granted.
"""
import errno
import hashlib
import os

from tools.pinned_proc_view import _now, _stat
from tools.proc_openat2_bootstrap import (
    BootstrapError, NativeOpenat2, _DIR, _Lease, _require,
)
from tools.proc_view_scope_model import _mount


class _LeafOpenNotFound(FileNotFoundError):
    """Only the native component-open operation returned ENOENT."""


class _OpenOrigin:
    """Tag open errors before lease validation; never reinterpret other errors.

    The frozen lease's opened() includes pre/post checks and retain validation.
    Catching FileNotFoundError around that whole method would misclassify a
    validation failure as an absent leaf. This adapter marks only the native
    opener boundary, leaving filesystem/identity/readlink errors untouched.
    """
    def __init__(self, native):
        self.native = native

    def open_component(self, parent, name, kind):
        try:
            return self.native.open_component(parent, name, kind)
        except FileNotFoundError as error:
            if error.errno == errno.ENOENT:
                raise _LeafOpenNotFound(errno.ENOENT, 'NATIVE_COMPONENT_NOT_FOUND') from error
            raise

    def filesystem_magic(self, fd):
        return self.native.filesystem_magic(fd)

    def link(self, fd):
        return self.native.link(fd)


def _path_read(lease, root, components):
    current, directories = root, []
    for name in components[:-1]:
        current = lease.opened(current, name, 'directory')
        directories.append(current)
    raw = lease.read(current, components[-1])
    # On any error outer cleanup owns all remaining descriptors. Do not hide a
    # read error by trying nested finally closes that might themselves fail.
    for fd in reversed(directories):
        lease.release(fd)
    return raw


def _link(lease, parent, name, *, optional=False):
    try:
        fd = lease.opened(parent, name, 'link')
    except _LeafOpenNotFound as error:
        # This handler covers only the exact protected leaf open. In particular
        # neither the ns directory nor readlinkat can be laundered into absence.
        if optional and name == 'pid' and error.errno == errno.ENOENT:
            return {'status': 'ENOENT', 'errno': errno.ENOENT}
        raise
    text = lease.native.link(fd)
    lease.check(fd)
    lease.release(fd)
    return {'status': 'PRESENT', 'link': text}


def _inspect(lease, root):
    begin = _now()
    anchor = lease.retain(os.open('/', _DIR), 'directory', proc=False)
    parts = root.split('/')[1:]
    # The native root has only / as its parent. Additional fixture parents are
    # ordinary controlled files and never get a native-origin evidence label.
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
    owner_before = _stat(lease.read(owner, 'stat'), lease.owner[0])
    status_before = lease.status(owner)
    persistent = [proc, self_link, owner, fdinfo]
    mount_id = lease.mount_id(fdinfo, proc)
    _require(all(lease.mount_id(fdinfo, fd) == mount_id for fd in persistent[1:]),
             'MOUNT_ID_CHANGED')

    # Same scope rules as frozen ProcView.scope, with protected reader origins
    # and the intentionally narrower 16KiB bound inherited from the N lease.
    boot = hashlib.sha256(_path_read(lease, proc, ('sys', 'kernel', 'random', 'boot_id'))).hexdigest()
    uptime = lease.read(proc, 'uptime').decode('ascii', 'strict').strip()
    namespace = lease.opened(owner, 'ns', 'directory')
    mount_namespace = _link(lease, namespace, 'mnt')['link']
    pid_namespace = _link(lease, namespace, 'pid', optional=True)
    mount_namespace_end = _link(lease, namespace, 'mnt')['link']
    pid_namespace_end = _link(lease, namespace, 'pid', optional=True)
    _require(mount_namespace == mount_namespace_end and pid_namespace == pid_namespace_end,
             'NAMESPACE_ENDPOINT_CHANGED')
    lease.release(namespace)
    mountinfo = lease.read(owner, 'mountinfo').decode('utf-8', 'strict')
    mount = _mount(mountinfo, mount_id,
                   [os.major(lease.root_device), os.minor(lease.root_device)])
    _require(lease.read(owner, 'mountinfo').decode('utf-8', 'strict') == mountinfo,
             'MOUNT_ENDPOINT_CHANGED')
    _require(hashlib.sha256(_path_read(lease, proc, ('sys', 'kernel', 'random', 'boot_id'))).hexdigest() == boot,
             'BOOT_ENDPOINT_CHANGED')

    # Neither a held old root nor a closed earlier bootstrap can replace these
    # fresh owner, named-root and persistent-target checks in this same lease.
    _require(_stat(lease.read(owner, 'stat'), lease.owner[0]) == owner_before,
             'OWNER_GENERATION_CHANGED')
    _require(lease.status(owner) == status_before, 'OWNER_STATUS_CHANGED')
    _require(lease.native.link(self_link) == str(lease.owner[0]), 'OWNER_MAPPING')
    _require(all(lease.mount_id(fdinfo, fd) == mount_id for fd in persistent),
             'MOUNT_ID_CHANGED')
    lease.check(anchor)
    named = lease.retain(os.open(parts[-1], _DIR, dir_fd=anchor), 'directory')
    _require(lease.identities[named] == lease.identities[proc] and
             lease.mount_id(fdinfo, named) == mount_id, 'NAMED_ROOT_CHANGED')
    for fd in lease.fds:
        lease.check(fd)

    return {'kind': 'OPENAT2_ENDPOINT_SCOPE_V1', 'clock_id': 'CLOCK_BOOTTIME',
            'acquisition_backend': ('INJECTED_OPENAT2_SCOPE_ONLY' if lease.injected
                                    else 'NATIVE_OPENAT2_SCOPE_ONLY'),
            'start_ns': begin, 'end_ns': _now(), 'endpoint_checks_pass': True,
            'root': {**lease.identities[proc], 'fs_magic': 0x9FA0, 'mount_id': mount_id},
            'owner': owner_before, 'owner_status': status_before,
            'credentials': lease.owner[2], 'boot_sha256': boot, 'uptime': uptime,
            'mount_namespace': mount_namespace, 'pid_namespace': pid_namespace,
            'mount': mount, 'lease_closed': True, 'full_ProcView_interface': False,
            'restricted_open_count': lease.open_count, 'read_call_count': lease.read_count,
            'reader_origins': lease.origins, 'runtime_scope_confirmed': False,
            'namespace_equality_proven': False, 'full_host_visibility_proven': False,
            'temporal_visibility_proven': False, 'negative_pid_witness_allowed': False,
            'policy_acceptance': False, 'legacy_fallback_allowed': False,
            'lifetime_acceptance': False,
            'trust_assumptions': ['TRUSTED_NATIVE_BINDINGS', 'EXCLUSIVE_SAME_PROCESS_FD_OWNERSHIP',
                                  'NO_UNOBSERVED_PRIVILEGED_MOUNT_OR_FILTER_ABA',
                                  'NO_UNOBSERVED_NATIVE_THREAD_INTERFERENCE']}


def inspect_protected_scope(root='/proc', *, _native=None):
    """One PRIVATE local scope inspection; errors raise, all authority false.

    Reuses fixed N bounds (64 opens/4096 reads/16KiB per file). A large mountinfo
    may therefore reject; it is not truncated or accepted under a weaker gate.
    No writer, subprocess, observer, journal, payload or device dispatcher.
    """
    root = os.fspath(root)
    injected = _native is not None
    _require(root == '/proc' or injected, 'FIXTURE_ROOT')
    _require(type(root) is str and root.startswith('/') and
             all(part not in {'', '.', '..'} for part in root.split('/')[1:]), 'ROOT_PATH')
    lease = _Lease(_OpenOrigin(_native if injected else NativeOpenat2()), injected)
    primary = None
    try:
        result = _inspect(lease, root)
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
