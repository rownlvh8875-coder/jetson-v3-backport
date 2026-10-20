"""Opt-in Cinque V3 CPU staging into immutable physical input bindings.

SPDX-License-Identifier: MIT
Copyright (c) 2026 Zeph Leggett. Design derived from tjdgus200/openpilot
third_party/jetlink/jetlink/direct_inputs.py at a890f6df1bd3eb0478754c68d8b5f92f15e8b722; restricted to the
existing Cinque V3 camera/scalars12 contract. See input_cast.c for MIT notice.

No compact map decoder or new wire flags are supported. Buffer ownership stays
with the engine and staging touches only new_img/desire/traffic_convention/
action_t. The server's existing finite/output/identity/state gates remain active.
"""
import numpy as np


class DirectInputs:
    def __init__(self, spec, dest):
        from jetlink.cinque_v3 import CANONICAL_SPEC, DTYPE_TRANSFORMS, validate_spec
        validate_spec(spec.to_dict())
        if spec.packed_nelem != 12 or tuple(spec.packed_shapes) != ('desire', 'traffic_convention', 'action_t'):
            raise ValueError('Direct inputs support only the Cinque V3 scalars12 contract')
        if not isinstance(dest, dict) or set(dest) != set(spec.input_shapes):
            raise ValueError('Direct input bindings do not match the complete model contract')
        self.spec, self.dest = spec, dest
        self.canonical = CANONICAL_SPEC
        self.bindings = []
        for name, shape in spec.input_shapes.items():
            value = dest[name]
            dtype = np.dtype(DTYPE_TRANSFORMS.get(name, spec.input_dtypes[name]))
            if (not isinstance(value, np.ndarray) or tuple(value.shape) != tuple(shape) or value.dtype != dtype
                    or not value.flags.c_contiguous or not value.flags.aligned or not value.flags.writeable):
                raise ValueError(f'Unsupported direct input binding: {name}')
            self.bindings.append((name, value, value.ctypes.data, tuple(shape), dtype, value.strides))
        arrays = [value for _, value, *_ in self.bindings]
        if any(np.shares_memory(left, right) for i, left in enumerate(arrays) for right in arrays[i + 1:]):
            raise ValueError('Direct input bindings overlap')
        # Native compilation/loading and its fixed self-test happen only here.
        # The runtime flag is checked by the queue before importing this module.
        if __package__ == 'jetlink':
            from jetlink.input_cast import native_u8_to_f16
        else:
            from .input_cast import native_u8_to_f16
        self.convert = native_u8_to_f16()

    def _check_bindings(self, dest):
        if dest is not self.dest or self.spec.to_dict() != self.canonical or set(dest) != {b[0] for b in self.bindings}:
            raise ValueError('Direct input container/model changed after preparation')
        for name, value, pointer, shape, dtype, strides in self.bindings:
            if (dest.get(name) is not value or value.ctypes.data != pointer or value.shape != shape
                    or value.dtype != dtype or value.strides != strides or not value.flags.c_contiguous
                    or not value.flags.aligned or not value.flags.writeable):
                raise ValueError(f'Direct input binding changed after preparation: {name}')

    def stage(self, warped, packed, dest):
        """Validate all sources/bindings before the first destination write."""
        self._check_bindings(dest)
        if (not isinstance(warped, np.ndarray) or warped.dtype != np.uint8
                or warped.shape != self.spec.warped_shape or not warped.flags.c_contiguous
                or not warped.flags.aligned):
            raise ValueError('Invalid direct image shape/type/storage')
        if (not isinstance(packed, np.ndarray) or packed.dtype != np.float32 or packed.shape != (12,)
                or not packed.flags.c_contiguous or not packed.flags.aligned or not np.isfinite(packed).all()):
            raise ValueError('Invalid direct scalar context; compact maps are unsupported')
        if any(np.shares_memory(source, value) for source in (warped, packed)
               for _, value, *_ in self.bindings):
            raise ValueError('Direct source overlaps an engine binding')
        # Scalar destinations were fixed to float32 at preparation and checked
        # again above. casting=no forbids implicit narrowing or overflow.
        self.convert(warped, dest['new_img'])
        np.copyto(dest['desire'], packed[:8], casting='no')
        np.copyto(dest['traffic_convention'], packed[8:10].reshape(1, 2), casting='no')
        np.copyto(dest['action_t'], packed[10:12].reshape(1, 2), casting='no')
