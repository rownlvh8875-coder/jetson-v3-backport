"""CPU_FAKE only: no FunctionFS, USB, io_setup/io_submit/io_getevents/io_destroy.

The writer/controller and native ABI arrays are real; only kernel queue calls
are replaced. External-source characterization uses a separate interpreter.
"""
import ctypes
import errno
import gc
import importlib
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import threading
import time
import weakref

import pytest

ROOT = Path(__file__).resolve().parents[1]


def modules():
    path = ROOT / 'experimental/jetson_optimizations/ffs_aio.py'
    assert path.is_file(), 'isolated AIO controller has not been implemented'
    return (importlib.import_module('experimental.jetson_optimizations.ffs_aio'),
            importlib.import_module('experimental.jetson_optimizations.aio_writer_native'))


class FakeQueue:
    """Hardware boundary with terminal events and an inspectable byte stream."""
    def __init__(self, fd, depth):
        self.depth = depth
        self.events = queue.Queue()
        self.accepted = []
        self.stream = bytearray()
        self.submissions = []
        self.actions = []
        self.closed = False
        self.acked = []
        self.auto = True
        self.result2 = 0
        self.entered, self.release = threading.Event(), threading.Event()

    def submit(self, requests):
        self.submissions.append(tuple((token, len(data)) for token, data in requests))
        action = self.actions.pop(0) if self.actions else len(requests)
        if action == 'block':
            self.entered.set()
            assert self.release.wait(2), 'test must release the CPU fake submit'
            action = len(requests)
        if isinstance(action, BaseException):
            raise action
        if type(action) is not int or not 0 < action <= len(requests):
            return action
        for token, data in requests[:action]:
            self.accepted.append(token)
            self.stream.extend(data)
            if self.auto:
                self.events.put((token, len(data), len(data) if self.result2 == 'same' else self.result2))
        return action

    def reap(self, minimum, timeout):
        try:
            value = self.events.get(timeout=timeout)
        except queue.Empty:
            return []
        if isinstance(value, BaseException):
            raise value
        return [value]

    def complete(self, token):
        self.acked.append(token)

    def close(self):
        self.closed = True


def writer(auto=True, abort=None):
    mod, _ = modules()
    fake = FakeQueue(7, 32)
    fake.auto = auto
    failures = []
    value = mod.AioWriter(7, abort or (lambda: failures.append('abort')),
                          factory=lambda fd, depth: fake, enabled=True)
    return value, fake, failures


def until(predicate, timeout=1):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(.002)
    assert predicate(), 'CPU fake did not reach the expected controller state'


def failed_close(value, monkeypatch):
    mod, _ = modules()
    monkeypatch.setattr(mod, 'CLOSE_TIMEOUT', .03)
    with pytest.raises(mod.AioCleanupError):
        value.close()


def test_aio_is_disabled_without_explicit_guard_and_factory_never_called():
    mod, native = modules()
    with pytest.raises(mod.AioWriteError):
        mod.AioWriter(7, lambda: None, factory=lambda *args: pytest.fail('factory called'))
    with pytest.raises(RuntimeError):
        native.Aio(7, 32)


@pytest.mark.parametrize('secondary', [0, 'same'])
def test_complete_framed_parts_preserve_bytes_and_both_kernel_result_forms(secondary):
    value, fake, _ = writer()
    fake.result2 = secondary
    parts = [b'HEADER', bytes(range(256)) * 260, b'INFER', b'padding']
    assert value.write([memoryview(p) for p in parts], time.monotonic() + 1) == 66578
    until(lambda: value.retained_bytes == 0)
    value.check()
    value.close()
    assert bytes(fake.stream) == b''.join(parts)
    assert [length for batch in fake.submissions for _, length in batch] == [32768, 32768, 1042]
    assert fake.closed


def test_partial_submit_and_eagain_never_resend_an_accepted_prefix():
    value, fake, _ = writer()
    fake.actions = [1, BlockingIOError(errno.EAGAIN, 'queue full'), 1]
    payload = b'A' * 32768 + b'B' * 32768 + b'C' * 19
    value.write([memoryview(payload)], time.monotonic() + 1)
    until(lambda: value.retained_bytes == 0)
    value.close()
    assert bytes(fake.stream) == payload
    assert len(fake.accepted) == len(set(fake.accepted)) == 3


def test_pending_payloads_remain_bounded_until_all_completions(monkeypatch):
    value, fake, _ = writer(auto=False)
    done, errors = threading.Event(), []
    payload = memoryview(bytes(range(256)) * (32 * 160))
    def send():
        try:
            value.write([payload], time.monotonic() + 2)
        except BaseException as exc:
            errors.append(exc)
        finally:
            done.set()
    thread = threading.Thread(target=send)
    thread.start()
    seen = set()
    max_bytes = 0
    while not done.is_set() or value.retained_bytes:
        max_bytes = max(max_bytes, value.retained_bytes)
        assert value.retained_bytes <= 1048576
        assert len(value.pending) <= 32
        for token, length in [p for batch in list(fake.submissions) for p in batch]:
            if token not in seen and token in fake.accepted:
                seen.add(token)
                fake.events.put((token, length, 0))
        if errors:
            raise errors[0]
        time.sleep(.001)
    thread.join(1)
    value.close()
    assert max_bytes == 1048576 and bytes(fake.stream) == payload.tobytes()


@pytest.mark.parametrize('event', [(1, 9, 0), (1, -5, 0), (1, 10, 4),
                                  (99, 10, 0), (1, 10), ('1', 10, 0)])
def test_bad_completions_abort_once_and_quarantine_without_fallback(event, monkeypatch):
    value, fake, aborts = writer(auto=False)
    value.write([memoryview(b'0123456789')], time.monotonic() + 1)
    fake.events.put(event)
    until(lambda: value.error is not None)
    with pytest.raises(modules()[0].AioWriteError):
        value.write([memoryview(b'RESEND')], time.monotonic() + 1)
    failed_close(value, monkeypatch)
    assert value.retained_bytes == 10 and not fake.closed
    assert bytes(fake.stream) == b'0123456789' and aborts == ['abort']


def test_timeout_reaper_failure_and_abort_failure_keep_live_buffers(monkeypatch):
    def bad_abort():
        raise OSError('endpoint disable failed')
    value, fake, _ = writer(auto=False, abort=bad_abort)
    value.write([memoryview(b'data')], time.monotonic() + .03)
    until(lambda: value.error is not None)
    until(lambda: not value.thread.is_alive())
    failed_close(value, monkeypatch)
    assert value.retained_bytes == 4 and not fake.closed and value.abort_error
    second, kernel, _ = writer(auto=False)
    second.write([memoryview(b'data')], time.monotonic() + 1)
    kernel.events.put(OSError('io_getevents failed'))
    until(lambda: second.error is not None)
    failed_close(second, monkeypatch)
    assert second.retained_bytes == 4 and not kernel.closed


@pytest.mark.parametrize('count', [0, -1, 33, True])
def test_invalid_submission_count_preserves_uncertain_ownership(count, monkeypatch):
    value, fake, aborts = writer()
    fake.actions = [count]
    with pytest.raises(modules()[0].AioWriteError):
        value.write([memoryview(b'data')], time.monotonic() + 1)
    failed_close(value, monkeypatch)
    assert value.retained_bytes == 4 and not fake.closed and aborts == ['abort']


def test_close_does_not_wait_for_cv_held_by_blocked_submit_or_destroy_its_context(monkeypatch):
    value, fake, _ = writer(auto=False)
    fake.actions = ['block']
    errors = []
    def send():
        try:
            value.write([memoryview(b'data')], time.monotonic() + 1)
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=send)
    thread.start()
    assert fake.entered.wait(1)
    started = time.monotonic()
    failed_close(value, monkeypatch)
    assert time.monotonic() - started < .3 and not fake.closed
    fake.release.set()
    thread.join(1)
    assert not thread.is_alive() and errors and value.retained_bytes == 4


def test_foreign_submitter_is_rejected_without_interleaving_messages():
    value, fake, _ = writer()
    value.write([memoryview(b'first')], time.monotonic() + 1)
    until(lambda: not value.pending)
    errors = []
    def send():
        try:
            value.write([memoryview(b'foreign')], time.monotonic() + 1)
        except BaseException as exc:
            errors.append(exc)
    thread = threading.Thread(target=send)
    thread.start(); thread.join(1)
    value.close()
    assert errors and bytes(fake.stream) == b'first'


def test_completion_after_absolute_deadline_is_not_accepted_as_success():
    value, fake, _ = writer(auto=False)
    original = fake.reap
    def delayed(minimum, timeout):
        event = original(minimum, 1)
        time.sleep(.04)
        return event
    fake.reap = delayed
    value.write([memoryview(b'data')], time.monotonic() + .02)
    fake.events.put((1, 4, 0))
    until(lambda: value.error is not None or value.retained_bytes == 0)
    assert value.error is not None, 'a late terminal event must not extend the send deadline'
    with pytest.raises(modules()[0].AioCleanupError):
        value.close()


def test_completion_during_submit_waits_for_registration_without_false_unknown_token():
    value, fake, _ = writer(auto=False)
    original_submit, original_reap = fake.submit, fake.reap
    fetched = threading.Event()
    def reap(minimum, timeout):
        result = original_reap(minimum, timeout)
        if result:
            fetched.set()
        return result
    def submit(requests):
        result = original_submit(requests)
        token, data = requests[0]
        fake.events.put((token, len(data), 0))
        assert fetched.wait(1)
        time.sleep(.02)  # Kernel returns completion before io_submit returns.
        return result
    fake.reap = reap
    value.write([memoryview(b'first')], time.monotonic() + 1)
    fake.submit = submit
    value.write([memoryview(b'second')], time.monotonic() + 1)
    fake.events.put((1, 5, 0))
    until(lambda: not value.pending or value.error is not None)
    value.check()
    value.close()
    assert bytes(fake.stream) == b'firstsecond'


class FakeSyscalls:
    def __init__(self):
        self.destroy_fail = False
        self.submitted = []
        self.completions = []
        self.actions = []
        self.event_count = None
    def __call__(self, number, *args):
        number = number.value
        # x86_64 only in this CPU ABI fixture; no libc dispatch.
        if number == 206:
            ctypes.cast(args[1], ctypes.POINTER(ctypes.c_ulong))[0] = 7
            return 0
        if number == 207:
            if self.destroy_fail:
                raise OSError(errno.EBUSY, 'kernel still owns context')
            return 0
        if number == 209:
            count = args[1].value
            accepted = self.actions.pop(0) if self.actions else count
            if isinstance(accepted, BaseException):
                raise accepted
            self.submitted.extend((args[2][i].contents.data, ctypes.addressof(args[2][i].contents))
                                  for i in range(min(count, max(0, accepted))))
            return accepted
        if number == 208:
            if self.event_count is not None:
                return self.event_count
            events = args[3]
            for i, (token, result, result2) in enumerate(self.completions):
                events[i].data, events[i].res, events[i].res2 = token, result, result2
            count = len(self.completions); self.completions = []
            return count
        raise AssertionError('unexpected CPU fake syscall')


def test_native_slots_and_readonly_export_owners_survive_until_completion():
    _, native = modules()
    calls = FakeSyscalls()
    value = native.Aio(7, 32, enabled=True, syscall=calls, machine='x86_64')
    payload = bytearray(b'abcd')
    value.submit([(1, payload)])
    with pytest.raises(BufferError):
        payload.extend(b'x')
    value.submit([(2, b'efgh')])
    assert calls.submitted[0][1] != calls.submitted[1][1]
    with pytest.raises(RuntimeError):
        value.close()
    calls.completions = [(2, 4, 4), (1, 4, 0)]
    assert value.reap(1, .01) == [(2, 4, 4), (1, 4, 0)]
    value.complete(2); value.complete(1)
    payload.extend(b'x')
    value.submit([(3, b'last')])
    assert len({token for token, _ in calls.submitted}) == 3
    value.complete(3)
    value.close()


def test_native_destroy_failure_keeps_context_for_retry_and_bad_event_count_is_quarantined():
    _, native = modules()
    calls = FakeSyscalls()
    value = native.Aio(7, 32, enabled=True, syscall=calls, machine='x86_64')
    calls.destroy_fail = True
    with pytest.raises(OSError):
        value.close()
    assert value.context != 0
    calls.destroy_fail = False
    value.close()
    assert value.context == 0


def test_native_partial_submit_and_eagain_reuse_only_unsubmitted_slots_and_tokens():
    _, native = modules()
    calls = FakeSyscalls()
    calls.actions = [1, BlockingIOError(errno.EAGAIN, 'CPU queue full'), 1]
    value = native.Aio(7, 32, enabled=True, syscall=calls, machine='x86_64')
    assert value.submit([(1, b'first'), (2, b'next')]) == 1
    with pytest.raises(BlockingIOError):
        value.submit([(2, b'next')])
    assert value.submit([(2, b'next')]) == 1
    assert [token for token, _ in calls.submitted] == [1, 2]
    assert calls.submitted[0][1] != calls.submitted[1][1]
    value.complete(1); value.complete(2)
    with pytest.raises(ValueError):
        value.submit([(1, b'reused')])
    value.close()


@pytest.mark.parametrize('failure', ['submit-count', 'event-count'])
def test_native_bad_kernel_counts_keep_owner_and_refuse_context_destroy(failure):
    _, native = modules()
    calls = FakeSyscalls()
    value = native.Aio(7, 32, enabled=True, syscall=calls, machine='x86_64')
    data = bytearray(b'kept')
    if failure == 'submit-count':
        calls.actions = [33]
        with pytest.raises(RuntimeError):
            value.submit([(1, data)])
    else:
        value.submit([(1, data)])
        calls.event_count = 33
        with pytest.raises(RuntimeError):
            value.reap(1, .01)
    with pytest.raises(RuntimeError):
        value.close()
    with pytest.raises(BufferError):
        data.extend(b'no-free')
    assert value.context == 7


def test_failed_cleanup_cannot_free_native_owners_when_caller_drops_object():
    _, native = modules()
    calls = FakeSyscalls()
    value = native.Aio(7, 32, enabled=True, syscall=calls, machine='x86_64')
    data = bytearray(b'kernel-owned')
    value.submit([(1, data)])
    with pytest.raises(RuntimeError):
        value.close()
    reference = weakref.ref(value)
    del value
    gc.collect()
    assert reference() is not None, 'failed close must quarantine the context and exporters'
    with pytest.raises(BufferError):
        data.extend(b'x')


def test_failed_writer_cleanup_retains_payloads_after_caller_drops_object(monkeypatch):
    value, fake, _ = writer(auto=False)
    value.write([memoryview(b'kernel-owned')], time.monotonic() + .02)
    until(lambda: value.error is not None)
    failed_close(value, monkeypatch)
    reference = weakref.ref(value)
    del value
    gc.collect()
    assert reference() is not None and reference().retained_bytes == 12
    assert not fake.closed


def external_destroy_failure_characterization():
    """Manual source audit; excluded from portable tests requiring no checkout."""
    source = ROOT / '.reference/jetson-review-a890/third_party/jetlink/jetlink/transport/aio_writer_native.py'
    assert source.is_file()
    code = '''import ctypes,importlib.util,json,sys
spec=importlib.util.spec_from_file_location('external_native',sys.argv[1])
mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
value=mod.Aio.__new__(mod.Aio);value._ctx=ctypes.c_ulong(7);value._destroy=207
def failure(*args):raise OSError('CPU_FAKE destroy rejected')
value._call=failure
try:value.close()
except OSError:pass
print(json.dumps({'context_after_failure':value._ctx.value}))
'''
    result = subprocess.run([sys.executable, '-c', code, str(source)], capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)['context_after_failure'] == 0


@pytest.mark.parametrize('version,fault', [(2, False), (3, False), (3, True)])
def test_current_stream_framing_executes_with_only_native_queue_substituted(tmp_path, version, fault):
    reference = Path(os.environ.get('CARROT_REFERENCE_ROOT', ROOT / '.reference/carrot-wip-ba186'))
    candidate = Path(os.environ.get('CARROT_CANDIDATE_ROOT', reference))
    package = candidate / 'third_party/jetlink'
    assert (package / 'jetlink/transport/base.py').is_file(), 'provide the current-source candidate'
    code = '''import errno,json,runpy,sys,time
from pathlib import Path
from jetlink import protocol as P
from jetlink.transport.base import StreamTransport,LinkError
from jetlink.transport.ffs import FfsTransport
from experimental.jetson_optimizations.ffs_aio import AioWriter,AioWriteError,AioCleanupError
helpers=runpy.run_path(sys.argv[1]);FakeQueue=helpers['FakeQueue'];until=helpers['until']
version=int(sys.argv[2]);fault=sys.argv[3]=='True'
fake=FakeQueue(7,32)
if fault:fake.actions=[1,OSError(errno.EIO,'CPU_FAKE submit rejected')]
writer=AioWriter(7,lambda:None,factory=lambda fd,depth:fake,enabled=True)
class Boundary(StreamTransport):
  tx_align=FfsTransport.tx_align
  write_chunk=FfsTransport.write_chunk
  def _write(self,bufs):
    try:return writer.write(bufs,time.monotonic()+self._write_timeout(.15))
    except AioWriteError as error:raise LinkError(str(error)) from error
  def _read_into(self,*args):raise AssertionError('CPU test must not open endpoints')
  def close(self):pass
transport=Boundary(protocol_version=version)
parts=[b'INFERHDR',bytes(range(256))*1600,b'CONTEXT']
length=sum(map(len,parts));header=P.pack_header(P.Msg.INFER_REQ,19,length,version=version)
expected=header+b''.join(parts)
expected+=b'\\0'*(-len(expected)%transport.tx_align)
try:transport.send(P.Msg.INFER_REQ,19,parts,timeout=.15)
except LinkError:
  assert fault
  assert bytes(fake.stream)==expected[:32768]
  assert len(fake.accepted)==1
  assert len(fake.submissions)==2
  try:writer.close()
  except AioCleanupError:pass
else:
  assert not fault
  until(lambda:writer.retained_bytes==0)
  writer.check();writer.close()
  assert bytes(fake.stream)==expected
print(json.dumps({'protocol':version,'fault':fault,'framed_nbytes':len(expected),'evidence':'CPU_FAKE'}))
'''
    env = {**os.environ, 'PYTHONPATH': os.pathsep.join((str(package), str(ROOT)))}
    result = subprocess.run([sys.executable, '-c', code, str(Path(__file__).resolve()), str(version), str(fault)],
                            env=env, cwd=tmp_path, capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stdout + result.stderr
    report = json.loads(result.stdout)
    assert report['evidence'] == 'CPU_FAKE' and report['framed_nbytes'] == 425984
