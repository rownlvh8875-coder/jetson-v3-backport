"""Actual optional candidate EngineHost/queues; CPU physical buffers only."""
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS

import numpy as np

from jetlink.cinque_v3 import CANONICAL_SPEC, DTYPE_TRANSFORMS
from jetlink.server.cache import EngineCache
from jetlink.server.session import EngineHost
from jetlink.spec import ModelSpec


def make_engine(spec):
    """Full semantic V3, canonical TRT physical dtype transformation, CPU only."""
    class Engine:
        dtype_transforms = dict(DTYPE_TRANSFORMS)

        def __init__(self):
            self.inputs = {n: NS(shape=s, dtype=np.dtype(DTYPE_TRANSFORMS.get(n, spec.input_dtypes[n])))
                           for n, s in spec.input_shapes.items()}
            self.outputs = {n: NS(shape=s, dtype=np.dtype(DTYPE_TRANSFORMS.get(n, spec.output_dtypes[n])))
                            for n, s in spec.output_shapes.items()}
            self.buffers = {n: np.full(v.shape, 7, v.dtype) for n, v in self.inputs.items()}
            self.last_gpu_us = 0

        def host_input(self, name):
            return self.buffers[name]

        def run(self):
            output = {'outputs': np.full(spec.output_shapes['outputs'], .125, np.float32)}
            for source, target in spec.state_pairs.items():
                output[target] = self.buffers[source] + np.array(1, self.buffers[source].dtype)
            return output

        def warm(self):
            self.run()
            return 'FIXTURE_NATIVE_CPU; no TRT/CUDA'

        def close(self):
            pass

    return Engine()


def v2_unchanged():
    from jetlink.queues import PolicyQueues
    spec = ModelSpec('2' * 64, 222, 4,
        {'img': (1, 12, 1, 2), 'big_img': (1, 12, 1, 2), 'features_buffer': (1, 2, 3),
         'desire_pulse': (1, 2, 8), 'traffic_convention': (1, 2), 'action_t': (1, 2)},
        {'outputs': (1, 7)}, {'plan': slice(0, 4), 'hidden_state': slice(4, 7)}, 'FIXTURE-V2')
    queues = PolicyQueues(spec)
    buffers = {n: np.zeros(s, np.float16) for n, s in spec.input_shapes.items()}
    queues.step_into(np.full(spec.warped_shape, 13, np.uint8), np.ones(spec.packed_nelem, np.float32), buffers)
    assert np.all(buffers['traffic_convention'] == 1)
    assert np.all(buffers['action_t'] == 1)
    return not hasattr(queues, '_direct_inputs')


def main():
    assert v2_unchanged()
    report = {'evidence': 'FIXTURE_NATIVE_CPU', 'v2_unchanged': True}
    spec = ModelSpec.from_dict(CANONICAL_SPEC)
    engine = make_engine(spec)
    backend = NS(name='trt', suffix='.fixture', tag=lambda: 'FIXTURE_NATIVE_CPU',
                 describe=lambda: {'backend': 'trt', 'runtime_version': 'CPU_FAKE', 'device': 'CPU_FAKE'})
    with tempfile.TemporaryDirectory(prefix='input-fastpath-host-') as directory:
        host = EngineHost(EngineCache(Path(directory), backend))
        try:
            try:
                loaded = host._warm(engine, spec)
            except ValueError:
                if os.environ.get('CARROT_TRT_INPUT_FASTPATH', '0') not in ('0', '1'):
                    report['flag_rejected'] = True
                    print(json.dumps(report))
                    return
                raise
            host.loaded = loaded
            states = {name: engine.buffers[name].copy() for name in spec.state_pairs}
            assert all(not np.any(value) for value in states.values())
            rng = np.random.default_rng(3901)
            for _ in range(2):
                warped = rng.integers(0, 256, spec.warped_shape, dtype=np.uint8)
                packed = np.linspace(-1, 1, 12, dtype=np.float32)
                loaded.queues.step_into(warped, packed, loaded.host_inputs)
                assert engine.buffers['new_img'].tobytes() == warped.astype(np.float16).tobytes()
                assert all(np.array_equal(engine.buffers[n], value) for n, value in states.items())
            converter = 'jetlink.managed_input_cast' if 'jetlink.managed_input_cast' in sys.modules else 'jetlink.input_cast'
            report.update(state_untouched=True, exact_images=True,
                          native_loaded=converter in sys.modules,
                          source=str(Path(sys.modules['jetlink.queues'].__file__).resolve()))
            # Compilation is confined to preparation; after cache clear, a
            # frame must still use its already prepared closure without loading.
            if converter in sys.modules:
                sys.modules[converter].native_u8_to_f16.cache_clear()
                import subprocess
                subprocess.run = lambda *a, **kw: (_ for _ in ()).throw(AssertionError('per-frame compilation'))
                loaded.queues.step_into(warped, packed, loaded.host_inputs)
            print(json.dumps(report))
        finally:
            host.close()


if __name__ == '__main__':
    main()
