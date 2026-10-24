"""810e variant of the reviewed source-backed fork fixture; CPU_FAKE only.

Reuses the historical fixture mechanics without editing its bytes. The manager
and modeld nodes are now read from810e. Native dependencies and modeld.main are
explicitly reduced exactly as in the historical fixture; no real process runs.
"""
from pathlib import Path

path=Path(__file__).with_name('recorder_activation_fork.py')
source=path.read_text()
def once(old,new):
    global source
    if source.count(old)!=1:raise ValueError('reviewed fork fixture anchor drift')
    source=source.replace(old,new)

once('from adapters.carrot.recorder import PACKAGE, recorder_files\nfrom adapters.carrot.recorder_activation import activation_files\nfrom recording.hook import BASE_SHA, MODEL',
     'from adapters.carrot.recorder_810e import PACKAGE, recorder_files, BASE_SHA, MODEL, recorder_footer\nactivation_files=recorder_files')
once("marker=b'\\n\\n# M18 exact-input observer; default OFF.\\n'\n    footer=marker+model.split(marker)[1]",
     "footer=recorder_footer(files).encode()\n    assert model.endswith(footer)")
once('from test_v3_input_hook import fake_namespace','from recorder_810e_support import fake_namespace')
once("'recording._fork_armer'","'openpilot.selfdrive.modeld.jetlink.input_recording._fork_armer'")
once('from test_v3_input_hook import Spec','from recorder_810e_support import nav_spec as Spec')
once('source_model_sha=Spec.sha256','source_model_sha=armer.NAV_MODEL_SHA')
once('source_spec_sha=hashlib.sha256(armer.canonical(Spec().to_dict())).hexdigest()',
     'source_spec_sha=armer.NAV_SPEC_SHA')
# Source verification has its own exact-byte/HEAD tests. This reduced-main fixture
# cannot pass production source hashes; only mount/source checks are overridden.
once('_require_volatile_parent=lambda:None','_require_volatile_parent=lambda:None\n_verify_source=lambda ns:None')
exec(compile(source,str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
