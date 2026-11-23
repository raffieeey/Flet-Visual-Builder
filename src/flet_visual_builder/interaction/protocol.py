"""Drag payload protocol shared by the palette and the design canvas.

Flet transports a single string through ``Draggable.data``. Both sides of a drag
must agree on that string, so the encoding lives here rather than in either panel.
"""

from __future__ import annotations

from typing import Literal

DRAG_GROUP = "fvb-widgets"

DragKind = Literal["create", "move"]


def encode_create(type_id: str) -> str:
    """Palette drag payload for a new widget of ``type_id``."""
    return f"create:{type_id}"


def encode_move(node_id: str) -> str:
    """Canvas drag payload for an existing node."""
    return f"move:{node_id}"


def decode_drag(payload: object) -> tuple[DragKind, str] | None:
    """Parse a payload produced by :func:`encode_create` or :func:`encode_move`."""
    if not isinstance(payload, str):
        return None
    kind, _, value = payload.partition(":")
    if not value:
        return None
    if kind == "create":
        return "create", value
    if kind == "move":
        return "move", value
    return None
