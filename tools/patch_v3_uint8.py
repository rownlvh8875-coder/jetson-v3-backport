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
    import onnx
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
    onnx.save(model, str(dst))
    if retypes_out is not None:
        Path(retypes_out).write_text(json.dumps(retypes, indent=2))
    return retypes


def main() -> None:
    if len(sys.argv) < 3:
        print(f"usage: {sys.argv[0]} in.onnx out.onnx [retypes.json]",
              file=sys.stderr)
        raise SystemExit(2)
    retypes = patch_file_v3(sys.argv[1], sys.argv[2],
                            sys.argv[3] if len(sys.argv) > 3 else None)
    print("patched; retypes:", retypes)


if __name__ == '__main__':
    main()
