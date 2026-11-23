"""Interaction primitives: drag protocol and drop resolution."""

from .drop import ResolvedDrop, Zone, resolve_drop
from .protocol import DRAG_GROUP, decode_drag, encode_create, encode_move

__all__ = [
    "DRAG_GROUP",
    "ResolvedDrop",
    "Zone",
    "decode_drag",
    "encode_create",
    "encode_move",
    "resolve_drop",
]
