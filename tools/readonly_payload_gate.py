"""Build a memory-only exact-source gate; no device dispatcher or IO at build."""


def build_decoder(expected_sha,mode='stdout'):
    """Expected SHA must come from an independently reviewed release manifest.

    execute runs trusted pinned preflight source; it is not a sandbox. stdout
    emits exact verified bytes for a separate python -B stdin receiver. The
    caller must still verify that receiver/runtime and fresh device gates.
    """
    if (type(expected_sha) is not str or len(expected_sha)!=64 or
        any(c not in '0123456789abcdef' for c in expected_sha)):
        raise ValueError('SOURCE_PIN')
    if type(mode) is not str or mode not in ('stdout','execute'):raise ValueError('MODE')
    template='''import sys

def _fail(code):
    sys.stderr.write("READONLY_PAYLOAD_GATE:"+code+"\\n")
    raise SystemExit(78)

if sys.flags.optimize!=0:_fail("OPTIMIZED_INTERPRETER")
if not sys.dont_write_bytecode:_fail("BYTECODE_ENABLED")

import os,base64,zlib,hashlib
encoded=os.environ.pop("M192_AUDIT_SRC",None)
if type(encoded) is not str or not encoded or len(encoded)>1398104:
    _fail("ENCODING_INVALID")
try:
    packed=base64.b64decode(encoded,validate=True)
    if base64.b64encode(packed).decode("ascii")!=encoded or len(packed)>1048576:
        _fail("ENCODING_INVALID")
except (ValueError,UnicodeError):
    _fail("ENCODING_INVALID")
try:
    stream=zlib.decompressobj()
    source=stream.decompress(packed,262145)
except zlib.error:
    _fail("COMPRESSION_INVALID")
if not source or len(source)>262144:_fail("SOURCE_SIZE_INVALID")
if not stream.eof or stream.unused_data or stream.unconsumed_tail:
    _fail("COMPRESSION_INVALID")
if hashlib.sha256(source).hexdigest()!=@@SHA@@:_fail("SOURCE_PIN_MISMATCH")
@@ACTION@@
'''
    action=('sys.stdout.buffer.write(source)' if mode=='stdout' else
        'exec(compile(source,"<pinned-readonly-preflight>","exec"))')
    return template.replace('@@SHA@@',repr(expected_sha)).replace('@@ACTION@@',action)
