"""Design-only policy helpers for a protocol-3 Carrot Jetson model peer.

This module is intentionally independent from openpilot so its trust boundary
can be reviewed before touching carrot-wip. It does not open USB, select a real
model, write Params, or change the Jetson.

The eventual carrot-wip integration should preserve these properties:
- only the explicit USB/TRT/Jetson capability opts into host model selection;
- legacy Jetsons without the capability keep the fixed V2 behavior;
- a loaded model identity is either None or an exact lowercase SHA256;
- this HELLO metadata is descriptive, not authentication; the full ModelSpec
  still needs the existing offroad approval and validation gates.
"""
from __future__ import annotations

import re
from typing import Any


CAPABILITY = "carrot_model_selection_v1"
CAPABILITY_VERSION = 1
_SHA256 = re.compile(r"[0-9a-f]{64}")


class PeerPolicyError(ValueError):
    pass


def _capability(peer: dict[str, Any]) -> dict[str, Any] | None:
    value = peer.get(CAPABILITY)
    if not isinstance(value, dict):
        return None
    if type(value.get("version")) is not int or value["version"] != CAPABILITY_VERSION:
        return None
    # Fail closed on unknown capability semantics. A later version can define
    # new fields rather than letting an old comma silently reinterpret them.
    if set(value) != {"version", "selection"} or value.get("selection") != "host":
        return None
    return value


def is_managed_jetson_peer(peer: Any, mode: str = "usb") -> bool:
    """Return True only for the explicit protocol-3 Jetson selector contract."""
    return (
        mode == "usb"
        and isinstance(peer, dict)
        and type(peer.get("protocol")) is int
        and peer["protocol"] == 3
        and peer.get("carrot_host") == "jetson"
        and peer.get("backend") == "trt"
        and isinstance(peer.get("device"), str)
        and bool(peer["device"])
        and _capability(peer) is not None
    )


def loaded_sha(peer: Any, mode: str = "usb") -> str | None:
    """Return the host-selected SHA, or None while no model is selected.

    Invalid identity on an otherwise managed Jetson is an error instead of a
    fallback to another big model. The caller may then use the internal model.
    """
    if not is_managed_jetson_peer(peer, mode):
        raise PeerPolicyError("peer is not an approved managed Jetson contract")
    value = peer.get("loaded")
    if value is None:
        return None
    if not isinstance(value, str) or _SHA256.fullmatch(value) is None:
        raise PeerPolicyError("invalid Jetson loaded model SHA256")
    return value


def selection_kind(peer: Any, mode: str = "usb") -> str:
    """Classify only the distinction needed by the future carrot-wip patch."""
    if is_managed_jetson_peer(peer, mode):
        return "managed-jetson"
    if isinstance(peer, dict) and peer.get("carrot_host") == "jetson":
        return "legacy-jetson"
    return "other"
