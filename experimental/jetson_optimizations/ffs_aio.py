"""DEFER_UNTIL_LATENCY_PROBLEM: isolated AIO TX controller, default disabled.

Reviewed source: tjdgus200/openpilot a890f6df1bd3eb0478754c68d8b5f92f15e8b722,
third_party/jetlink/jetlink/transport/ffs_aio.py. No transport
subclass, daemon hook, synchronous fallback, framing change or timeout increase.
Unlike that source, this copy retains bounded immutable payload owners until
validated completion and never holds the condition during a native submission.
Failure quarantines uncertain requests; process-level recovery may be necessary.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import threading
import time

REQUEST_BYTES = 32 * 1024
DEPTH = 32
CLOSE_TIMEOUT = 1.0  # Source cleanup bound, not a frame/transport deadline.
# A failed close must not turn into a use-after-free when its caller releases
# this object. Quarantined contexts intentionally survive until process exit.
_LIVE_WRITERS = {}


class AioWriteError(RuntimeError):
    pass


class AioCleanupError(AioWriteError):
    """Ownership is unresolved: caller must not free endpoint data or rebind."""


@dataclass(frozen=True)
class Pending:
    expected: int
    deadline: float


def _chunks(views):
    """Gather framed parts without changing a byte or materializing a message."""
    current = bytearray()
    for view in views:
        at = 0
        while at < view.nbytes:
            count = min(REQUEST_BYTES - len(current), view.nbytes - at)
            current.extend(view[at:at + count])
            at += count
            if len(current) == REQUEST_BYTES:
                ready, current = current, bytearray()
                yield memoryview(ready).toreadonly()
    if current:
        yield memoryview(current).toreadonly()


class AioWriter:
    """One submitter and one reaper; explicit opt-in, never auto-selected.

    The queue API is submit([(token, contiguous_bytes), ...]), reap(min, timeout),
    complete(token), close(). Only native kernel calls are substituted in tests.
    write() means queued, not completed, as in the reviewed external controller.
    A future transport must check errors before/after recv and retain its own
    existing watchdog; this module deliberately supplies no transport integration.
    """
    def __init__(self, fd, abort, factory=None, *, enabled=False):
        if enabled is not True:
            raise AioWriteError('experimental AIO is disabled')
        if factory is None:
            from .aio_writer_native import Aio
            factory = lambda descriptor, depth: Aio(descriptor, depth, enabled=True)
        self.aio = factory(fd, DEPTH)
        self.abort = abort
        self.cv = threading.Condition()
        self.pending = {}
        self._owners = {}  # Pending + submitted-but-uncertain payloads; <= 1 MiB.
        self.error = self.abort_error = None
        self.stopping = False
        self._sequence = 1
        self._owner_ident = self._active_writer = None
        self._submitting = False
        self._submit_deadline = None
        _LIVE_WRITERS[id(self)] = self
        self.thread = threading.Thread(target=self._run, name='jetlink-isolated-aio', daemon=True)
        self.thread.start()

    @property
    def retained_bytes(self):
        with self.cv:
            return sum(map(len, self._owners.values()))

    def check(self):
        with self.cv:
            if self.error is not None:
                raise AioWriteError(self.error)
            if self.stopping:
                raise AioWriteError('AIO writer closing')

    def _fail(self, error):
        with self.cv:
            first = self.error is None
            if first:
                self.error = f'FunctionFS AIO write failed: {error}'
            self.cv.notify_all()
        if first:
            try:
                self.abort()
            except Exception as exc:
                # Do not let abort failure escape and hide the ownership latch.
                with self.cv:
                    self.abort_error = str(exc)
                    self.cv.notify_all()

    def write(self, bufs, deadline):
        views = [memoryview(buf).cast('B') for buf in bufs]
        total = sum(view.nbytes for view in views)
        iterator, batch = iter(_chunks(views)), []
        ident = threading.get_ident()
        with self.cv:
            self.check()
            if self._owner_ident not in (None, ident) or self._active_writer is not None:
                raise AioWriteError('one AIO submitter thread is required')
            self._owner_ident = self._active_writer = ident
        exhausted = False
        uncertain = False
        try:
            while True:
                with self.cv:
                    self.check()
                    left = deadline - time.monotonic()
                    if left <= 0:
                        raise AioWriteError('send deadline expired')
                    if not batch and not exhausted:
                        room = DEPTH - len(self._owners)
                        for _ in range(room):
                            try:
                                data = next(iterator)
                            except StopIteration:
                                exhausted = True
                                break
                            token = self._sequence
                            self._sequence += 1
                            self._owners[token] = data
                            batch.append((token, data))
                    if not batch:
                        if exhausted:
                            return total
                        self.cv.wait(left)
                        continue
                    # Reserve before dropping the condition; a blocking syscall
                    # must not prevent close() observing the active submitter.
                    uncertain = True
                    self._submitting = True
                    self._submit_deadline = deadline
                try:
                    queued = self.aio.submit(batch)
                except OSError as exc:
                    # A negative io_submit result accepts zero requests. EAGAIN
                    # retries only the unsubmitted suffix, within the old budget.
                    uncertain = False
                    with self.cv:
                        self._submitting = False
                        self.cv.notify_all()
                    if exc.errno == errno.EAGAIN:
                        with self.cv:
                            self.check()
                            self.cv.wait(min(.01, max(0., deadline - time.monotonic())))
                        continue
                    raise
                with self.cv:
                    if type(queued) is not int or not 0 < queued <= len(batch):
                        raise AioWriteError('invalid AIO submission count; ownership uncertain')
                    for token, data in batch[:queued]:
                        self.pending[token] = Pending(len(data), deadline)
                    batch = batch[queued:]
                    uncertain = False
                    self._submitting = False
                    self.cv.notify_all()
        except Exception as exc:
            with self.cv:
                if not uncertain:
                    for token, _ in batch:
                        self._owners.pop(token, None)  # Proven unsubmitted only.
            self._fail(exc)
            raise AioWriteError(self.error) from exc
        finally:
            with self.cv:
                self._active_writer = None
                self._submitting = False
                self.cv.notify_all()

    def _run(self):
        while True:
            with self.cv:
                while not self.pending and not self.error:
                    if self.stopping and self._active_writer is None:
                        return
                    self.cv.wait()
                if self.error:
                    return
            try:
                events = self.aio.reap(1, .01)
                with self.cv:
                    # Completion can precede io_submit's return. Wait for its
                    # accepted-prefix bookkeeping without locking close out.
                    while self._submitting:
                        left = self._submit_deadline - time.monotonic()
                        if left <= 0:
                            raise AioWriteError('submission completion registration deadline expired')
                        self.cv.wait(min(left, .01))
                    # Validate the whole batch before releasing any owner.
                    seen = set()
                    for event in events:
                        if not isinstance(event, (tuple, list)) or len(event) != 3:
                            raise AioWriteError('malformed AIO completion')
                        token, result, result2 = event
                        if any(type(v) is not int for v in event) or token in seen:
                            raise AioWriteError('malformed or duplicate AIO completion token')
                        request = self.pending.get(token)
                        if (request is None or result != request.expected or result2 not in (0, result)
                                or time.monotonic() >= request.deadline):
                            raise AioWriteError('unknown, short or failed AIO completion')
                        seen.add(token)
                    for token, _, _ in events:
                        self.aio.complete(token)
                        del self.pending[token]
                        del self._owners[token]
                    if self.pending and time.monotonic() >= min(p.deadline for p in self.pending.values()):
                        raise AioWriteError('completion deadline expired')
                    self.cv.notify_all()
            except Exception as exc:
                self._fail(exc)
                return

    def close(self):
        if threading.current_thread() is self.thread:
            raise AioCleanupError('reaper cannot destroy its own context')
        end = time.monotonic() + CLOSE_TIMEOUT
        with self.cv:
            self.stopping = True
            self.cv.notify_all()
            while self._active_writer is not None and time.monotonic() < end:
                self.cv.wait(max(0., end - time.monotonic()))
            if self._active_writer is not None:
                raise AioCleanupError('AIO submitter still owns context; refusing rebind')
        self.thread.join(max(0., end - time.monotonic()))
        with self.cv:
            if self.thread.is_alive() or self.pending or self._owners or self.abort_error:
                raise AioCleanupError('AIO ownership/abort unresolved; refusing free and rebind')
            if self.aio is not None:
                try:
                    self.aio.close()
                except Exception as exc:
                    raise AioCleanupError('native AIO cleanup failed; refusing rebind') from exc
                self.aio = None
            _LIVE_WRITERS.pop(id(self), None)
