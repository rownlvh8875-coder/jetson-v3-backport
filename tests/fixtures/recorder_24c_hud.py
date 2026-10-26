"""Bounded POSIX pipe CPU_FAKE child, never an H264 encoder.

The exact source builds its complete ffmpeg argv and starts this executable in
place of absent FFmpeg. It independently hashes each fully drained RGBA frame.
AUD fixture bytes exercise the source stdout/send worker without codec claims.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import time


def main():
    args = sys.argv[1:]
    if args == ['-hide_banner', '-muxers']:
        print(' E h264 CPU_FAKE bounded pipe; no encoding')
        return
    if args == ['-hide_banner', '-encoders']:
        print(' V..... libx264 CPU_FAKE command control; no encoding')
        return
    assert args[args.index('-f') + 1] == 'rawvideo'
    assert args[args.index('-pix_fmt') + 1] == 'rgba'
    assert args[args.index('-c:v') + 1] == 'libx264'
    assert args[args.index('-i') + 1] == 'pipe:0'
    assert args[-3:] == ['-f', 'h264', 'pipe:1']
    width, height = map(int, args[args.index('-s:v') + 1].split('x'))
    frame_bytes = width * height * 4
    assert 0 < frame_bytes <= 1024 * 1024
    path = Path(os.environ['M19C05_HUD_PIPE_RECEIPT'])
    with path.open('x', buffering=1) as receipt:
        def emit(value):
            receipt.write(json.dumps(value, sort_keys=True) + '\n')
        emit(dict(event='started', pid=os.getpid(), ppid=os.getppid(),
                  monotonic_ns=time.monotonic_ns(), argv=args,
                  classification='CPU_FAKE_PIPE_NOT_ENCODER'))
        pending = bytearray()
        started = time.monotonic_ns()
        count = 0
        deadline = time.monotonic() + 45
        while count < 1024 and time.monotonic() < deadline:
            block = os.read(0, min(4096, frame_bytes - len(pending)))
            if not block:
                break
            pending.extend(block)
            # Deliberate bounded backpressure makes concurrent source writes
            # observable. This is a fixture pace, never encoder latency data.
            time.sleep(.001)
            if len(pending) == frame_bytes:
                emit(dict(event='frame', index=count, bytes=len(pending),
                          sha256=hashlib.sha256(pending).hexdigest(),
                          started_ns=started, completed_ns=time.monotonic_ns()))
                os.write(1, b'\x00\x00\x00\x01\x09\xf0')
                pending.clear()
                started = time.monotonic_ns()
                count += 1
        assert not pending, 'partial source RGBA frame at pipe close'
        emit(dict(event='exit', frames=count, monotonic_ns=time.monotonic_ns()))


if __name__ == '__main__':
    main()
