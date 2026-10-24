"""M19-B0 CPU fixtures only. Never contact or change a comma/Jetson."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import types
import sys
import multiprocessing
import stat
import time

import numpy as np
import pytest

from adapters.carrot import recorder_activation as revision
from adapters.carrot.recorder import FOOTER, PACKAGE, recorder_files
from recording import hook as original
from test_v3_input_hook import Spec, Sink, fake_namespace, frame

REPO = Path(__file__).resolve().parents[1]
REFERENCE = REPO / '.reference/m15-carrot-nav-366d6eae'


@pytest.fixture(scope='session')
def candidate_files():
    return revision.activation_files(REFERENCE)


@pytest.fixture
def activated_module(tmp_path, monkeypatch, candidate_files):
    files = candidate_files
    for name, data in files.items():
        q = tmp_path / name
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(data)
    path = tmp_path / PACKAGE / 'hook.py'
    spec = importlib.util.spec_from_file_location('recording._activation_fixture', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    directory = tmp_path / 'volatile-parent' / 'carrot-v3-input-capture'
    directory.parent.mkdir()
    monkeypatch.setattr(module, 'DISCOVERY_DIRECTORY', directory)
    # Filesystem mount/parent ownership is a separately tested contract. These
    # local temp files are FIXTURE storage, never claimed to be device tmpfs.
    monkeypatch.setattr(module, '_require_volatile_parent', lambda: None)
    # Unit observer fixtures are not running inside the actual manager child.
    # The real guard is exercised separately by source-backed fork fixtures.
    module._unpatched_context_check = getattr(module, '_modeld_import_context', None)
    monkeypatch.setattr(module, '_modeld_import_context', lambda namespace: True, raising=False)
    monkeypatch.setattr(module, '_boot_id', lambda: 'fixture-boot')
    monkeypatch.delenv('CARROT_V3_INPUT_CAPTURE', raising=False)
    return module


def arm(module, tmp_path, **kwargs):
    out = tmp_path / 'outputs'
    out.mkdir(exist_ok=True)
    return module.arm_discovered(output_root=out, source_model_sha=Spec.sha256,
        source_spec_sha=hashlib.sha256(module.canonical(Spec().to_dict())).hexdigest(),
        offroad=True, frames=10, depth=4, **kwargs)


def install(module, *, sink=None, verifier=None, spec=None):
    ns = fake_namespace(spec)
    sink = sink or Sink()
    state = module.install_discovered(ns, recorder_factory=lambda *a, **k: sink,
                                     source_verifier=verifier or (lambda ns: None))
    return ns, state, sink


def test_three_profiles_and_two_file_delta(tmp_path):
    before = recorder_files(REFERENCE)
    after = revision.activation_files(REFERENCE)
    assert set(after) == set(before)
    assert {n for n in before if before[n] != after[n]} == {original.MODEL, PACKAGE + '/hook.py'}
    assert before[original.MODEL].endswith(FOOTER.encode())
    assert hashlib.sha256((REPO / 'patches/carrot-nav-v3-input-recorder.patch').read_bytes()).hexdigest() == revision.M18_PATCH_SHA
    destination = tmp_path / 'candidate'
    manifest = revision.build_activation_candidate(REFERENCE, destination)
    forward = (destination / '.activation-v2/forward.patch').read_bytes()
    reverse = (destination / '.activation-v2/reverse.patch').read_bytes()
    assert manifest['profile'] == 'M19A_TO_ACTIVATION_V2_OFFLINE_ONLY'
    assert len(manifest['touched_files']) == 2
    for n, b in before.items():
        q = tmp_path / 'roundtrip' / n
        q.parent.mkdir(parents=True, exist_ok=True)
        q.write_bytes(b)
    target = tmp_path / 'roundtrip'
    for patch, expected in ((forward, after), (reverse, before)):
        subprocess.run(['git', '-C', str(target), 'apply', '--check', '-'], input=patch, check=True)
        subprocess.run(['git', '-C', str(target), 'apply', '-'], input=patch, check=True)
        assert {n: (target/n).read_bytes() for n in expected} == expected
    m18 = (REPO / 'patches/carrot-nav-v3-input-recorder.patch').read_bytes()
    subprocess.run(['git', '-C', str(target), 'apply', '--reverse', '--check', '-'], input=m18, check=True)
    subprocess.run(['git', '-C', str(target), 'apply', '--reverse', '-'], input=m18, check=True)
    assert hashlib.sha256((target/original.MODEL).read_bytes()).hexdigest() == original.SOURCE_PINS[original.MODEL]
    assert not (target/PACKAGE).exists()


def test_existing_hook_functions_and_observer_class_are_frozen(candidate_files):
    before=ast.parse((REPO/'recording/hook.py').read_bytes())
    after=ast.parse(candidate_files[PACKAGE+'/hook.py'])
    after_by_name={n.name:n for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
    for node in before.body:
        if isinstance(node,(ast.FunctionDef,ast.ClassDef)) and node.name!='install':
            assert ast.dump(node)==ast.dump(after_by_name[node.name])


def test_original_model_ast_and_missing_ticket_footer(tmp_path):
    raw = revision.activation_files(REFERENCE)[original.MODEL]
    tree = ast.parse(raw)
    base = subprocess.check_output(['git', '-C', str(REFERENCE), 'show', original.BASE_SHA+':'+original.MODEL])
    assert ast.dump(ast.Module(body=tree.body[:-1], type_ignores=[])) == ast.dump(ast.parse(base))
    calls = []
    def missing(path):
        calls.append(path)
        raise FileNotFoundError
    def trap(*a, **k):
        raise AssertionError('missing ticket must not import')
    objects = {n: object() for n in ('JoiningModel', 'Warp', 'Client', 'CameraGapTrace')}
    ctx = {**objects, 'os': types.SimpleNamespace(lstat=missing), '__builtins__': {'__import__': trap, 'OSError': OSError, 'Exception': Exception}}
    exec(compile(ast.Module(body=[tree.body[-1]], type_ignores=[]), '<OFF-footer-fixture>', 'exec'), ctx)
    assert calls == ['/dev/shm/carrot-v3-input-capture/arm.ticket']
    assert all(ctx[k] is v for k, v in objects.items())


def test_unexpected_discovery_exception_is_also_observer_only(candidate_files):
    tree=ast.parse(candidate_files[original.MODEL])
    def broken(path): raise RuntimeError('fixture audit-hook error')
    objects={n:object() for n in ('JoiningModel','Warp','Client','CameraGapTrace')}
    ctx={**objects,'os':types.SimpleNamespace(lstat=broken)}
    exec(compile(ast.Module(body=[tree.body[-1]],type_ignores=[]),'<OFF-footer-fault>', 'exec'),ctx)
    assert all(ctx[k] is v for k,v in objects.items())


def test_no_ticket_has_no_recorder_work(activated_module):
    m = activated_module
    ns, state, sink = install(m)
    assert state is None and sink.records == [] and sink.stops == []
    assert not m.DISCOVERY_DIRECTORY.exists()


def test_valid_ticket_activates_once_without_environment(activated_module, tmp_path):
    m = activated_module
    value = arm(m, tmp_path)
    ns, state, sink = install(m)
    assert state is not None
    assert not (m.DISCOVERY_DIRECTORY/'arm.ticket').exists()
    assert (m.DISCOVERY_DIRECTORY/'arm.ticket.consumed').exists()
    assert (m.DISCOVERY_DIRECTORY/('.capture-'+value['capture_id']+'.consumed')).exists()
    image, _, _, _ = frame(ns)
    c = ns['Client']()
    assert c.infer(image, np.zeros(28, dtype=np.float32), 1) is c
    assert len(sink.records) == 1
    assert install(m)[1] is None


@pytest.mark.parametrize('offroad', [False, 0, None])
def test_arm_requires_true_external_offroad(activated_module, tmp_path, offroad):
    m = activated_module
    with pytest.raises(ValueError):
        m.arm_discovered(output_root=tmp_path, source_model_sha='1'*64, source_spec_sha='2'*64, offroad=offroad)
    assert not m.DISCOVERY_DIRECTORY.exists()


@pytest.mark.parametrize('seconds', [0, 301, True])
def test_expiry_maximum_not_relaxed(activated_module, tmp_path, seconds):
    with pytest.raises(ValueError):
        arm(activated_module, tmp_path, expires_seconds=seconds)


@pytest.mark.parametrize('kind', ['expired', 'boot', 'malformed', 'moved', 'duplicate-json', 'oversize'])
def test_invalid_owned_tickets_fail_recorder_only(activated_module, tmp_path, kind):
    m = activated_module
    v = arm(m, tmp_path)
    path = m.DISCOVERY_DIRECTORY/'arm.ticket'
    if kind == 'expired':
        v['armed_monotonic_ns'] = 0; v['expires_monotonic_ns'] = 1
        path.write_bytes(m.canonical(v))
    elif kind == 'boot':
        v['boot_id'] = 'wrong-boot'; path.write_bytes(m.canonical(v))
    elif kind == 'malformed': path.write_bytes(b'{bad')
    elif kind == 'moved':
        v['ticket_path'] = str(tmp_path/'different-ticket'); path.write_bytes(m.canonical(v))
    elif kind == 'duplicate-json': path.write_bytes(path.read_bytes()[:-1]+b',"schema":1}')
    else: path.write_bytes(b'x'*8193)
    ns, state, sink = install(m)
    assert state is None and sink.records == []
    assert not path.exists()
    assert install(m)[1] is None
    c = ns['Client']()
    assert c.infer(None, np.zeros(28, dtype=np.float32), 0) is c


@pytest.mark.parametrize('kind', ['symlink', 'fifo', 'file-mode', 'directory-mode', 'hardlink'])
def test_unsafe_filesystem_object_is_not_followed_or_removed(activated_module, tmp_path, kind):
    m = activated_module
    arm(m, tmp_path)
    path = m.DISCOVERY_DIRECTORY/'arm.ticket'
    if kind in ('symlink', 'fifo'):
        path.unlink()
        if kind == 'symlink': path.symlink_to(tmp_path/'do-not-touch')
        else: os.mkfifo(path, 0o600)
    elif kind == 'file-mode': path.chmod(0o644)
    elif kind == 'directory-mode': m.DISCOVERY_DIRECTORY.chmod(0o755)
    else: os.link(path, tmp_path/'hardlink')
    assert install(m)[1] is None
    assert os.path.lexists(path)
    assert not (tmp_path/'do-not-touch').exists()


def test_source_drift_consumes_without_changing_model(activated_module, tmp_path):
    m = activated_module
    arm(m, tmp_path)
    def reject(ns): raise ValueError('source drift')
    ns, state, sink = install(m, verifier=reject)
    assert state is None
    assert not (m.DISCOVERY_DIRECTORY/'arm.ticket').exists()
    c = ns['Client']()
    failure = RuntimeError('original exception')
    c.failure = failure
    with pytest.raises(RuntimeError) as e: c.infer(None, np.zeros(28, dtype=np.float32), 0)
    assert e.value is failure


def test_enabled_infer_exception_identity_is_unchanged(activated_module,tmp_path):
    m=activated_module;arm(m,tmp_path);ns,state,sink=install(m)
    assert state is not None
    image,_,_,_=frame(ns);client=ns['Client']();failure=RuntimeError('existing infer failure');client.failure=failure
    with pytest.raises(RuntimeError) as caught:client.infer(image,np.zeros(28,dtype=np.float32),0)
    assert caught.value is failure and len(client.calls)==1


@pytest.mark.parametrize('field', ['sha256', 'checkpoint'])
def test_source_identity_or_spec_drift_stops_observer(activated_module, tmp_path, field):
    m = activated_module
    arm(m, tmp_path)
    s = Spec(); setattr(s, field, 'changed')
    ns, state, sink = install(m, spec=s)
    c = ns['Client']()
    assert state.disabled and sink.stops
    assert c.infer(None, np.zeros(28, dtype=np.float32), 0) is c
    assert install(m)[1] is None


@pytest.mark.parametrize('failure', ['output-collision', 'writer-start', 'writer-observe'])
def test_recorder_failure_never_rearms_or_changes_infer(activated_module, tmp_path, failure):
    m = activated_module
    v = arm(m, tmp_path)
    if failure == 'output-collision': Path(v['output']).mkdir()
    class Bad(Sink):
        def observe(self, *a): raise OSError('writer stopped')
    if failure == 'writer-start':
        ns = fake_namespace()
        def bad_factory(*a, **k): raise OSError('writer start')
        state = m.install_discovered(ns, recorder_factory=bad_factory, source_verifier=lambda ns: None)
        assert state is None
    else:
        ns, state, sink = install(m, sink=Bad())
        if state is not None:
            image, _, _, _ = frame(ns)
            c = ns['Client']()
            assert c.infer(image, np.zeros(28, dtype=np.float32), 0) is c
            assert state.disabled
    assert install(m)[1] is None


def test_consumed_marker_prevents_implicit_rearm(activated_module, tmp_path):
    m = activated_module
    arm(m, tmp_path)
    assert install(m)[1] is not None
    with pytest.raises((ValueError, FileExistsError)):
        arm(m, tmp_path)


def test_stale_environment_cannot_choose_another_ticket(activated_module, tmp_path, monkeypatch):
    m = activated_module
    arm(m, tmp_path)
    monkeypatch.setenv('CARROT_V3_INPUT_CAPTURE', str(tmp_path/'unrelated'))
    assert install(m)[1] is not None


def test_non_modeld_import_must_leave_ticket_for_normal_child(activated_module, tmp_path, monkeypatch):
    m = activated_module
    arm(m, tmp_path)
    monkeypatch.setattr(m, '_modeld_import_context', lambda namespace: False)
    assert install(m)[1] is None
    assert (m.DISCOVERY_DIRECTORY/'arm.ticket').exists()
    assert not (m.DISCOVERY_DIRECTORY/'arm.ticket.consumed').exists()


def test_real_context_guard_rejects_test_runner(activated_module):
    m = activated_module
    assert m._unpatched_context_check is not None
    assert m._unpatched_context_check(fake_namespace()) is False


@pytest.mark.parametrize('kind',['uid','gid','directory-symlink'])
def test_directory_identity_drift_never_consumes(activated_module,tmp_path,monkeypatch,kind):
    m=activated_module;arm(m,tmp_path);path=m.DISCOVERY_DIRECTORY/'arm.ticket'
    if kind=='uid':
        uid=os.geteuid();monkeypatch.setattr(m.os,'geteuid',lambda:uid+1)
    elif kind=='gid':
        gid=os.getegid();monkeypatch.setattr(m.os,'getegid',lambda:gid+1)
    else:
        original_dir=m.DISCOVERY_DIRECTORY
        alias=original_dir.with_name('alias');alias.symlink_to(original_dir,target_is_directory=True)
        monkeypatch.setattr(m,'DISCOVERY_DIRECTORY',alias)
    assert install(m)[1] is None
    assert path.exists()


@pytest.mark.parametrize('mount', ['tmpfs','ext4','missing','duplicate'])
def test_volatile_mount_gate(activated_module,monkeypatch,mount):
    m=activated_module
    monkeypatch.setattr(m,'DISCOVERY_DIRECTORY',Path('/dev/shm/carrot-v3-input-capture'))
    # Extract the unmodified implementation, not the unit fixture override.
    ns={};exec('from pathlib import Path\nimport os,stat\n'+revision.HOOK_EXTENSION.split('def _require_volatile_parent():',1)[0],ns)
    source='def _require_volatile_parent():'+revision.HOOK_EXTENSION.split('def _require_volatile_parent():',1)[1].split('\n\ndef _discovery_directory',1)[0]
    ns.update(_no_symlinks=original._no_symlinks)
    exec(source,ns)
    real=Path.read_text
    def text(path,*args,**kwargs):
        if str(path)=='/proc/self/mountinfo':
            line='10 1 0:1 / /dev/shm rw - '+('tmpfs' if mount in ('tmpfs','duplicate') else 'ext4')+' fixture rw\n'
            return '' if mount=='missing' else line* (2 if mount=='duplicate' else 1)
        return real(path,*args,**kwargs)
    monkeypatch.setattr(Path,'read_text',text)
    if mount=='tmpfs':ns['_require_volatile_parent']()
    else:
        with pytest.raises(ValueError):ns['_require_volatile_parent']()


def test_concurrent_consumers_have_one_winner(activated_module,tmp_path):
    m=activated_module;arm(m,tmp_path)
    context=multiprocessing.get_context('fork');queue=context.Queue()
    def worker():queue.put(install(m)[1] is not None)
    children=[context.Process(target=worker) for _ in range(2)]
    for p in children:p.start()
    for p in children:p.join(10);assert p.exitcode==0
    assert sorted(queue.get(timeout=2) for _ in children)==[False,True]
    queue.close();queue.join_thread()


def test_capture_id_claim_blocks_copied_consumed_ticket(activated_module,tmp_path):
    m=activated_module;arm(m,tmp_path);path=m.DISCOVERY_DIRECTORY/'arm.ticket';raw=path.read_bytes()
    assert install(m)[1] is not None
    # Simulated incomplete cleanup in private fixture: ID claim still exists.
    path.with_name('arm.ticket.consumed').unlink()
    fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as f:f.write(raw)
    assert install(m)[1] is None
    assert not path.exists()


def test_activation_v2_real_host_writer_complete10_and_exact_reader(activated_module,tmp_path):
    from recording.dataset import Dataset
    m=activated_module;value=arm(m,tmp_path);ns=fake_namespace()
    state=m.install_discovered(ns,source_verifier=lambda ns:None)
    assert state is not None
    rec=state.recorder;deadline=time.monotonic()+8
    while not rec.ready and rec.reason is None and time.monotonic()<deadline:
        rec.poll();time.sleep(.005)
    snapshots=[]
    try:
        assert rec.ready
        client=ns['Client']()
        for i in range(10):
            image,_,_,_=frame(ns,fid=17+i)
            packed=np.arange(28,dtype=np.float32);packed[0]=-0.0
            snapshots.append((image.tobytes(),packed[:8].tobytes()))
            assert client.infer(image,packed,i,reset=i==0) is client
            time.sleep(.05)
        assert rec.count==10 and state.disabled
    finally:rec.close(timeout=10)
    assert rec.reason is None
    with Dataset(value['output']) as dataset:
        assert len(dataset)==10
        for i,expected in enumerate(snapshots):
            feed=dataset.ort_feeds(i)
            assert feed['new_img'].tobytes()==expected[0] and feed['desire'].tobytes()==expected[1]
    assert install(m)[1] is None


def test_candidate_destination_cannot_overwrite(tmp_path):
    destination = tmp_path/'existing'; destination.mkdir(); keep=destination/'keep';keep.write_bytes(b'user')
    with pytest.raises(ValueError): revision.build_activation_candidate(REFERENCE, destination)
    assert keep.read_bytes() == b'user'


@pytest.mark.parametrize('strategy,environment,helper,outcome,expected', [
    ('B','none','no','complete',[True,False]),
    ('B','none','yes','complete',[True,False]),
    ('B','none','yes','failed',[True,False]),
    ('B','none','no','source_drift',[False,False]),
    ('A','inherited','no','complete',[True,False]),
    ('A','shell_only','no','complete',[False,False]),
    ('A','inherited','yes','complete',[False,False]),
])
def test_source_backed_real_fork_import_choreography(tmp_path, strategy, environment, helper, outcome, expected):
    command=[sys.executable,'-B',str(REPO/'tests/fixtures/recorder_activation_fork.py'),
             str(REFERENCE),str(tmp_path/'fork-root'),strategy,environment,helper,outcome]
    result=subprocess.run(command,cwd=REPO,capture_output=True,text=True,timeout=40,
                          env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'})
    assert result.returncode==0,result.stderr
    value=json.loads(result.stdout.strip().splitlines()[-1])
    assert value['fork_start_method']=='fork'
    assert value['manager_preimport_target'] is False and value['offroad_modeld_started'] is False
    assert value['parent_target_after_children'] is False
    children=[r for r in value['events'] if r['actor']=='modeld']
    assert [r['active'] for r in children]==expected
    if strategy=='B':
        assert value['manager_capture_env_after'] is False
        assert value['ticket_remaining'] is (outcome=='source_drift')
        if helper=='yes':
            assert next(r for r in value['events'] if r['actor']=='prepare_helper')['ticket_remaining'] is True
    elif environment=='inherited':
        assert value['manager_capture_env_after'] is True
        if helper=='yes':
            assert next(r for r in value['events'] if r['actor']=='prepare_helper')['ticket_remaining'] is False
    else:
        assert value['ticket_remaining'] is True
