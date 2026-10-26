import base64
import hashlib
import json
import os
import stat

import pytest

from tools.proc_view_journal import JournalError,PrivateJournal,verify_journal


def test_roundtrip_private_bytes_and_whole_file_anchor(tmp_path):
    path=tmp_path/'events.jsonl'
    with PrivateJournal(path) as journal:
        journal.append('METADATA',{'cmdline':b'private\0payload','uid':123})
        anchor=journal.seal()
    result=verify_journal(path,anchor)
    assert result['complete'] is True and result['events']==3
    assert result['kinds']=={'HEADER':1,'METADATA':1,'END':1}
    assert anchor['sha256']==hashlib.sha256(path.read_bytes()).hexdigest()
    assert stat.S_IMODE(path.stat().st_mode)==0o600
    assert base64.b64encode(b'private\0payload') in path.read_bytes()


def test_existing_file_and_symlink_are_not_overwritten(tmp_path):
    path=tmp_path/'exists';path.write_bytes(b'keep')
    with pytest.raises(FileExistsError):PrivateJournal(path)
    link=tmp_path/'link';link.symlink_to(path)
    with pytest.raises(OSError):PrivateJournal(link)
    assert path.read_bytes()==b'keep'


def test_parent_symlink_and_shared_permissions_rejected(tmp_path):
    parent=tmp_path/'private';parent.mkdir(mode=0o700)
    alias=tmp_path/'alias';alias.symlink_to(parent,target_is_directory=True)
    with pytest.raises((OSError,JournalError)):PrivateJournal(alias/'record')
    parent.chmod(0o755)
    with pytest.raises(JournalError,match='PARENT_PRIVATE'):PrivateJournal(parent/'record')


@pytest.mark.parametrize('tail',[b'',b'\n',b'{}\n'])
def test_truncation_or_extra_bytes_rejected_even_with_original_anchor(tmp_path,tail):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        journal.append('SCAN',{'pids':[1,42]});anchor=journal.seal()
    raw=path.read_bytes()
    path.write_bytes(raw.rsplit(b'\n',2)[0]+b'\n' if tail==b'' else raw+tail)
    with pytest.raises(JournalError):verify_journal(path,anchor)


def test_prefix_with_new_hash_cannot_omit_terminal_marker(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        anchor=journal.seal()
    path.write_bytes(path.read_bytes().splitlines(keepends=True)[0])
    altered={**anchor,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    with pytest.raises(JournalError):verify_journal(path,altered)


@pytest.mark.parametrize('kind,data',[('BAD',{}),('SCAN',{'n':float('nan')}),('SCAN',{'n':float('inf')}),('SCAN',{1:'bad'}),('SCAN',{'n':object()})])
def test_unsupported_payload_rejects_and_poison_seal(tmp_path,kind,data):
    with PrivateJournal(tmp_path/'record') as journal:
        with pytest.raises(JournalError):journal.append(kind,data)
        with pytest.raises(JournalError):journal.seal()


def test_capacity_exhaustion_is_sticky_not_silent_eviction(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path,max_bytes=5000) as journal:
        with pytest.raises(JournalError,match='BUDGET'):journal.append('METADATA',{'blob':'x'*4500})
        with pytest.raises(JournalError):journal.seal()
    assert b'"kind":"END"' not in path.read_bytes()


def test_event_budget_reserves_terminal_and_never_drops(tmp_path):
    with PrivateJournal(tmp_path/'record',max_events=3) as journal:
        journal.append('SCAN',{'pids':[1]})
        with pytest.raises(JournalError,match='BUDGET'):journal.append('SCAN',{'pids':[2]})
        with pytest.raises(JournalError):journal.seal()


def test_short_writes_are_completed_without_packet_loss(tmp_path,monkeypatch):
    original=os.write
    monkeypatch.setattr(os,'write',lambda fd,data:original(fd,data[:7]))
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        journal.append('PROBE',{'pid':42});anchor=journal.seal()
    assert verify_journal(path,anchor)['complete'] is True


def test_write_failure_never_seals_partial_file(tmp_path,monkeypatch):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        monkeypatch.setattr(os,'write',lambda fd,data:0)
        with pytest.raises(JournalError):journal.append('PROBE',{})
        with pytest.raises(JournalError):journal.seal()


def test_fsync_failure_never_returns_anchor(tmp_path,monkeypatch):
    with PrivateJournal(tmp_path/'record') as journal:
        def fail(fd):raise OSError('private error text')
        monkeypatch.setattr(os,'fsync',fail)
        with pytest.raises(JournalError):journal.seal()
        assert journal.state=='FAILED'


def test_duplicate_keys_and_noncanonical_bytes_rejected(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:anchor=journal.seal()
    raw=path.read_bytes().replace(b'"sequence":1',b'"sequence":1,"sequence":1',1)
    path.write_bytes(raw)
    with pytest.raises(JournalError):verify_journal(path,{**anchor,'sha256':hashlib.sha256(raw).hexdigest()})


def test_payload_is_snapshotted_before_caller_mutation(tmp_path):
    path=tmp_path/'record';value={'x':[1,2]}
    with PrivateJournal(path) as journal:
        journal.append('PROBE',value);value['x'].append(99);anchor=journal.seal()
    assert b'99' not in path.read_bytes().splitlines()[1].split(b'"data":')[1].split(b'"kind":')[0]
    assert verify_journal(path,anchor)['complete']


def test_close_failure_cannot_return_anchor_or_be_retried(tmp_path,monkeypatch):
    journal=PrivateJournal(tmp_path/'record');original=os.close;closed=[]
    def fail(fd):
        original(fd);closed.append(fd)
        if len(closed)==1:raise OSError('private close fixture')
    monkeypatch.setattr(os,'close',fail)
    with pytest.raises(JournalError):journal.seal()
    journal.abort()
    assert len(closed)==len(set(closed))==2 and journal.state=='FAILED'


def test_private_file_permissions_and_hardlinks_rechecked(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:anchor=journal.seal()
    alias=tmp_path/'alias';os.link(path,alias)
    with pytest.raises(JournalError):verify_journal(path,anchor)


def test_reentrant_write_callback_poison_cannot_seal(tmp_path,monkeypatch):
    journal=PrivateJournal(tmp_path/'record');original=os.write;inside=[False]
    def nested(fd,data):
        if not inside[0]:
            inside[0]=True
            try:journal.append('PROBE',{'nested':True})
            except JournalError:pass
        return original(fd,data)
    monkeypatch.setattr(os,'write',nested)
    with pytest.raises(JournalError):journal.append('SCAN',{})
    with pytest.raises(JournalError):journal.seal()
    journal.abort()


def test_proc_stream_requires_closed_lifecycle_not_just_file_footer(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        journal.append('PROC_EVENT',{'schema':1,'session':'a'*32,'sequence':1,'timestamp_ns':1,
                                    'event':'VIEW_BEGIN','details':{'backend':'INJECTED_TEST_BACKEND'}})
        anchor=journal.seal()
    with pytest.raises(JournalError):verify_journal(path,anchor)


def test_standalone_file_is_not_semantic_process_completeness(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:anchor=journal.seal()
    result=verify_journal(path,anchor)
    assert result['complete'] is True and result['semantic_complete'] is False


def test_bytes_and_reserved_dictionary_have_distinct_lossless_wire(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        journal.append('METADATA',{'value':b'x'})
        journal.append('METADATA',{'value':{'_bytes_base64':'eA=='}})
        anchor=journal.seal()
    first=json.loads(path.read_bytes().splitlines()[1])['record']['data']
    second=json.loads(path.read_bytes().splitlines()[2])['record']['data']
    assert first!=second
    assert verify_journal(path,anchor)['complete']


def test_replay_reads_no_more_than_trusted_anchor_budget(tmp_path,monkeypatch):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:anchor=journal.seal()
    real=os.fdopen;consumed=[0]
    class Growing:
        def __init__(self,file):self.file=file;self.first=True
        def __enter__(self):return self
        def __exit__(self,*args):self.file.close()
        def readline(self,limit):
            consumed[0]+=limit
            return b'x'*(min(limit,anchor['bytes']+1))
    monkeypatch.setattr(os,'fdopen',lambda *a,**kw:Growing(real(*a,**kw)))
    with pytest.raises(JournalError):verify_journal(path,anchor)
    assert consumed[0]<=anchor['bytes']+1


def test_corruption_error_survives_close_failure_and_all_fds_close(tmp_path,monkeypatch):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:anchor=journal.seal()
    path.write_bytes(path.read_bytes()+b'x')
    before=set(os.listdir('/proc/self/fd'));original=os.close;calls=[]
    def broken(fd):
        name=os.readlink(f'/proc/self/fd/{fd}')
        original(fd);calls.append(fd)
        if name==str(path):raise OSError(5,'private cleanup detail')
    monkeypatch.setattr(os,'close',broken)
    with pytest.raises(JournalError,match='SIZE') as caught:verify_journal(path,anchor)
    assert caught.value.private_cleanup_errors[0]['errno']==5
    assert set(os.listdir('/proc/self/fd'))==before


def test_abort_retains_cleanup_failure_out_of_band(tmp_path,monkeypatch):
    journal=PrivateJournal(tmp_path/'record');original=os.close;calls=[]
    def broken(fd):
        original(fd);calls.append(fd)
        if len(calls)==1:raise OSError(5,'private abort detail')
    monkeypatch.setattr(os,'close',broken)
    journal.abort()
    assert journal.cleanup_errors==[{'type':'OSError','errno':5}] and len(calls)==2


def test_wire_decoder_preserves_bytes_and_escaped_literal_dict():
    import tools.proc_view_journal as module
    value={'bytes':b'a','literal':{'_bytes_base64':'YQ=='},'escaped':{'_dict_items':'literal'}}
    restored=module.decode_wire(module.parse_canonical(module.canonical(value)))
    assert restored==value


@pytest.mark.parametrize('value',[
    {'_bytes_base64':base64.b64encode(b'x'*(1024*1024+1)).decode()},
    {'_dict_items':[['_bytes_base64','literal'],['z'*129,'too long']]},
])
def test_replay_cannot_accept_values_outside_writer_limits(value):
    from tools.proc_view_journal import parse_canonical
    raw=json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    with pytest.raises(JournalError):parse_canonical(raw)


def test_outcome_is_final_semantic_record_before_footer(tmp_path):
    path=tmp_path/'record'
    with PrivateJournal(path) as journal:
        journal.append('OUTCOME',{'status':'BLOCKED_CAPABILITY_OR_SCOPE'})
        journal.append('PROBE',{'pid':42})
        anchor=journal.seal()
    with pytest.raises(JournalError):verify_journal(path,anchor)
