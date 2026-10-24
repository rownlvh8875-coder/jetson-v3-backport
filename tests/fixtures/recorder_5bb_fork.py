"""New source-bound profile in the frozen fork/lazy-import fixture; CPU_FAKE."""
from pathlib import Path

path=Path(__file__).with_name('recorder_810e_fork.py')
source=path.read_text()
old='from adapters.carrot.recorder_810e import PACKAGE, recorder_files, BASE_SHA, MODEL, recorder_footer'
new='from adapters.carrot.recorder_5bb import PACKAGE, recorder_files, BASE_SHA, MODEL, recorder_footer'
assert source.count(old)==1
# The reviewed historical adapter generates its inner fixture source at runtime.
exec(compile(source.replace(old,new),str(path),'exec'),{'__name__':'__main__','__file__':str(path)})
