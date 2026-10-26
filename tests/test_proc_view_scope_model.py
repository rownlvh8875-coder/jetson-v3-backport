"""Literal proposed evidence, never device or kernel acquisition proof."""
from copy import deepcopy

import pytest

from tools.proc_view_scope_model import assess


def record():
    root = {'device': [0, 4], 'inode': 1, 'kind': 'directory', 'fs_magic': 40864}
    fdinfo = 'pos:\t0\nflags:\t02600000\nmnt_id:\t20\n'
    roles = ['pid_list', 'self_stat', 'owner_status', 'mountinfo', 'boot_id',
             'mount_namespace', 'pid_namespace', 'root_fdinfo', 'named_root_fdinfo']
    return {
        'schema': 1, 'kind': 'PINNED_PROC_VIEW_RECORD_V1',
        'flag_abi': 'LINUX_ASM_GENERIC',
        'clock_id': 'CLOCK_BOOTTIME', 'start_ns': 100, 'end_ns': 200,
        'lease': {'id': 'a' * 64, 'owner_pid': 42, 'owner_start_ticks': 7,
                  'opened_ns': 50, 'closed_ns': None,
                  'open_mode': 'READONLY_DIRECTORY_NOFOLLOW_CLOEXEC',
                  'root': root, 'root_fdinfo': fdinfo,
                  'named_root': deepcopy(root), 'named_root_fdinfo': fdinfo},
        'owner': {'pid': 42, 'start_ticks': 7, 'self_pid': 42, 'stat_pid': 42,
                  'uid': [1000, 1000, 1000, 1000],
                  'gid': [1000, 1000, 1000, 1000], 'groups': [1000]},
        'boot_sha256': 'b' * 64, 'mount_namespace_sha256': 'c' * 64,
        'pid_namespace': {'status': 'ENOENT', 'errno': 2},
        'mountinfo': '20 1 0:4 / /proc rw,nosuid,nodev,noexec,relatime - proc proc rw\n',
        'operations': [
            {'name': name, 'scheme': 'DIRFD', 'lease_id': 'a' * 64,
             'device': [0, 4],
             'fdinfo': fdinfo if name in {'pid_list', 'mount_namespace', 'pid_namespace'}
                       else 'pos: 0\nflags: 02400000\nmnt_id: 20\n',
             'access_kind': 'directory' if name == 'pid_list' else
                            'readlink_parent' if name in {'mount_namespace', 'pid_namespace'} else 'file',
             'start_ns': 110 + i * 2, 'end_ns': 111 + i * 2,
             'status': 'ENOENT' if name == 'pid_namespace' else 'OK'}
            for i, name in enumerate(roles)
        ],
    }


def rejected(value, code, baseline=None):
    result = assess(value, baseline)
    assert result['status'] == 'REJECTED_SCOPE_RECORD'
    assert code in result['reasons']
    assert result['runtime_scope_confirmed'] is False
    assert result['negative_pid_witness_allowed'] is False
    assert result['policy_acceptance'] is False
    return result


def test_coherent_enoent_record_is_only_conditional():
    result = assess(record())
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    assert result['admissibility'] == 'OFFLINE_NOT_ADMISSIBLE'
    assert result['runtime_scope_confirmed'] is False
    assert result['full_host_visibility_proven'] is False
    assert result['namespace_equality_proven'] is False
    assert result['negative_pid_witness_allowed'] is False
    assert result['policy_acceptance'] is False
    assert result['legacy_fallback_allowed'] is False
    assert 'TEMPORAL_VISIBILITY' in result['unproved_obligations']
    assert 'TRUSTED_FD_ACQUISITION' in result['unproved_obligations']


def test_present_namespace_does_not_upgrade_record_to_runtime_proof():
    value = record()
    value['pid_namespace'] = {'status': 'PRESENT', 'link_sha256': 'd' * 64}
    next(o for o in value['operations'] if o['name'] == 'pid_namespace')['status'] = 'OK'
    result = assess(value)
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    assert result['namespace_equality_proven'] is False
    assert result['runtime_scope_confirmed'] is False


def test_matching_endpoints_do_not_exclude_visibility_aba():
    # Both unrestricted endpoints are consistent with an unobserved filtered
    # interval. The model must retain that uncertainty even for identical input.
    value = record()
    result = assess(deepcopy(value), value)
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    assert result['temporal_visibility_proven'] is False
    assert result['negative_pid_witness_allowed'] is False


def test_permission_failure_is_not_supported_missing_namespace():
    value = record()
    value['pid_namespace'] = {'status': 'ERROR', 'errno': 13}
    rejected(value, 'PID_NAMESPACE_UNAVAILABLE')


def test_closed_lease_cannot_be_rebound_by_same_numeric_id():
    value = record()
    value['lease']['closed_ns'] = 90
    rejected(value, 'LEASE_NOT_LIVE')


def test_absolute_metadata_cannot_be_attached_to_dirfd_evidence():
    value = record()
    value['operations'].append({**value['operations'][-1], 'name': 'metadata',
                                'scheme': 'ABSOLUTE', 'start_ns': 140, 'end_ns': 141})
    rejected(value, 'CROSS_VIEW_OPERATION')


def test_child_cannot_reuse_parent_lease_after_fork():
    value = record()
    value['owner'].update(pid=43, self_pid=43, stat_pid=43)
    rejected(value, 'OWNER_MAPPING')


def test_source_asserted_verified_flag_cannot_override_proof_boundary():
    value = record()
    value['verified'] = True
    rejected(value, 'SCHEMA')


@pytest.mark.parametrize('flags', ['02', '01', '02200000', '0600000', '012600000'])
def test_declared_readonly_lease_cannot_contradict_raw_root_flags(flags):
    value = record()
    value['lease']['root_fdinfo'] = 'mnt_id: 20\nflags: ' + flags + '\n'
    rejected(value, 'LEASE_MODE')


def test_named_root_flags_cannot_be_writable():
    value = record()
    value['lease']['named_root_fdinfo'] = 'mnt_id: 20\nflags: 02\n'
    rejected(value, 'LEASE_MODE')


def test_optional_fdinfo_inode_must_match_declared_root():
    value = record()
    value['lease']['root_fdinfo'] += 'ino: 99\n'
    rejected(value, 'ROOT_CHANGED')


def test_matching_optional_inode_is_consistent_but_not_acquisition_proof():
    value = record()
    value['lease']['root_fdinfo'] += 'ino: 1\n'
    result = assess(value)
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    assert result['runtime_scope_confirmed'] is False


def test_unknown_flag_abi_cannot_be_inferred_from_numeric_flags():
    value = record()
    value['flag_abi'] = 'UNKNOWN_TARGET_ABI'
    rejected(value, 'FLAG_ABI')


def test_overlapping_snapshots_never_become_sequential_lifetime_evidence():
    value = record()
    value['start_ns'] += 50
    value['end_ns'] += 50
    for operation in value['operations']:
        operation['start_ns'] += 50
        operation['end_ns'] += 50
    result = assess(value, record())
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    assert result['negative_pid_witness_allowed'] is False


def test_namespace_value_requires_a_correlated_operation():
    value = record()
    value['operations'] = [o for o in value['operations'] if o['name'] != 'pid_namespace']
    rejected(value, 'INCOMPLETE_OPERATIONS')


def test_namespace_enoent_cannot_be_replaced_with_successful_read_status():
    value = record()
    next(o for o in value['operations'] if o['name'] == 'pid_namespace')['status'] = 'OK'
    rejected(value, 'PID_NAMESPACE_PROVENANCE')


def test_file_read_cannot_claim_directory_target_flags():
    value = record()
    operation = next(o for o in value['operations'] if o['name'] == 'self_stat')
    operation['fdinfo'] = 'flags: 02600000\nmnt_id: 20\n'
    rejected(value, 'OPERATION_MODE')


@pytest.mark.parametrize('path,bad,code', [
    (('schema',), True, 'SCHEMA'),
    (('clock_id',), 'CLOCK_MONOTONIC', 'CLOCK'),
    (('end_ns',), 99, 'CLOCK'),
    (('start_ns',), True, 'CLOCK'),
    (('lease', 'opened_ns'), 101, 'LEASE_NOT_LIVE'),
    (('lease', 'id'), '', 'SCHEMA'),
    (('lease', 'open_mode'), 'WRITABLE_DIRECTORY', 'LEASE_MODE'),
    (('lease', 'root', 'fs_magic'), 123, 'NOT_PROCFS'),
    (('lease', 'root', 'kind'), 'symlink', 'NOT_PROCFS'),
    (('lease', 'named_root', 'inode'), 99, 'ROOT_CHANGED'),
    (('lease', 'named_root', 'device'), [0, 5], 'ROOT_CHANGED'),
    (('lease', 'root_fdinfo'), 'pos: 0\n', 'FDINFO'),
    (('lease', 'root_fdinfo'), 'mnt_id: 20\nmnt_id: 20\n', 'FDINFO'),
    (('lease', 'named_root_fdinfo'), 'mnt_id: 21\n', 'ROOT_CHANGED'),
    (('owner', 'uid'), [True, 1000, 1000, 1000], 'SCHEMA'),
    (('owner', 'groups'), [1000, 1000], 'SCHEMA'),
    (('owner', 'stat_pid'), 43, 'OWNER_MAPPING'),
    (('boot_sha256',), 'unknown', 'SCHEMA'),
    (('pid_namespace',), [], 'SCHEMA'),
], ids=['bool-schema', 'wrong-clock', 'reversed-clock', 'bool-clock', 'late-open',
        'missing-lease', 'writable-lease', 'fake-filesystem', 'symlink-root',
        'changed-inode', 'changed-device', 'missing-mount-id', 'duplicate-mount-id',
        'named-mount-mismatch', 'bool-uid', 'duplicate-group', 'wrong-self-stat',
        'missing-boot-binding', 'namespace-shape'])
def test_inconsistent_raw_relationships_reject(path, bad, code):
    value = record()
    parent = value
    for key in path[:-1]:
        parent = parent[key]
    parent[path[-1]] = bad
    rejected(value, code)


@pytest.mark.parametrize('mountinfo,code', [
    ('', 'MOUNTINFO'),
    ('malformed row', 'MOUNTINFO'),
    ('21 1 0:4 / /proc rw - proc proc rw\n', 'MOUNT_NOT_CURRENT'),
    ('20 1 0:5 / /proc rw - proc proc rw\n', 'MOUNT_IDENTITY'),
    ('20 1 0:4 /42 /proc rw - proc proc rw\n', 'MOUNT_IDENTITY'),
    ('20 1 0:4 / /elsewhere rw - proc proc rw\n', 'MOUNT_IDENTITY'),
    ('20 1 0:4 / /proc rw - tmpfs tmpfs rw\n', 'MOUNT_IDENTITY'),
    ('20 1 0:4 / /proc rw - proc proc rw,hidepid=2\n', 'VISIBILITY'),
    ('20 1 0:4 / /proc rw - proc proc rw,hidepid=ptraceable\n', 'VISIBILITY'),
    ('20 1 0:4 / /proc rw - proc proc rw,subset=pid\n', 'VISIBILITY'),
    ('20 1 0:4 / /proc rw - proc proc rw,future_filter=yes\n', 'VISIBILITY'),
    ('20 1 0:4 / /proc rw - proc proc rw\n20 1 0:4 / /proc rw - proc proc rw\n', 'MOUNTINFO'),
    ('20 1 0:4 / /proc rw - proc proc rw\n21 20 0:4 / /proc rw - proc proc rw\n', 'AMBIGUOUS_MOUNT'),
    ('20 1 0:4 / /proc rw - proc proc rw\n21 20 0:5 / /proc/42/stat rw - tmpfs tmpfs rw\n', 'UNREVIEWED_SUBMOUNT'),
], ids=['empty', 'malformed', 'detached', 'wrong-device', 'partial-root',
        'wrong-name', 'wrong-fstype', 'hidepid2', 'ptrace-filter', 'subset',
        'future-filter', 'duplicate-id', 'stacked', 'pid-submount'])
def test_mount_correlation_and_visibility_counterexamples(mountinfo, code):
    value = record()
    value['mountinfo'] = mountinfo
    rejected(value, code)


@pytest.mark.parametrize('change,code', [
    ('empty', 'INCOMPLETE_OPERATIONS'),
    ('missing', 'INCOMPLETE_OPERATIONS'),
    ('duplicate-required', 'INCOMPLETE_OPERATIONS'),
    ('other-mount', 'CROSS_VIEW_OPERATION'),
    ('other-device', 'CROSS_VIEW_OPERATION'),
    ('other-lease', 'CROSS_VIEW_OPERATION'),
    ('unknown-field', 'SCHEMA'),
    ('clock-outside', 'CLOCK'),
    ('overlap', 'CLOCK'),
    ('incomplete', 'INCOMPLETE_OPERATION'),
], ids=lambda value: value)
def test_operation_chain_cannot_hide_missing_or_mixed_reads(change, code):
    value = record()
    operations = value['operations']
    if change == 'empty':
        operations.clear()
    elif change == 'missing':
        operations.pop()
    elif change == 'duplicate-required':
        operations.append({**operations[-1], 'start_ns': 140, 'end_ns': 141})
    elif change == 'other-mount':
        operations[0]['fdinfo'] = 'mnt_id: 21\n'
    elif change == 'other-device':
        operations[0]['device'] = [0, 5]
    elif change == 'other-lease':
        operations[0]['lease_id'] = 'd' * 64
    elif change == 'unknown-field':
        operations[0]['path'] = '/proc/self/fd/9/42/stat'
    elif change == 'clock-outside':
        operations[0]['start_ns'] = 99
    elif change == 'overlap':
        operations[1]['start_ns'] = 110
    elif change == 'incomplete':
        operations[0]['status'] = 'UNREADABLE'
    rejected(value, code)


def later_record():
    value = record()
    value['start_ns'] += 200
    value['end_ns'] += 200
    for operation in value['operations']:
        operation['start_ns'] += 200
        operation['end_ns'] += 200
    return value


def test_later_read_interval_does_not_change_view_fingerprint():
    baseline = record()
    result = assess(later_record(), baseline)
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    assert result['record_fingerprint'] == assess(baseline)['record_fingerprint']
    assert result['temporal_visibility_proven'] is False


def test_baseline_from_later_clock_cannot_validate_earlier_record():
    rejected(record(), 'CLOCK', later_record())


@pytest.mark.parametrize('change', ['boot', 'mount-namespace', 'uid', 'lease', 'pid-namespace'])
def test_changed_context_rejects_reuse_of_old_baseline(change):
    baseline = record()
    value = later_record()
    if change == 'boot':
        value['boot_sha256'] = 'd' * 64
    elif change == 'mount-namespace':
        value['mount_namespace_sha256'] = 'd' * 64
    elif change == 'uid':
        value['owner']['uid'][0] = 1001
    elif change == 'lease':
        value['lease']['id'] = 'd' * 64
        for operation in value['operations']:
            operation['lease_id'] = 'd' * 64
    elif change == 'pid-namespace':
        value['pid_namespace'] = {'status': 'PRESENT', 'link_sha256': 'd' * 64}
        next(o for o in value['operations'] if o['name'] == 'pid_namespace')['status'] = 'OK'
    rejected(value, 'BASELINE_CHANGED', baseline)


def test_output_does_not_echo_invalid_private_values():
    value = record()
    value['mountinfo'] = 'PRIVATE_DEVICE_OR_ROUTE_VALUE'
    result = rejected(value, 'MOUNTINFO')
    assert 'PRIVATE_DEVICE_OR_ROUTE_VALUE' not in repr(result)


def test_assessment_does_not_mutate_input():
    value = record()
    before = deepcopy(value)
    assess(value, deepcopy(value))
    assert value == before


def test_assessment_has_no_implicit_io(monkeypatch):
    import builtins
    import os
    import socket

    def forbidden(*args, **kwargs):
        raise AssertionError('offline model attempted I/O')

    with monkeypatch.context() as patch:
        patch.setattr(builtins, 'open', forbidden)
        patch.setattr(os, 'open', forbidden)
        patch.setattr(socket, 'socket', forbidden)
        result = assess(record())
    assert result['status'] == 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
