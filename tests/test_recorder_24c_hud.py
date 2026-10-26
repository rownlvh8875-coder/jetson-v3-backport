"""Concurrent exact24c HUD source and recorder/model identity, CPU_FAKE only.

Catches a recorder lag/mutation or software HUD interference with model inputs.
Whole source H264UsbPipeline startup, submit_rgba, _write_all, stdout and close
execute unchanged. A safe display sink replaces hardware, and a bounded POSIX
pipe child replaces unavailable FFmpeg; neither encodes nor measures throughput.
JoiningModel/transport/Session/EngineHost run in separate fixture processes.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import threading
import time
import types

import numpy as np
import pytest

from adapters.carrot import recorder_24c as profile
from recorder_810e_support import REFERENCE
from test_recorder_24c_wire import run_24c_case


TARGET = '24c1ba5e4b3428f56fa0e402f5a10097e2e94c32'
HUD_PATH = 'openpilot/selfdrive/carrot/cluster/cluster_h264_pipeline.py'
HUD_SHA256 = '0c5de22e32c5f0e5fa77a5c5c620e94615d2ad1fefed9cab2edff47569a0c6b5'
CONTROLS = [
    pytest.param(False, False, False, False, False, id='socket-inline-basic'),
    pytest.param(False, True, True, True, True, id='socket-chunks-nav-overlap'),
    pytest.param(True, False, True, False, True, id='shared-nav-no-overlap'),
    pytest.param(True, True, False, True, False, id='shared-chunks-no-nav'),
]


def digest(value):
    return hashlib.sha256(memoryview(value).cast('B')).hexdigest()


def expected_inputs():
    """Independent synthetic input oracle, before any source/recorder execution."""
    frames = []
    for index, pulse in enumerate((0, 1, 0, 0, 1)):
        image = np.arange(393216, dtype=np.uint8) + index
        desire = np.array([0, pulse, 0, 0, 0, 0, 0, 0], np.float32)
        traffic = np.array([[1, 0] if index % 2 == 0 else [0, 1]], np.float32)
        action = np.array([[index / 4, (4 - index) / 4]], np.float32)
        frames.append(dict(zip(('new_img', 'desire', 'traffic_convention', 'action_t'),
                               map(digest, (image, desire, traffic, action)))))
    return frames


class OfflineDisplay:
    """In-memory source egress sink; never opens USB or a network connection."""
    def __init__(self):
        self.started = self.stopped = False
        self.chunks = []

    def start_h264_stream(self, requested):
        assert requested == 4096 and not self.started
        self.started = True
        return requested

    def send_h264_chunk(self, value, **options):
        assert self.started and not self.stopped
        self.chunks.append(dict(bytes=len(value), monotonic_ns=time.monotonic_ns()))

    def stop_h264_stream(self):
        assert self.started and not self.stopped
        self.stopped = True


def load_hud_source(root, monkeypatch):
    raw = subprocess.check_output(['git', '-C', str(REFERENCE), 'show', TARGET + ':' + HUD_PATH])
    assert hashlib.sha256(raw).hexdigest() == HUD_SHA256
    assert profile.SOURCE_PINS[HUD_PATH] == HUD_SHA256
    path = root / HUD_PATH
    path.parent.mkdir(parents=True)
    path.write_bytes(raw)
    dependency = types.ModuleType('cluster_usb_display')
    dependency.TuringUsbDisplay = OfflineDisplay
    monkeypatch.setitem(sys.modules, dependency.__name__, dependency)
    module = types.ModuleType('_m19c05_exact24c_hud')
    module.__file__ = str(path)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    exec(compile(raw, str(path), 'exec'), module.__dict__)
    return module


def pipe_events(path):
    if not path.exists():
        return []
    # A child may be writing the last JSON line while the worker is active.
    return [json.loads(line) for line in path.read_text().splitlines() if line.endswith('}')]


@contextmanager
def active_hud(root, monkeypatch, threads):
    assert os.name == 'posix', 'POSIX pipe fixture must run in the checked WSL environment'
    root.mkdir()
    module = load_hud_source(root, monkeypatch)
    display = OfflineDisplay()
    child_log = root / 'pipe-child.jsonl'
    helper = Path(__file__).with_name('fixtures') / 'recorder_24c_hud.py'
    executable = root / 'cpu-fake-ffmpeg-pipe'
    executable.write_bytes(('#!' + sys.executable + '\n').encode() + helper.read_bytes())
    executable.chmod(0o700)
    monkeypatch.setenv('M19C05_HUD_PIPE_RECEIPT', str(child_log))
    pipeline = module.H264UsbPipeline(
        usb_display=display, width=256, height=128, encoder_align=16, fps=20,
        bitrate='300k', gop=20, backend='ffmpeg', library_path='UNUSED_CPU_FAKE',
        ffmpeg_path=str(executable), ffmpeg_encoder='libx264', device_path='UNUSED_CPU_FAKE',
        input_format='auto', slice_max_bytes=4096, rate_control='vbr-cfr',
        realtime_priority=False, requested_chunk_size=4096, wait_for_ack=False,
        soft_ack=False, dump_path='', debug=False, ffmpeg_threads=threads)
    source_frame = bytearray(np.arange(256 * 128 * 4, dtype=np.uint8).tobytes())
    source_hash = digest(source_frame)
    stopped, ready = threading.Event(), threading.Event()
    writes, failures = [], []
    evidence = dict(classification='CPU_FAKE_PIPE_NOT_ENCODER', source_commit=TARGET,
                    source_sha256=HUD_SHA256, ffmpeg_threads=threads,
                    real_ffmpeg_available=shutil.which('ffmpeg') is not None,
                    parent_pid=os.getpid(), frame_bytes=len(source_frame),
                    frame_sha256=source_hash, submissions=writes)

    def produce():
        evidence['worker_thread_id'] = threading.get_ident()
        try:
            while not stopped.is_set():
                started = time.monotonic_ns()
                pipeline.submit_rgba(source_frame, 256, 128)
                writes.append(dict(index=len(writes), started_ns=started,
                                   completed_ns=time.monotonic_ns(),
                                   encoder_alive=pipeline.encoder_pid is not None))
                if len(writes) >= 3:
                    ready.set()
        except BaseException as error:
            failures.append(repr(error))
            ready.set()

    pipeline.start()
    evidence['encoder_pid'] = pipeline.encoder_pid
    assert evidence['encoder_pid'] not in (None, os.getpid())
    worker = threading.Thread(target=produce, name='exact24c-source-rgba-submit', daemon=True)
    worker.start()
    try:
        assert ready.wait(5) and not failures, failures
        assert len(writes) >= 3
        yield evidence
    finally:
        stopped.set()
        worker.join(5)
        pipeline.close()
        worker.join(2)
        evidence.update(worker_terminated=not worker.is_alive(), failures=failures,
                        child_returncode=pipeline._proc.returncode,
                        source_frame_unchanged=digest(source_frame) == source_hash,
                        display_started=display.started, display_stopped=display.stopped,
                        stdout_chunks=display.chunks, pipe_events=pipe_events(child_log))
        (root / 'hud-source-receipt.json').write_text(json.dumps(evidence, indent=2) + '\n')
        assert not worker.is_alive() and not failures, failures
        assert pipeline._proc.returncode == 0
        assert evidence['source_frame_unchanged']


def observe_brackets(observers, evidence):
    """Use each observer timestamp, with progressing source submissions around it.

    A timestamp may land between two writes. Requiring exact in-call membership
    would turn a legitimate scheduling gap into an intermittent test failure.
    Adjacent completed/started writes and independent child drains bracket every
    observation instead; neither one whole-case interval nor pre/post work earns
    this assertion.
    """
    writes = evidence['submissions']
    frames = [event for event in evidence['pipe_events'] if event['event'] == 'frame']
    brackets = []
    for stamp in observers:
        before = max((w for w in writes if w['completed_ns'] < stamp), key=lambda w: w['index'])
        after = min((w for w in writes if w['started_ns'] > stamp), key=lambda w: w['index'])
        drained_before = max((f for f in frames if f['completed_ns'] < stamp), key=lambda f: f['index'])
        drained_after = min((f for f in frames if f['completed_ns'] > stamp), key=lambda f: f['index'])
        assert 1 <= after['index'] - before['index'] <= 2
        assert stamp - before['completed_ns'] < 750_000_000
        assert after['started_ns'] - stamp < 750_000_000
        assert drained_before['index'] < drained_after['index']
        assert before['encoder_alive'] and after['encoder_alive']
        brackets.append(dict(observer_monotonic_ns=stamp,
                             source_before=before, source_after=after,
                             child_before=drained_before, child_after=drained_after))
    assert any(observers[0] < w['completed_ns'] < observers[-1] for w in writes)
    assert any(observers[0] < f['completed_ns'] < observers[-1] for f in frames)
    return brackets


@pytest.mark.parametrize('threads', [0, 1], ids=['threads-auto', 'threads-one'])
@pytest.mark.parametrize('shared,chunks,compact,overlap,nav', CONTROLS)
def test_concurrent_hud_preserves_five_source_model_frames(
        tmp_path, monkeypatch, shared, chunks, compact, overlap, nav, threads):
    expected = expected_inputs()
    controls = dict(shared=shared, chunks=chunks, compact=compact, overlap=overlap, nav=nav)
    inactive_root = tmp_path / 'hud-inactive'
    inactive_root.mkdir()
    baseline = run_24c_case(inactive_root, monkeypatch, **controls)
    active_root = tmp_path / 'hud-active'
    active_root.mkdir()
    with active_hud(active_root / 'hud', monkeypatch, threads) as hud:
        active = run_24c_case(active_root, monkeypatch, **controls)
        # Allow an actual subsequent source submission/child drain to finish;
        # records retain their original monotonic_ns values from the observer.
        deadline = time.monotonic() + 3
        last_observer = active['observer_monotonic_ns'][-1]
        while not any(w['started_ns'] > last_observer for w in hud['submissions']):
            assert time.monotonic() < deadline
            time.sleep(.002)
    for result in (baseline, active):
        assert result['source_commit'] == TARGET
        assert result['profile'] == 'RECORDER_24C_HUD_HOST_V1'
        assert result['client']['recorded_hashes'] == result['client']['submitted_hashes'] == result['server']['engine_hashes'] == expected
        assert len(set(row['new_img'] for row in result['client']['recorded_hashes'])) == 5
        assert result['observer_monotonic_ns'] == sorted(set(result['observer_monotonic_ns']))
    assert baseline['client']['scalar_hashes'] == active['client']['scalar_hashes']
    frames = [event for event in hud['pipe_events'] if event['event'] == 'frame']
    assert len(frames) >= 5
    assert all(frame['sha256'] == hud['frame_sha256'] and frame['bytes'] == hud['frame_bytes'] for frame in frames)
    assert hud['worker_thread_id'] != threading.get_ident()
    started, = [event for event in hud['pipe_events'] if event['event'] == 'started']
    assert started['pid'] == hud['encoder_pid'] and started['ppid'] == os.getpid()
    argv = started['argv']
    if threads:
        assert argv[argv.index('-filter_threads') + 1] == '1'
        assert argv[argv.index('-threads:v') + 1] == '1'
    else:
        assert '-filter_threads' not in argv and '-threads:v' not in argv
    assert hud['display_started'] and hud['display_stopped'] and hud['stdout_chunks']
    brackets = observe_brackets(active['observer_monotonic_ns'], hud)
    receipt = dict(status='PASS', evidence_kind='OFFLINE_CPU_FAKE_SOURCE_HUD_MODEL_IDENTITY',
                   source_commit=TARGET, controls=controls, ffmpeg_threads=threads,
                   inactive_baseline=True, expected_hashes=expected,
                   recorded_hashes=active['client']['recorded_hashes'],
                   original_infer_hashes=active['client']['submitted_hashes'],
                   engine_first12_hashes=active['server']['engine_hashes'],
                   observer_hud_brackets=brackets, hud=hud,
                   limitations=['CPU_FAKE pipe child performs no H264 encoding.',
                                'CPU_FAKE model/warp; no GPU, ORT, TensorRT, USB or device.',
                                'No 20 Hz, encoder thread scheduling, latency or vehicle claim.'])
    (tmp_path / 'hud-model-identity-receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
