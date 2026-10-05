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


def main() -> None:
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
