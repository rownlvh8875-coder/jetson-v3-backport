"""Experimental H2D-only recurrence; all next-state D2H/CPU gates remain.

FiniteKernel is adapted from tjdgus200/openpilot's IEEE exponent scanner:
third_party/jetlink/jetlink/server/backends/trt/device_state.py at commit
a890f6df1bd3eb0478754c68d8b5f92f15e8b722.
CUDA imports/compilation are lazy and occur only after explicit flag=1 setup.
This module never authorizes a model, relaxes a CPU gate, or aliases bindings.

MIT License
Copyright (c) 2026 Zeph Leggett

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
from __future__ import annotations

import ctypes
import math

import numpy as np

_UNSET = object()


FINITE_SOURCE = r'''
extern "C" __global__ void check_finite(const void *data, unsigned long long n,
                                      unsigned int width, unsigned int *bad) {
  for (unsigned long long i = (unsigned long long)blockIdx.x * blockDim.x + threadIdx.x;
       i < n; i += (unsigned long long)gridDim.x * blockDim.x) {
    unsigned int bits = width == 2 ? ((const unsigned short *)data)[i] : ((const unsigned int *)data)[i];
    unsigned int mask = width == 2 ? 0x7c00u : 0x7f800000u;
    if ((bits & mask) == mask) atomicOr(bad, 1u);
  }
}
'''


def _runtime():
    from jetlink.server.backends.trt import cudart
    return cudart


def _checked(result):
    error, *values = result
    if int(error) != 0:
        raise RuntimeError(f'CUDA device-state operation failed: {error}')
    return values[0] if len(values) == 1 else tuple(values)


class FiniteKernel:
    """The external finite scanner, with lazy CUDA/NVRTC imports."""
    def __init__(self):
        try:
            from cuda.bindings import driver, nvrtc
        except ImportError:
            from cuda import cuda as driver, nvrtc
        cuda = _runtime()
        self.driver, self.module = driver, None
        device = cuda.check(cuda._rt.cudaGetDevice())
        _, major, minor = cuda.device_name(device)
        program = _checked(nvrtc.nvrtcCreateProgram(FINITE_SOURCE.encode(), b'carrot_state.cu', 0, [], []))
        try:
            _checked(nvrtc.nvrtcCompileProgram(program, 1, [f'--gpu-architecture=compute_{major}{minor}'.encode()]))
            size = _checked(nvrtc.nvrtcGetPTXSize(program))
            ptx = b'\0' * size
            _checked(nvrtc.nvrtcGetPTX(program, ptx))
        finally:
            _checked(nvrtc.nvrtcDestroyProgram(program))
        self.module = _checked(driver.cuModuleLoadData(ptx))
        try:
            self.function = _checked(driver.cuModuleGetFunction(self.module, b'check_finite'))
        except BaseException:
            self.close()
            raise

    def launch(self, binding, bad, stream):
        count = binding.nbytes // binding.dtype.itemsize
        args = (ctypes.c_uint64(binding.device_ptr), ctypes.c_uint64(count),
                ctypes.c_uint(binding.dtype.itemsize), ctypes.c_uint64(bad))
        pointers = (ctypes.c_void_p * len(args))(*(ctypes.addressof(arg) for arg in args))
        _checked(self.driver.cuLaunchKernel(self.function, min(4096, (count + 255) // 256), 1, 1,
                                          256, 1, 1, 0, stream, ctypes.addressof(pointers), 0))

    def close(self):
        if self.module is not None:
            _checked(self.driver.cuModuleUnload(self.module))
            self.module = None


def _memset(cuda, target, size, stream):
    operation = getattr(cuda, 'memset_async', None)
    if operation is not None:
        return operation(target, size, stream)
    return cuda.check(cuda._rt.cudaMemsetAsync(target, 0, size, stream))


def _copy_device(cuda, target, source, size, stream):
    operation = getattr(cuda, 'memcpy_d2d_async', None)
    if operation is not None:
        return operation(target, source, size, stream)
    kind = cuda._rt.cudaMemcpyKind.cudaMemcpyDeviceToDevice
    return cuda.check(cuda._rt.cudaMemcpyAsync(target, source, size, kind, stream))


class DeviceState:
    """Distinct device input buffers updated only after CPU validation/commit.

    Initial/reset state H2D is scheduled outside CUDA graph capture. Every
    next-state still travels D2H and through StatefulState validation. A failed
    generation cannot reset itself; reset/close drain pending work before the
    caller zeros host state or frees any binding.
    """
    def __init__(self, inputs, outputs, pairs, stream, *, owner=_UNSET, cuda=None, kernel_factory=None):
        if not isinstance(pairs, dict) or not pairs or len(set(pairs.values())) != len(pairs):
            raise ValueError('device state needs distinct, nonempty state pairs')
        if not isinstance(inputs, dict) or not isinstance(outputs, dict) or set(inputs).intersection(outputs):
            raise ValueError('device state requires separate named input/output bindings')
        logical = {**inputs, **outputs}
        owner = logical if owner is _UNSET else owner
        if (not isinstance(owner, dict) or set(owner) != set(logical)
                or any(owner[name] is not binding for name, binding in logical.items())):
            raise ValueError('device state allocation owner differs from logical bindings')
        self.owner = owner
        # CUDA copies use host_ptr while CPU gates read host. Both must address
        # exactly the same physical array from the FIRST configuration, rather
        # than merely remain unchanged after an invalid descriptor is captured.
        # Validate every binding, including non-state images/scalars/outputs,
        # before importing CUDA, creating the scanner, or allocating scratch.
        all_bindings = []
        for kind, mapping in (('inputs', inputs), ('outputs', outputs)):
            for name, binding in mapping.items():
                try:
                    array, dtype, shape = binding.host, np.dtype(binding.dtype), tuple(binding.shape)
                    valid = (isinstance(name, str) and binding.name == name
                        and binding.is_input is (kind == 'inputs')
                        and type(binding.device_ptr) is int and binding.device_ptr > 0
                        and type(binding.host_ptr) is int and binding.host_ptr > 0
                        and type(binding.nbytes) is int and binding.nbytes > 0
                        and all(type(dim) is int and dim > 0 for dim in shape)
                        and dtype.kind in 'biuf' and dtype.isnative and not dtype.hasobject
                        and binding.device_ptr % dtype.alignment == 0
                        and isinstance(array, np.ndarray) and array.shape == shape and array.dtype == dtype
                        and array.nbytes == binding.nbytes == math.prod(shape) * dtype.itemsize
                        and binding.host_ptr == array.ctypes.data
                        and array.flags.c_contiguous and array.flags.aligned and array.flags.writeable)
                except (AttributeError, TypeError, ValueError, OverflowError):
                    valid = False
                if not valid:
                    raise ValueError(f'invalid initial physical binding: {name}')
                all_bindings.append(binding)
        for index, binding in enumerate(all_bindings):
            for other in all_bindings[index + 1:]:
                if (binding.device_ptr < other.device_ptr + other.nbytes
                        and other.device_ptr < binding.device_ptr + binding.nbytes):
                    raise ValueError('device binding buffers overlap')
                if np.shares_memory(binding.host, other.host):
                    raise ValueError('host binding buffers overlap')
        if (set(pairs) != {name for name in inputs if name.startswith('state_')}
                or set(pairs.values()) != {name for name in outputs if name.startswith('next_state_')}):
            raise ValueError('device state requires every state pair, without orphans')
        self.pairs = []
        for name, output in pairs.items():
            if name not in inputs or output not in outputs or output != 'next_' + name:
                raise ValueError(f'invalid state pair {name!r}/{output!r}')
            target, source = inputs[name], outputs[output]
            if (tuple(target.shape) != tuple(source.shape) or np.dtype(target.dtype) != np.dtype(source.dtype)
                    or target.nbytes != source.nbytes or target.nbytes <= 0
                    or np.dtype(target.dtype) not in (np.dtype('float16'), np.dtype('float32'))
                    or any(type(d) is not int or d <= 0 for d in target.shape)
                    or target.nbytes != math.prod(target.shape) * np.dtype(target.dtype).itemsize):
                raise ValueError(f'invalid device state shape/dtype/size: {name}')
            self.pairs.append((target, source))
        # Check ALL bindings against every state binding, not only each pair.
        # Cross-pair aliases can corrupt an input before validation just as a
        # same-pair alias can. Host state/output storage must also be distinct.
        states = [binding for pair in self.pairs for binding in pair]
        for state in states:
            start, end = int(state.device_ptr), int(state.device_ptr) + state.nbytes
            if start <= 0:
                raise ValueError('device state has no allocated device buffer')
            for other in all_bindings:
                if other is state:
                    continue
                other_start = int(other.device_ptr)
                if start < other_start + other.nbytes and other_start < end:
                    raise ValueError('device state buffers overlap')
                if np.shares_memory(state.host, other.host):
                    raise ValueError('host state/output buffers overlap')
        self.input_names = frozenset(pairs)
        self.output_names = frozenset(pairs.values())
        self.inputs, self.outputs = inputs, outputs
        self.bindings = [(kind, name, binding, int(binding.device_ptr), int(binding.host_ptr),
                          tuple(binding.shape), np.dtype(binding.dtype), binding.nbytes,
                          binding.host, binding.host.ctypes.data, binding.host.strides)
                         for kind, mapping in (('inputs', inputs), ('outputs', outputs))
                         for name, binding in mapping.items()]
        self.stream = stream
        self.cuda = cuda if cuda is not None else _runtime()
        self.kernel = self.bad_device = self.bad_host = None
        self.initialized = self.pending = self.inflight = self.checked = self.failed = self.closed = False
        try:
            self.kernel = (kernel_factory or FiniteKernel)()
            self.bad_device = self.cuda.malloc(4)
            self.bad_host = self.cuda.host_alloc(4)
            self.bad = (ctypes.c_uint32 * 1).from_address(int(self.bad_host))
            self.bad[0] = 0
        except BaseException:
            self.close()
            raise

    def _check_bindings(self, inputs=_UNSET, outputs=_UNSET, owner=_UNSET):
        current_inputs = self.inputs if inputs is _UNSET else inputs
        current_outputs = self.outputs if outputs is _UNSET else outputs
        current_owner = self.owner if owner is _UNSET else owner
        if (current_inputs is not self.inputs or current_outputs is not self.outputs
                or current_owner is not self.owner or set(self.owner) != {name for _, name, *_ in self.bindings}
                or set(self.inputs) != {name for kind, name, *_ in self.bindings if kind == 'inputs'}
                or set(self.outputs) != {name for kind, name, *_ in self.bindings if kind == 'outputs'}):
            self.failed = True
            raise RuntimeError('device state binding container changed; reload required')
        for kind, name, binding, device, host, shape, dtype, size, array, pointer, strides in self.bindings:
            mapping = self.inputs if kind == 'inputs' else self.outputs
            if (mapping.get(name) is not binding or self.owner.get(name) is not binding
                    or binding.name != name or binding.is_input is not (kind == 'inputs')
                    or type(binding.device_ptr) is not int or int(binding.device_ptr) != device
                    or type(binding.host_ptr) is not int or int(binding.host_ptr) != host
                    or type(binding.nbytes) is not int or tuple(binding.shape) != shape
                    or np.dtype(binding.dtype) != dtype or binding.nbytes != size
                    or binding.host is not array or array.ctypes.data != pointer
                    or binding.host_ptr != array.ctypes.data or array.nbytes != size
                    or tuple(array.shape) != shape or array.dtype != dtype or array.strides != strides
                    or not array.flags.c_contiguous or not array.flags.aligned or not array.flags.writeable):
                self.failed = True
                raise RuntimeError(f'device state binding changed: {name}; reload required')

    def before_run(self, inputs=_UNSET, outputs=_UNSET, owner=_UNSET):
        if self.failed or self.closed:
            raise RuntimeError('device state generation invalid; reload required')
        self._check_bindings(inputs, outputs, owner)
        self.inflight, self.checked = True, False
        if not self.initialized:
            for target, _ in self.pairs:
                self.cuda.memcpy_h2d_async(target.device_ptr, target.host_ptr, target.nbytes, self.stream)
            self.initialized = True

    def enqueue_check(self):
        self._check_bindings()
        _memset(self.cuda, self.bad_device, 4, self.stream)
        for _, source in self.pairs:
            self.kernel.launch(source, self.bad_device, self.stream)
        self.cuda.memcpy_d2h_async(self.bad_host, self.bad_device, 4, self.stream)

    def after_sync(self, inputs=_UNSET, outputs=_UNSET, owner=_UNSET):
        self._check_bindings(inputs, outputs, owner)
        self.pending = self.inflight = False
        if self.bad[0]:
            self.failed = True
            raise FloatingPointError('non-finite stateful GPU output')
        self.checked = True

    def enqueue_feedback(self, inputs=_UNSET, outputs=_UNSET, owner=_UNSET):
        if self.failed or self.closed or not self.checked:
            raise RuntimeError('device feedback requires a validated live run')
        self._check_bindings(inputs, outputs, owner)
        # Mark pending BEFORE enqueueing: even the first failed CUDA call may
        # have accepted work, and a later call may leave a partial commit.
        self.pending, self.checked = True, False
        try:
            for target, source in self.pairs:
                _copy_device(self.cuda, target.device_ptr, source.device_ptr, target.nbytes, self.stream)
        except BaseException:
            self.failed = True
            raise

    def invalidate(self):
        self.failed = True

    def drain(self, *, force=False):
        if force or self.pending or self.inflight:
            # If this raises, retain flags and every allocation. Freeing live
            # buffers after a failed drain would be a use-after-free risk.
            self.cuda.stream_sync(self.stream)
            self.pending = self.inflight = False

    def reset(self, inputs=_UNSET, outputs=_UNSET, owner=_UNSET):
        if self.failed or self.closed:
            raise RuntimeError('invalid device state cannot reset; reload required')
        self._check_bindings(inputs, outputs, owner)
        self.drain()
        self.initialized = self.checked = False

    def close(self, inputs=_UNSET, outputs=_UNSET, owner=_UNSET):
        if self.closed:
            return
        self.drain(force=True)
        self._check_bindings(inputs, outputs, owner)
        if self.kernel is not None:
            self.kernel.close()
            self.kernel = None
        if self.bad_device is not None:
            self.cuda.free(self.bad_device)
            self.bad_device = None
        if self.bad_host is not None:
            self.cuda.host_free(self.bad_host)
            self.bad_host = None
        self.closed = True
