"""Source-backed810e manager fork/lazy import and actor isolation, CPU_FAKE."""
import json
import ast
import os
from pathlib import Path
import subprocess
import sys
import pytest
from recorder_810e_support import REFERENCE
from recorder_810e_support import blob

ROOT=Path(__file__).resolve().parents[1]


def test_both_production_model_import_sites_are_lazy_main_only():
    for path in ('openpilot/selfdrive/modeld/modeld.py','openpilot/selfdrive/modeld/jetlink/prepare.py'):
        tree=ast.parse(blob(path));parents={child:node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
        imports=[n for n in ast.walk(tree) if isinstance(n,ast.ImportFrom) and n.module=='openpilot.selfdrive.modeld.jetlink.model']
        assert len(imports)==1
        node=imports[0]
        while not isinstance(node,ast.FunctionDef):node=parents[node]
        assert node.name=='main'


@pytest.mark.parametrize('helper,outcome,expected',[
    ('no','complete',[True,False]),
    ('yes','complete',[True,False]),
    ('yes','failed',[True,False]),
    ('no','source_drift',[False,False]),
])
def test_exact810_fork_actor_and_second_child(tmp_path,helper,outcome,expected):
    result=subprocess.run([sys.executable,'-B',str(ROOT/'tests/fixtures/recorder_810e_fork.py'),
        str(REFERENCE),str(tmp_path/'root'),'B','none',helper,outcome],cwd=ROOT,capture_output=True,
        text=True,timeout=40,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
    assert result.returncode==0,result.stdout+result.stderr
    value=json.loads(result.stdout.strip().splitlines()[-1])
    assert value['fork_start_method']=='fork'
    assert value['manager_preimport_target'] is False
    assert value['offroad_modeld_started'] is False
    assert value['parent_target_after_children'] is False
    assert not value['manager_capture_env_after']
    assert [e['active'] for e in value['events'] if e['actor']=='modeld']==expected
    if helper=='yes':assert next(e for e in value['events'] if e['actor']=='prepare_helper')['ticket_remaining'] is True
    assert value['ticket_remaining'] is (outcome=='source_drift')
