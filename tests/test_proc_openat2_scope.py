"""Local endpoint integration fixtures; no device or process-policy approval."""
import errno
import inspect
import os
from pathlib import Path

import pytest

from test_proc_openat2_bootstrap import FixtureNative, stat_text
from tools.pinned_proc_view import ProcView
from tools.proc_openat2_bootstrap import BootstrapError
from tools.proc_openat2_scope import inspect_protected_scope


@pytest.fixture
def tree(tmp_path):
    root = tmp_path / 'proc'
    owner = root / str(os.getpid())
    (owner / 'fdinfo').mkdir(parents=True)
    (owner / 'ns').mkdir()
    (root / 'self').symlink_to(str(os.getpid()))
    (owner / 'stat').write_text(stat_text(os.getpid()))
    (owner / 'status').write_text(
        'Uid:\t' + ' '.join(map(str, (*os.getresuid(), os.geteuid()))) + '\n'
        'Gid:\t' + ' '.join(map(str, (*os.getresgid(), os.getegid()))) + '\n'
        'Groups:\t' + ' '.join(map(str, os.getgroups())) + '\n')
    (owner / 'ns' / 'mnt').symlink_to('mnt:[1234]')
    (owner / 'ns' / 'pid').symlink_to('pid:[1235]')
    device = root.stat().st_dev
    (owner / 'mountinfo').write_text(
        f'41 1 {os.major(device)}:{os.minor(device)} / /proc rw,nosuid,nodev,noexec - proc proc rw\n')
    (root / 'sys/kernel/random').mkdir(parents=True)
    (root / 'sys/kernel/random/boot_id').write_text('fixture-boot\n')
    (root / 'uptime').write_text('123.25 11.00\n')
    return root


def no_authority(value):
    assert value['kind'] == 'OPENAT2_ENDPOINT_SCOPE_V1'
    assert value['lease_closed'] is True
    assert value['full_ProcView_interface'] is False
    for key in ('runtime_scope_confirmed', 'namespace_equality_proven',
                'full_host_visibility_proven', 'temporal_visibility_proven',
                'negative_pid_witness_allowed', 'policy_acceptance',
                'legacy_fallback_allowed', 'lifetime_acceptance'):
        assert value[key] is False


def run_clean(root, native):
    before = set(os.listdir('/proc/self/fd'))
    value = inspect_protected_scope(root, _native=native)
    assert set(os.listdir('/proc/self/fd')) == before
    no_authority(value)
    return value


def test_success_common_scope_fields_equal_frozen_validator_with_distinct_backend(tree):
    old_native = FixtureNative()
    old_native.describe = lambda fd: {'fs_magic': 0x9FA0, 'mount_id': 41}
    with ProcView(tree, native=old_native) as old:
        expected = old.scope()
    assert expected['endpoint_checks_pass'] is True
    native = FixtureNative()
    value = run_clean(tree, native)
    assert value['endpoint_checks_pass'] is True
    for key in ('owner', 'owner_status', 'credentials', 'boot_sha256',
                'mount_namespace', 'pid_namespace', 'mount', 'uptime'):
        assert value[key] == expected[key]
    for key in ('device', 'inode', 'kind', 'fs_magic', 'mount_id', 'flags'):
        assert value['root'][key] == expected['root'][key]
    assert value['acquisition_backend'] == 'INJECTED_OPENAT2_SCOPE_ONLY'
    assert value['acquisition_backend'] != expected['acquisition_backend']
    assert all(row['resolve'] == 15 and row['native_origin'] is False for row in value['reader_origins'])
    assert {'boot_id', 'sys', 'kernel', 'random', 'uptime', 'ns', 'mnt', 'pid', 'mountinfo'} <= {n for _, n, _ in native.calls}


def test_closed_bootstrap_receipt_is_never_reused(tree, monkeypatch):
    import tools.proc_openat2_bootstrap as bootstrap
    monkeypatch.setattr(bootstrap, 'bootstrap_procfs_origin', lambda *_a, **_k: pytest.fail('closed receipt reused'))
    assert 'receipt' not in inspect.signature(inspect_protected_scope).parameters
    assert run_clean(tree, FixtureNative())['endpoint_checks_pass'] is True
    with pytest.raises(TypeError):
        inspect_protected_scope(tree, _native=FixtureNative(), receipt={'origin_supported': True})


@pytest.mark.parametrize('component', ['self', 'fdinfo', 'stat', 'status', 'sys', 'kernel', 'random', 'boot_id', 'uptime', 'ns', 'mnt', 'pid', 'mountinfo'])
def test_cross_mount_at_every_scope_path_rejects_without_fallback(tree, component):
    native = FixtureNative()
    original = native.open_component
    def denied(parent, name, kind):
        if name == component:
            raise OSError(errno.EXDEV, 'fixture boundary')
        return original(parent, name, kind)
    native.open_component = denied
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(OSError) as failed:
        inspect_protected_scope(tree, _native=native)
    assert failed.value.errno == errno.EXDEV
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('mutate', [
    lambda text: text.replace(' / /proc ', ' /hidden /proc '),
    lambda text: text.replace(' / /proc ', ' / /elsewhere '),
    lambda text: text.replace('- proc proc', '- ext4 proc'),
    lambda text: text.replace('rw,nosuid', 'rw,hidepid=2,nosuid'),
    lambda text: text.replace('rw,nosuid', 'rw,hidepid=0,hidepid=0,nosuid'),
    lambda text: text.replace('rw,nosuid', 'rw,subset=pid,nosuid'),
    lambda text: text + text,
    lambda text: text + text.replace('41 1', '42 41').replace(' /proc ', ' /proc/uptime '),
    lambda text: text.replace('41 1', '42 1'),
])
def test_strict_mount_profile_is_not_weakened(tree, mutate):
    path = tree / str(os.getpid()) / 'mountinfo'
    path.write_text(mutate(path.read_text()))
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(ValueError):
        inspect_protected_scope(tree, _native=FixtureNative())
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('path', ['boot_id', 'mountinfo', 'stat', 'status'])
def test_endpoint_mutation_rejects(tree, path):
    native = FixtureNative()
    seen = []
    def change(name, fd):
        if name == path:
            seen.append(fd)
            if len(seen) == 2:
                target = Path(os.readlink(f'/proc/self/fd/{fd}'))
                if path == 'stat':
                    target.write_text(stat_text(os.getpid(), 501))
                elif path == 'status':
                    target.write_text(target.read_text().replace('Uid:', 'Wrong:'))
                else:
                    target.write_text(target.read_text() + 'changed\n')
    native.after_open = change
    with pytest.raises((BootstrapError, ValueError)):
        inspect_protected_scope(tree, _native=native)


@pytest.mark.parametrize('field', ['mnt', 'pid'])
def test_namespace_endpoint_drift_rejects(tree, field):
    native = FixtureNative()
    original = native.link
    seen = []
    def changed(fd):
        text = original(fd)
        if Path(os.readlink(f'/proc/self/fd/{fd}')).name == field:
            seen.append(fd)
            if len(seen) == 2:
                return text + '-changed'
        return text
    native.link = changed
    with pytest.raises(BootstrapError, match='NAMESPACE_ENDPOINT_CHANGED'):
        inspect_protected_scope(tree, _native=native)


def test_exact_pid_namespace_leaf_enoent_is_supported_but_never_authority(tree):
    (tree / str(os.getpid()) / 'ns/pid').unlink()
    value = run_clean(tree, FixtureNative())
    assert value['pid_namespace'] == {'status': 'ENOENT', 'errno': 2}


@pytest.mark.parametrize('where', ['parent', 'readlink', 'permission'])
def test_nested_or_postopen_namespace_error_is_not_supported_absence(tree, where):
    native = FixtureNative()
    opening, linking = native.open_component, native.link
    def fail_open(parent, name, kind):
        if (where == 'parent' and name == 'ns') or (where == 'permission' and name == 'pid'):
            number = errno.ENOENT if where == 'parent' else errno.EACCES
            raise OSError(number, 'not exact leaf absence')
        return opening(parent, name, kind)
    def fail_link(fd):
        if where == 'readlink' and Path(os.readlink(f'/proc/self/fd/{fd}')).name == 'pid':
            raise FileNotFoundError(errno.ENOENT, 'after leaf open')
        return linking(fd)
    native.open_component, native.link = fail_open, fail_link
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(OSError):
        inspect_protected_scope(tree, _native=native)
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('number', [errno.ENOSYS, errno.EINVAL, errno.EPERM, errno.EAGAIN])
def test_unsupported_native_failure_is_not_retried(tree, number):
    native = FixtureNative()
    calls = []
    def fail(*args):
        calls.append(args)
        raise OSError(number, 'unsupported')
    native.open_component = fail
    with pytest.raises(OSError) as failed:
        inspect_protected_scope(tree, _native=native)
    assert failed.value.errno == number and len(calls) == 1


def test_oversized_mountinfo_rejects_instead_of_truncating(tree):
    (tree / str(os.getpid()) / 'mountinfo').write_bytes(b'x' * 16385)
    with pytest.raises(BootstrapError, match='READ_LIMIT'):
        inspect_protected_scope(tree, _native=FixtureNative())


def test_candidate_never_calls_statx_and_local_profile_is_not_waived(monkeypatch):
    from tools.pinned_proc_view import NativeLinux
    monkeypatch.setattr(NativeLinux, 'describe', lambda *_: pytest.fail('statx called'))
    before = set(os.listdir('/proc/self/fd'))
    try:
        value = inspect_protected_scope()
    except OSError as failed:
        assert failed.errno == errno.EXDEV  # Existing local proc submount refused.
    except ValueError as failed:
        assert str(failed) == 'UNREVIEWED_SUBMOUNT'
    else:
        assert value['endpoint_checks_pass'] is True
        assert value['acquisition_backend'] == 'NATIVE_OPENAT2_SCOPE_ONLY'
        assert all(row['native_origin'] for row in value['reader_origins'])
        no_authority(value)
    assert set(os.listdir('/proc/self/fd')) == before


def test_all_scope_opens_share_continuously_live_root_lease(tree):
    native = FixtureNative()
    original = native.open_component
    roots = []
    def checked(parent, name, kind):
        if not roots:
            roots.append((parent, os.fstat(parent)))
        fd, node = roots[0]
        current = os.fstat(fd)
        assert (current.st_dev, current.st_ino) == (node.st_dev, node.st_ino)
        return original(parent, name, kind)
    native.open_component = checked
    value = run_clean(tree, native)
    assert value['restricted_open_count'] == len(native.calls)
    assert len(native.calls) <= 64
    with pytest.raises(OSError) as failed:
        os.fstat(roots[0][0])
    assert failed.value.errno == errno.EBADF


def test_named_root_replacement_after_scope_reads_rejects(tree, monkeypatch):
    import tools.proc_openat2_scope as module
    original = module.os.open
    seen = []
    other = tree.parent / 'replacement'
    other.mkdir()
    def changed(path, flags, *args, **kwargs):
        if path == tree.name:
            seen.append(path)
            if len(seen) == 2:
                return original(other, flags)
        return original(path, flags, *args, **kwargs)
    monkeypatch.setattr(module.os, 'open', changed)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='NAMED_ROOT_CHANGED'):
        inspect_protected_scope(tree, _native=FixtureNative())
    assert set(os.listdir('/proc/self/fd')) == before


def test_pid_namespace_appearance_between_endpoints_rejects(tree):
    native = FixtureNative()
    original = native.open_component
    seen = []
    def changed(parent, name, kind):
        if name == 'pid':
            seen.append(name)
            if len(seen) == 1:
                raise FileNotFoundError(errno.ENOENT, 'first leaf absent')
        return original(parent, name, kind)
    native.open_component = changed
    with pytest.raises(BootstrapError, match='NAMESPACE_ENDPOINT_CHANGED'):
        inspect_protected_scope(tree, _native=native)


def test_persistent_root_flag_drift_during_scope_rejects(tree):
    native = FixtureNative()
    original = native.open_component
    root_fd = []
    def changed(parent, name, kind):
        if not root_fd:
            root_fd.append(parent)
        if name == 'uptime':
            os.set_inheritable(root_fd[0], True)
        return original(parent, name, kind)
    native.open_component = changed
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='FD_IDENTITY_CHANGED'):
        inspect_protected_scope(tree, _native=native)
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('close_error', [False, True])
def test_scope_read_failure_primary_survives_all_owned_cleanup(tree, monkeypatch, close_error):
    import tools.proc_openat2_scope as module
    native = FixtureNative()
    original_open, original_close = native.open_component, module.os.close
    closing = []
    def bad_close(fd):
        original_close(fd)
        closing.append(fd)
        raise OSError(errno.EIO, 'secondary close failure')
    def failed(parent, name, kind):
        if name == 'boot_id':
            if close_error:
                monkeypatch.setattr(module.os, 'close', bad_close)
            raise OSError(errno.EACCES, 'primary scope read failure')
        return original_open(parent, name, kind)
    native.open_component = failed
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(OSError) as error:
        inspect_protected_scope(tree, _native=native)
    assert error.value.errno == errno.EACCES
    if close_error:
        assert len(closing) >= 4 and len(error.value.private_cleanup_errors) == len(closing)
    assert set(os.listdir('/proc/self/fd')) == before


def test_final_close_failure_cannot_return_endpoint_success(tree, monkeypatch):
    import tools.proc_openat2_scope as module
    native = FixtureNative()
    original_open, original_close = module.os.open, module.os.close
    named = []
    closing = []
    def bad_close(fd):
        original_close(fd)
        closing.append(fd)
        raise OSError(errno.EIO, 'final close failure')
    def opened(path, flags, *args, **kwargs):
        fd = original_open(path, flags, *args, **kwargs)
        if path == tree.name:
            named.append(fd)
            if len(named) == 2:
                monkeypatch.setattr(module.os, 'close', bad_close)
        return fd
    monkeypatch.setattr(module.os, 'open', opened)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='CLEANUP_FAILED'):
        inspect_protected_scope(tree, _native=native)
    assert len(closing) >= 4 and set(os.listdir('/proc/self/fd')) == before


def test_partial_scope_reads_preserve_full_digest(tree, monkeypatch):
    import tools.proc_openat2_scope as module
    expected = run_clean(tree, FixtureNative())
    original = module.os.read
    monkeypatch.setattr(module.os, 'read', lambda fd, n: original(fd, min(n, 7)))
    value = run_clean(tree, FixtureNative())
    for key in ('boot_sha256', 'mount', 'owner', 'owner_status'):
        assert value[key] == expected[key]


@pytest.mark.parametrize('limit', ['_OPEN_LIMIT', '_READ_CALL_LIMIT'])
def test_scope_remains_bounded_by_frozen_lease_budget(tree, monkeypatch, limit):
    import tools.proc_openat2_bootstrap as bootstrap
    monkeypatch.setattr(bootstrap, limit, 8)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(BootstrapError, match='LIMIT'):
        inspect_protected_scope(tree, _native=FixtureNative())
    assert set(os.listdir('/proc/self/fd')) == before


@pytest.mark.parametrize('where', ['post_open_filesystem', 'parent_check'])
def test_validation_enoent_never_becomes_supported_pid_namespace_absence(tree, monkeypatch, where):
    import tools.proc_openat2_bootstrap as bootstrap
    native = FixtureNative()
    if where == 'post_open_filesystem':
        original = native.filesystem_magic
        def failed(fd):
            if Path(os.readlink(f'/proc/self/fd/{fd}')).name == 'pid':
                raise FileNotFoundError(errno.ENOENT, 'already opened leaf validation failed')
            return original(fd)
        native.filesystem_magic = failed
    else:
        original = bootstrap._Lease.check
        checks = []
        def failed(lease, fd):
            if Path(os.readlink(f'/proc/self/fd/{fd}')).name == 'ns':
                checks.append(fd)
                # Each mnt open has before/after parent checks. Reject the
                # next pid open's parent check, before its native leaf syscall.
                if len(checks) in {3, 6}:
                    raise FileNotFoundError(errno.ENOENT, 'namespace parent validation failed')
            return original(lease, fd)
        monkeypatch.setattr(bootstrap._Lease, 'check', failed)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(FileNotFoundError) as error:
        inspect_protected_scope(tree, _native=native)
    assert error.value.errno == errno.ENOENT
    assert set(os.listdir('/proc/self/fd')) == before
