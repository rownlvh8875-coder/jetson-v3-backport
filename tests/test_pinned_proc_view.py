"""Offline acquisition tests: real local files; native boundary doubled explicitly."""
import errno
import os
from pathlib import Path

import pytest

from tools.pinned_proc_view import AcquisitionError, NativeLinux, ProcView


def stat_text(pid, start=500, ppid=1, comm='actor ) with spaces'):
    return f'{pid} ({comm}) S {ppid} ' + ' '.join(['0'] * 17 + [str(start)]) + '\n'


class FixtureNative:
    def describe(self, fd):
        return {'fs_magic': 0x9FA0, 'mount_id': 41}

    def link(self,fd):
        return NativeLinux().link(fd)


@pytest.fixture
def tree(tmp_path):
    pid = os.getpid()
    (tmp_path/'self').symlink_to(str(pid))
    for number in {1, pid, 42}:
        node = tmp_path/str(number)
        (node/'ns').mkdir(parents=True)
        (node/'stat').write_text(stat_text(number))
        (node/'status').write_text(f'Name:\tfixture\nUid:\t{os.getuid()} {os.geteuid()} {os.geteuid()} {os.geteuid()}\nGid:\t{os.getgid()} {os.getegid()} {os.getegid()} {os.getegid()}\nGroups:\t'+' '.join(map(str,os.getgroups()))+'\n')
        (node/'cmdline').write_bytes(b'fixture\0--observe\0')
        (node/'cgroup').write_text('0::/fixture\n')
        (node/'ns'/'mnt').symlink_to('mnt:[1234]')
        (node/'ns'/'pid').symlink_to('pid:[1235]')
        device=tmp_path.stat().st_dev
        (node/'mountinfo').write_text(f'41 1 {os.major(device)}:{os.minor(device)} / /proc rw,nosuid,nodev,noexec - proc proc rw\n')
    (tmp_path/'sys/kernel/random').mkdir(parents=True)
    (tmp_path/'sys/kernel/random/boot_id').write_text('fixture-boot\n')
    (tmp_path/'uptime').write_text('123.25 11.00\n')
    return tmp_path


def test_reads_held_generation_and_repeated_fresh_enumeration(tree):
    with ProcView(tree, native=FixtureNative()) as view:
        first = view.enumerate()
        assert first['pids'] == sorted({1, 42, os.getpid()})
        assert first['negative_pid_witness_allowed'] is False
        assert view.enumerate()['pids'] == first['pids']
        with view.generation(42) as actor:
            assert actor.identity()['start_ticks'] == 500
            assert actor.read('cmdline') == b'fixture\0--observe\0'
        assert view.probe(42)['status'] == 'PRESENT'


def test_nonproc_filesystem_rejected_without_reinterpreting_text(tree):
    with pytest.raises(AcquisitionError, match='NOT_PROCFS'):
        ProcView(tree, native=type('Nonproc',(),{'describe':lambda s,fd:{'fs_magic':1,'mount_id':41}})())


def test_symlink_root_and_intermediate_symlink_rejected(tree, tmp_path):
    alias=tmp_path/'alias'; alias.symlink_to(tree, target_is_directory=True)
    with pytest.raises(OSError):
        ProcView(alias, native=FixtureNative())
    (tree/'42'/'cmdline').unlink()
    (tree/'42'/'cmdline').symlink_to('../1/cmdline')
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            with pytest.raises(OSError):actor.read('cmdline')


@pytest.mark.parametrize('field',['../stat','/etc/passwd','fd/0','ns/pid','stat/../cmdline',''])
def test_closed_fields_prevent_traversal_and_magic_link_proxy(tree,field):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            with pytest.raises(ValueError):actor.read(field)


@pytest.mark.parametrize('pid',[0,-1,True,'42',1.5])
def test_invalid_pid_rejected_before_lookup(tree,pid):
    with ProcView(tree,native=FixtureNative()) as view:
        with pytest.raises(ValueError):view.probe(pid)


def test_native_describes_local_proc_fd():
    fd=os.open('/proc',os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW|os.O_CLOEXEC)
    try:
        value=NativeLinux().describe(fd)
        assert value['fs_magic']==0x9FA0
        assert type(value['mount_id']) is int and value['mount_id']>0
    finally:os.close(fd)


def test_same_device_different_mount_is_rejected(tree):
    class Submount(FixtureNative):
        def describe(self,fd):
            result=super().describe(fd)
            if Path(os.readlink(f'/proc/self/fd/{fd}')).name=='cmdline':result['mount_id']=42
            return result
    with ProcView(tree,native=Submount()) as view:
        with view.generation(42) as actor:
            with pytest.raises(AcquisitionError,match='CROSS_MOUNT'):actor.read('cmdline')


def test_closed_generation_cannot_adopt_recycled_fd(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        old=view.generation(42);old.close()
        with view.generation(42):
            with pytest.raises(AcquisitionError,match='GENERATION_CLOSED'):old.identity()


def test_held_generation_rejects_changed_start_and_fresh_probe_sees_it(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            (tree/'42/stat').write_text(stat_text(42,start=700))
            with pytest.raises(AcquisitionError,match='GENERATION_CHANGED'):actor.identity()
        assert view.probe(42)['start_ticks']==700


def test_fresh_missing_is_not_admissible_absence_and_permission_is_unreadable(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        assert view.probe(123456)['status']=='NOT_FOUND'
        original=os.open
        def denied(path,flags,*args,**kwargs):
            if path=='42':raise PermissionError(errno.EACCES,'fixture')
            return original(path,flags,*args,**kwargs)
        monkeypatch.setattr(os,'open',denied)
        assert view.probe(42)['status']=='UNREADABLE'
        assert view.probe(42)['negative_pid_witness_allowed'] is False


@pytest.mark.parametrize('content',[b'bad', b'42 (x) S 1\n',stat_text(41).encode(),stat_text(42,start=-1).encode()])
def test_malformed_stat_is_unreadable_not_absent(tree,content):
    (tree/'42/stat').write_bytes(content)
    with ProcView(tree,native=FixtureNative()) as view:
        assert view.probe(42)['status']=='UNREADABLE'


def test_oversized_read_rejected_and_fd_closed(tree):
    (tree/'42/cmdline').write_bytes(b'x'*262145)
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            before=set(os.listdir('/proc/self/fd'))
            with pytest.raises(AcquisitionError,match='READ_LIMIT'):actor.read('cmdline')
            assert set(os.listdir('/proc/self/fd'))==before


def test_named_root_rebind_and_credentials_drift_fail_closed(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        monkeypatch.setattr(os,'getresuid',lambda:(12345,12345,12345))
        with pytest.raises(AcquisitionError,match='OWNER_CHANGED'):view.enumerate()


def test_snapshot_missing_pid_namespace_keeps_error_but_never_authorizes(tree):
    (tree/str(os.getpid())/'ns/pid').unlink()
    with ProcView(tree,native=FixtureNative()) as view:
        value=view.scope()
        assert value['pid_namespace']=={'status':'ENOENT','errno':2}
        assert value['endpoint_checks_pass'] is True
        assert value['temporal_visibility_proven'] is False
        assert value['runtime_scope_confirmed'] is False
        assert value['policy_acceptance'] is False
        assert value['negative_pid_witness_allowed'] is False
        assert value['trust_assumptions']


def test_metadata_and_parent_are_same_view_bracketed_with_field_errors(tree):
    (tree/'42/cgroup').unlink()
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            value=actor.metadata()
        assert value['identity']['pid']==42
        assert value['fields']['cmdline']==b'fixture\0--observe\0'
        assert value['errors']['cgroup']['errno']==2
        assert value['parent']['before']==value['parent']['after']=={'pid':1,'ppid':1,'start_ticks':500}
        assert value['atomic_snapshot'] is False


def test_metadata_read_race_cannot_claim_generation_stability(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            original=actor.read
            def race(field):
                raw=original(field)
                if field=='cmdline':(tree/'42/stat').write_text(stat_text(42,start=999))
                return raw
            monkeypatch.setattr(actor,'read',race)
            with pytest.raises(AcquisitionError,match='GENERATION_CHANGED'):actor.metadata()


def test_real_local_scope_and_metadata_remain_acquisition_only():
    with ProcView() as view:
        value=view.scope()
        # WSL may install proc submounts. Refusal is retained, not skipped/waived.
        if not value['endpoint_checks_pass']:
            assert value['errors']['scope']['reason']=='UNREVIEWED_SUBMOUNT'
        assert value['policy_acceptance'] is False
        with view.generation(os.getpid()) as actor:
            metadata=actor.metadata()
        assert metadata['identity']['pid']==os.getpid()
        assert metadata['fields']['cmdline']
        assert metadata['exe_target']['stable_endpoints'] is True


def test_child_mapping_requires_same_view_parent_and_current_generation(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        handshake=view.mapping_identity()
        assert handshake['pid']==os.getpid()
        child=dict(handshake,pid=42,start_ticks=500,ppid=os.getpid())
        (tree/'42/stat').write_text(stat_text(42,ppid=os.getpid()))
        value=view.compare_child_mapping(child)
        assert value['mapping_matches'] is True
        assert value['owned_child'] is False
        assert value['signal_authority'] is False
        child['start_ticks']=999
        assert view.compare_child_mapping(child)['mapping_matches'] is False


@pytest.mark.parametrize('field,value',[('mount_id',99),('boot_sha256','0'*64),('mount_namespace','mnt:[999]'),('ppid',99)])
def test_child_mapping_mismatch_cannot_grant_ownership(tree,field,value):
    with ProcView(tree,native=FixtureNative()) as view:
        child=dict(view.mapping_identity(),pid=42,ppid=os.getpid(),start_ticks=500)
        child[field]=value
        result=view.compare_child_mapping(child)
        assert result['mapping_matches'] is False
        assert result['owned_child'] is False


def test_owner_fs_credentials_change_invalidates_scope(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        path=tree/str(os.getpid())/'status'
        path.write_text(path.read_text().replace('Uid:', 'Unexpected:'))
        with pytest.raises(AcquisitionError,match='OWNER_STATUS'):view.enumerate()


def test_renamed_named_root_rejected_held_fd_not_retargeted(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        moved=tree.with_name(tree.name+'-moved')
        tree.rename(moved);tree.mkdir()
        with pytest.raises(AcquisitionError,match='NAMED_ROOT_CHANGED'):view.enumerate()


@pytest.mark.parametrize('mask,mount_id',[(0,41),(0x1000,0)])
def test_native_requires_returned_mount_id_support(mask,mount_id):
    native=NativeLinux()
    def incomplete(fd,path,flags,want,out):
        out._obj.mask=mask;out._obj.mount_id=mount_id
        return 0
    native._sx=incomplete
    fd=os.open('/proc',os.O_RDONLY|os.O_DIRECTORY)
    try:
        with pytest.raises(AcquisitionError,match='UNSUPPORTED_MOUNT_ID'):native.describe(fd)
    finally:os.close(fd)


def test_unknown_native_abi_rejects_without_query(monkeypatch):
    monkeypatch.setattr('platform.machine',lambda:'unsupported-fixture')
    with pytest.raises(AcquisitionError,match='UNSUPPORTED_ABI'):NativeLinux()


def test_closed_view_and_forked_owner_rejected(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        monkeypatch.setattr(os,'getpid',lambda:987654)
        with pytest.raises(AcquisitionError,match='OWNER_CHANGED'):view.enumerate()
    with pytest.raises(AcquisitionError,match='VIEW_CLOSED'):view.enumerate()


def test_snapshot_permission_error_is_not_missing_pid_namespace(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        real=view._link
        def denied(parent,field):
            if field=='pid':raise PermissionError(errno.EACCES,'fixture')
            return real(parent,field)
        monkeypatch.setattr(view,'_link',denied)
        result=view.scope()
        assert result['endpoint_checks_pass'] is False
        assert result['errors']['scope']['errno']==errno.EACCES
        assert 'pid_namespace' not in result


def test_deleted_held_generation_never_reopens_replacement(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            (tree/'42').rename(tree/'old42')
            (tree/'42').mkdir();(tree/'42/stat').write_text(stat_text(42,start=900))
            assert actor.identity()['start_ticks']==500
            assert view.probe(42)['start_ticks']==900


def test_intermediate_namespace_symlink_cannot_redirect_scope(tree):
    import shutil
    path=tree/str(os.getpid())/'ns'
    shutil.rmtree(path)
    path.symlink_to('../1/ns',target_is_directory=True)
    with ProcView(tree,native=FixtureNative()) as view:
        assert view.scope()['endpoint_checks_pass'] is False


def test_two_missing_parent_reads_are_not_verified_ancestry(tree):
    (tree/'1/stat').unlink()
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            value=actor.metadata()
        assert value['parent']['before'] is None and value['parent']['after'] is None
        assert value['parent_generation_bracket_pass'] is False


def test_changed_command_rejected_by_double_read(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            original=actor.read
            def change(field):
                raw=original(field)
                if field=='cmdline':(tree/'42/cmdline').write_bytes(b'changed\0')
                return raw
            monkeypatch.setattr(actor,'read',change)
            with pytest.raises(AcquisitionError,match='CMDLINE_CHANGED'):actor.metadata()


def test_descriptor_flags_drift_rejected_even_when_inode_matches(tree):
    import fcntl
    with ProcView(tree,native=FixtureNative()) as view:
        fcntl.fcntl(view._root,fcntl.F_SETFD,0)
        with pytest.raises(AcquisitionError,match='FD_IDENTITY_CHANGED'):view.enumerate()


def test_scope_rejects_changed_boot_between_endpoint_reads(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        original=view._path_read
        def mutate(components):
            raw=original(components)
            (tree/'sys/kernel/random/boot_id').write_text('other-boot\n')
            return raw
        monkeypatch.setattr(view,'_path_read',mutate)
        result=view.scope()
        assert result['endpoint_checks_pass'] is False


def test_scope_rejects_namespace_endpoint_drift(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        original=view._link
        def mutate(parent,field):
            raw=original(parent,field)
            if field=='mnt':
                path=tree/str(os.getpid())/'ns/mnt'
                path.unlink();path.symlink_to('mnt:[5678]')
            return raw
        monkeypatch.setattr(view,'_link',mutate)
        assert view.scope()['endpoint_checks_pass'] is False


def test_nested_owner_enoent_does_not_label_target_missing(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        original=view._guard; calls=0
        def transient():
            nonlocal calls
            calls+=1
            if calls==2:raise FileNotFoundError(errno.ENOENT,'owner fixture')
            return original()
        monkeypatch.setattr(view,'_guard',transient)
        assert view.probe(42)['status']=='UNREADABLE'


def test_native_rejects_full_readlink_buffer_instead_of_truncated_success():
    native=NativeLinux()
    native._rl=lambda fd,path,buf,size:size
    with pytest.raises(AcquisitionError,match='READLINK_LIMIT'):native.link(0)


def test_view_entry_failure_closes_fds(tree,monkeypatch):
    view=ProcView(tree,native=FixtureNative())
    def fail():raise AcquisitionError('fixture')
    monkeypatch.setattr(view,'_guard',fail)
    with pytest.raises(AcquisitionError):view.__enter__()
    assert not view._fds


def test_generation_entry_failure_closes_only_owned_handle(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        base=set(view._fds);actor=view.generation(42)
        def fail():raise AcquisitionError('fixture')
        monkeypatch.setattr(actor,'identity',fail)
        with pytest.raises(AcquisitionError):actor.__enter__()
        assert view._fds==base


def test_long_offline_read_sequence_has_bounded_explicit_audit_retention(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        for _ in range(1000):assert view.probe(42)['status']=='PRESENT'
        log=view.audit()
        assert len(log['operations'])<=512
        assert log['dropped_operations']>0
        assert log['complete'] is False
        assert log['policy_acceptance'] is False


def test_failed_link_attempt_retained_without_raw_exception_text(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            with pytest.raises(FileNotFoundError):actor.link('cwd')
        failed=[r for r in view.audit()['operations'] if r['status']=='FAILED']
        assert any(r['field']=='cwd' and r['error']['errno']==2 for r in failed)
        assert all('No such file' not in str(r) for r in failed)


def test_fatal_metadata_rejection_retains_private_partial_evidence(tree,monkeypatch):
    with ProcView(tree,native=FixtureNative()) as view:
        with view.generation(42) as actor:
            def fail(field):raise AcquisitionError('CROSS_MOUNT')
            monkeypatch.setattr(actor,'read',fail)
            with pytest.raises(AcquisitionError) as caught:actor.metadata()
            assert caught.value.private_partial['identity']['pid']==42


def test_bootstrap_self_symlink_mount_authenticated_before_any_probe(tree):
    class ForeignSelf(FixtureNative):
        def describe(self,fd):
            result=super().describe(fd)
            if os.path.islink(f'/proc/self/fd/{fd}') and os.readlink(f'/proc/self/fd/{fd}').endswith('/self'):
                result['mount_id']=77
            return result
    with pytest.raises(AcquisitionError,match='LINK_CROSS_MOUNT'):ProcView(tree,native=ForeignSelf())


def test_thread_leader_profile_rejects_nonleader_before_fd_acquisition(tree,monkeypatch):
    import threading
    monkeypatch.setattr(threading,'get_native_id',lambda:os.getpid()+1)
    with pytest.raises(AcquisitionError,match='THREAD_PROFILE'):ProcView(tree,native=FixtureNative())


def test_close_attempts_all_handles_and_reports_failure_without_retry(tree,monkeypatch):
    view=ProcView(tree,native=FixtureNative());original=os.close;closed=[]
    def partial(fd):
        original(fd);closed.append(fd)
        if len(closed)==1:raise OSError(errno.EIO,'private fixture text')
    monkeypatch.setattr(os,'close',partial)
    view.close()
    assert not view._fds and len(closed)==3
    assert view.audit()['cleanup_errors']==[{'type':'OSError','errno':errno.EIO}]


def test_backend_provenance_differentiates_fixture_from_native(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        assert view.scope()['acquisition_backend']=='INJECTED_TEST_BACKEND'
    with ProcView() as view:
        assert view.scope()['acquisition_backend']=='NATIVE_GLIBC_LP64_STATX'


def test_failed_directory_lookup_retains_its_phase_in_private_audit(tree):
    with ProcView(tree,native=FixtureNative()) as view:
        assert view.probe(123456)['status']=='NOT_FOUND'
        assert any(r['operation']=='OPEN_DIRECTORY' and r['status']=='FAILED' and r['error']['errno']==2
                   for r in view.audit()['operations'])


def test_generation_entry_cleanup_failure_preserves_original_error(tree,monkeypatch):
    view=ProcView(tree,native=FixtureNative());actor=view.generation(42)
    fd=actor._fd;original=os.close
    def failing_close(number):
        original(number)
        if number==fd:raise OSError(errno.EIO,'cleanup fixture')
    def invalid():raise AcquisitionError('ORIGINAL_FAILURE')
    monkeypatch.setattr(os,'close',failing_close)
    monkeypatch.setattr(actor,'identity',invalid)
    with pytest.raises(AcquisitionError,match='ORIGINAL_FAILURE') as caught:actor.__enter__()
    assert caught.value.private_cleanup_errors[0]['errno']==errno.EIO
    view.close()


def test_scope_interval_includes_initial_guard(tree,monkeypatch):
    import tools.pinned_proc_view as module
    ticks=iter(range(1,100000))
    monkeypatch.setattr(module,'_now',lambda:next(ticks))
    with ProcView(tree,native=FixtureNative()) as view:
        start=view._operation_count
        value=view.scope()
        initial=[row for row in view.audit()['operations'] if row['sequence']>start]
        assert value['start_ns']<=min(row['start_ns'] for row in initial)


def test_native_syscall_failure_has_no_fallback():
    import ctypes
    native=NativeLinux()
    def unsupported(*args):ctypes.set_errno(errno.ENOSYS);return -1
    native._sx=unsupported
    fd=os.open('/proc',os.O_RDONLY|os.O_DIRECTORY)
    try:
        with pytest.raises(OSError) as caught:native.describe(fd)
        assert caught.value.errno==errno.ENOSYS
    finally:os.close(fd)


def test_namespace_backend_enoent_is_not_missing_entry(tree):
    class MissingReadlink(FixtureNative):
        def link(self,fd):
            if os.readlink(f'/proc/self/fd/{fd}').endswith('/ns/pid'):
                raise FileNotFoundError(errno.ENOENT,'native query fixture')
            return super().link(fd)
    with ProcView(tree,native=MissingReadlink()) as view:
        value=view.scope()
        assert value['endpoint_checks_pass'] is False
        assert 'pid_namespace' not in value


def test_read_rejection_and_close_failure_keep_both_errors(tree,monkeypatch):
    (tree/'42/cmdline').write_bytes(b'x'*262145)
    with pytest.raises(AcquisitionError,match='CLEANUP_FAILED'):
        with ProcView(tree,native=FixtureNative()) as view:
            with view.generation(42) as actor:
                original=os.close
                def fail(fd):
                    path=os.readlink(f'/proc/self/fd/{fd}')
                    original(fd)
                    if path.endswith('/42/cmdline'):raise OSError(errno.EIO,'private fixture')
                monkeypatch.setattr(os,'close',fail)
                with pytest.raises(AcquisitionError,match='READ_LIMIT') as caught:actor.read('cmdline')
                assert caught.value.private_cleanup_errors[0]['errno']==errno.EIO
