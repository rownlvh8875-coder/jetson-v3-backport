#!/usr/bin/env python3
"""Retype Cinque v3's uint8 image-queue inputs to fp16 for TensorRT 10.3.

=====================================================================
DESIGN (from real graph analysis, not assumed):

  v3 ONNX (measured):
    new_img      uint8  -> Unsqueeze -> unsqueeze
    state_img_q  uint8  -> Slice     -> slice_1
    Concat(slice_1, unsqueeze) -> next_state_img_q  (uint8)
    next_state_img_q -> Gather -> Slice -> Reshape -> Concat -> cat_2
    cat_2 -> Cast(uint8->fp16) [node__to_copy_4] -> vision trunk (fp16)

  TensorRT 10.3 rejects UINT8 *graph inputs*
  ("Found unsupported input type of UINT8"), so the inputs must be
  retyped -- but unlike v2 there is NO head Cast to drop. v2's
  patch_uint8_inputs() would fail here ("could not find the head Cast"),
  and merely adding 'new_img' to IMG_INPUTS would hit exactly that.

  This patch retypes the two image-queue inputs (new_img, state_img_q)
  to FLOAT16 and updates the next_state_img_q output declaration to
  FLOAT16. The queue ops (Unsqueeze/Slice/Concat/Gather/Reshape) are pure
  data movement, and 0..255 is exactly representable in fp16, so the
  vision trunk receives BIT-IDENTICAL fp16 values: the downstream Cast
  (node__to_copy_4) changes from uint8->fp16 into a fp16->fp16 no-op.
  This is verified by ORT multi-frame parity (patched vs original),
  not claimed from the 0..255 range alone.

  next_state_img_q is intentionally LEFT as fp16 (no trailing Cast back
  to uint8): the server feeds next_state_* straight back as state_*,
  so fp16->fp16 feedback is consistent and a trailing Cast would only
  add a pointless quantize step.

SERVER IMPACT (must match):
  - The server must feed fp16 for new_img/state_img_q (like v2's LUT
    uint8->fp16 conversion in queues.py).
  - Engine I/O dtypes after this patch:
      new_img: float16, state_img_q: float16, next_state_img_q: float16
    The session's _check_shapes must allow exactly these backend-declared
    transforms (see dtype_transforms), not compare against the raw ONNX
    dtypes.

Interface mirrors production onnx_patch.py so this can move into
carrot-jetson's jetlink/onnx_patch.py later:
  needs_patch_v3(model) -> bool
  patch_v3_uint8_inputs(model) -> dict[str, str]  (retype record)

JETSON ONLY for the actual build; the patch itself is pure ONNX
rewriting and is unit-tested on the dev VM against the real v3 ONNX.
=====================================================================
"""
from __future__ import annotations

import sys
from pathlib import Path

V3_IMG_INPUTS = ('new_img', 'state_img_q')
V3_IMG_OUTPUT = 'next_state_img_q'
# data-movement ops allowed on the image-queue path; anything else there
# is unexpected and fails closed instead of being silently retyped
_QUEUE_OPS = ('Unsqueeze', 'Slice', 'Concat', 'Gather', 'Reshape')


def _elem_type_of(vi) -> int:
    from onnx import TensorProto
    return vi.type.tensor_type.elem_type


def needs_patch_v3(model) -> bool:
    """True when v3's image-queue inputs are still uint8."""
    from onnx import TensorProto
    return any(vi.name in V3_IMG_INPUTS
               and _elem_type_of(vi) == TensorProto.UINT8
               for vi in model.graph.input)


def _consumers(graph):
    cons = {}
    for n in graph.node:
        for i in n.input:
            cons.setdefault(i, []).append(n)
    return cons


def patch_v3_uint8_inputs(model) -> dict[str, str]:
    """Retype v3's uint8 image-queue path to fp16. In place.

    Returns the retype record {tensor_name: 'float16'} for the session's
    dtype_transforms contract. Raises ValueError on any unexpected graph
    shape instead of guessing.
    """
    from onnx import TensorProto
    g = model.graph

    targets = [vi for vi in g.input if vi.name in V3_IMG_INPUTS]
    if len(targets) != len(V3_IMG_INPUTS):
        missing = set(V3_IMG_INPUTS) - {vi.name for vi in targets}
        raise ValueError(f"v3 patch: missing image inputs {sorted(missing)}")
    for vi in targets:
        if _elem_type_of(vi) != TensorProto.UINT8:
            raise ValueError(
                f"v3 patch: {vi.name} is not uint8 (already patched?)")

    # Fail-closed structural check: the image inputs must feed ONLY the
    # known queue data-movement ops. Anything else means this is not the
    # graph we analyzed, and blind retyping could change numerics.
    cons = _consumers(g)
    fp16_tensors: set[str] = set(V3_IMG_INPUTS)
    queue = list(V3_IMG_INPUTS)
    while queue:
        t = queue.pop()
        for n in cons.get(t, []):
            if n.op_type == 'Cast':
                if not any(a.name == 'to' and a.i == TensorProto.FLOAT16 for a in n.attribute):
                    raise ValueError(f"v3 patch: unexpected Cast target ({n.name})")
                # the vision read-path Cast: stop here, it becomes a no-op
                continue
            if n.op_type not in _QUEUE_OPS:
                raise ValueError(
                    f"v3 patch: unexpected {n.op_type} ({n.name}) on the "
                    f"image-queue path at tensor {t!r}; refusing to retype")
            for o in n.output:
                if o not in fp16_tensors:
                    fp16_tensors.add(o)
                    queue.append(o)

    # The queue's Concat product is a graph output: its declaration must
    # follow the retype or parsers see a lie.
    out = next((o for o in g.output if o.name == V3_IMG_OUTPUT), None)
    if out is None:
        raise ValueError(f"v3 patch: graph output {V3_IMG_OUTPUT!r} missing")
    if _elem_type_of(out) != TensorProto.UINT8:
        raise ValueError(
            f"v3 patch: {V3_IMG_OUTPUT} is not uint8 (already patched?)")

    for vi in targets:
        vi.type.tensor_type.elem_type = TensorProto.FLOAT16
    out.type.tensor_type.elem_type = TensorProto.FLOAT16

    # Refresh stale value_info the same way production does: TensorRT
    # tolerates it, onnxruntime rejects the model.
    for vi in g.value_info:
        if vi.name in fp16_tensors and _elem_type_of(vi) == TensorProto.UINT8:
            vi.type.tensor_type.elem_type = TensorProto.FLOAT16

    return {n: 'float16' for n in
            ('new_img', 'state_img_q', 'next_state_img_q')}


def patch_file_v3(src: str | Path, dst: str | Path,
                  retypes_out: str | Path | None = None) -> dict[str, str]:
    """Load, patch, check, save. Returns the retype record."""
    import json
    import os
    import tempfile
    import onnx
    src, dst = Path(src), Path(dst)
    if src.resolve() == dst.resolve() or (retypes_out is not None and
            Path(retypes_out).resolve() in (src.resolve(), dst.resolve())):
        raise ValueError("v3 patch: output must not overwrite source/model")
    model = onnx.load(str(src))
    # tinygrad layout-hint ops: same treatment as production patch_file
    for n in [n for n in model.graph.node if n.domain == 'org.tinygrad']:
        if n.op_type != 'Contiguous':
            raise ValueError(f"v3 patch: unknown org.tinygrad op {n.op_type!r}")
        # Contiguous is a layout hint; bypass single-in single-out
        if len(n.input) != 1 or len(n.output) != 1:
            raise ValueError("v3 patch: Contiguous is not 1-in/1-out")
        src_t, dst_t = n.input[0], n.output[0]
        for m in model.graph.node:
            for i, name in enumerate(m.input):
                if name == dst_t:
                    m.input[i] = src_t
        model.graph.node.remove(n)
    if not needs_patch_v3(model):
        raise ValueError("v3 patch: model does not need it (not uint8 v3?)")
    retypes = patch_v3_uint8_inputs(model)
    onnx.checker.check_model(model, full_check=False)
    dst.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=dst.name + '.build-', dir=dst.parent) as td:
        staged = Path(td) / 'patched.onnx'
        onnx.save(model, str(staged))
        os.replace(staged, dst)
    if retypes_out is not None:
        Path(retypes_out).write_text(json.dumps(retypes, indent=2))
    return retypes


import json
CANONICAL_JSON = '{"checkpoint": "b9facbcc-4d47-410e-b3ce-dfcbad12ba92/56320/f78ed37d-afad-4dbc-8050-40ea885eedde/12864", "frame_skip": 4, "input_dtypes": {"action_t": "float32", "desire": "float32", "new_img": "uint8", "state_desire_q": "float32", "state_feat_q": "float32", "state_img_q": "uint8", "traffic_convention": "float32"}, "input_shapes": {"action_t": [1, 2], "desire": [8], "new_img": [2, 6, 128, 256], "state_desire_q": [132, 1, 8], "state_feat_q": [128, 1, 16384], "state_img_q": [2, 5, 6, 128, 256], "traffic_convention": [1, 2]}, "nbytes": 766354845, "output_dtypes": {"next_state_desire_q": "float32", "next_state_feat_q": "float32", "next_state_img_q": "uint8", "outputs": "float32"}, "output_shapes": {"next_state_desire_q": [132, 1, 8], "next_state_feat_q": [128, 1, 16384], "next_state_img_q": [2, 5, 6, 128, 256], "outputs": [1, 18452]}, "output_slices": {"action": [2062, 2066], "desire_pred": [855, 887], "desire_state": [2054, 2062], "hidden_state": [2066, 18450], "lane_lines": [0, 528], "lane_lines_prob": [528, 536], "lead": [1907, 2051], "lead_prob": [2051, 2054], "meta": [800, 855], "pad": [18450, 18452], "plan": [917, 1907], "pose": [887, 899], "road_edges": [536, 800], "road_transform": [905, 917], "wide_from_device_euler": [899, 905]}, "sha256": "404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4"}'


PATCH_ID = 'cinque-v3-image-fp16-v1'
DTYPE_TRANSFORMS = dict.fromkeys(('new_img', 'state_img_q', 'next_state_img_q'), 'float16')
CANONICAL_SPEC = json.loads(CANONICAL_JSON)


def file_identity(path):
    import hashlib
    digest, size = hashlib.sha256(), 0
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(4 << 20), b''):
            digest.update(block)
            size += len(block)
    return {'sha256': digest.hexdigest(), 'nbytes': size}


def is_v3_spec(spec):
    return bool(spec and (spec.get('sha256') == CANONICAL_SPEC['sha256']
                         or 'new_img' in spec.get('input_shapes', {})))


def validate_spec(spec):
    if spec != CANONICAL_SPEC:
        raise ValueError('V3 identity/semantic spec differs from the pinned model')


def physical_contract(spec):
    return {kind: {n: (tuple(s), DTYPE_TRANSFORMS.get(n, spec[kind[:-1]+'_dtypes'][n]))
                   for n, s in spec[kind[:-1]+'_shapes'].items()}
            for kind in ('inputs', 'outputs')}


def validate_source(path, spec):
    validate_spec(spec)
    identity = file_identity(path)
    if identity != {k: CANONICAL_SPEC[k] for k in ('sha256', 'nbytes')}:
        raise ValueError('V3 source hash/size mismatch')
    validate_graph_file(path, spec, patched=False)
    return identity


def validate_graph_file(path, spec, patched):
    import onnx
    import numpy as np
    model = onnx.load(str(path), load_external_data=False)
    contract = physical_contract(spec) if patched else {
        kind: {n: (tuple(s), spec[kind[:-1]+'_dtypes'][n]) for n, s in spec[kind[:-1]+'_shapes'].items()}
        for kind in ('inputs', 'outputs')}
    for kind, values in (('inputs', model.graph.input), ('outputs', model.graph.output)):
        actual = {v.name: (tuple(d.dim_value for d in v.type.tensor_type.shape.dim),
                          str(np.dtype(onnx.helper.tensor_dtype_to_np_dtype(v.type.tensor_type.elem_type))))
                  for v in values}
        if len(actual) != len(values) or actual != contract[kind]:
            raise ValueError(f'V3 {kind} graph contract mismatch')
    props = {p.key: p.value for p in model.metadata_props}
    if decode_output_slices(props['output_slices']) != spec['output_slices']:
        raise ValueError('V3 output slices mismatch')
    if props.get('model_checkpoint') != spec['checkpoint']:
        raise ValueError('V3 checkpoint mismatch')


def build_record(source, patched, engine, spec):
    validate_graph_file(patched, spec, patched=True)
    return {'source': source, 'patched': file_identity(patched),
            'engine': file_identity(engine), 'patch_id': PATCH_ID,
            'semantic_spec': spec, 'dtype_transforms': DTYPE_TRANSFORMS.copy()}


def validate_record(record, engine, spec):
    validate_spec(spec)
    if set(record) != {'source', 'patched', 'engine', 'patch_id', 'semantic_spec', 'dtype_transforms'}:
        raise ValueError('invalid V3 build record fields')
    if (record['source'] != {k: CANONICAL_SPEC[k] for k in ('sha256', 'nbytes')}
        or record['semantic_spec'] != spec or record['patch_id'] != PATCH_ID
        or record['dtype_transforms'] != DTYPE_TRANSFORMS):
        raise ValueError('V3 build record identity/contract mismatch')
    for name in ('patched', 'engine'):
        value = record[name]
        if (set(value) != {'sha256', 'nbytes'} or type(value['nbytes']) is not int or value['nbytes'] <= 0
            or not isinstance(value['sha256'], str) or len(value['sha256']) != 64
            or any(c not in '0123456789abcdef' for c in value['sha256'])):
            raise ValueError(f'invalid V3 {name} identity')
    if record['engine'] != file_identity(engine):
        raise ValueError('V3 record belongs to a different engine')
    return DTYPE_TRANSFORMS.copy()

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



def record_digest(record):
    """Detect sidecar corruption; this is not a cryptographic signature."""
    import hashlib
    return hashlib.sha256(json.dumps(record, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
