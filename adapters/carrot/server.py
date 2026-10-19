"""Small, fail-closed source edits for the current carrot-wip Jetson host.

The reference is read only. Returned files are overlaid by the integration
driver in its separate candidate; no GPU imports or device actions happen here.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

PREFIX = 'third_party/jetlink/jetlink/'
ROOT = Path(__file__).resolve().parents[2]
# Full reviewed bodies: unchanged endpoints alone cannot authorize replacement.
REFERENCE_SOURCES = {
    'spec.py': '65ea2deb8c139a5f08e6e512ba354b1eb1f0ed4ca334a37417017fde1d1e073f',
    'queues.py': '36412b1aec7e261578f3b08aad82344f7c5607e248cefcf8ad5661869c94daeb',
    'server/session.py': '8f05ea76763f34fb025aa3e467e75f466349fa699cbe19956df893e7a181af40',
    'onnx_patch.py': '2551902a7dd4fb0a50d046696f17bdb073c02ba3c4dddba6e63cf8b89aedc503',
    'onnx_meta.py': '17eabd7f663020c857f6c426c78aa021e7853fd9b761f3cb1f3d481ea584db94',
    'server/backends/trt/build.py': '35e9a5f57b1a875ce5d8acac2a3e774051351a38fcd3738f99663628a3c6bba8',
    'server/backends/trt/__init__.py': 'dd604510a62aa8b8d2ee7b44b5bd91ab9386666805b5eef9b656e3af6ba2d009',
    'server/backends/trt/engine.py': '3bda5e88432cceda3af13fb4a83873befceb006b6dd76ce308c64e660e2f9648',
    'server/control.py': 'f69345e416faf74e11ddee7bd89e69f570504b1ffa730f6c416db01ed28918f4',
    'server/main.py': 'db09427220eae1eb5346ea4ebb9b5dc286dea491dd34e3baac7ac3e2f31f5813',
}


def _replace(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f'current server source anchor changed: {old[:90]!r}')
    return source.replace(old, new)


def _section(source: str, start: str, end: str, new: str) -> str:
    if source.count(start) != 1 or source.count(end) != 1:
        raise ValueError(f'current server section changed: {start!r}')
    a, b = source.index(start), source.index(end)
    return source[:a] + new + source[b:]


def server_files(reference: Path) -> dict[str, bytes]:
    """Return changed/new repo-relative files; reject changed upstream seams."""
    out: dict[str, bytes] = {}

    def read(name):
        source = (reference / PREFIX / name).read_text(encoding='utf-8')
        if hashlib.sha256(source.encode('utf-8')).hexdigest() != REFERENCE_SOURCES[name]:
            raise ValueError(f'current server source body changed; review required: {name}')
        return source

    def save(name, source):
        out[PREFIX + name] = source.encode('utf-8')

    spec = read('spec.py')
    spec = _replace(spec, 'from dataclasses import dataclass', 'from dataclasses import dataclass, field')
    spec = _replace(spec, '  checkpoint: str | None\n', '''  checkpoint: str | None
  # Optional so pre-extension queued specs preserve their exact wire form.
  input_dtypes: dict[str, str] = field(default_factory=dict)
  output_dtypes: dict[str, str] = field(default_factory=dict)
''')
    spec = _replace(spec, '  @property\n  def img_shape', '''  def validate_stateful(self) -> list[tuple[str, str]]:
    if not self.stateful:
      raise ValueError('validate_stateful on a non-stateful spec')
    if set(self.input_dtypes) != set(self.input_shapes) or set(self.output_dtypes) != set(self.output_shapes):
      raise ValueError('stateful spec requires complete dtype declarations')
    pairs = list(self.state_pairs.items())
    if not pairs:
      raise ValueError('stateful spec admits no state pairs')
    for name in self.input_shapes:
      if name.startswith('state_') and name not in self.state_pairs:
        raise ValueError(f'state input {name!r} has no output')
    for a, b in pairs:
      if self.input_shapes[a] != self.output_shapes[b] or self.input_dtypes[a] != self.output_dtypes[b]:
        raise ValueError(f'state pair {a!r}/{b!r} shape/dtype mismatch')
    if {n for n in self.output_shapes if n.startswith('next_state_')} != {b for _, b in pairs}:
      raise ValueError('orphan next_state output')
    return pairs

  @property
  def img_shape''')
    spec = _replace(spec, '  def to_dict(self) -> dict:\n    return {', '  def to_dict(self) -> dict:\n    d = {')
    spec = _replace(spec, "      'output_slices': {k: [v.start, v.stop] for k, v in self.output_slices.items()},\n    }", "      'output_slices': {k: [v.start, v.stop] for k, v in self.output_slices.items()},\n    }\n    if self.input_dtypes:\n      d['input_dtypes'] = dict(self.input_dtypes)\n    if self.output_dtypes:\n      d['output_dtypes'] = dict(self.output_dtypes)\n    return d")
    spec = _replace(spec, "      checkpoint=d.get('checkpoint'))", "      checkpoint=d.get('checkpoint'),\n      input_dtypes=dict(d.get('input_dtypes', {})),\n      output_dtypes=dict(d.get('output_dtypes', {})))")
    spec = _replace(spec, '    checkpoint=meta.model_checkpoint,', '    checkpoint=meta.model_checkpoint,\n    input_dtypes=dict(meta.input_types) if STATEFUL_FRAME in meta.inputs else {},\n    output_dtypes=dict(meta.output_types) if STATEFUL_FRAME in meta.inputs else {},')
    save('spec.py', spec)

    # Keep the CURRENT queued implementation, append the existing reviewed state.
    queues = _replace(read('queues.py'), 'from jetlink.spec import ModelSpec',
                      'from jetlink.spec import ModelSpec, STATEFUL_FRAME')
    local = (ROOT / 'jetlink/queues.py').read_text(encoding='utf-8')
    save('queues.py', queues.rstrip() + '\n\n\n' + local[local.index('class StateValidationError'):])
    save('cinque_v3.py', (ROOT / 'jetlink/cinque_v3.py').read_text(encoding='utf-8'))

    session = read('server/session.py')
    session = _replace(session, '  def __init__(self, cache: EngineCache, telemetry=None, sleep_after: float = 0.0):',
                          '  def __init__(self, cache: EngineCache, telemetry=None, sleep_after: float = 0.0,\n               managed_selection: bool = False, offroad=None):')
    session = _replace(session, '    self.cache = cache\n', '    self.cache = cache\n    self.managed_selection = bool(managed_selection)\n    self.offroad = offroad\n')
    session = _replace(session, '  # -- listeners ------------------------------------------------------------', '''  def can_provision(self) -> bool:
    if not self.managed_selection:
      return True
    active = self.session
    if active is not None and getattr(active.t, 'protocol_version', P.VERSION) == 3:
      return False
    try:
      return callable(self.offroad) and self.offroad() is True
    except Exception:
      return False

  def require_provisioning(self) -> None:
    if not self.can_provision():
      raise PermissionError('managed Jetson preparation requires trusted offroad authorization and no attached protocol3 session')

  # -- listeners ------------------------------------------------------------''')
    session = _replace(session, '    entry = self.cache.entry(req.sha256)\n    model_path =', '    self.require_provisioning()\n    entry = self.cache.entry(req.sha256)\n    model_path =')
    session = _replace(session, '    remembered = self.cache.last_loaded()', '    if not self.can_provision():\n      return\n    remembered = self.cache.last_loaded()')
    session = _replace(session, "    job.detail = 'loading engine' if job.load_only else 'building engine'", "    self.require_provisioning()\n    job.detail = 'loading engine' if job.load_only else 'building engine'")
    session = _replace(session, '      self._unload()\n', '      self.require_provisioning()\n      self._unload()\n')
    session = _replace(session, '    self.request(req, session)\n', '    if self.can_provision():\n      self.request(req, session)\n')
    session = _replace(session, '      loaded = self._warm(engine, spec)', '      self.require_provisioning()\n      loaded = self._warm(engine, spec)\n      self.require_provisioning()')
    session = _replace(session, '    return self.backend.load(artifact, report=self._progress)', '    self.require_provisioning()\n    return self.backend.load(artifact, report=self._progress)')
    session = _replace(session, '    self.backend.build(model_path, artifact, report=self._progress, meta_extra=meta_extra)', '''    self.require_provisioning()
    options = {'authorize': self.require_provisioning} if self.managed_selection and self.backend.name == 'trt' else {}
    self.backend.build(model_path, artifact, report=self._progress, meta_extra=meta_extra, **options)''')
    session = _replace(session, '  host_inputs: dict\n', '  host_inputs: dict\n  valid: bool = True\n  prev_feat: object = None\n')
    session = _replace(session, "      if loaded is not None:\n        return {'state': 'ready'", "      if loaded is not None and loaded.valid:\n        return {'state': 'ready'")
    session = session.replace('loaded is not None and loaded.sha256 == sha256', 'loaded is not None and loaded.valid and loaded.sha256 == sha256')
    session = _replace(session, 'return self.loaded.sha256 if self.loaded else None', 'return self.loaded.sha256 if self.loaded and self.loaded.valid else None')
    session = _replace(session, '''      if (self.loaded is not None and self.loaded.sha256 == req.sha256
          and self.loaded.spec.frame_skip == req.frame_skip):
        return self._ready(self.loaded)''', '''      if (self.loaded is not None and self.loaded.valid and self.loaded.sha256 == req.sha256
          and self.loaded.spec.frame_skip == req.frame_skip):
        if req.nbytes not in (0, self.loaded.spec.nbytes):
          return {'state': 'failed', 'sha256': req.sha256, 'chunk': CHUNK, 'detail': 'model size mismatch'}
        return self._ready(self.loaded)''')
    session = _replace(session, "      return ModelSpec.from_dict({**d, 'frame_skip': req.frame_skip})", "      cached = ModelSpec.from_dict(d)\n      if (cached.sha256 != req.sha256 or cached.frame_skip != req.frame_skip\n          or req.nbytes not in (0, cached.nbytes)):\n        raise ValueError('cached spec identity/size/frame_skip mismatch')\n      return cached")
    session = _replace(session, "    spec = ModelSpec.from_dict({**d, 'frame_skip': frame_skip})", "    spec = ModelSpec.from_dict(d)\n    if spec.sha256 != sha256 or spec.frame_skip != frame_skip:\n      log.error('remembered model differs from exact cached spec; refusing preload')\n      return")
    session = _replace(session, '      assert spec is not None\n      self._write_spec(entry, spec)', '      assert spec is not None\n      _check_request_spec(req, spec)\n      self._write_spec(entry, spec)')
    session = _replace(session, "    self._build(model_path, entry.path, {'spec': spec.to_dict()})", "    _check_request_spec(req, spec)\n    self._build(model_path, entry.path, {'spec': spec.to_dict()})")
    session = _section(session, '  def _warm(self, engine, spec: ModelSpec) -> Loaded:\n', '  def unload(self) -> None:\n', '''  def _warm(self, engine, spec: ModelSpec) -> Loaded:
    from jetlink.queues import PolicyQueues, StatefulState
    _check_shapes(engine, spec)
    host_inputs = {n: engine.host_input(n) for n in engine.inputs}
    for name, value in host_inputs.items():
      io = engine.inputs[name]
      if tuple(value.shape) != tuple(io.shape) or value.dtype != np.dtype(io.dtype):
        raise ValueError(f'physical host input contract mismatch: {name}')
    queues = StatefulState(spec, host_inputs) if spec.stateful else PolicyQueues(spec)
    queues.reset()
    warped = np.zeros(spec.warped_shape, np.uint8)
    packed = np.zeros(spec.packed_nelem, np.float32)
    queues.step_into(warped, packed, host_inputs)
    _check_finite_inputs(host_inputs)
    log.info("%s", engine.warm())
    _validate_outputs(engine, engine.run())
    queues.reset()
    previous = None if spec.stateful else np.zeros(spec.feat_dim, np.float32)
    return Loaded(spec.sha256, spec, engine, queues, host_inputs, prev_feat=previous)

''')
    session = _section(session, 'def _check_shapes(engine, spec: ModelSpec) -> None:\n', '\n\nclass Session:\n', CHECKS)
    session = _replace(session, '    self.request: Request | None = None\n', '''    self.request: Request | None = None
    self._hello_loaded = None
    self._hello_spec = None
    self._prepared_loaded = None
    self._prepared_spec = None
''')
    session = _replace(session, "      'protocol': P.VERSION,", "      'protocol': P.validate_version(getattr(self.t, 'protocol_version', P.VERSION)),")
    session = _replace(session, '    info = self.host.backend.describe()', '''    info = dict(self.host.backend.describe())
    for reserved in ('protocol', 'carrot_host', 'carrot_model_selection_v1'):
      info.pop(reserved, None)''')
    session = _replace(session, "    if info.get('backend') == 'trt':", '''    with self.host.lock:
      loaded = self.host.loaded
      if resp['protocol'] == 3 and loaded is not None and loaded.valid:
        try:
          loaded.queues.reset()
          if loaded.prev_feat is not None:
            loaded.prev_feat[...] = 0
        except Exception:
          loaded.valid = False
          log.exception('new protocol3 session state reset failed; generation invalid')
      resp['loaded'] = loaded.sha256 if loaded is not None and loaded.valid else None
      self._hello_loaded = loaded if loaded is not None and loaded.valid else None
      self._hello_spec = json.loads(json.dumps(loaded.spec.to_dict())) if self._hello_loaded else None
    if resp['protocol'] == 3 and info.get('backend') == 'trt':
      self.host.managed_selection = True
      self.host.session = self
      resp['carrot_host'] = 'jetson'
      resp['carrot_model_selection_v1'] = {'version': 1, 'selection': 'host'}
    if info.get('backend') == 'trt':''')
    session = _section(session, '  def on_engine_req(self, msg: Message) -> None:\n', '  def _respond_engine(self, seq: int) -> None:\n', ENGINE_REQUEST)
    session = _replace(session, "    self._send_json(P.Msg.ENGINE_RESP, seq, self.host.status(*self._wanted()))", "    response = self.host.status(*self._wanted())\n    if response.get('state') == 'ready':\n      with self.host.lock:\n        self._prepared_loaded = self.host.loaded\n        self._prepared_spec = json.loads(json.dumps(response['spec']))\n    self._send_json(P.Msg.ENGINE_RESP, seq, response)")
    session = _replace(session, '  def on_upload_chunk(self, msg: Message) -> None:\n', "  def on_upload_chunk(self, msg: Message) -> None:\n    if getattr(self.t, 'protocol_version', P.VERSION) == 3:\n      return self._error(msg.seq, 'resident_only', 'provision through the offroad host control path')\n")
    session = _replace(session, '  def on_upload_done(self, msg: Message) -> None:\n', "  def on_upload_done(self, msg: Message) -> None:\n    if getattr(self.t, 'protocol_version', P.VERSION) == 3:\n      return self._error(msg.seq, 'resident_only', 'provision through the offroad host control path')\n")
    session = _replace(session, '''      if (loaded is None or loaded.sha256 != wanted_sha
          or loaded.spec.frame_skip != wanted_skip):''', '''      if (loaded is None or not loaded.valid or loaded.sha256 != wanted_sha
          or loaded.spec.frame_skip != wanted_skip
          or loaded is not self._prepared_loaded or loaded.spec.to_dict() != self._prepared_spec):''')
    session = _replace(session, '''    if flags & P.Flag.RESET_QUEUES:
      loaded.queues.reset()
''', '')
    session = _replace(session, '    if msg.payload.nbytes != spec.infer_req_nbytes:', '''    server_history = getattr(self.t, 'protocol_version', P.VERSION) == 3 and not spec.stateful
    packed_nelem = spec.packed_nelem - (spec.feat_dim if server_history else 0)
    if msg.payload.nbytes != P.INFER_REQ_SIZE + spec.warped_nbytes + packed_nelem * 4:''')
    session = _replace(session, '    packed = np.frombuffer(msg.payload, np.float32, spec.packed_nelem, off)', '''    packed = np.frombuffer(msg.payload, np.float32, packed_nelem, off)
    if server_history:
      previous = np.zeros_like(loaded.prev_feat) if flags & P.Flag.RESET_QUEUES else loaded.prev_feat
      packed = np.concatenate((packed, previous))''')
    session = _section(session, '    # Gathers land straight in TensorRT', '    total_us = int((time.perf_counter() - t0) * 1e6)\n', INFER)
    session = _replace(session, '      parts.append(json.dumps(self.telemetry.read()).encode())', "      parts.append(json.dumps({**self.telemetry.read(), 'loaded': self.host.loaded.sha256 if self.host.loaded and self.host.loaded.valid else None}).encode())")
    save('server/session.py', session)

    onnx_patch = read('onnx_patch.py')
    onnx_patch = _replace(onnx_patch, 'def patch_file(src: str, dst: str, check: bool = True) -> str:',
                          'def patch_file(src: str, dst: str, check: bool = True, spec: dict | None = None) -> str:')
    onnx_patch = _replace(onnx_patch, '''  if needs_patch(model):
    patch_uint8_inputs(model)''', '''  from jetlink.cinque_v3 import validate_source, needs_patch_v3, patch_v3_uint8_inputs
  if any(vi.name == 'new_img' for vi in model.graph.input):
    validate_source(src, spec)
    if not needs_patch_v3(model):
      raise ValueError('V3 graph is already retyped or has unexpected dtypes')
    patch_v3_uint8_inputs(model)
  elif needs_patch(model):
    patch_uint8_inputs(model)''')
    save('onnx_patch.py', onnx_patch)
    meta = read('onnx_meta.py')
    meta = _replace(meta, "    return pickle.loads(codecs.decode(raw.encode(), 'base64'))", "    from jetlink.cinque_v3 import decode_output_slices\n    return {name: slice(*bounds) for name, bounds in decode_output_slices(raw).items()}")
    save('onnx_meta.py', meta)

    build = read('server/backends/trt/build.py')
    build = _replace(build, '                 timing_cache: str | Path | None = None) -> Path:',
                      '                 timing_cache: str | Path | None = None, authorize=None) -> Path:')
    build = _replace(build, '  onnx_path, out_path = Path(onnx_path), Path(out_path)', '  if authorize is not None:\n    authorize()\n  onnx_path, out_path = Path(onnx_path), Path(out_path)')
    build = _replace(build, "    report('build', 0.0, 'building engine')", "    if authorize is not None:\n      authorize()\n    report('build', 0.0, 'building engine')")
    build = _replace(build, '    _save_timing_cache(cache, timing_cache)', '    if authorize is not None:\n      authorize()\n    _save_timing_cache(cache, timing_cache)')
    build = _replace(build, '    patch_file(str(onnx_path), str(patched))',
                      '    patch_file(str(onnx_path), str(patched), spec=semantic)')
    build = _replace(build, '  from jetlink.onnx_patch import patch_file\n', '''  from jetlink.onnx_patch import patch_file
  from jetlink import cinque_v3 as v3
  semantic = (meta_extra or {}).get('spec')
  v3_source = None
  if semantic is None:
    from jetlink.onnx_meta import parse_file
    if 'new_img' in parse_file(str(onnx_path)).inputs:
      raise ValueError('stateful TRT build requires its pinned semantic spec')
  if v3.is_v3_spec(semantic):
    v3_source = v3.validate_source(onnx_path, semantic)
    protected = {'backend', 'trt_version', 'device', 'cinque_v3_record', 'cinque_v3_record_sha256'}
    if protected.intersection(meta_extra or {}):
      raise ValueError('meta_extra contains protected V3 build fields')
  v3_record = None
''')
    build = _replace(build, '    report(\'patch\', 1.0, \'patched\')', '''    if v3_source is not None:
      v3.validate_graph_file(patched, semantic, patched=True)
    report('patch', 1.0, 'patched')''')
    build = _replace(build, '    shutil.move(str(staged), str(out_path))', '''    if v3_source is not None:
      v3_record = v3.build_record(v3_source, patched, staged, semantic)
    else:
      shutil.move(str(staged), str(out_path))''')
    build = _replace(build, "  out_path.with_suffix('.json').write_text(json.dumps(meta, indent=2))", "  if v3_record is not None:\n    meta['cinque_v3_record'] = v3_record\n    meta['cinque_v3_record_sha256'] = v3.record_digest(v3_record)\n    if authorize is not None:\n      authorize()\n    _publish_v3(staged, out_path, meta)\n  else:\n    out_path.with_suffix('.json').write_text(json.dumps(meta, indent=2))")
    # Keep the existing builder/configuration. Only extend the lifetime of its
    # temporary directory until the V3 plan/sidecar pair has been published.
    tail = build.index('  meta = {', build.index('def build_engine('))
    build = build[:tail] + ''.join('  ' + line if line.strip() else line for line in build[tail:].splitlines(keepends=True))
    build += PUBLISH_V3
    save('server/backends/trt/build.py', build)
    backend = read('server/backends/trt/__init__.py')
    backend = _replace(backend, '            meta_extra: dict | None = None) -> Path:', '            meta_extra: dict | None = None, authorize=None) -> Path:')
    backend = _replace(backend, '                               timing_cache=_build.timing_cache_path(Path(out_path).parent, self.device))',
                        '                               timing_cache=_build.timing_cache_path(Path(out_path).parent, self.device), authorize=authorize)')
    backend = _replace(backend, '    return TrtEngine(str(artifact), device=self.device if self.device else None)', '''    import json
    from jetlink import cinque_v3 as v3
    sidecar = artifact.with_suffix('.json')
    meta = json.loads(sidecar.read_text()) if sidecar.is_file() else {}
    semantic = meta.get('spec')
    transforms = {}
    if v3.is_v3_spec(semantic):
      if (meta.get('backend') != 'trt' or meta.get('trt_version') != self.runtime_version
          or meta.get('device') != _build.device_tag(self.device)):
        raise ValueError('V3 artifact runtime/device identity mismatch')
      record = meta.get('cinque_v3_record')
      if not isinstance(record, dict) or meta.get('cinque_v3_record_sha256') != v3.record_digest(record):
        raise ValueError('missing or corrupt V3 build record')
      transforms = v3.validate_record(record, artifact, semantic)
    return TrtEngine(str(artifact), device=self.device if self.device else None,
                     semantic_spec=semantic, dtype_transforms=transforms)''')
    save('server/backends/trt/__init__.py', backend)
    engine = read('server/backends/trt/engine.py')
    engine = _replace(engine, '  def __init__(self, plan_path: str, log_severity=trt.Logger.WARNING, device: int | None = None):',
                        '  def __init__(self, plan_path: str, log_severity=trt.Logger.WARNING, device: int | None = None,\n               semantic_spec: dict | None = None, dtype_transforms: dict | None = None):')
    engine = _replace(engine, '    self.context = self.engine.create_execution_context()', '''    self.dtype_transforms = dict(dtype_transforms or {})
    names = [self.engine.get_tensor_name(i) for i in range(self.engine.num_io_tensors)]
    if ('new_img' in names or any(n.startswith(('state_', 'next_state_')) for n in names)
        or (semantic_spec and 'new_img' in semantic_spec.get('input_shapes', {}))):
      from jetlink import cinque_v3 as v3
      v3.validate_spec(semantic_spec)
      if self.dtype_transforms != v3.DTYPE_TRANSFORMS:
        raise ValueError('V3 engine has no approved physical dtype transform')
      actual = {'inputs': {}, 'outputs': {}}
      for name in names:
        kind = 'inputs' if self.engine.get_tensor_mode(name) == trt.TensorIOMode.INPUT else 'outputs'
        actual[kind][name] = (tuple(self.engine.get_tensor_shape(name)),
                             str(np.dtype(TRT_TO_NP[self.engine.get_tensor_dtype(name)])))
      if actual != v3.physical_contract(semantic_spec):
        raise ValueError('V3 engine physical contract mismatch before buffer allocation')
    self.context = self.engine.create_execution_context()''')
    save('server/backends/trt/engine.py', engine)
    control = read('server/control.py')
    for method in ('_cmd_download', '_cmd_prepare', '_cmd_import'):
        anchor = f'  def {method}(self, client: _Client, msg: dict) -> dict:\n'
        control = _replace(control, anchor, anchor + '    self.host.require_provisioning()\n')
    control = _replace(control, '    self._download_event(state, \'started\')\n    try:', "    self._download_event(state, 'started')\n    try:\n      self.host.require_provisioning()")
    control = _replace(control, '                          should_stop=lambda: state.cancel)', '                          should_stop=lambda: state.cancel or not self.host.can_provision())')
    control = _replace(control, '  def _run_import(self, path: Path, name) -> None:\n', '  def _run_import(self, path: Path, name) -> None:\n    self.host.require_provisioning()\n')
    save('server/control.py', control)
    main = read('server/main.py')
    main = _replace(main, "  p.add_argument('--build', metavar='ONNX', help='build an engine and exit')", "  p.add_argument('--managed-jetson', action='store_true',\n                 help='protocol3 resident selection; provisioning stays disabled until a trusted offroad provider is wired')\n  p.add_argument('--build', metavar='ONNX', help='build an engine and exit')")
    main = _replace(main, '  args = p.parse_args(argv)', "  args = p.parse_args(argv)\n  if args.managed_jetson and args.build:\n    p.error('managed build requires a trusted offroad provider; configure after read-only inventory')")
    main = _replace(main, '                    sleep_after=sleeper.after if sleeper is not None else 0.0)\n  control = None', '                    sleep_after=sleeper.after if sleeper is not None else 0.0,\n                    managed_selection=args.managed_jetson)\n  control = None')
    main = _replace(main, '  control = None\n', '''  if args.managed_jetson:
    original_opener = opener
    def opener():
      transport = original_opener()
      if transport is not None:
        transport.protocol_version = 3
      return transport
  control = None
''')
    save('server/main.py', main)
    return out


PUBLISH_V3 = '''

def _publish_v3(staged: Path, target: Path, meta: dict) -> None:
  """Restore the prior pair on recoverable publish errors; not crash atomic.

  A process/power failure between the two renames is detected by the persistent
  engine digest when loading, before device-buffer allocation.
  """
  import os
  sidecar = target.with_suffix('.json')
  staged_meta = staged.with_suffix('.json')
  staged_meta.write_text(json.dumps(meta, indent=2))
  old_plan, old_meta = staged.parent / 'previous.plan', staged.parent / 'previous.json'
  had_plan, had_meta = target.is_file(), sidecar.is_file()
  if had_plan:
    shutil.copyfile(target, old_plan)
  if had_meta:
    shutil.copyfile(sidecar, old_meta)
  try:
    os.replace(staged, target)
    os.replace(staged_meta, sidecar)
  except Exception:
    # copyfile also works when an injected/OS rename error persists; retain
    # backups in the staging directory until both restorations finish.
    if had_plan:
      shutil.copyfile(old_plan, target)
    else:
      target.unlink(missing_ok=True)
    if had_meta:
      shutil.copyfile(old_meta, sidecar)
    else:
      sidecar.unlink(missing_ok=True)
    raise
'''


CHECKS = '''def _check_request_spec(req: Request, spec: ModelSpec) -> None:
  if (spec.sha256 != req.sha256 or spec.frame_skip != req.frame_skip
      or req.nbytes not in (0, spec.nbytes)):
    raise ValueError('requested model and semantic spec identity/size differ')


def _check_shapes(engine, spec: ModelSpec) -> None:
  """Exact named physical contract; only the pinned V3 transform is admitted."""
  EngineCache._validate_sha256(spec.sha256)
  if type(spec.nbytes) is not int or spec.nbytes <= 0 or type(spec.frame_skip) is not int or spec.frame_skip <= 0:
    raise ValueError('invalid model spec size/frame_skip')
  if spec.stateful:
    spec.validate_stateful()
  transforms = getattr(engine, 'dtype_transforms', {})
  if transforms:
    from jetlink import cinque_v3 as v3
    v3.validate_spec(spec.to_dict())
    if transforms != v3.DTYPE_TRANSFORMS:
      raise ValueError('unapproved physical dtype transform')
  for kind in ('inputs', 'outputs'):
    values = getattr(engine, kind)
    shapes = getattr(spec, kind[:-1] + '_shapes')
    dtypes = getattr(spec, kind[:-1] + '_dtypes')
    if set(values) != set(shapes):
      raise ValueError(f'{kind} names do not match spec')
    for name, io in values.items():
      if tuple(io.shape) != tuple(shapes[name]):
        raise ValueError(f'{kind} {name}: engine shape {io.shape} != spec {shapes[name]}')
      want = transforms.get(name, dtypes.get(name))
      if not spec.stateful and kind == 'inputs' and name in ('img', 'big_img') and want == 'uint8':
        want = 'float16'  # Existing V2 head-Cast rewrite, unchanged.
      if want is not None and np.dtype(io.dtype) != np.dtype(want):
        # V2's pre-extension cache did not carry dtypes. Its established fp16
        # physical inputs remain valid; new declared contracts are exact.
        raise ValueError(f'{kind} {name}: physical dtype {io.dtype} != {want}')


def _check_finite_inputs(values):
  if any(not np.all(np.isfinite(value)) for value in values.values()):
    raise FloatingPointError('non-finite physical input')


def _validate_outputs(engine, outputs):
  if set(outputs) != set(engine.outputs):
    raise ValueError('output names do not match physical contract')
  for name, io in engine.outputs.items():
    value = np.asarray(outputs[name])
    if tuple(value.shape) != tuple(io.shape) or value.dtype != np.dtype(io.dtype):
      raise ValueError(f'output {name}: physical shape/dtype mismatch')
    if not np.all(np.isfinite(value)):
      raise FloatingPointError(f'non-finite output {name}')
  out32 = np.asarray(outputs['outputs'], dtype=np.float32).reshape(-1)
  if not np.all(np.isfinite(out32)):
    raise FloatingPointError('non-finite wire output')
  return out32
'''


ENGINE_REQUEST = '''  def on_engine_req(self, msg: Message) -> None:
    d = json.loads(bytes(msg.payload))
    self._prepared_loaded = self._prepared_spec = None
    if (type(d.get('nbytes')) is not int or type(d.get('frame_skip', DEFAULT_FRAME_SKIP)) is not int):
      raise ValueError('model size and frame_skip must be integers')
    self.request = Request(str(d['sha256']), d['nbytes'], d.get('frame_skip', DEFAULT_FRAME_SKIP))
    if getattr(self.t, 'protocol_version', P.VERSION) == 3:
      # The wire cannot trigger a surprise load/build while a car is onroad.
      # Offroad host control prepares a generation; this request only adopts it.
      with self.host.lock:
        loaded = self.host.loaded
        req = self.request
        if (loaded is None or not loaded.valid or loaded is not self._hello_loaded
            or loaded.spec.to_dict() != self._hello_spec or loaded.sha256 != req.sha256
            or req.frame_skip != loaded.spec.frame_skip or req.nbytes not in (0, loaded.spec.nbytes)):
          response = {'state': 'failed', 'sha256': req.sha256, 'chunk': CHUNK,
                      'detail': 'resident generation/identity/size mismatch; repeat HELLO after offroad preparation'}
        else:
          self._prepared_loaded = loaded
          self._prepared_spec = json.loads(json.dumps(loaded.spec.to_dict()))
          response = self.host._ready(loaded)
    else:
      response = self.host.request(self.request, self)
      if response.get('state') == 'ready':
        with self.host.lock:
          self._prepared_loaded = self.host.loaded
          self._prepared_spec = json.loads(json.dumps(response['spec']))
    self._send_json(P.Msg.ENGINE_RESP, msg.seq, response)

'''


INFER = '''    reset_backup = None
    commit_started = False
    try:
      if not np.all(np.isfinite(packed)):
        raise FloatingPointError('non-finite packed input')
      if flags & P.Flag.RESET_QUEUES:
        if spec.stateful:
          reset_backup = {a: loaded.host_inputs[a].copy() for a, _ in loaded.queues.pairs}
        loaded.queues.reset()
      loaded.queues.step_into(warped, packed, loaded.host_inputs)
      _check_finite_inputs(loaded.host_inputs)
      queue_us = int((time.perf_counter() - t0) * 1e6)
      outputs = loaded.engine.run()
      out32 = _validate_outputs(loaded.engine, outputs)
      if spec.stateful:
        staged = loaded.queues.validate_next_states(outputs)
        commit_started = True
        loaded.queues.commit_next_states(staged)
      elif server_history:
        hidden = out32[spec.output_slices['hidden_state']]
        if hidden.shape != loaded.prev_feat.shape:
          raise ValueError('hidden state slice shape mismatch')
        np.copyto(loaded.prev_feat, hidden, casting='no')
      status = P.Status.OK
    except Exception as e:
      # Validation preserves the old state. A copy fault can leave a partial
      # commit. Both discard this generation; only a new load can recover it.
      loaded.valid = False
      if reset_backup is not None and not commit_started:
        try:
          for name, value in reset_backup.items():
            np.copyto(loaded.host_inputs[name], value, casting='no')
        except Exception:
          log.exception('could not restore pre-RESET state; generation remains invalid')
      status = P.Status.NOT_FINITE if isinstance(e, FloatingPointError) else P.Status.INFER_FAILED
      log.error('invalidating engine generation: %s', e)
      self._send(P.Msg.INFER_RESP, msg.seq, (P.pack_infer_resp(frame_id, status, 0, 0, 0),))
      return

'''
