"""Actual 5bb source nodes in source-backed POSIX fork/actor simulation."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys

import pytest

from adapters.carrot import recorder_5bb as r
from recorder_810e_support import REFERENCE


def test_5bb_model_import_sites_still_lazy_main_only():
    for name in ['openpilot/selfdrive/modeld/modeld.py','openpilot/selfdrive/modeld/jetlink/prepare.py']:
        tree=ast.parse(r.sources(REFERENCE)[name]);parents={c:n for n in ast.walk(tree) for c in ast.iter_child_nodes(n)}
        nodes=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module=='openpilot.selfdrive.modeld.jetlink.model']
        assert len(nodes)==1
        node=nodes[0]
        while not isinstance(node,ast.FunctionDef):node=parents[node]
        assert node.name=='main'


@pytest.mark.parametrize('helper,outcome,expected',[('no','complete',[True,False]),('yes','complete',[True,False]),('yes','failed',[True,False]),('no','source_drift',[False,False])])
def test_5bb_fork_guard_helper_and_second_child(tmp_path,helper,outcome,expected):
    helper_path=Path(__file__).with_name('fixtures')/'recorder_5bb_fork.py'
    result=subprocess.run([sys.executable,'-B',str(helper_path),str(REFERENCE),str(tmp_path/'root'),'B','none',helper,outcome],
        capture_output=True,text=True,timeout=40,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout.strip().splitlines()[-1])
    assert value['fork_start_method']=='fork'
    assert not value['manager_preimport_target'] and not value['offroad_modeld_started']
    assert not value['parent_target_after_children'] and not value['manager_capture_env_after']
    assert [e['active'] for e in value['events'] if e['actor']=='modeld']==expected
    if helper=='yes':assert next(e for e in value['events'] if e['actor']=='prepare_helper')['ticket_remaining']
    assert value['ticket_remaining'] is (outcome=='source_drift')
