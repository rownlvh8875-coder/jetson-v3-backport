"""Disabled experimental Linux AIO ABI port; never imported by a transport.

Source: tjdgus200/openpilot a890f6df1bd3eb0478754c68d8b5f92f15e8b722,
third_party/jetlink/jetlink/transport/aio_writer_native.py (MIT, Zeph Leggett).
ABI layouts/syscall numbers/PWRITEV and private Py_buffer prototypes are reused.
Changed ownership: retain an exported buffer and a unique slot per request until
controller validation; refuse destroy during active calls or unresolved requests;
do not clear a context whose io_destroy failed. CPU tests inject syscall().
"""
from __future__ import annotations

import ctypes
import os
import platform
import threading
import time

_SYSCALLS = {'aarch64': (0, 1, 2, 4), 'x86_64': (206, 207, 209, 208)}
IOCB_CMD_PWRITEV = 8
_LIVE_CONTEXTS = {}  # No destructor may free exporters for unresolved I/O.


class _Iocb(ctypes.Structure):
    _fields_ = [('data', ctypes.c_uint64), ('key', ctypes.c_uint32), ('rw_flags', ctypes.c_uint32),
                ('opcode', ctypes.c_uint16), ('reqprio', ctypes.c_int16), ('fildes', ctypes.c_uint32),
                ('buf', ctypes.c_uint64), ('nbytes', ctypes.c_uint64), ('offset', ctypes.c_int64),
                ('reserved2', ctypes.c_uint64), ('flags', ctypes.c_uint32), ('resfd', ctypes.c_uint32)]


class _Event(ctypes.Structure):
    _fields_ = [('data', ctypes.c_uint64), ('obj', ctypes.c_uint64), ('res', ctypes.c_int64), ('res2', ctypes.c_int64)]


class _Iovec(ctypes.Structure):
    _fields_ = [('base', ctypes.c_void_p), ('len', ctypes.c_size_t)]


class _Timespec(ctypes.Structure):
    _fields_ = [('sec', ctypes.c_long), ('nsec', ctypes.c_long)]


class _PyBuffer(ctypes.Structure):
    _fields_ = [('buf', ctypes.c_void_p), ('obj', ctypes.c_void_p), ('len', ctypes.c_ssize_t),
                ('itemsize', ctypes.c_ssize_t), ('readonly', ctypes.c_int), ('ndim', ctypes.c_int),
                ('format', ctypes.c_char_p), ('shape', ctypes.c_void_p), ('strides', ctypes.c_void_p),
                ('suboffsets', ctypes.c_void_p), ('internal', ctypes.c_void_p)]


_get_buffer = ctypes.PYFUNCTYPE(ctypes.c_int, ctypes.py_object, ctypes.POINTER(_PyBuffer), ctypes.c_int)(
    ('PyObject_GetBuffer', ctypes.pythonapi))
_release_buffer = ctypes.PYFUNCTYPE(None, ctypes.POINTER(_PyBuffer))(
    ('PyBuffer_Release', ctypes.pythonapi))


def address(buf):
    """Return pointer, size and a retained exporter, including read-only bytes."""
    owner = memoryview(buf).cast('B')
    view = _PyBuffer()
    _get_buffer(owner, ctypes.byref(view), 0)
    try:
        return view.buf or 0, view.len, owner
    finally:
        _release_buffer(ctypes.byref(view))


class Aio:
    def __init__(self, fd, depth, *, enabled=False, syscall=None, machine=None):
        if enabled is not True:
            raise RuntimeError('experimental native AIO is disabled')
        if type(depth) is not int or not 1 <= depth <= 32:
            raise ValueError('AIO depth must be 1..32')
        self._setup, self._destroy, self._submit, self._getevents = _SYSCALLS[machine or platform.machine()]
        if syscall is None:
            self._libc = ctypes.CDLL(None, use_errno=True)
            syscall = self._libc.syscall
            syscall.restype = ctypes.c_long
        self._syscall = syscall
        self.depth = depth
        self._ctx = ctypes.c_ulong(0)
        self._lock = threading.Lock()
        self._submit_owner = self._reap_owner = None
        self._submitting = self._reaping = self._closing = False
        self._uncertain = False
        self._live = {}  # token -> (slot, exporter); no slot/token reuse in flight.
        self._highest_token = 0  # Constant space; never accumulate a token history.
        self._iocbs = (_Iocb * depth)()
        self._iovecs = (_Iovec * depth)()
        self._events = (_Event * depth)()
        self._timeout = _Timespec()
        for i, cb in enumerate(self._iocbs):
            cb.opcode, cb.fildes = IOCB_CMD_PWRITEV, fd
            cb.buf, cb.nbytes = ctypes.addressof(self._iovecs[i]), 1
        self._call(self._setup, ctypes.c_long(depth), ctypes.byref(self._ctx))
        _LIVE_CONTEXTS[id(self)] = self

    @property
    def context(self):
        return self._ctx.value

    def _call(self, number, *args):
        result = self._syscall(ctypes.c_long(number), *args)
        if result < 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error))
        return result

    def _begin(self, kind):
        ident = threading.get_ident()
        with self._lock:
            owner = getattr(self, '_' + kind + '_owner')
            active = '_submitting' if kind == 'submit' else '_reaping'
            if not self.context or self._closing or self._uncertain or getattr(self, active):
                raise RuntimeError('AIO context closed, busy or uncertain')
            if owner not in (None, ident):
                raise RuntimeError('one native ' + kind + ' thread required')
            setattr(self, '_' + kind + '_owner', ident)
            setattr(self, active, True)

    def submit(self, requests):
        self._begin('submit')
        staged = []
        try:
            with self._lock:
                if not requests or len(requests) > self.depth - len(self._live):
                    raise ValueError('native AIO depth exceeded')
                used = {slot for slot, _ in self._live.values()}
                slots = [i for i in range(self.depth) if i not in used]
                for (token, data), slot in zip(requests, slots):
                    if (type(token) is not int or not 0 < token < 1 << 64 or token <= self._highest_token
                            or (staged and token <= staged[-1])):
                        raise ValueError('invalid or reused AIO token')
                    pointer, length, owner = address(data)
                    if not 0 < length <= 32768:
                        owner.release()
                        raise ValueError('AIO request must contain 1..32768 bytes')
                    self._iovecs[slot].base, self._iovecs[slot].len = pointer, length
                    self._iocbs[slot].data = token
                    self._live[token] = (slot, owner)
                    staged.append(token)
                pointers = (ctypes.POINTER(_Iocb) * len(staged))(
                    *(ctypes.pointer(self._iocbs[self._live[token][0]]) for token in staged))
            try:
                count = self._call(self._submit, self._ctx, ctypes.c_long(len(staged)), pointers)
            except OSError:
                self._discard(staged, unsubmitted=True)
                raise
            if type(count) is not int or not 0 < count <= len(staged):
                self._uncertain = True
                raise RuntimeError('invalid io_submit count; retain all staged owners')
            self._discard(staged[count:], unsubmitted=True)
            self._highest_token = staged[count - 1]
            return count
        except (ValueError, TypeError):
            self._discard(staged, unsubmitted=True)
            raise
        except Exception:
            if staged and any(token in self._live for token in staged):
                self._uncertain = True
            raise
        finally:
            with self._lock:
                self._submitting = False

    def _discard(self, tokens, *, unsubmitted=False):
        with self._lock:
            for token in tokens:
                _, owner = self._live.pop(token)
                owner.release()

    def complete(self, token):
        self._discard([token])

    def reap(self, minimum, timeout):
        self._begin('reap')
        try:
            end = time.monotonic() + timeout
            while True:
                left = max(0., end - time.monotonic())
                self._timeout.sec = int(left)
                self._timeout.nsec = int((left - int(left)) * 1e9)
                try:
                    count = self._call(self._getevents, self._ctx, ctypes.c_long(minimum), ctypes.c_long(self.depth),
                                       self._events, ctypes.byref(self._timeout))
                except InterruptedError:
                    if time.monotonic() >= end:
                        return []
                    continue
                if type(count) is not int or not 0 <= count <= self.depth:
                    self._uncertain = True
                    raise RuntimeError('invalid io_getevents count')
                return [(int(self._events[i].data), int(self._events[i].res), int(self._events[i].res2))
                        for i in range(count)]
        finally:
            with self._lock:
                self._reaping = False

    def close(self):
        with self._lock:
            if self._submitting or self._reaping or self._live or self._uncertain or self._closing:
                raise RuntimeError('AIO data/context still owned; refusing destroy')
            if not self.context:
                return
            self._closing = True
        try:
            self._call(self._destroy, self._ctx)
            self._ctx = ctypes.c_ulong(0)  # Successful destroy alone releases it.
            _LIVE_CONTEXTS.pop(id(self), None)
        finally:
            with self._lock:
                self._closing = False
