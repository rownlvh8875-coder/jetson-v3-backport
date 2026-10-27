"""Actual optional CURRENT Session/TrtEngine, fake only TRT/CUDA/NVRTC."""
from __future__ import annotations

from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import runpy
import sys
import tempfile
from types import SimpleNamespace as NS

import numpy as np
import pytest


@contextmanager
def fixture(flag='1', *, full=False):
    import jetlink.server.session as session
    import jetlink.spec as spec_module
    helpers = runpy.run_path(str(Path(__file__).with_name('test_production_v3.py')))
    with tempfile.TemporaryDirectory() as temporary, pytest.MonkeyPatch.context() as patch:
        # Every hardware fixture gets fresh actual TRT modules; retaining a
        # previous module would retain its previous fake CUDA allocation pool.
        for name in list(sys.modules):
            if name == 'jetlink.server.backends.trt' or name.startswith('jetlink.server.backends.trt.'):
                patch.delitem(sys.modules, name)
        if flag is None:
            patch.delenv('CARROT_TRT_DEVICE_STATE', raising=False)
        else:
            patch.setenv('CARROT_TRT_DEVICE_STATE', flag)
        prod = NS(session=session, spec=spec_module)
        hardware = helpers['gpu'].__wrapped__(prod, patch)
        gpu = next(hardware)
        root = Path(temporary)
        source = helpers['source'].__wrapped__(gpu, root, patch)
        if full:
            # Full canonical tensor shapes with a tiny, identity-bound ONNX
            # fixture. This remains CPU_FAKE/FIXTURE, not real-model parity.
            import base64
            import pickle
            import onnx
            from onnx import helper as H, TensorProto as T
            canonical = json.loads((Path(__file__).resolve().parents[1] / 'artifacts/cinque_v3.json').read_text())
            types = {'uint8': T.UINT8, 'float32': T.FLOAT}
            inputs = [H.make_tensor_value_info(n, types[canonical['input_dtypes'][n]], shape)
                      for n, shape in canonical['input_shapes'].items()]
            outputs = [H.make_tensor_value_info(n, types[canonical['output_dtypes'][n]], shape)
                       for n, shape in canonical['output_shapes'].items()]
            nodes = [H.make_node('Cast', ['new_img'], ['vision'], to=T.FLOAT16),
                     H.make_node('Reshape', ['state_img_q', 'shape'], ['next_state_img_q']),
                     H.make_node('Identity', ['state_desire_q'], ['next_state_desire_q']),
                     H.make_node('Identity', ['state_feat_q'], ['next_state_feat_q']),
                     H.make_node('Constant', [], ['outputs'], value=H.make_tensor('out', T.FLOAT,
                         canonical['output_shapes']['outputs'], [0.] * int(np.prod(canonical['output_shapes']['outputs']))))]
            graph = H.make_model(H.make_graph(nodes, 'full-shape-fixture', inputs, outputs,
                [H.make_tensor('shape', T.INT64, [5], canonical['input_shapes']['state_img_q'])]),
                ir_version=9, opset_imports=[H.make_opsetid('', 17)])
            H.set_model_props(graph, {'model_checkpoint': canonical['checkpoint'],
                'output_slices': base64.b64encode(pickle.dumps({n: slice(*bounds)
                    for n, bounds in canonical['output_slices'].items()})).decode()})
            onnx.save(graph, source.path)
            canonical.update(gpu.common.file_identity(source.path))
            patch.setattr(gpu.common, 'CANONICAL_SPEC', canonical)
            source = NS(path=source.path, spec=canonical)
        backend = gpu.backend.TrtBackend()
        plan = root / 'fixture.plan'
        backend.build(source.path, plan, meta_extra={'spec': source.spec})
        import importlib
        package = 'jetlink.server.backends.trt.'
        try:
            module = importlib.import_module(package + 'managed_device_state')
        except ModuleNotFoundError as error:
            if error.name != package + 'managed_device_state':
                raise
            module = importlib.import_module(package + 'device_state')
        trace, pending = [], []
        options = NS(scan_bad=False, gpu_bad=None, cpu_bad=None, d2d_failure=0,
                     d2d_count=0, drain_failure=False, kernels=0, capturing=False,
                     capture_fail=None, known={}, current_engine=None)
        original_h2d, original_d2h, original_sync = gpu.cuda.memcpy_h2d_async, gpu.cuda.memcpy_d2h_async, gpu.cuda.stream_sync
        original_free, original_host_free = gpu.cuda.free, gpu.cuda.host_free

        def flush():
            while pending:
                target, origin, size = pending.pop(0)
                ctypes.memmove(target, origin, size)

        def array(binding, *, host=False):
            pointer = binding.host_ptr if host else binding.device_ptr
            memory = (ctypes.c_char * binding.nbytes).from_address(pointer)
            return np.frombuffer(memory, binding.dtype).reshape(binding.shape)

        def h2d(target, origin, size, stream):
            flush()  # Earlier D2D in this same stream precedes this operation.
            trace.append(('h2d', options.known.get(target, '?')))
            original_h2d(target, origin, size, stream)

        def d2h(target, origin, size, stream):
            name = options.known.get(origin, '?')
            trace.append(('d2h', name))
            engine = options.current_engine
            if engine and options.gpu_bad and name == options.gpu_bad[0]:
                array(engine.outputs[name]).flat[-1] = options.gpu_bad[1]
            original_d2h(target, origin, size, stream)
            if engine and options.cpu_bad and name == options.cpu_bad[0]:
                array(engine.outputs[name], host=True).flat[-1] = options.cpu_bad[1]

        def sync(stream):
            trace.append(('sync', stream))
            if options.drain_failure:
                raise RuntimeError('CPU_FAKE stream drain failed')
            flush()
            original_sync(stream)

        def d2d(target, origin, size, stream):
            options.d2d_count += 1
            trace.append(('feedback', options.known[target]))
            engine = options.current_engine
            # Every host pair must already have been committed, including the
            # final pair, before the FIRST device copy is accepted.
            for state, output in engine.device_state.pairs:
                np.testing.assert_array_equal(state.host, output.host)
            if options.d2d_failure == options.d2d_count:
                raise RuntimeError('CPU_FAKE partial device feedback enqueue failed')
            pending.append((target, origin, size))

        def memset(pointer, size, stream):
            trace.append(('memset', pointer))
            ctypes.memset(pointer, 0, size)

        class Kernel:
            def __init__(self):
                options.kernels += 1
            def launch(self, binding, bad, stream):
                trace.append(('scan', binding.name))
                if options.scan_bad or not np.isfinite(array(binding)).all():
                    ctypes.c_uint32.from_address(bad).value = 1
            def close(self):
                trace.append(('kernel_close', None))

        gpu.cuda.memcpy_h2d_async, gpu.cuda.memcpy_d2h_async = h2d, d2h
        gpu.cuda.stream_sync, gpu.cuda.memcpy_d2d_async = sync, d2d
        gpu.cuda.memset_async = memset
        gpu.cuda.free = lambda pointer: (trace.append(('free', pointer)), original_free(pointer))[-1]
        gpu.cuda.host_free = lambda pointer: (trace.append(('host_free', pointer)), original_host_free(pointer))[-1]
        patch.setattr(module, 'FiniteKernel', Kernel)

        def load():
            engine = backend.load(plan)
            options.current_engine = engine
            options.known = {binding.device_ptr: name for name, binding in engine.bindings.items()}
            execute = engine.context.execute_async_v3
            def execution(stream):
                flush()
                trace.append(('execute', stream))
                if options.capturing and options.capture_fail == 'enqueue':
                    raise RuntimeError('CPU_FAKE capture enqueue failure')
                return execute(stream)
            engine.context.execute_async_v3 = execution
            return engine

        environment = NS(gpu=gpu, root=root, backend=backend, source=source, session=session,
                         spec=spec_module.ModelSpec.from_dict(source.spec), module=module,
                         options=options, trace=trace, pending=pending, load=load, array=array, patch=patch)
        try:
            yield environment
        finally:
            options.drain_failure = False
            engine = options.current_engine
            if engine is not None and engine.bindings:
                engine.close()
            hardware.close()


def live(environment):
    env = environment
    engine = env.load()
    host = env.session.EngineHost(env.session.EngineCache(env.root / 'cache', env.backend))
    loaded = host._warm(engine, env.spec)
    host.loaded = loaded
    sent = []
    transport = NS(protocol_version=3,
                   send=lambda mt, seq, parts=(), flags=0: sent.append((mt, seq, b''.join(memoryview(part).cast('B') for part in parts))))
    session = env.session.Session(transport, host)
    result = NS(engine=engine, host=host, loaded=loaded, session=session, sent=sent, env=env, seq=0)
    hello(result)
    return result


def hello(current):
    from jetlink import protocol as P
    current.seq += 1
    current.session.handle(NS(msg_type=P.Msg.HELLO_REQ, seq=current.seq, payload=memoryview(b'{}')))
    current.seq += 1
    payload = {'sha256': current.env.spec.sha256, 'nbytes': current.env.spec.nbytes,
               'frame_skip': current.env.spec.frame_skip}
    current.session.handle(NS(msg_type=P.Msg.ENGINE_REQ, seq=current.seq,
                              payload=memoryview(json.dumps(payload).encode())))


def infer(current, reset=False):
    from jetlink import protocol as P
    spec = current.env.spec
    current.seq += 1
    flags = P.Flag.RESET_QUEUES if reset else 0
    payload = (P.pack_infer_req(current.seq, flags)
               + np.full(spec.warped_shape, 11, np.uint8).tobytes()
               + np.full(spec.packed_nelem, .25, np.float32).tobytes())
    current.session.handle(NS(msg_type=P.Msg.INFER_REQ, seq=current.seq, payload=memoryview(payload)))
    return P.unpack_infer_resp(current.sent[-1][2])[1]


def states(current, *, device=False):
    return {name: (current.env.array(binding).copy() if device else binding.host.copy())
            for name, binding in current.engine.inputs.items() if name.startswith('state_')}


def off():
    cases = 0
    for value in (None, '0'):
        with fixture(value) as env:
            current = live(env)
            assert current.engine.device_state is None and env.options.kernels == 0
            assert infer(current) == 0 and infer(current) == 0
            assert not any(operation[0] in ('scan', 'feedback') for operation in env.trace)
            assert 'cuda.bindings.driver' not in sys.modules and 'cuda.nvrtc' not in sys.modules
            current.session.close()
            current.host.close()
            cases += 1
    for value in ('', 'true', '2', ' 1'):
        with fixture(value) as env:
            allocations = env.gpu.state.allocations
            with pytest.raises(ValueError):
                env.load()
            assert env.gpu.state.allocations == allocations and env.options.kernels == 0
            cases += 1
    # V2 with flag=1 still uses the unchanged queued/current engine path.
    with fixture('1') as env:
        from current_carrot_server_peer import fixture as legacy_fixture
        spec = legacy_fixture('v2')
        descriptors = {name: {'mode': 0, 'shape': shape, 'dtype': 'float16'} for name, shape in spec.input_shapes.items()}
        descriptors['outputs'] = {'mode': 1, 'shape': spec.output_shapes['outputs'], 'dtype': 'float32'}
        plan = env.root / 'legacy.plan'
        plan.write_text(json.dumps(descriptors))
        engine = env.backend.load(plan)
        host = env.session.EngineHost(env.session.EngineCache(env.root / 'legacy-cache', env.backend))
        host.loaded = host._warm(engine, spec)
        assert engine.device_state is None and env.options.kernels == 0
        host.close()
        cases += 1
    return cases


def contracts():
    from dataclasses import replace
    cases = 0
    with fixture() as env:
        engine = env.load()
        pairs = env.spec.state_pairs
        baseline_allocations = env.gpu.state.allocations
        names = list(pairs)
        for fault in ('empty', 'duplicate', 'orphan', 'wrong-name', 'shape', 'dtype', 'uint8',
                      'float64', 'nbytes', 'alias', 'cross-alias', 'host-alias',
                      'host-pointer-alias', 'host-pointer-mismatch', 'nonstate-host-pointer',
                      'host-shape', 'host-dtype', 'host-size', 'host-readonly',
                      'nonstate-device-pointer', 'nonstate-device-overlap', 'nonstate-host-overlap',
                      'initial-name', 'initial-direction'):
            inputs, outputs, mapping = engine.inputs.copy(), engine.outputs.copy(), pairs.copy()
            name, output = names[0], pairs[names[0]]
            if fault == 'empty': mapping = {}
            elif fault == 'duplicate': mapping[names[1]] = output
            elif fault == 'orphan': del mapping[name]
            elif fault == 'wrong-name': mapping[name] = 'outputs'
            elif fault == 'shape': outputs[output] = replace(outputs[output], shape=(int(np.prod(outputs[output].shape)),))
            elif fault == 'dtype': outputs[output] = replace(outputs[output], dtype=np.dtype('float32'))
            elif fault in ('uint8', 'float64'):
                dtype = np.dtype(fault)
                inputs[name] = replace(inputs[name], dtype=dtype, nbytes=int(np.prod(inputs[name].shape)) * dtype.itemsize)
                outputs[output] = replace(outputs[output], dtype=dtype, nbytes=inputs[name].nbytes)
            elif fault == 'nbytes': outputs[output] = replace(outputs[output], nbytes=outputs[output].nbytes + 1)
            elif fault == 'alias': outputs[output] = replace(outputs[output], device_ptr=inputs[name].device_ptr)
            elif fault == 'cross-alias': outputs[output] = replace(outputs[output], device_ptr=inputs[names[1]].device_ptr)
            elif fault == 'host-alias': outputs[output] = replace(outputs[output], host=inputs[name].host)
            elif fault == 'host-pointer-alias': outputs[output] = replace(outputs[output], host_ptr=inputs[name].host_ptr)
            elif fault == 'host-pointer-mismatch': outputs[output] = replace(outputs[output], host_ptr=outputs[output].host_ptr + 2)
            elif fault == 'nonstate-host-pointer': inputs['action_t'] = replace(inputs['action_t'], host_ptr=inputs['traffic_convention'].host_ptr)
            elif fault == 'host-shape': outputs[output] = replace(outputs[output], host=outputs[output].host.reshape(-1))
            elif fault == 'host-dtype': outputs[output] = replace(outputs[output], host=outputs[output].host.astype(np.float64))
            elif fault == 'host-size': outputs[output] = replace(outputs[output], host=np.zeros((1,), outputs[output].dtype))
            elif fault == 'host-readonly':
                array = outputs[output].host.copy()
                array.flags.writeable = False
                outputs[output] = replace(outputs[output], host=array, host_ptr=array.ctypes.data)
            elif fault == 'nonstate-device-pointer': inputs['action_t'] = replace(inputs['action_t'], device_ptr=0)
            elif fault == 'nonstate-device-overlap': inputs['action_t'] = replace(inputs['action_t'], device_ptr=inputs['traffic_convention'].device_ptr)
            elif fault == 'nonstate-host-overlap': inputs['action_t'] = replace(inputs['action_t'], host=inputs['traffic_convention'].host, host_ptr=inputs['traffic_convention'].host_ptr)
            elif fault == 'initial-name': inputs['new_img'] = replace(inputs['new_img'], name='state_img_q')
            elif fault == 'initial-direction': outputs[output] = replace(outputs[output], is_input=True)
            with pytest.raises(ValueError):
                env.module.DeviceState(inputs, outputs, mapping, engine.stream)
            assert env.gpu.state.allocations == baseline_allocations and env.options.kernels == 0
            cases += 1
        for owner in (None, {}, dict(engine.bindings, new_img=replace(engine.inputs['new_img']))):
            with pytest.raises(ValueError):
                env.module.DeviceState(engine.inputs, engine.outputs, pairs, engine.stream, owner=owner)
            assert env.gpu.state.allocations == baseline_allocations and env.options.kernels == 0
            cases += 1
    return cases


def runtime(combined=False):
    cases = 0
    with fixture(full=combined) as env:
        if combined:
            env.patch.setenv('CARROT_TRT_INPUT_FASTPATH', '1')
        current = live(env)
        if combined:
            assert current.loaded.queues._direct_inputs is not None
        state = current.engine.device_state
        assert state is not None and not state.initialized
        assert all(not np.any(value) for value in states(current).values())
        first = len(env.trace)
        assert infer(current) == 0 and state.pending
        np.testing.assert_array_equal(current.loaded.host_inputs['state_feat_q'], 1)
        first_trace = env.trace[first:]
        assert len([row for row in first_trace if row[0] == 'feedback']) == len(env.spec.state_pairs)
        assert all(('d2h', name) in first_trace for name in env.spec.output_shapes)
        assert max(i for i, row in enumerate(first_trace) if row[0] in ('scan', 'd2h')) < min(i for i, row in enumerate(first_trace) if row[0] == 'feedback')
        second = len(env.trace)
        assert infer(current) == 0
        np.testing.assert_array_equal(current.loaded.host_inputs['state_feat_q'], 2)
        assert not any(op == 'h2d' and name.startswith('state_') for op, name in env.trace[second:])
        assert all(('d2h', name) in env.trace[second:] for name in env.spec.output_shapes)
        cases += 1
        before_reset = len(env.trace)
        assert infer(current, reset=True) == 0
        np.testing.assert_array_equal(current.loaded.host_inputs['state_feat_q'], 1)
        reset_trace = env.trace[before_reset:]
        assert reset_trace[0][0] == 'sync', 'pending feedback drains before RESET zeros/initial H2D'
        assert all(('h2d', name) in reset_trace for name in env.spec.state_pairs)
        resident = id(current.engine)
        hello(current)
        assert id(current.engine) == resident and not state.initialized
        assert all(not np.any(value) for value in states(current).values())
        assert infer(current) == 0
        np.testing.assert_array_equal(current.loaded.host_inputs['state_feat_q'], 1)
        cases += 1
        with pytest.raises(RuntimeError):
            current.engine.load_inputs({})
        before_close = len(env.trace)
        current.session.close()
        current.host.close()
        assert not env.pending
        close_trace = env.trace[before_close:]
        assert close_trace[0][0] == 'sync' and any(row[0] == 'free' for row in close_trace)
        cases += 1
    return cases


def bindings():
    from dataclasses import replace
    cases = 0
    for fault in ('object', 'device-pointer', 'host-pointer', 'shape', 'dtype', 'size',
                  'host-object', 'container', 'names', 'readonly', 'binding-name',
                  'nonstate-name', 'direction', 'owner-object', 'owner-container', 'owner-names',
                  'inputs-none', 'outputs-none', 'owner-none'):
        with fixture() as env:
            current = live(env)
            assert infer(current) == 0
            current.engine.device_state.drain()
            inputs = current.engine.inputs
            outputs = current.engine.outputs
            target = inputs['state_img_q']
            original = (target.device_ptr, target.host_ptr, target.shape, target.dtype, target.nbytes, target.host,
                        target.name, target.is_input)
            image_name = inputs['new_img'].name
            owner = current.engine.bindings
            original_owner = owner['new_img']
            foreign = None
            if fault == 'object': inputs['state_img_q'] = replace(target)
            elif fault == 'device-pointer': target.device_ptr += 2
            elif fault == 'host-pointer': target.host_ptr += 2
            elif fault == 'shape': target.shape = (int(np.prod(target.shape)),)
            elif fault == 'dtype': target.dtype = np.dtype('float32')
            elif fault == 'size': target.nbytes -= 2
            elif fault == 'host-object': target.host = target.host.copy()
            elif fault == 'container': current.engine.inputs = dict(inputs)
            elif fault == 'names': inputs['unexpected'] = target
            elif fault == 'readonly': target.host.flags.writeable = False
            elif fault == 'binding-name': target.name = 'new_img'
            elif fault == 'nonstate-name': inputs['new_img'].name = 'state_img_q'
            elif fault == 'direction': target.is_input = False
            elif fault == 'owner-object':
                foreign = env.gpu.cuda.malloc(original_owner.nbytes)
                owner['new_img'] = replace(original_owner, device_ptr=foreign)
            elif fault == 'owner-container': current.engine.bindings = dict(owner)
            elif fault == 'owner-names': owner['unexpected_owner'] = original_owner
            elif fault == 'inputs-none': current.engine.inputs = None
            elif fault == 'outputs-none': current.engine.outputs = None
            elif fault == 'owner-none': current.engine.bindings = None
            operations = len(env.trace)
            assert infer(current) != 0 and not current.loaded.valid
            assert not any(row[0] in ('h2d', 'd2h', 'feedback', 'scan') for row in env.trace[operations:])
            frees = env.gpu.state.frees
            with pytest.raises(RuntimeError): current.engine.close()
            assert env.gpu.state.frees == frees, 'binding ownership drift must not free unknown pointers'
            if foreign is not None:
                assert foreign in env.gpu.state.pool
            (target.device_ptr, target.host_ptr, target.shape, target.dtype, target.nbytes, target.host,
             target.name, target.is_input) = original
            inputs['new_img'].name = image_name
            target.host.flags.writeable = True
            inputs['state_img_q'] = target
            inputs.pop('unexpected', None)
            current.engine.inputs = inputs
            current.engine.outputs = outputs
            owner['new_img'] = original_owner
            owner.pop('unexpected_owner', None)
            current.engine.bindings = owner
            assert current.engine.device_state.failed, 'restoring metadata does not revive the generation'
            current.session.close()
            current.host.close()
            if foreign is not None:
                assert foreign in env.gpu.state.pool, 'foreign allocation remains owned by the test'
                env.gpu.cuda.free(foreign)
            cases += 1
    return cases


def faults():
    cases = 0
    for name in ('outputs', 'next_state_img_q', 'next_state_desire_q', 'next_state_feat_q'):
        for location in ('gpu', 'cpu'):
            for value in (np.nan, np.inf):
                with fixture() as env:
                    current = live(env)
                    assert infer(current) == 0
                    current.engine.device_state.drain()
                    before_host, before_device = states(current), states(current, device=True)
                    before_d2d = env.options.d2d_count
                    setattr(env.options, location + '_bad', (name, value))
                    assert infer(current) != 0 and not current.loaded.valid
                    assert env.options.d2d_count == before_d2d
                    for state in before_host:
                        np.testing.assert_array_equal(states(current)[state], before_host[state])
                        np.testing.assert_array_equal(states(current, device=True)[state], before_device[state])
                    hello(current)
                    assert not current.loaded.valid
                    assert infer(current, reset=True) != 0
                    with pytest.raises(RuntimeError): current.engine.device_state.reset()
                    current.session.close()
                    current.host.close()
                    cases += 1
    for kind in ('shape', 'dtype', 'missing', 'scan', 'host-commit', 'feedback'):
        with fixture() as env:
            current = live(env)
            assert infer(current) == 0
            current.engine.device_state.drain()
            before = states(current, device=True)
            count = env.options.d2d_count
            binding = current.engine.outputs['next_state_feat_q']
            original_host = binding.host
            if kind == 'shape': binding.host = binding.host.reshape(-1)
            elif kind == 'dtype': binding.host = binding.host.astype(np.float64)
            elif kind == 'missing': del current.engine.outputs['next_state_feat_q']
            elif kind == 'scan': env.options.scan_bad = True
            elif kind == 'host-commit': current.loaded.host_inputs['state_desire_q'].flags.writeable = False
            elif kind == 'feedback': env.options.d2d_failure = count + 2
            assert infer(current) != 0 and not current.loaded.valid
            if kind == 'feedback':
                assert current.engine.device_state.pending and current.engine.device_state.failed
                assert len(env.pending) == 1, 'first feedback enqueue accepted; second failed'
            else:
                assert env.options.d2d_count == count
                for state, value in before.items():
                    np.testing.assert_array_equal(states(current, device=True)[state], value)
            # Restore deliberately damaged binding metadata only for safe
            # cleanup. The invalid generation remains invalid after restore.
            binding.host = original_host
            current.engine.outputs['next_state_feat_q'] = binding
            current.loaded.host_inputs['state_desire_q'].flags.writeable = True
            current.session.close()
            current.host.close()
            cases += 1
    return cases


def drain():
    cases = 0
    with fixture() as env:
        current = live(env)
        assert infer(current) == 0 and current.engine.device_state.pending
        before = states(current)
        frees = env.gpu.state.frees
        allocations = len(env.gpu.state.pool)
        env.options.drain_failure = True
        hello(current)
        assert not current.loaded.valid
        for name, value in before.items():
            np.testing.assert_array_equal(states(current)[name], value)
        with pytest.raises(RuntimeError):
            current.engine.close()
        assert env.gpu.state.frees == frees and len(env.gpu.state.pool) == allocations
        assert current.engine.bindings and current.engine.device_state.pending
        env.options.drain_failure = False
        current.session.close()
        current.host.close()
        assert not current.engine.bindings and not env.pending
        cases += 1
    with fixture() as env:
        current = live(env)
        env.options.drain_failure = True
        assert infer(current) != 0 and current.engine.device_state.inflight
        frees = env.gpu.state.frees
        with pytest.raises(RuntimeError): current.engine.close()
        assert env.gpu.state.frees == frees
        env.options.drain_failure = False
        current.session.close()
        current.host.close()
        cases += 1
    return cases


def capture():
    cases = 0
    for failure in ('begin', 'enqueue', None):
        with fixture() as env:
            env.options.capture_fail = failure
            def begin(stream):
                if failure == 'begin': raise RuntimeError('CPU_FAKE begin capture failed')
                env.options.capturing = True
            def end(stream):
                env.options.capturing = False
                return 123
            env.gpu.cuda.stream_begin_capture = begin
            env.gpu.cuda.stream_end_capture = end
            env.gpu.cuda.graph_instantiate = lambda graph: graph
            env.gpu.cuda.graph_destroy = lambda graph: env.trace.append(('graph_destroy', graph))
            env.gpu.cuda.graph_exec_destroy = lambda graph: None
            env.gpu.cuda.graph_launch = lambda graph, stream: env.options.current_engine._enqueue()
            current = live(env)
            assert not env.options.capturing
            assert (current.engine.graph_exec is not None) == (failure is None)
            assert infer(current) == 0 and infer(current) == 0
            np.testing.assert_array_equal(current.loaded.host_inputs['state_feat_q'], 2)
            current.session.close()
            current.host.close()
            cases += 1
    return cases


if __name__ == '__main__':
    action = sys.argv[1]
    cases = runtime(combined=True) if action == 'combined' else globals()[action]()
    print(json.dumps({'evidence': 'CPU_FAKE/FIXTURE', 'scenario': action, 'cases': cases}))
