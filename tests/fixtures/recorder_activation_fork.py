"""Linux CPU_FAKE subprocess: real pinned PythonProcess/fork/import choreography.

No openpilot native process, GPU, messaging or device is run. modeld's original
module body/definitions/import statements are retained with native dependencies
stubbed; main is reduced to its exact lazy JoiningModel import. The target model
body is replaced by fixture classes plus the real activation footer. Production
ticket consumption and role guard run, with explicit temp-filesystem/source pins.
"""
from __future__ import annotations
import ast
import hashlib
import importlib
import importlib.abc
import importlib.util
import json
import multiprocessing
import os
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import MagicMock

from adapters.carrot.recorder import PACKAGE, recorder_files
from adapters.carrot.recorder_activation import activation_files
from recording.hook import BASE_SHA, MODEL


def main():
    reference, root, strategy, env_mode, helper_first, outcome = sys.argv[1:]
    reference, root = Path(reference), Path(root)
    root.mkdir()
    assert multiprocessing.get_start_method() == 'fork'
    blob=lambda n: subprocess.check_output(['git','-C',str(reference),'show',BASE_SHA+':'+n])
    process_raw=blob('openpilot/system/manager/process.py')
    modeld_raw=blob('openpilot/selfdrive/modeld/modeld.py')
    assert hashlib.sha256(process_raw).hexdigest()=='fa18404da91b45ad67ff990ac3a70a7488eca5987a26f7c61e66501dff704752'
    assert hashlib.sha256(modeld_raw).hexdigest()=='008b225da01394083fbfb691eee4af6b49d39adfe27eede863701c4ec1e00594'
    files=activation_files(reference) if strategy=='B' else recorder_files(reference)
    for n,b in files.items():
        q=root/n;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)
    actual_names={'openpilot.system.manager.process','openpilot.selfdrive.modeld.modeld',
                  'openpilot.selfdrive.modeld.jetlink.model'}
    allowed=set(actual_names)
    for name in list(allowed):
        pieces=name.split('.')
        allowed.update('.'.join(pieces[:i]) for i in range(1,len(pieces)))
    for name in allowed - actual_names:
        q=root/Path(*name.split('.'))/'__init__.py'
        q.parent.mkdir(parents=True,exist_ok=True)
        if not q.exists():q.write_text('')
    for q in (root/'openpilot').rglob('*/'):
        if not (q/'__init__.py').exists():(q/'__init__.py').write_text('')
    events=root/'events.jsonl';ticket_dir=root/'volatile'/'carrot-v3-input-capture'
    ticket_dir.parent.mkdir()
    model_tree=ast.parse(modeld_raw)
    lazy=[n for n in ast.walk(model_tree) if isinstance(n,ast.ImportFrom) and n.module=='openpilot.selfdrive.modeld.jetlink.model']
    assert len(lazy)==1 and lazy[0].names[0].name=='JoiningModel'
    body=ast.parse('''
import sys
from fixture_support import event, OUTCOME
capture = getattr(sys.modules['openpilot.selfdrive.modeld.jetlink.model'], '_m18_input_capture', None)
event({'actor':'modeld', 'active':capture is not None, 'outcome':OUTCOME,
       'capture_env':bool(os.getenv('CARROT_V3_INPUT_CAPTURE'))})
if capture is not None:
    if OUTCOME == 'failed': capture.stop('fixture terminal writer failure')
    else: capture.recorder.count=10; capture.disabled=True
''').body
    for n in model_tree.body:
        if isinstance(n,ast.FunctionDef) and n.name=='main':n.body=[lazy[0],*body]
    modeld_source=ast.unparse(ast.fix_missing_locations(model_tree))+'\n'
    process_tree=ast.parse(process_raw)
    selected=[n for n in process_tree.body if isinstance(n,(ast.FunctionDef,ast.ClassDef)) and n.name in
              ('launcher','join_process','ManagerProcess','PythonProcess','ensure_running')]
    process_prefix='''
from __future__ import annotations
import importlib, os, signal, time, traceback
from abc import ABC, abstractmethod
from collections.abc import ValuesView
from multiprocessing import Process, get_context
from unittest.mock import MagicMock
cloudlog=MagicMock(); sentry=MagicMock(); messaging=MagicMock()
enable_fault_handler=lambda:None
setproctitle=lambda name:None
flush_crash_reports=lambda:None
report_process_exit=lambda *a:None
'''
    process_source=process_prefix+ast.unparse(ast.Module(body=selected,type_ignores=[]))+'\n'
    context_paths={'openpilot.selfdrive.modeld.modeld':('main','openpilot/selfdrive/modeld/modeld.py',hashlib.sha256(modeld_source.encode()).hexdigest()),
                   'openpilot.system.manager.process':('launcher','openpilot/system/manager/process.py',hashlib.sha256(process_source.encode()).hexdigest())}
    (root/'openpilot/selfdrive/modeld/modeld.py').write_text(modeld_source)
    (root/'openpilot/system/manager/process.py').write_text(process_source)
    support='''
import json, os
from pathlib import Path
EVENTS=Path(EVENT_PATH)
OUTCOME=TERMINAL_OUTCOME
def event(value):
    with EVENTS.open('a') as f:f.write(json.dumps(value)+'\\n')
class Sink:
    count=0
    reason=None
    def __init__(self,*a,**k):event({'actor':'sink','started':True})
    def stop(self,reason):self.reason=reason
'''.replace('EVENT_PATH',repr(str(events))).replace('TERMINAL_OUTCOME',repr(outcome))
    (root/'fixture_support.py').write_text(support)
    hook_path=root/PACKAGE/'hook.py'
    injection='''
# CPU_FAKE instrumentation only: preserve real consume and real context guard.
from fixture_support import Sink
DISCOVERY_DIRECTORY=Path(TEMP_DIRECTORY)
CONTEXT_SOURCE_PINS=FIXTURE_CONTEXT_PINS
_require_volatile_parent=lambda:None
_fixture_install=install
def install(namespace, **kwargs):
    kwargs['recorder_factory']=Sink
    kwargs['source_verifier']=lambda ns:None
    return _fixture_install(namespace, **kwargs)
'''.replace('TEMP_DIRECTORY',repr(str(ticket_dir))).replace('FIXTURE_CONTEXT_PINS',repr(context_paths))
    hook_path.write_bytes(hook_path.read_bytes()+injection.encode())
    model=files[MODEL]
    marker=b'\n\n# M18 exact-input observer; default OFF.\n'
    footer=marker+model.split(marker)[1]
    footer=footer.replace(b'/dev/shm/carrot-v3-input-capture/arm.ticket',str(ticket_dir/'arm.ticket').encode())
    # Only the fixture's target model body is inert; the footer is executed as-is.
    target_prefix='''
import os
from test_v3_input_hook import fake_namespace
globals().update(fake_namespace())
JoiningModel=object
'''
    (root/MODEL).write_bytes(target_prefix.encode()+footer)

    class NativeStubs(importlib.abc.MetaPathFinder,importlib.abc.Loader):
        def find_spec(self,fullname,path=None,target=None):
            if (fullname.startswith(('openpilot.','tinygrad','opendbc','msgq'))
                    and fullname not in allowed
                    and not fullname.startswith('openpilot.selfdrive.modeld.jetlink.input_recording')):
                return importlib.util.spec_from_loader(fullname,self,is_package=True)
        def create_module(self,spec):return None
        def exec_module(self,module):
            module.__path__=[]
            module.__getattr__=lambda key:MagicMock(name=module.__name__+'.'+key)
    sys.meta_path.insert(0,NativeStubs());sys.path.insert(0,str(root))
    sys.path.insert(1,str(Path(__file__).resolve().parents[1]))
    os.environ.pop('CARROT_V3_INPUT_CAPTURE',None)
    proc=importlib.import_module('openpilot.system.manager.process')
    config=ast.parse(blob('openpilot/system/manager/process_config.py'))
    policy=next(n for n in config.body if isinstance(n,ast.FunctionDef) and n.name=='only_onroad')
    policy_ns={};exec(compile('from __future__ import annotations\n'+ast.unparse(policy),'<source-backed-policy>','exec'),policy_ns)
    process=proc.PythonProcess('modeld','openpilot.selfdrive.modeld.modeld',policy_ns['only_onroad'])
    manager_tree=ast.parse(blob('openpilot/system/manager/manager.py'))
    manager_init=next(n for n in manager_tree.body if isinstance(n,ast.FunctionDef) and n.name=='manager_init')
    prepare=next(n for n in manager_init.body if isinstance(n,ast.For) and any(isinstance(x,ast.Call) and isinstance(x.func,ast.Attribute) and x.func.attr=='prepare' for x in ast.walk(n)))
    exec(compile(ast.Module(body=[prepare],type_ignores=[]),'<actual-manager-prepare-loop>','exec'),{'managed_processes':{'modeld':process}})
    target='openpilot.selfdrive.modeld.jetlink.model'
    assert target not in sys.modules
    assert not any(n.startswith('openpilot.selfdrive.modeld.jetlink.input_recording') for n in sys.modules)
    proc.ensure_running({'modeld':process}.values(),False)
    assert process.proc is None

    # External future OFF arming is simulated locally, not performed on a device.
    armer_spec=importlib.util.spec_from_file_location('recording._fork_armer',hook_path)
    armer=importlib.util.module_from_spec(armer_spec);armer_spec.loader.exec_module(armer)
    outputs=root/'outputs';outputs.mkdir()
    from test_v3_input_hook import Spec
    kwargs=dict(output_root=outputs,source_model_sha=Spec.sha256,
                source_spec_sha=hashlib.sha256(armer.canonical(Spec().to_dict())).hexdigest(),offroad=True,frames=10)
    if strategy=='B':armer.arm_discovered(**kwargs)
    else:
        ticket_dir.mkdir(mode=0o700)
        armer.arm_ticket(ticket_dir/'arm.ticket',**kwargs)
    if env_mode=='inherited':os.environ['CARROT_V3_INPUT_CAPTURE']=str(ticket_dir/'arm.ticket')
    elif env_mode=='shell_only':
        subprocess.run(['bash','-c','export CARROT_V3_INPUT_CAPTURE="$1"','fixture',str(ticket_dir/'arm.ticket')],check=True)
        assert 'CARROT_V3_INPUT_CAPTURE' not in os.environ
    if outcome=='source_drift':
        q=root/'openpilot/system/manager/process.py'
        q.write_bytes(q.read_bytes()+b'\n# fixture source drift\n')
    if helper_first=='yes':
        def helper():
            importlib.import_module(target)
            from fixture_support import event
            event({'actor':'prepare_helper','ticket_remaining':(ticket_dir/'arm.ticket').exists()})
        child=multiprocessing.get_context('fork').Process(target=helper)
        child.start();child.join(15);assert child.exitcode==0
    for _ in range(2):
        proc.ensure_running({'modeld':process}.values(),True)
        process.proc.join(15);assert process.proc.exitcode==0
        proc.ensure_running({'modeld':process}.values(),False)
    assert target not in sys.modules  # Child imports do not contaminate manager.
    records=[json.loads(v) for v in events.read_text().splitlines()]
    print(json.dumps({'strategy':strategy,'env_mode':env_mode,'helper_first':helper_first,'outcome':outcome,
        'fork_start_method':multiprocessing.get_start_method(),'manager_preimport_target':False,
        'offroad_modeld_started':False,'parent_target_after_children':False,'events':records,
        'ticket_remaining':(ticket_dir/'arm.ticket').exists(),
        'manager_capture_env_after':bool(os.getenv('CARROT_V3_INPUT_CAPTURE')),
        'scope':'CPU_FAKE/FIXTURE, reduced main and inert native dependencies, real ticket/context/fork'}))


if __name__=='__main__':main()
