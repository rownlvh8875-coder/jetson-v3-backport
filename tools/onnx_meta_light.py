#!/usr/bin/env python3
"""Memory-light ONNX metadata reader.

Walks the protobuf wire format and extracts only:
  - graph inputs  (name, elem_type, shape)
  - graph outputs (name, elem_type, shape)
  - metadata_props (output_slices, model_checkpoint, ...)

The 766 MB of initializers/weights are skipped, never materialised.
Mirrors the intent of jetlink/onnx_meta.py::_parse_tinygrad, but needs
only the `onnx` package (its protobuf runtime), not tinygrad.

Usage:
  python3 tools/onnx_meta_light.py <model.onnx>
"""
from __future__ import annotations

import sys

# ONNX TensorProto.DataType -> numpy dtype name (same table as onnx_meta.py)
ELEM_TYPE = {
  1: 'float32', 2: 'uint8', 3: 'int8', 4: 'uint16', 5: 'int16', 6: 'int32',
  7: 'int64', 9: 'bool', 10: 'float16', 11: 'float64', 12: 'uint32', 13: 'uint64',
}


class _Reader:
  def __init__(self, buf: bytes):
    self.buf = buf
    self.pos = 0

  def eof(self) -> bool:
    return self.pos >= len(self.buf)

  def varint(self) -> int:
    shift = result = 0
    while True:
      b = self.buf[self.pos]; self.pos += 1
      result |= (b & 0x7f) << shift
      if not b & 0x80:
        return result
      shift += 7

  def tag(self) -> tuple[int, int]:
    t = self.varint()
    return t >> 3, t & 7

  def bytes(self) -> bytes:
    n = self.varint()
    b = self.buf[self.pos:self.pos + n]
    self.pos += n
    return b

  def skip(self, wire: int) -> None:
    if wire == 0:
      self.varint()
    elif wire == 1:
      self.pos += 8
    elif wire == 2:
      n = self.varint()  # NB: read length first; `self.pos += self.varint()`
      self.pos += n      # would use the pre-call pos (off by one)
    elif wire == 5:
      self.pos += 4
    else:
      raise ValueError(f"unsupported wire type {wire}")

  def sub(self) -> "_Reader":
    return _Reader(self.bytes())


def _parse_shape(r: _Reader) -> tuple[int, ...]:
  dims = []
  while not r.eof():
    fid, wire = r.tag()
    if fid == 1 and wire == 2:  # TensorShapeProto.dim
      d = r.sub()
      val = 0
      while not d.eof():
        df, dw = d.tag()
        if df == 1 and dw == 0:      # dim_value
          val = d.varint()
        elif df == 2 and dw == 2:    # dim_param (symbolic) -> 0
          d.bytes(); val = 0
        else:
          d.skip(dw)
      dims.append(val)
    else:
      r.skip(wire)
  return tuple(dims)


def _parse_value_info(buf: bytes) -> tuple[str, int, tuple[int, ...]]:
  """ValueInfoProto -> (name, elem_type, shape)."""
  r = _Reader(buf)
  name, elem, shape = "", 0, ()
  while not r.eof():
    fid, wire = r.tag()
    if fid == 1 and wire == 2:
      name = r.bytes().decode()
    elif fid == 2 and wire == 2:  # TypeProto
      t = r.sub()
      while not t.eof():
        tf, tw = t.tag()
        if tf == 1 and tw == 2:  # tensor_type
          tt = t.sub()
          while not tt.eof():
            ef, ew = tt.tag()
            if ef == 1 and ew == 0:
              elem = tt.varint()
            elif ef == 2 and ew == 2:
              shape = _parse_shape(tt.sub())
            else:
              tt.skip(ew)
        else:
          t.skip(tw)
    else:
      r.skip(wire)
  return name, elem, shape


def _parse_graph(buf: bytes) -> tuple[dict, dict]:
  inputs, outputs = {}, {}
  r = _Reader(buf)
  while not r.eof():
    fid, wire = r.tag()
    if (fid == 11 or fid == 12) and wire == 2:  # GraphProto.input/.output
      name, elem, shape = _parse_value_info(r.bytes())
      (inputs if fid == 11 else outputs)[name] = (shape, elem)
    else:
      r.skip(wire)  # nodes, initializers, value_info skipped
  return inputs, outputs


def parse_meta_light(path: str) -> dict:
  """-> {'inputs': {name: (shape, dtype)}, 'outputs': {...}, 'props': {...}}"""
  with open(path, "rb") as f:
    data = f.read()
  r = _Reader(data)
  inputs = outputs = None
  props: dict[str, str] = {}
  while not r.eof():
    fid, wire = r.tag()
    if fid == 7 and wire == 2:          # ModelProto.graph
      inputs, outputs = _parse_graph(r.bytes())
    elif fid == 14 and wire == 2:       # ModelProto.metadata_props
      e = r.sub()
      k = v = ""
      while not e.eof():
        ef, ew = e.tag()
        if ef == 1 and ew == 2:
          k = e.bytes().decode()
        elif ef == 2 and ew == 2:
          v = e.bytes().decode()
        else:
          e.skip(ew)
      props[k] = v
    else:
      r.skip(wire)
  if inputs is None:
    raise ValueError("no graph found in ONNX file")
  return {
    "inputs": {n: (s, ELEM_TYPE.get(t, f"unknown({t})")) for n, (s, t) in inputs.items()},
    "outputs": {n: (s, ELEM_TYPE.get(t, f"unknown({t})")) for n, (s, t) in outputs.items()},
    "props": props,
  }


def decode_output_slices(encoded: str) -> dict:
  """Interpret only the observed dict[str, slice] pickle grammar; execute nothing."""
  import base64
  import pickletools
  stack, memo, mark = [], {}, object()
  for op, arg, _ in pickletools.genops(base64.b64decode(encoded)):
    name = op.name
    if name in ('PROTO', 'FRAME'): continue
    if name == 'EMPTY_DICT': stack.append({})
    elif name == 'MARK': stack.append(mark)
    elif name in ('SHORT_BINUNICODE', 'BINUNICODE', 'BININT', 'BININT1', 'BININT2'): stack.append(arg)
    elif name == 'NONE': stack.append(None)
    elif name == 'MEMOIZE': memo[len(memo)] = stack[-1]
    elif name in ('BINGET', 'LONG_BINGET'): stack.append(memo[arg])
    elif name == 'STACK_GLOBAL':
      symbol, module = stack.pop(), stack.pop()
      if (module, symbol) != ('builtins', 'slice'): raise ValueError('forbidden slice metadata global')
      stack.append(('slice-constructor',))
    elif name == 'TUPLE3':
      args = tuple(stack[-3:]); del stack[-3:]; stack.append(args)
    elif name == 'REDUCE':
      args, constructor = stack.pop(), stack.pop()
      if constructor != ('slice-constructor',) or len(args) != 3 or args[2] is not None:
        raise ValueError('forbidden slice metadata constructor')
      if any(type(v) is not int or v < 0 for v in args[:2]) or args[0] > args[1]:
        raise ValueError('invalid output slice bounds')
      stack.append(list(args[:2]))
    elif name in ('SETITEMS', 'SETITEM'):
      if name == 'SETITEM':
        value, key = stack.pop(), stack.pop(); stack[-1][key] = value
      else:
        boundary = next(i for i in range(len(stack)-1, -1, -1) if stack[i] is mark)
        values = stack[boundary+1:]; del stack[boundary:]
        if len(values) % 2: raise ValueError('invalid slice metadata dictionary')
        stack[-1].update(zip(values[::2], values[1::2]))
    elif name == 'STOP': break
    else: raise ValueError(f'forbidden slice metadata opcode: {name}')
  if len(stack) != 1 or type(stack[0]) is not dict or not all(
      type(k) is str and type(v) is list and len(v) == 2 for k, v in stack[0].items()):
    raise ValueError('invalid output slice metadata')
  return stack[0]


def check_meta_against_spec(path, spec):
  meta = parse_meta_light(str(path))
  for kind, prefix in (('inputs', 'input'), ('outputs', 'output')):
    actual = {n: (list(shape), dtype) for n, (shape, dtype) in meta[kind].items()}
    expected = {n: (shape, spec[prefix+'_dtypes'][n]) for n, shape in spec[prefix+'_shapes'].items()}
    if actual != expected: raise ValueError(f'{kind} mismatch: {actual} != {expected}')
  slices = decode_output_slices(meta['props']['output_slices'])
  if slices != spec['output_slices']: raise ValueError('output_slices mismatch')
  if meta['props']['model_checkpoint'] != spec['checkpoint']: raise ValueError('checkpoint mismatch')
  return dict(inputs=meta['inputs'], outputs=meta['outputs'], output_slices=slices,
              checkpoint=meta['props']['model_checkpoint'])


def main() -> None:
  if len(sys.argv) == 3:
    import json
    from pathlib import Path
    print(json.dumps(check_meta_against_spec(sys.argv[1], json.loads(Path(sys.argv[2]).read_text())), indent=2))
    return
  meta = parse_meta_light(sys.argv[1])
  print("inputs:")
  for n, (s, t) in meta["inputs"].items():
    print(f"  {n:<20} {str(s):<28} {t}")
  print("outputs:")
  for n, (s, t) in meta["outputs"].items():
    print(f"  {n:<20} {str(s):<28} {t}")
  print("metadata_props:", sorted(meta["props"]))


if __name__ == "__main__":
  main()
