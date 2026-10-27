"""Offline characterization of the unchanged strict native mount-ID boundary.

Only native return values are doubled. These are not device-support tests and
do not implement or select a compatibility backend.
"""
import ctypes
import errno
import os

import pytest

from tools.pinned_proc_view import AcquisitionError, NativeLinux, ProcView
from tools.proc_view_capability import probe_capability


def native_returns(mask, mount_id, *, fs_magic=0x9FA0, fs_errno=None, statx_errno=None):
    native = NativeLinux()
    calls = {'fstatfs': 0, 'statx': 0}

    def fstatfs(fd, value):
        calls['fstatfs'] += 1
        if fs_errno is not None:
            ctypes.set_errno(fs_errno)
            return -1
        value._obj.words[0] = fs_magic
        return 0

    def statx(fd, path, flags, requested_mask, value):
        calls['statx'] += 1
        assert path == b'' and flags == 0x1000 and requested_mask == 0x1000
        if statx_errno is not None:
            ctypes.set_errno(statx_errno)
            return -1
        value._obj.mask = mask
        value._obj.mount_id = mount_id
        return 0

    native._fs, native._sx = fstatfs, statx
    return native, calls


@pytest.mark.parametrize('mask,mount_id', [
    (0, 0), (0, 41), (0x7FF, 41), (0x1000, 0), (0x17FF, 0),
])
def test_successful_queries_without_both_mount_id_requirements_reject(mask, mount_id):
    native, calls = native_returns(mask, mount_id)
    with pytest.raises(AcquisitionError, match='^UNSUPPORTED_MOUNT_ID$'):
        native.describe(123)
    assert calls == {'fstatfs': 1, 'statx': 1}


@pytest.mark.parametrize('mask', [0x1000, 0x17FF])
def test_reported_mount_bit_and_positive_id_preserve_native_descriptor_result(mask):
    native, calls = native_returns(mask, 41)
    assert native.describe(123) == {'fs_magic': 0x9FA0, 'mount_id': 41}
    assert calls == {'fstatfs': 1, 'statx': 1}


@pytest.mark.parametrize('number', [errno.EACCES, errno.EIO])
def test_fstatfs_error_is_not_relabelled_as_missing_mount_id_or_retried(number):
    native, calls = native_returns(0x1000, 41, fs_errno=number)
    with pytest.raises(OSError) as failed:
        native.describe(123)
    assert failed.value.errno == number
    assert calls == {'fstatfs': 1, 'statx': 0}


@pytest.mark.parametrize('number', [errno.ENOSYS, errno.EPERM])
def test_statx_error_is_not_relabelled_as_success_or_retried(number):
    native, calls = native_returns(0x1000, 41, statx_errno=number)
    with pytest.raises(OSError) as failed:
        native.describe(123)
    assert failed.value.errno == number
    assert calls == {'fstatfs': 1, 'statx': 1}


@pytest.mark.parametrize('mask,mount_id', [(0x7FF, 41), (0x1000, 0)])
def test_constructor_failure_closes_owned_descriptors_before_any_scope(mask, mount_id):
    native, calls = native_returns(mask, mount_id)
    before = set(os.listdir('/proc/self/fd'))
    with pytest.raises(AcquisitionError, match='^UNSUPPORTED_MOUNT_ID$'):
        ProcView(native=native)
    assert set(os.listdir('/proc/self/fd')) == before
    assert calls == {'fstatfs': 1, 'statx': 1}


@pytest.mark.parametrize('mask,mount_id', [(0x7FF, 41), (0x1000, 0)])
def test_injected_old_profile_keeps_closed_blocked_receipt_and_no_authority(mask, mount_id):
    native, calls = native_returns(mask, mount_id)
    out = probe_capability(view_factory=lambda **kwargs: ProcView(native=native, **kwargs))
    assert out['status'] == 'BLOCKED_NATIVE_CAPABILITY'
    assert out['reason_code'] == 'UNSUPPORTED_MOUNT_ID'
    assert out['failure_phase'] == 'CONSTRUCT' and out['errno_code'] == 'NONE'
    assert out['evidence_kind'] == 'INJECTED_FIXTURE'
    assert out['events'] == 3 and out['processes_created'] == 0
    assert all(out[key] is False for key in (
        'journal_created', 'sampling_window_started', 'ticket_created',
        'device_validation', 'policy_acceptance', 'negative_pid_witness_allowed',
        'lifetime_acceptance', 'temporal_visibility_proven',
    ))
    assert calls == {'fstatfs': 1, 'statx': 1}


def test_valid_mount_id_does_not_waive_the_procfs_filesystem_check():
    native, calls = native_returns(0x1000, 41, fs_magic=0xEF53)
    with pytest.raises(AcquisitionError, match='^NOT_PROCFS$'):
        ProcView(native=native)
    assert calls == {'fstatfs': 1, 'statx': 1}
