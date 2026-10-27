"""Local/native and explicitly injected tests; never actual comma validation."""
import ctypes
import errno
import fcntl
import os
from pathlib import Path
import stat

import pytest

from tools.proc_openat2_bootstrap import (
    BootstrapError, NativeOpenat2, RESOLVE_GUARDS, bootstrap_procfs_origin,
)
from tools.pinned_proc_view import NativeLinux


def stat_text(pid, start=500):
    return f'{pid} (bootstrap fixture) S 1 ' + ' '.join(['0'] * 17 + [str(start)]) + '\n'


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / 'proc'
    owner = root / str(os.getpid())
    (owner / 'fdinfo').mkdir(parents=True)
    (root / 'self').symlink_to(str(os.getpid()))
    (owner / 'stat').write_text(stat_text(os.getpid()))
    (owner / 'status').write_text(
        'Uid:\t' + ' '.join(map(str, (*os.getresuid(), os.geteuid()))) + '\n'
        'Gid:\t' + ' '.join(map(str, (*os.getresgid(), os.getegid()))) + '\n'
        'Groups:\t' + ' '.join(map(str, os.getgroups())) + '\n'
    )
    return root


class FixtureNative:
    """Ordinary opens are confined to controlled local fixtures, never native evidence."""
    def __init__(self):
        self.calls = []
        self.mutate_record = lambda name, raw: raw
        self.after_open = lambda name, fd: None

    def filesystem_magic(self, fd):
        return 0x9FA0

    def link(self, fd):
        return NativeLinux().link(fd)

    def open_component(self, parent, name, kind):
        self.calls.append((parent, name, kind))
        directory = Path(os.readlink(f'/proc/self/fd/{parent}'))
        if directory.name == 'fdinfo':
            target = int(name)
            node = os.fstat(target)
            flags = fcntl.fcntl(target, fcntl.F_GETFL) | os.O_CLOEXEC
            raw = f'pos:\t0\nflags:\t0{flags:o}\nmnt_id:\t41\nino:\t{node.st_ino}\n'
            (directory / name).write_text(self.mutate_record(name, raw))
        flags = {'directory': os.O_RDONLY | os.O_DIRECTORY,
                 'file': os.O_RDONLY, 'link': os.O_PATH}[kind]
        fd = os.open(name, flags | os.O_NOFOLLOW | os.O_CLOEXEC, dir_fd=parent)
        self.after_open(name, fd)
        return fd


def no_authority(value):
    assert value['root_lease_closed'] is True and value['full_scope_checked'] is False
    for key in ('runtime_scope_confirmed', 'namespace_equality_proven',
                'full_host_visibility_proven', 'temporal_visibility_proven',
                'negative_pid_witness_allowed', 'policy_acceptance',
                'legacy_fallback_allowed'):
        assert value[key] is False


def test_injected_finite_bootstrap_is_not_native_or_policy_evidence(tree):
    native = FixtureNative()
    before = set(os.listdir('/proc/self/fd'))
    value = bootstrap_procfs_origin(tree, _native=native)
    assert value['origin_supported'] is True
    assert value['evidence_kind'] == 'INJECTED_FIXTURE'
    assert value['root']['mount_id'] == 41
    assert value['named_root_verified'] is True
    assert value['restricted_open_count'] == len(native.calls)
    assert value['reader_origins'] and all(row['resolve'] == RESOLVE_GUARDS for row in value['reader_origins'])
    assert set(os.listdir('/proc/self/fd')) == before
    no_authority(value)


def test_real_local_bootstrap_matches_independent_statx_oracle_without_using_it(monkeypatch):
    fd = os.open('/proc', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        expected = NativeLinux().describe(fd)['mount_id']
    finally:
        os.close(fd)
    monkeypatch.setattr(NativeLinux, 'describe', lambda *_: pytest.fail('candidate used statx'))
    before = set(os.listdir('/proc/self/fd'))
    value = bootstrap_procfs_origin()
    assert value['evidence_kind'] == 'NATIVE_LOCAL_PROCFS'
    assert value['root']['mount_id'] == expected
    assert all(row['native_origin'] is True for row in value['reader_origins'])
    assert set(os.listdir('/proc/self/fd')) == before
    no_authority(value)


def test_native_open_rejects_existing_cross_mount_without_creating_one():
    native = NativeOpenat2()
    fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        with pytest.raises(OSError) as failure:
            native.open_component(fd, 'proc', 'directory')
        assert failure.value.errno == errno.EXDEV
    finally:
        os.close(fd)


def test_native_final_opath_link_is_held_without_traversal(tmp_path):
    (tmp_path / 'target').write_text('private local fixture')
    (tmp_path / 'link').symlink_to('target')
    fd = os.open(tmp_path, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    native = NativeOpenat2()
    try:
        with pytest.raises(OSError) as failure:
            native.open_component(fd, 'link', 'file')
        assert failure.value.errno == errno.ELOOP
        held = native.open_component(fd, 'link', 'link')
        try:
            assert stat.S_ISLNK(os.fstat(held).st_mode)
            assert native.link(held) == 'target'
        finally:
            os.close(held)
    finally:
        os.close(fd)


@pytest.mark.parametrize('name', ['', '.', '..', '../stat', '/proc', 'a/b', 'x\0y'])
def test_component_validation_precedes_the_syscall(name):
    native = NativeOpenat2()
    native._syscall = lambda *_: pytest.fail('invalid component reached syscall')
    with pytest.raises((BootstrapError, ValueError)):
        native.open_component(1, name, 'file')


@pytest.mark.parametrize('number', [errno.ENOSYS, errno.EINVAL, errno.EPERM, errno.EXDEV, errno.EAGAIN])
def test_native_errors_preserve_fixed_guards_and_do_not_retry(number):
    native = NativeOpenat2()
    calls = []
    def failure(number_arg, parent, name, how, size):
        calls.append((number_arg.value, parent.value, name.value, how._obj.flags, how._obj.mode, how._obj.resolve, size.value))
        ctypes.set_errno(number)
        return -1
    native._syscall = failure
    with pytest.raises(OSError) as failed:
        native.open_component(3, 'stat', 'file')
    assert failed.value.errno == number
    assert calls == [(437, 3, b'stat', os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC, 0, 15, 24)]


@pytest.mark.parametrize('component', ['self', 'fdinfo', 'stat', 'status'])
def test_intermediate_or_leaf_exdev_is_not_bypassed(tree, component):
    native = FixtureNative()
    original = native.open_component
    def denied(parent, name, kind):
        if name == component:
            raise OSError(errno.EXDEV, 'fixture mount boundary')
        return original(parent, name, kind)
    native.open_component = denied
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(OSError) as failed:
        bootstrap_procfs_origin(tree, _native=native)
    assert failed.value.errno == errno.EXDEV
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('transform', [
    lambda raw: raw.replace('mnt_id:\t41\n', ''),
    lambda raw: raw + 'mnt_id:\t41\n',
    lambda raw: raw.replace('mnt_id:\t41', 'mnt_id:\t0'),
    lambda raw: raw.replace('mnt_id:\t41', 'mnt_id:\t-1'),
    lambda raw: raw.replace('mnt_id:\t41', 'mnt_id:\tbogus'),
    lambda raw: raw.replace('flags:\t0', 'flags:\t7'),
    lambda raw: raw + 'unreviewed:\t1\n',
    lambda raw: raw.replace('ino:\t', 'ino:\t999'),
])
def test_malformed_or_substituted_fdinfo_rejects_and_closes(tree, transform):
    native = FixtureNative()
    native.mutate_record = lambda name, raw: transform(raw)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises((BootstrapError, ValueError)):
        bootstrap_procfs_origin(tree, _native=native)
    assert set(os.listdir('/proc/self/fd')) == before


def test_optional_old_kernel_inode_field_does_not_remove_native_identity_checks(tree):
    native = FixtureNative()
    native.mutate_record = lambda name, raw: '\n'.join(line for line in raw.splitlines() if not line.startswith('ino:')) + '\n'
    value = bootstrap_procfs_origin(tree, _native=native)
    assert value['root']['mount_id'] == 41
    no_authority(value)


def test_wrong_owner_mapping_rejects_before_pid_directory_reads(tree):
    (tree / 'self').unlink()
    (tree / 'self').symlink_to(str(os.getpid() + 1000))
    with pytest.raises(BootstrapError, match='OWNER_MAPPING'):
        bootstrap_procfs_origin(tree, _native=FixtureNative())


def test_nonproc_filesystem_rejects_before_reader_bootstrap(tree):
    native = FixtureNative()
    native.filesystem_magic = lambda fd: 0xEF53
    with pytest.raises(BootstrapError, match='NOT_PROCFS'):
        bootstrap_procfs_origin(tree, _native=native)
    assert native.calls == []


def test_native_custom_root_is_not_an_implicit_fixture(tmp_path):
    with pytest.raises(BootstrapError, match='FIXTURE_ROOT'):
        bootstrap_procfs_origin(tmp_path)


def test_oversized_owner_stat_rejects_without_leaking(tree):
    (tree / str(os.getpid()) / 'stat').write_bytes(b'x' * 16385)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='READ_LIMIT'):
        bootstrap_procfs_origin(tree, _native=FixtureNative())
    assert set(os.listdir('/proc/self/fd')) == before


def test_partial_reads_are_accumulated_within_the_budget(tree, monkeypatch):
    import tools.proc_openat2_bootstrap as module
    original = module.os.read
    monkeypatch.setattr(module.os, 'read', lambda fd, count: original(fd, min(count, 7)))
    value = bootstrap_procfs_origin(tree, _native=FixtureNative())
    assert value['origin_supported'] is True
    no_authority(value)


def test_close_failure_cannot_return_success_and_other_fds_are_attempted(tree, monkeypatch):
    import tools.proc_openat2_bootstrap as module
    original = module.os.close
    calls = []
    def close_then_fail_once(fd):
        original(fd)
        calls.append(fd)
        if len(calls) == 1:
            raise OSError(errno.EIO, 'fixture close failure')
    monkeypatch.setattr(module.os, 'close', close_then_fail_once)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='CLEANUP_FAILED'):
        bootstrap_procfs_origin(tree, _native=FixtureNative())
    assert len(calls) > 1 and set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('field', ['cloexec', 'status_flags'])
def test_owned_fd_flag_drift_is_rejected(tree, field):
    native = FixtureNative()
    def change(name, fd):
        if name == 'self':
            if field == 'cloexec':
                os.set_inheritable(fd, True)
        if name == 'fdinfo' and field == 'status_flags':
            fcntl.fcntl(fd, fcntl.F_SETFL, fcntl.fcntl(fd, fcntl.F_GETFL) | os.O_NONBLOCK)
    native.after_open = change
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='FD_FLAGS'):
        bootstrap_procfs_origin(tree, _native=native)
    assert set(os.listdir('/proc/self/fd')) == before


def test_live_parent_fd_replacement_is_rejected(tree):
    native = FixtureNative()
    original = native.open_component
    def replace(parent, name, kind):
        child = original(parent, name, kind)
        if name == 'fdinfo':
            replacement = os.open(tree, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC)
            try:
                os.dup2(replacement, parent, inheritable=False)
            finally:
                os.close(replacement)
        return child
    native.open_component = replace
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='FD_IDENTITY_CHANGED'):
        bootstrap_procfs_origin(tree, _native=native)
    assert set(os.listdir('/proc/self/fd')) == before


def test_owner_generation_change_is_rejected(tree):
    native = FixtureNative()
    seen = []
    def change(name, fd):
        if name == 'stat':
            seen.append(fd)
            if len(seen) == 2:
                (tree / str(os.getpid()) / 'stat').write_text(stat_text(os.getpid(), 501))
    native.after_open = change
    with pytest.raises(BootstrapError, match='OWNER_GENERATION_CHANGED'):
        bootstrap_procfs_origin(tree, _native=native)


def test_owner_full_status_change_is_rejected(tree):
    native = FixtureNative()
    seen = []
    def change(name, fd):
        if name == 'status':
            seen.append(fd)
            if len(seen) == 2:
                path = tree / str(os.getpid()) / 'status'
                rows = path.read_text().splitlines()
                values = rows[0].split()
                values[-1] = str(int(values[-1]) + 1)
                rows[0] = 'Uid:\t' + ' '.join(values[1:])
                path.write_text('\n'.join(rows) + '\n')
    native.after_open = change
    with pytest.raises(BootstrapError, match='OWNER_STATUS_CHANGED'):
        bootstrap_procfs_origin(tree, _native=native)


def test_named_root_replacement_is_rejected(tree, monkeypatch):
    import tools.proc_openat2_bootstrap as module
    original = module.os.open
    seen = []
    other = tree.parent / 'other'
    other.mkdir()
    def replaced(path, flags, *args, **kwargs):
        if path == tree.name:
            seen.append(path)
            if len(seen) == 2:
                return original(other, flags)
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(module.os, 'open', replaced)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='NAMED_ROOT_CHANGED'):
        bootstrap_procfs_origin(tree, _native=FixtureNative())
    assert set(os.listdir('/proc/self/fd')) == before


def test_different_target_mount_id_rejects(tree):
    native = FixtureNative()
    native.mutate_record = lambda name, raw: raw if os.readlink(f'/proc/self/fd/{name}') == str(tree) else raw.replace('41', '42', 1)
    with pytest.raises(BootstrapError, match='MOUNT_ID_CHANGED'):
        bootstrap_procfs_origin(tree, _native=native)


@pytest.mark.parametrize('bound', ['_OPEN_LIMIT', '_READ_CALL_LIMIT'])
def test_operation_budget_is_enforced_and_fds_close(tree, monkeypatch, bound):
    import tools.proc_openat2_bootstrap as module
    monkeypatch.setattr(module, bound, 1)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='LIMIT'):
        bootstrap_procfs_origin(tree, _native=FixtureNative())
    assert set(os.listdir('/proc/self/fd')) == before


def test_primary_failure_is_preserved_with_cleanup_diagnostic(tree, monkeypatch):
    import tools.proc_openat2_bootstrap as module
    native = FixtureNative()
    native.open_component = lambda *_: (_ for _ in ()).throw(OSError(errno.EXDEV, 'primary'))
    original = module.os.close
    def broken(fd):
        original(fd)
        raise OSError(errno.EIO, 'secondary')
    # Do not fail a fixture ancestor close before the deliberate primary.
    ordinary = module._Lease.release
    def selectively_broken(self, fd):
        if self.root_device is not None:
            monkeypatch.setattr(module.os, 'close', broken)
        return ordinary(self, fd)
    monkeypatch.setattr(module._Lease, 'release', selectively_broken)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(OSError) as failed:
        bootstrap_procfs_origin(tree, _native=native)
    assert failed.value.errno == errno.EXDEV
    assert failed.value.private_cleanup_errors
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('entry', [1, 2, 8])
def test_native_identity_failure_after_registration_preserves_primary_and_closes(tree, monkeypatch, entry):
    import tools.proc_openat2_bootstrap as module
    original = module._identity
    calls = []
    def fail(fd):
        calls.append(fd)
        if len(calls) == entry:
            raise OSError(errno.EIO, 'primary identity failure')
        return original(fd)
    monkeypatch.setattr(module, '_identity', fail)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(OSError) as failed:
        bootstrap_procfs_origin(tree, _native=FixtureNative())
    assert failed.value.errno == errno.EIO
    assert set(os.listdir('/proc/self/fd')) == before
