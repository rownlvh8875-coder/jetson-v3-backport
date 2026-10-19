"""CURRENT TRT modules with fake CUDA/TRT boundaries and exact tiny ONNX identity.

Reuses only the previously validated hardware substitutes. The production
adapter, builder, patcher, sidecar, TrtEngine and EngineHost are CURRENT code.
Binding CANONICAL_SPEC to the tiny source is explicit FIXTURE evidence, never
evidence that the full Cinque ONNX or an Orin engine passed.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import runpy
import shutil
import tempfile
from types import SimpleNamespace as NS

import numpy as np
import pytest


def run():
    import jetlink.server.session as session_module
    import jetlink.spec as spec_module
    helpers = runpy.run_path(str(Path(__file__).with_name('test_production_v3.py')))
    prod = NS(session=session_module, spec=spec_module)
    cases = 0
    with tempfile.TemporaryDirectory() as directory, pytest.MonkeyPatch.context() as patch:
        root = Path(directory)
        hardware = helpers['gpu'].__wrapped__(prod, patch)
        gpu = next(hardware)
        source = helpers['source'].__wrapped__(gpu, root, patch)
        backend = gpu.backend.TrtBackend()
        out = root / 'fixture.plan'
        from jetlink.onnx_patch import patch_file

        def rejects(fn):
            nonlocal cases
            before = gpu.state.allocations
            with pytest.raises((ValueError, TypeError, KeyError, OSError, RuntimeError, AttributeError)):
                fn()
            assert gpu.state.allocations == before, 'failed preflight must not allocate buffers'
            cases += 1

        rejects(lambda: patch_file(str(source.path), str(root / 'unknown.onnx')))
        rejects(lambda: backend.build(source.path, out))
        backend.build(source.path, out, meta_extra={'spec': source.spec})
        metadata_path = out.with_suffix('.json')
        good_metadata = json.loads(metadata_path.read_text())
        assert good_metadata['cinque_v3_record']['source'] == gpu.common.file_identity(source.path)
        assert good_metadata['cinque_v3_record']['engine'] == gpu.common.file_identity(out)
        assert gpu.state.flags[-1] == 0, 'preserve the CURRENT TRT10.3 weak typed builder'
        before_pair = (out.read_bytes(), metadata_path.read_bytes())
        cases += 1
        for field in ('backend', 'trt_version', 'device', 'cinque_v3_record', 'cinque_v3_record_sha256'):
            rejects(lambda: backend.build(source.path, out, meta_extra={'spec': source.spec, field: 'bad'}))
        for failure in ('parse', 'build'):
            gpu.state.fail = failure
            rejects(lambda: backend.build(source.path, out, meta_extra={'spec': source.spec}))
            assert (out.read_bytes(), metadata_path.read_bytes()) == before_pair
        gpu.state.fail = None
        original_replace = os.replace
        for failed_target in (out, metadata_path):
            def fail_publish(src, dst):
                if Path(dst) == failed_target:
                    raise OSError('CPU_FAKE recoverable publish failure')
                return original_replace(src, dst)
            with pytest.MonkeyPatch.context() as publication:
                publication.setattr(os, 'replace', fail_publish)
                rejects(lambda: backend.build(source.path, out, meta_extra={'spec': source.spec}))
            assert (out.read_bytes(), metadata_path.read_bytes()) == before_pair

        permission = [True]
        original_builder = gpu.trt.Builder
        class AuthorizationLossBuilder(original_builder):
            def build_serialized_network(self, network, config):
                plan = super().build_serialized_network(network, config)
                permission[0] = False
                return plan
        def authorize():
            if permission[0] is not True:
                raise PermissionError('CPU_FAKE trusted offroad authorization lost')
        # The hardware call finishes; authorization loss prevents publication.
        with pytest.MonkeyPatch.context() as changing:
            changing.setattr(gpu.trt, 'Builder', AuthorizationLossBuilder)
            rejects(lambda: backend.build(source.path, out, meta_extra={'spec': source.spec}, authorize=authorize))
        assert (out.read_bytes(), metadata_path.read_bytes()) == before_pair

        # Source is consumed only while building. Persisted record supports
        # a fresh backend object after both source and patched temp disappear.
        source.path.unlink()
        engine = gpu.backend.TrtBackend().load(out)
        host = session_module.EngineHost(session_module.EngineCache(root / 'cache', backend))
        spec = spec_module.ModelSpec.from_dict(source.spec)
        loaded = host._warm(engine, spec)
        host.loaded = loaded
        assert all(not np.any(value) for name, value in loaded.host_inputs.items() if name.startswith('state_'))
        assert not list(root.glob('tmp*/patched.onnx'))
        cases += 1
        # All actual fp16/fp32 state outputs reject NaN and Inf before commit.
        original_run = engine.run
        for name in engine.outputs:
            for bad in (np.nan, np.inf):
                outputs = original_run()
                before = {a: loaded.host_inputs[a].copy() for a, _ in loaded.queues.pairs}
                outputs[name].flat[-1] = bad
                with pytest.raises(FloatingPointError):
                    session_module._validate_outputs(engine, outputs)
                for state, value in before.items():
                    np.testing.assert_array_equal(loaded.host_inputs[state], value)
                cases += 1
        host.close()

        for fault in ('missing', 'corrupt', 'list', 'runtime', 'device', 'source', 'semantic', 'record-digest'):
            metadata = json.loads(before_pair[1])
            if fault == 'missing': metadata_path.unlink()
            elif fault == 'corrupt': metadata_path.write_text('{')
            elif fault == 'list': metadata_path.write_text('[]')
            else:
                if fault == 'runtime': metadata['trt_version'] = '99.0'
                elif fault == 'device': metadata['device'] = 'another-GPU'
                elif fault == 'source':
                    metadata['cinque_v3_record']['source']['sha256'] = '0' * 64
                    metadata['cinque_v3_record_sha256'] = gpu.common.record_digest(metadata['cinque_v3_record'])
                elif fault == 'semantic': metadata['spec']['checkpoint'] = 'bad'
                else: metadata['cinque_v3_record_sha256'] = '0' * 64
                metadata_path.write_text(json.dumps(metadata))
            rejects(lambda: backend.load(out))
            metadata_path.write_bytes(before_pair[1])
        renamed = root / 'ordinary-v2-name.plan'
        shutil.copyfile(out, renamed)
        rejects(lambda: backend.load(renamed))
        for fault in ('shape', 'dtype', 'mode', 'missing', 'extra', 'missing-frame', 'renamed-frame'):
            def mutate(ios):
                if fault == 'shape': ios['new_img']['shape'] = [6, 2, 1, 1]
                elif fault == 'dtype': ios['new_img']['dtype'] = 'float32'
                elif fault == 'mode': ios['new_img']['mode'] = 1
                elif fault == 'missing': del ios['state_feat_q']
                elif fault == 'missing-frame': del ios['new_img']
                elif fault == 'renamed-frame': ios['unrecognized_frame'] = ios.pop('new_img')
                else: ios['unexpected'] = ios['action_t'].copy()
            gpu.state.mutation = mutate
            rejects(lambda: backend.load(out))
        gpu.state.mutation = None
        # A pre-extension V2 plan still loads with no sidecar via the unchanged
        # TrtEngine path, in contrast to a renamed stateful plan.
        from current_carrot_server_peer import fixture
        legacy_spec = fixture('v2')
        descriptors = {n: {'mode': 0, 'shape': shape, 'dtype': 'float16'}
                       for n, shape in legacy_spec.input_shapes.items()}
        descriptors.update({n: {'mode': 1, 'shape': shape, 'dtype': 'float32'}
                            for n, shape in legacy_spec.output_shapes.items()})
        legacy = root / 'legacy-v2.plan'
        legacy.write_text(json.dumps(descriptors))
        legacy_engine = backend.load(legacy)
        legacy_engine.close()
        cases += 1
        hardware.close()
    return {'evidence': 'CPU_FAKE/FIXTURE', 'cases': cases}
