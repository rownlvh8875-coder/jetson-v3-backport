"""Exact Cinque V3 protocol2 compatibility, not authentication or GPU validation."""
import hashlib
import json
import re

CAPABILITY = 'cinque_v3_stateful_v2'
CANONICAL_SPEC = json.loads(r'''{
  "sha256": "404a18cfd86d29637d20c697dfde245bb47c666ae016730ab674c65f4d1e1aa4",
  "nbytes": 766354845,
  "frame_skip": 4,
  "checkpoint": "b9facbcc-4d47-410e-b3ce-dfcbad12ba92/56320/f78ed37d-afad-4dbc-8050-40ea885eedde/12864",
  "input_shapes": {
    "new_img": [
      2,
      6,
      128,
      256
    ],
    "desire": [
      8
    ],
    "traffic_convention": [
      1,
      2
    ],
    "action_t": [
      1,
      2
    ],
    "state_img_q": [
      2,
      5,
      6,
      128,
      256
    ],
    "state_desire_q": [
      132,
      1,
      8
    ],
    "state_feat_q": [
      128,
      1,
      16384
    ]
  },
  "output_shapes": {
    "outputs": [
      1,
      18452
    ],
    "next_state_img_q": [
      2,
      5,
      6,
      128,
      256
    ],
    "next_state_desire_q": [
      132,
      1,
      8
    ],
    "next_state_feat_q": [
      128,
      1,
      16384
    ]
  },
  "output_slices": {
    "lane_lines": [
      0,
      528
    ],
    "lane_lines_prob": [
      528,
      536
    ],
    "road_edges": [
      536,
      800
    ],
    "meta": [
      800,
      855
    ],
    "desire_pred": [
      855,
      887
    ],
    "pose": [
      887,
      899
    ],
    "wide_from_device_euler": [
      899,
      905
    ],
    "road_transform": [
      905,
      917
    ],
    "plan": [
      917,
      1907
    ],
    "lead": [
      1907,
      2051
    ],
    "lead_prob": [
      2051,
      2054
    ],
    "desire_state": [
      2054,
      2062
    ],
    "action": [
      2062,
      2066
    ],
    "hidden_state": [
      2066,
      18450
    ],
    "pad": [
      18450,
      18452
    ]
  },
  "input_dtypes": {
    "new_img": "uint8",
    "desire": "float32",
    "traffic_convention": "float32",
    "action_t": "float32",
    "state_img_q": "uint8",
    "state_desire_q": "float32",
    "state_feat_q": "float32"
  },
  "output_dtypes": {
    "outputs": "float32",
    "next_state_img_q": "uint8",
    "next_state_desire_q": "float32",
    "next_state_feat_q": "float32"
  }
}''')

def _json(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)

def validate_spec(value):
    if _json(value) != _json(CANONICAL_SPEC):
        raise ValueError('V3 identity/semantic spec differs from pinned model')

def capability():
    return {'version': 1, 'sha256': CANONICAL_SPEC['sha256'], 'nbytes': CANONICAL_SPEC['nbytes'],
            'spec_sha256': hashlib.sha256(_json(CANONICAL_SPEC).encode()).hexdigest()}

def validate_capability(value):
    if _json(value) != _json(capability()):
        raise ValueError('unsupported or missing V3 capability')

def valid_token(value):
    return isinstance(value, str) and re.fullmatch('[0-9a-f]{32}', value) is not None
