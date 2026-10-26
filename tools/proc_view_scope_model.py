"""Offline proposed-record model. Never a runtime scope or policy attestor."""
import hashlib
import json


class _Reject(ValueError):
    pass


def _require(condition, reason):
    if not condition:
        raise _Reject(reason)


def _keys(value, expected):
    _require(type(value) is dict and set(value) == set(expected.split()), 'SCHEMA')


def _integer(value, minimum=0, reason='SCHEMA'):
    _require(type(value) is int and minimum <= value <= 2**63 - 1, reason)
    return value


def _digest(value):
    _require(type(value) is str and len(value) == 64 and
             all(c in '0123456789abcdef' for c in value), 'SCHEMA')
    return value


def _device(value):
    _require(type(value) is list and len(value) == 2, 'SCHEMA')
    return [_integer(part) for part in value]


def _text(value, reason):
    _require(type(value) is str and 0 < len(value) <= 262144 and '\0' not in value, reason)
    return value


def _decimal(value, reason):
    _require(bool(value) and all(c in '0123456789' for c in value), reason)
    return _integer(int(value), reason=reason)


def _fd_value(raw, key, required=True):
    values = [line.partition(':')[2].strip() for line in _text(raw, 'FDINFO').splitlines()
              if line.partition(':')[0].strip() == key]
    _require(len(values) == 1 if required else len(values) <= 1, 'FDINFO')
    return values[0] if values else None


def _fd_mount_id(raw):
    value = _decimal(_fd_value(raw, 'mnt_id'), 'FDINFO')
    _require(value > 0, 'FDINFO')
    return value


def _fd_mode(raw, kind, reason, expected_inode=None):
    # This proposed record profile explicitly uses asm-generic UAPI values.
    # It never infers the native flag ABI of a device or authenticates a syscall.
    value = _fd_value(raw, 'flags')
    _require(bool(value) and all(c in '01234567' for c in value), 'FDINFO')
    flags = _integer(int(value, 8), reason='FDINFO')
    required = 0o2000000 | 0o400000  # CLOEXEC, NOFOLLOW, O_RDONLY=0
    if kind in {'directory', 'readlink_parent'}:
        required |= 0o200000  # DIRECTORY
    allowed = required | 0o100000  # Optional LARGEFILE
    _require(flags & 3 == 0 and flags & required == required and flags & ~allowed == 0,
             reason)
    inode = _fd_value(raw, 'ino', required=False)
    if inode is not None:
        inode = _decimal(inode, 'FDINFO')
        _require(inode > 0, 'FDINFO')
        if expected_inode is not None:
            _require(inode == expected_inode, 'ROOT_CHANGED')


def _root(value):
    _keys(value, 'device inode kind fs_magic')
    _device(value['device'])
    _integer(value['inode'], 1)
    _require(value['kind'] == 'directory' and type(value['fs_magic']) is int and
             value['fs_magic'] == 0x9FA0, 'NOT_PROCFS')
    return value


def _mount(raw, mount_id, device):
    rows = {}
    for line in _text(raw, 'MOUNTINFO').splitlines():
        fields = line.split()
        _require(fields.count('-') == 1, 'MOUNTINFO')
        separator = fields.index('-')
        _require(separator >= 6 and len(fields) == separator + 4, 'MOUNTINFO')
        identity = _decimal(fields[0], 'MOUNTINFO')
        _require(identity > 0 and identity not in rows, 'MOUNTINFO')
        parent = _decimal(fields[1], 'MOUNTINFO')
        numbers = fields[2].split(':')
        _require(len(numbers) == 2, 'MOUNTINFO')
        rows[identity] = {
            'mount_id': identity, 'parent_id': parent,
            'device': [_decimal(part, 'MOUNTINFO') for part in numbers],
            'root': fields[3], 'mountpoint': fields[4], 'type': fields[separator + 1],
            'options': fields[5].split(',') + fields[separator + 3].split(','),
        }
    _require(mount_id in rows, 'MOUNT_NOT_CURRENT')
    row = rows[mount_id]
    _require(row['device'] == device and row['root'] == '/' and
             row['mountpoint'] == '/proc' and row['type'] == 'proc', 'MOUNT_IDENTITY')
    _require(sum(r['mountpoint'] == '/proc' for r in rows.values()) == 1, 'AMBIGUOUS_MOUNT')
    _require(not any(r['mountpoint'].startswith('/proc/') for r in rows.values()),
             'UNREVIEWED_SUBMOUNT')
    harmless = {'ro', 'rw', 'nosuid', 'nodev', 'noexec', 'relatime', 'noatime',
                'nodiratime', 'strictatime', 'sync', 'async', 'dirsync', 'lazytime'}
    special = set()
    for option in row['options']:
        if option in harmless:
            continue
        key, separator, value = option.partition('=')
        _require(separator and key not in special, 'VISIBILITY')
        special.add(key)
        if key == 'hidepid':
            _require(value in {'0', 'off'}, 'VISIBILITY')
        elif key == 'gid':
            _decimal(value, 'VISIBILITY')
        else:
            raise _Reject('VISIBILITY')
    row['options'] = sorted(set(row['options']))
    return row


def _validate(record):
    _keys(record, 'schema kind flag_abi clock_id start_ns end_ns lease owner boot_sha256 '
                  'mount_namespace_sha256 pid_namespace mountinfo operations')
    _require(type(record['schema']) is int and record['schema'] == 1 and
             record['kind'] == 'PINNED_PROC_VIEW_RECORD_V1', 'SCHEMA')
    _require(record['flag_abi'] == 'LINUX_ASM_GENERIC', 'FLAG_ABI')
    _require(record['clock_id'] == 'CLOCK_BOOTTIME', 'CLOCK')
    start = _integer(record['start_ns'], reason='CLOCK')
    end = _integer(record['end_ns'], reason='CLOCK')
    _require(end >= start, 'CLOCK')
    lease, owner = record['lease'], record['owner']
    _keys(lease, 'id owner_pid owner_start_ticks opened_ns closed_ns open_mode root '
                 'root_fdinfo named_root named_root_fdinfo')
    _digest(lease['id'])
    _integer(lease['owner_pid'], 1)
    _integer(lease['owner_start_ticks'])
    _require(lease['closed_ns'] is None and
             _integer(lease['opened_ns']) <= start, 'LEASE_NOT_LIVE')
    _require(lease['open_mode'] == 'READONLY_DIRECTORY_NOFOLLOW_CLOEXEC', 'LEASE_MODE')
    root, named = _root(lease['root']), _root(lease['named_root'])
    mount_id = _fd_mount_id(lease['root_fdinfo'])
    _require(root == named and _fd_mount_id(lease['named_root_fdinfo']) == mount_id, 'ROOT_CHANGED')
    for key in ('root_fdinfo', 'named_root_fdinfo'):
        _fd_mode(lease[key], 'directory', 'LEASE_MODE', root['inode'])
    mount = _mount(record['mountinfo'], mount_id, root['device'])
    _keys(owner, 'pid start_ticks self_pid stat_pid uid gid groups')
    for key in ('pid', 'self_pid', 'stat_pid'):
        _integer(owner[key], 1)
    _integer(owner['start_ticks'])
    for key in ('uid', 'gid'):
        _require(type(owner[key]) is list and len(owner[key]) == 4, 'SCHEMA')
        for part in owner[key]:
            _integer(part)
    _require(type(owner['groups']) is list and len(owner['groups']) <= 65536, 'SCHEMA')
    for part in owner['groups']:
        _integer(part)
    _require(len(set(owner['groups'])) == len(owner['groups']), 'SCHEMA')
    _require(lease['owner_pid'] == owner['pid'] == owner['self_pid'] == owner['stat_pid']
             and lease['owner_start_ticks'] == owner['start_ticks'], 'OWNER_MAPPING')
    _digest(record['boot_sha256'])
    _digest(record['mount_namespace_sha256'])
    namespace = record['pid_namespace']
    _require(type(namespace) is dict, 'SCHEMA')
    if namespace.get('status') == 'PRESENT':
        _keys(namespace, 'status link_sha256')
        _digest(namespace['link_sha256'])
    else:
        _keys(namespace, 'status errno')
        _require(namespace['status'] == 'ENOENT' and type(namespace['errno']) is int and
                 namespace['errno'] == 2, 'PID_NAMESPACE_UNAVAILABLE')
    required = {'pid_list', 'self_stat', 'owner_status', 'mountinfo', 'boot_id',
                'mount_namespace', 'pid_namespace', 'root_fdinfo', 'named_root_fdinfo'}
    extra = {'pid_stat', 'metadata', 'parent_stat', 'fresh_pid_probe'}
    operations = record['operations']
    _require(type(operations) is list and len(required) <= len(operations) <= 4096,
             'INCOMPLETE_OPERATIONS')
    names = []
    last_end = start
    for operation in operations:
        _keys(operation, 'name scheme lease_id device fdinfo access_kind start_ns end_ns status')
        _require(type(operation['name']) is str and operation['name'] in required | extra,
                 'INCOMPLETE_OPERATIONS')
        names.append(operation['name'])
        _require(operation['scheme'] == 'DIRFD' and operation['lease_id'] == lease['id'],
                 'CROSS_VIEW_OPERATION')
        _require(_device(operation['device']) == root['device'] and
                 _fd_mount_id(operation['fdinfo']) == mount_id, 'CROSS_VIEW_OPERATION')
        kind = ('directory' if operation['name'] == 'pid_list' else
                'readlink_parent' if operation['name'] in {'mount_namespace', 'pid_namespace'} else 'file')
        _require(operation['access_kind'] == kind, 'OPERATION_KIND')
        _fd_mode(operation['fdinfo'], kind, 'OPERATION_MODE')
        if operation['name'] == 'pid_namespace':
            expected = 'OK' if namespace['status'] == 'PRESENT' else 'ENOENT'
            _require(operation['status'] == expected, 'PID_NAMESPACE_PROVENANCE')
        else:
            _require(operation['status'] == 'OK', 'INCOMPLETE_OPERATION')
        op_start = _integer(operation['start_ns'], reason='CLOCK')
        op_end = _integer(operation['end_ns'], reason='CLOCK')
        _require(last_end <= op_start <= op_end <= end, 'CLOCK')
        last_end = op_end
    _require(all(names.count(name) == 1 for name in required), 'INCOMPLETE_OPERATIONS')
    # Timing and process-row count are observations, not mounted-view identity.
    return {'flag_abi': record['flag_abi'], 'lease_id': lease['id'],
            'owner': {**owner, 'groups': sorted(owner['groups'])},
            'opened_ns': lease['opened_ns'], 'root': root, 'mount': mount,
            'boot_sha256': record['boot_sha256'],
            'mount_namespace_sha256': record['mount_namespace_sha256'],
            'pid_namespace': namespace}


def assess(record, baseline=None):
    """Check record relationships only. No supplied record is admissible evidence.

    A trusted FD acquisition/lease, namespace mapping, provider adaptation and
    temporal visibility still need independent proof. This function has no OS,
    process or network API and is not an alternative ProcReader implementation.
    """
    result = {
        'status': 'REJECTED_SCOPE_RECORD', 'admissibility': 'OFFLINE_NOT_ADMISSIBLE',
        'record_fingerprint': None, 'reasons': [],
        'runtime_scope_confirmed': False, 'namespace_equality_proven': False,
        'full_host_visibility_proven': False, 'temporal_visibility_proven': False,
        'negative_pid_witness_allowed': False, 'policy_acceptance': False,
        'legacy_fallback_allowed': False,
        'unproved_obligations': ['TRUSTED_FD_ACQUISITION', 'CONTINUOUS_LEASE_OWNERSHIP',
                                'TEMPORAL_VISIBILITY', 'COMPLETE_PROVIDER_ADAPTATION',
                                'CHILD_MAPPED_VIEW_BINDING', 'ACTUAL_CAPABILITY_VALIDATION',
                                'FLAG_ABI_ATTESTATION'],
    }
    try:
        core = _validate(record)
        if baseline is not None:
            _require(_validate(baseline) == core, 'BASELINE_CHANGED')
            _require(record['start_ns'] >= baseline['start_ns'] and
                     record['end_ns'] >= baseline['end_ns'], 'CLOCK')
        result['record_fingerprint'] = hashlib.sha256(
            json.dumps(core, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        result['status'] = 'CONDITIONALLY_CONSISTENT_MOUNTED_VIEW'
    except _Reject as error:
        result['reasons'] = [str(error)]
    except (KeyError, TypeError, ValueError, RecursionError):
        result['reasons'] = ['SCHEMA']
    return result
