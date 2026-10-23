"""Pure M17 provenance checks; no device access, preprocessing or model adoption."""
from __future__ import annotations

import json
import math
from pathlib import Path
import re

INPUT_PROOFS = (
    'paired_recorded_pixels', 'frame_timestamp_alignment', 'calibration_transform_history',
    'traffic_convention_history', 'exact_desire_pulse_history', 'exact_action_t_history',
    'pinned_warp_preprocessing', 'zero_initial_state_and_continuous_recurrence',
)


def require_offroad(flags: dict[str, str]) -> None:
    if flags != {'IsOffroad': '1', 'IsOnroad': '0'}:
        raise ValueError('exact offroad=1/onroad=0 required before read-only access')


def camera_availability(names: list[str]) -> dict[str, bool]:
    names = set(names)
    return {'full_road': 'fcamera.hevc' in names, 'full_wide': 'ecamera.hevc' in names,
            'qcamera': bool(names & {'qcamera.ts', 'qcamera.mp4'}), 'driver_camera': 'dcamera.hevc' in names}


def reconstruction_gate(proofs: dict[str, bool]) -> dict:
    missing = [name for name in INPUT_PROOFS if proofs.get(name) is not True]
    return {'status': 'BLOCKED_RECORDED_INPUT_RECONSTRUCTION' if missing else 'READY_FOR_DATASET_VALIDATION',
            'missing': missing, 'reconstructed_frames': 0, 'numerical_decision': 'PARITY_UNDETERMINED'}


class MotionObservations:
    """Count logged standstill→positive motion, allowing a zero-speed release gap."""

    def __init__(self):
        self.pending_standstill = False
        self.standstill_samples = 0
        self.stop_to_motion = 0

    def update(self, speed: float, standstill: bool) -> None:
        if not math.isfinite(speed) or type(standstill) is not bool:
            raise ValueError('finite speed and explicit standstill boolean required')
        if standstill:
            self.pending_standstill = True
            self.standstill_samples += 1
        elif self.pending_standstill and speed > 0:
            self.stop_to_motion += 1
            self.pending_standstill = False


def public_candidate(record: dict) -> dict:
    """Narrow public file identity; never accept raw route/time/location fields."""
    required = {'label', 'filename', 'bytes', 'sha256', 'camera_metadata_frames'}
    if set(record) != required or re.fullmatch(r'REC_CANDIDATE_\d{2}', str(record.get('label'))) is None:
        raise ValueError('only anonymous candidate identity fields permitted')
    if record['filename'] not in ('rlog.zst', 'rlog.bz2', 'rlog', 'qlog.zst', 'qlog.bz2', 'qlog'):
        raise ValueError('unexpected recording filename')
    if re.fullmatch('[0-9a-f]{64}', str(record['sha256'])) is None:
        raise ValueError('full SHA256 required')
    if any(type(record[n]) is not int or record[n] < 0 for n in ('bytes', 'camera_metadata_frames')) or record['bytes'] == 0:
        raise ValueError('invalid byte/frame count')
    return dict(record)


def write_exclusive(path: Path, value: dict) -> None:
    content = json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n'
    with path.open('x', encoding='utf-8') as stream:
        stream.write(content)
