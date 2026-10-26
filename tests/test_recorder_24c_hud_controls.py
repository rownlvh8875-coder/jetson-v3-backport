"""Exact24c software-only worker controls and CLI default/trailing override."""
import argparse
import ast
import types

import pytest

from adapters.carrot import recorder_24c as profile
from recorder_810e_support import REFERENCE
from test_recorder_24c_hud import load_hud_source


def pipeline(root,monkeypatch,threads):
    cls=load_hud_source(root,monkeypatch).H264UsbPipeline
    return cls(usb_display=None,width=64,height=96,encoder_align=1,fps=10,
        bitrate='2333k',gop=1,backend='ffmpeg',library_path='',ffmpeg_path='ffmpeg',
        ffmpeg_encoder='libx264',device_path='',input_format='nv12',slice_max_bytes=0,
        rate_control='vbr-cfr',realtime_priority=False,requested_chunk_size=0,
        wait_for_ack=False,soft_ack=False,dump_path='',debug=False,ffmpeg_threads=threads)


@pytest.mark.parametrize('encoder',['libx264','h264_v4l2m2m','h264_omx'])
def test_thread_options_change_only_software_pools_and_preserve_format(tmp_path,monkeypatch,encoder):
    automatic=pipeline(tmp_path/'auto',monkeypatch,0)._ffmpeg_command('ffmpeg',encoder,'h264')
    bounded=pipeline(tmp_path/'bounded',monkeypatch,1)._ffmpeg_command('ffmpeg',encoder,'h264')
    if encoder=='libx264':
        assert '-threads:v' not in automatic and '-filter_threads' not in automatic
        assert bounded.index('-filter_threads') < bounded.index('-i')
        assert bounded.index('-threads:v') > bounded.index('pipe:0')
        for flag in ('-filter_threads','-threads:v'):
            i=bounded.index(flag);assert bounded[i+1]=='1';del bounded[i:i+2]
    assert bounded==automatic


@pytest.mark.parametrize('threads',[-1,17])
def test_invalid_worker_budget_rejects_without_starting_encoder(tmp_path,monkeypatch,threads):
    with pytest.raises(ValueError,match='ffmpeg_threads must be between'):
        pipeline(tmp_path,monkeypatch,threads)


def thread_parser():
    raw=profile.sources(REFERENCE)['openpilot/selfdrive/carrot/cluster/main.py']
    nodes=[n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.Call)
        and isinstance(n.func,ast.Attribute) and n.func.attr=='add_argument'
        and n.args and isinstance(n.args[0],ast.Constant)
        and n.args[0].value=='--usb-h264-ffmpeg-threads']
    assert len(nodes)==1
    parser=argparse.ArgumentParser()
    code=ast.fix_missing_locations(ast.Module(body=[ast.Expr(value=nodes[0])],type_ignores=[]))
    exec(compile(code,'<exact24c-parser-option>','exec'),dict(parser=parser))
    return parser


@pytest.mark.parametrize('argv,expected',[([],0),(['--usb-h264-ffmpeg-threads','1'],1),
    (['--usb-h264-ffmpeg-threads','1','--usb-h264-ffmpeg-threads','0'],0)])
def test_source_cli_default_and_trailing_automatic_override(argv,expected):
    assert thread_parser().parse_args(argv).usb_h264_ffmpeg_threads==expected


@pytest.mark.parametrize('extra,expected',[([],1),(['--usb-h264-ffmpeg-threads','0'],0)])
def test_source_hud_defaults_one_worker_and_keeps_user_override(extra,expected):
    raw=profile.sources(REFERENCE)['tools/jetlink/hud.py']
    nodes=[n for n in ast.walk(ast.parse(raw)) if isinstance(n,ast.Assign)
        and any(isinstance(t,ast.Attribute) and isinstance(t.value,ast.Name)
            and t.value.id=='sys' and t.attr=='argv' for t in n.targets)]
    assert len(nodes)==1
    sys=types.SimpleNamespace(argv=['fixture-hud',*extra])
    exec(compile(ast.fix_missing_locations(ast.Module(body=nodes,type_ignores=[])),
        '<exact24c-hud-default-argv>','exec'),dict(sys=sys,__file__='fixture-hud'))
    assert thread_parser().parse_known_args(sys.argv[1:])[0].usb_h264_ffmpeg_threads==expected
