import ast
import base64
import hashlib
import os
import subprocess
import sys
import zlib

import pytest


def decoder(pin,mode='stdout'):
    from tools.readonly_payload_gate import build_decoder
    return build_decoder(pin,mode)


def invoke(source=b'print("PINNED_FIXTURE")\n',*,mode='stdout',flags=('-B',),pin=None,encoded=None):
    script=decoder(pin or hashlib.sha256(source).hexdigest(),mode)
    value=encoded if encoded is not None else base64.b64encode(zlib.compress(source)).decode()
    if len(value)>100000:
        # Exercise the decoder budget without exceeding the OS exec env limit.
        wrapper='import os,sys;os.environ["M192_AUDIT_SRC"]=sys.stdin.read();exec('+repr(script)+')'
        return subprocess.run([sys.executable,'-E',*flags,'-c',wrapper],capture_output=True,
            input=value.encode(),timeout=5)
    return subprocess.run([sys.executable,'-E',*flags,'-c',script],capture_output=True,
        env={**os.environ,'M192_AUDIT_SRC':value},timeout=5)


def test_exact_source_bytes_are_output_without_execution():
    source=b'raise AssertionError("must not execute in stdout mode")\n'
    out=invoke(source)
    assert out.returncode==0 and out.stdout==source and out.stderr==b''


def test_execute_mode_runs_the_exact_verified_preflight_once():
    out=invoke(mode='execute')
    assert out.returncode==0 and out.stdout==b'PINNED_FIXTURE\n' and out.stderr==b''


@pytest.mark.parametrize('flags',[('-O','-B'),('-OO','-B')])
def test_optimization_is_rejected_before_legacy_assert_source_runs(flags):
    out=invoke(b'assert False\nprint("BYPASSED")\n',mode='execute',flags=flags)
    assert out.returncode==78 and out.stdout==b''
    assert out.stderr==b'READONLY_PAYLOAD_GATE:OPTIMIZED_INTERPRETER\n'


def test_missing_bytecode_suppression_is_rejected():
    out=invoke(flags=())
    assert out.returncode==78 and out.stdout==b''
    assert out.stderr==b'READONLY_PAYLOAD_GATE:BYTECODE_ENABLED\n'


def test_source_mismatch_is_unconditional_and_never_executes():
    out=invoke(mode='execute',pin='0'*64)
    assert out.returncode==78 and out.stdout==b''
    assert out.stderr==b'READONLY_PAYLOAD_GATE:SOURCE_PIN_MISMATCH\n'


@pytest.mark.parametrize('encoded',['%%%','abc','eA==\n','A'*1398105],ids=['invalid','padding','whitespace','overbudget'])
def test_invalid_or_overbudget_base64_is_closed(encoded):
    out=invoke(encoded=encoded)
    assert out.returncode==78 and out.stdout==b''
    assert out.stderr==b'READONLY_PAYLOAD_GATE:ENCODING_INVALID\n'


def test_invalid_compression_is_closed():
    out=invoke(encoded=base64.b64encode(b'not zlib').decode())
    assert out.returncode==78 and out.stderr==b'READONLY_PAYLOAD_GATE:COMPRESSION_INVALID\n'


@pytest.mark.parametrize('suffix',[b'junk',zlib.compress(b'another stream')])
def test_trailing_or_concatenated_compression_is_rejected(suffix):
    out=invoke(encoded=base64.b64encode(zlib.compress(b'pass\n')+suffix).decode())
    assert out.returncode==78 and out.stderr==b'READONLY_PAYLOAD_GATE:COMPRESSION_INVALID\n'


def test_decompression_expansion_is_bounded_before_sha_or_exec():
    out=invoke(b'X'*262145,mode='execute')
    assert out.returncode==78 and out.stdout==b''
    assert out.stderr==b'READONLY_PAYLOAD_GATE:SOURCE_SIZE_INVALID\n'


def test_verified_empty_source_is_rejected():
    out=invoke(b'')
    assert out.returncode==78 and out.stderr==b'READONLY_PAYLOAD_GATE:SOURCE_SIZE_INVALID\n'


@pytest.mark.parametrize('pin,mode',[('x'*64,'stdout'),('0'*63,'stdout'),(True,'stdout'),
    ('0'*64,'arbitrary'),('0'*64,False)])
def test_builder_has_closed_hash_and_execution_modes(pin,mode):
    with pytest.raises(ValueError):decoder(pin,mode)


def test_gate_contains_no_production_assert_or_device_dispatch():
    text=decoder('0'*64)
    assert not any(isinstance(n,ast.Assert) for n in ast.walk(ast.parse(text)))
    assert all(token not in text for token in ('subprocess','socket','arm_discovered','mkdir','open('))
