"""Optional source overlay; standard/default candidate generation is untouched."""
import hashlib
from pathlib import Path


PREFIX = 'third_party/jetlink/jetlink/'
SOURCE = Path(__file__).resolve().parent
REVIEWED_STATEFUL_SHA256 = 'c3452c8949824372ccac8c2e6e2388e7ae263cbb58980e442d25725ed175b444'


def fastpath_optimization_files(files: dict[str, bytes]) -> dict[str, bytes]:
    """Return only four optional files; reject changed source, mutate nothing.

    The caller explicitly opts into generating experimental files. Runtime
    activation independently requires CARROT_TRT_INPUT_FASTPATH=1 before load.
    V2 uses PolicyQueues and never runs this constructor or imports these modules.
    """
    result = {}
    name = PREFIX + 'queues.py'
    try:
        source = files[name].decode('utf-8')
    except (KeyError, UnicodeDecodeError) as exc:
        raise ValueError('Input fastpath requires standard candidate queues') from exc
    start = source.find('class StatefulState:')
    if start < 0:
        raise ValueError('Input fastpath StatefulState source contract changed')
    before, state = source[:start], source[start:]
    if hashlib.sha256(state.encode('utf-8')).hexdigest() != REVIEWED_STATEFUL_SHA256:
        raise ValueError('Input fastpath StatefulState body changed; review required')
    anchor = '    self.host_inputs = host_inputs\n'
    if state.count(anchor) != 1:
        raise ValueError('Input fastpath StatefulState constructor changed')
    state = state.replace(anchor, anchor + '''    self._direct_inputs = None
    flag = __import__('os').environ.get('CARROT_TRT_INPUT_FASTPATH', '0')
    if flag not in ('0', '1'):
      raise ValueError('CARROT_TRT_INPUT_FASTPATH must be absent, 0 or 1')
    if flag == '1':
      from jetlink.direct_inputs import DirectInputs
      self._direct_inputs = DirectInputs(spec, host_inputs)
''', 1)
    anchor = '    spec = self.spec\n    if warped.shape != spec.warped_shape:\n'
    if state.count(anchor) != 1:
        raise ValueError('Input fastpath StatefulState.step_into source contract changed')
    state = state.replace(anchor, '''    if self._direct_inputs is not None:
      self._direct_inputs.stage(warped, packed, dest)
      return
''' + anchor, 1)
    result[name] = (before + state).encode('utf-8')
    for module in ('input_cast.c', 'input_cast.py', 'direct_inputs.py'):
        modern = PREFIX + 'server/backends/trt/managed_engine.py' in files
        target = PREFIX + ('managed_' + module if modern and module.startswith('input_cast') else module)
        if target in files:
            raise ValueError(f'Input fastpath module already exists: {target}')
        body = (SOURCE / module).read_text(encoding='utf-8')
        if modern:
            body = body.replace('from jetlink.input_cast import', 'from jetlink.managed_input_cast import')
            body = body.replace("with_name('input_cast.c')", "with_name('managed_input_cast.c')")
        result[target] = body.encode('utf-8')
    return result
