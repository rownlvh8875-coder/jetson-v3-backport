"""Rebind the frozen paired source fixture to exact24c and its generated hook.

Only profile import, expected pin count, receipt IDs and diagnostic labels differ.
All original behavior checks remain; no production source is rewritten.
"""
from pathlib import Path

path=Path(__file__).with_name('recorder_5bb_paired.py')
source=path.read_text()
before='from adapters.carrot import recorder_5bb as recorder'
after='from adapters.carrot import recorder_24c as recorder'
count='assert len(RAW) == len(recorder.SOURCE_PINS) == 33'
assert source.count(before)==source.count(count)==1
source=source.replace(before,after).replace(count,'assert len(RAW) == len(recorder.SOURCE_PINS) == 41')
source=source.replace('C04PAIR-','C05PAIR-').replace('<exact5bb','<exact24c')
exec(compile(source,str(path),'exec'),globals())
