"""Optional overlay only; the standard candidate never imports this adapter."""
from __future__ import annotations

from pathlib import Path

PREFIX = 'third_party/jetlink/jetlink/'


def _replace(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f'device-state source seam changed: {old[:100]!r}')
    return source.replace(old, new)


def device_optimization_files(files: dict[str, bytes]) -> dict[str, bytes]:
    """Return ONLY the optional changed files, without mutating ``files``."""
    modern = PREFIX + 'server/backends/trt/managed_engine.py' in files
    engine_name = PREFIX + 'server/backends/trt/' + ('managed_engine.py' if modern else 'engine.py')
    session_name = PREFIX + 'server/session.py'
    engine = files[engine_name].decode('utf-8')
    session = files[session_name].decode('utf-8')
    native_warm = native_infer = ''
    if '  def _warm_native(' in session:
        # Experimental recurrence belongs only to the managed V3 branch.
        # Retain upstream N16 methods and their module dependencies verbatim.
        start, end = session.index('  def _warm_native('), session.index('  def unload(')
        native_warm = session[start:end]
        session = session[:start] + session[end:]
        start = session.index('  def _infer_native(')
        native_infer, session = session[start:], session[:start]
    engine = _replace(engine, 'import ctypes\n', 'import ctypes\nimport os\n')
    engine = _replace(engine, '    self.logger = trt.Logger(log_severity)', '''    device_flag = os.environ.get('CARROT_TRT_DEVICE_STATE', '0')
    if device_flag not in ('0', '1'):
      raise ValueError('CARROT_TRT_DEVICE_STATE must be absent, 0, or 1')
    self._device_state_requested = device_flag == '1'
    self.device_state = None
    self.logger = trt.Logger(log_severity)''')
    engine = _replace(engine, '  # -- execution ------------------------------------------------------------', '''  def configure_device_state(self, pairs):
    if not self._device_state_requested:
      return
    if self.device_state is not None or self.graph_exec is not None:
      raise RuntimeError('device state must be configured once, before capture')
    from jetlink.server.backends.trt.device_state import DeviceState
    self.device_state = DeviceState(self.inputs, self.outputs, pairs, self.stream, owner=self.bindings)

  def _run_device_state(self):
    state = self.device_state
    started = time.perf_counter()
    try:
      state.before_run(self.inputs, self.outputs, self.bindings)
      if self.graph_exec is not None:
        cudart.graph_launch(self.graph_exec, self.stream)
      else:
        self._enqueue()
      # Preserve the current full D2H completion boundary. Only validated
      # feedback enqueued by Session can trail the reply.
      cudart.stream_sync(self.stream)
      state.after_sync(self.inputs, self.outputs, self.bindings)
    except BaseException:
      state.invalidate()
      raise
    self.last_gpu_us = int((time.perf_counter() - started) * 1e6)
    return {name: binding.host for name, binding in self.outputs.items()}

  def _capture_device_state_graph(self):
    state = self.device_state
    state.drain()
    capturing, graph = False, None
    try:
      cudart.stream_begin_capture(self.stream)
      capturing = True
      self._enqueue()
      capturing = False
      graph = cudart.stream_end_capture(self.stream)
      self.graph_exec = cudart.graph_instantiate(graph)
      return True
    except Exception:
      if capturing:
        try:
          graph = cudart.stream_end_capture(self.stream)
        except Exception:
          pass
      self.graph_exec = None
      try:
        cudart.stream_sync(self.stream)
      except BaseException:
        state.invalidate()
        raise
      return False
    finally:
      if graph is not None:
        cudart.graph_destroy(graph)

  # -- execution ------------------------------------------------------------''')
    engine = _replace(engine, '    from jetlink.server.backends.base import load_inputs\n', '''    if self.device_state is not None:
      raise RuntimeError('device feedback requires queue-managed state; explicit state upload is unsupported')
    from jetlink.server.backends.base import load_inputs
''')
    engine = _replace(engine, '    for b in self.inputs.values():\n      cudart.memcpy_h2d_async', '''    for name, b in self.inputs.items():
      if self.device_state is not None and name in self.device_state.input_names:
        continue
      cudart.memcpy_h2d_async''')
    engine = _replace(engine, '      cudart.memcpy_d2h_async(b.host_ptr, b.device_ptr, b.nbytes, self.stream)\n', '''      cudart.memcpy_d2h_async(b.host_ptr, b.device_ptr, b.nbytes, self.stream)
    if self.device_state is not None:
      self.device_state.enqueue_check()
''')
    engine = _replace(engine, '    if self.graph_exec is not None:\n      return True', '    if self.device_state is not None:\n      return self._capture_device_state_graph()\n    if self.graph_exec is not None:\n      return True')
    engine = _replace(engine, '    t0 = time.perf_counter()\n', '    if self.device_state is not None:\n      return self._run_device_state()\n    t0 = time.perf_counter()\n')
    engine = _replace(engine, '  def close(self) -> None:\n', '''  def close(self) -> None:
    if self.device_state is not None:
      # A failed drain deliberately aborts cleanup before ANY binding is freed.
      self.device_state.close(self.inputs, self.outputs, self.bindings)
      self.device_state = None
''')
    session = _replace(session, '    _check_shapes(engine, spec)\n', '''    _check_shapes(engine, spec)
    if spec.stateful and getattr(engine, '_device_state_requested', False):
      engine.configure_device_state(spec.state_pairs)
''')
    if session.count('    queues.reset()\n') != 2:
        raise ValueError('device-state warm reset seams changed')
    session = session.replace('    queues.reset()\n', '    _reset_device_state(engine, queues)\n')
    session = _replace(session, '          loaded.queues.reset()\n', '          _reset_device_state(loaded.engine, loaded.queues)\n')
    session = _replace(session, '        loaded.queues.reset()\n', '        _reset_device_state(loaded.engine, loaded.queues)\n')
    session = _replace(session, '        loaded.queues.commit_next_states(staged)\n', '''        loaded.queues.commit_next_states(staged)
        device_state = getattr(loaded.engine, 'device_state', None)
        if device_state is not None:
          device_state.enqueue_feedback(loaded.engine.inputs, loaded.engine.outputs, loaded.engine.bindings)
''')
    session = _replace(session, '\n      loaded.valid = False\n', '''
      loaded.valid = False
      device_state = getattr(loaded.engine, 'device_state', None)
      if device_state is not None:
        device_state.invalidate()
''')
    session = _replace(session, 'def _check_request_spec(req: Request, spec: ModelSpec) -> None:\n', '''def _reset_device_state(engine, queues):
  device_state = getattr(engine, 'device_state', None)
  if device_state is not None:
    device_state.reset(engine.inputs, engine.outputs, engine.bindings)
  queues.reset()


def _check_request_spec(req: Request, spec: ModelSpec) -> None:
''')
    if native_warm:
        session = session.replace('  def unload(', native_warm + '  def unload(', 1) + native_infer
    module_name = 'managed_device_state.py' if modern else 'device_state.py'
    if modern:
        engine = engine.replace('from jetlink.server.backends.trt.device_state import DeviceState',
                                'from jetlink.server.backends.trt.managed_device_state import DeviceState')
    module = Path(__file__).with_name('device_state.py').read_text(encoding='utf-8').encode('utf-8')
    return {engine_name: engine.encode(), session_name: session.encode(),
            PREFIX + 'server/backends/trt/' + module_name: module}
