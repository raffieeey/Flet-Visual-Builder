from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto


class DropZone(Enum):
    """Where within a hit box the pointer landed."""
    BEFORE = auto()   # top 25% — insert before this node
    INSIDE = auto()   # middle 50% — insert as child (if target accepts children)
    AFTER = auto()    # bottom 25% — insert after this node


@dataclass
class HitBox:
    node_id: str
    slot: str | None
    x: float
    y: float
    w: float
    h: float
    accepts_children: bool = False  # does this node accept drops inside?


@dataclass
class HitResult:
    box: HitBox
    zone: DropZone


class HitTestEngine:
    """Canvas-level hit-test engine.

    Boxes are registered front-to-back (parent first, children after).
    ``hit()`` iterates in reverse so the innermost (last registered) box wins.
    """

    def __init__(self) -> None:
        self._boxes: list[HitBox] = []

    def clear(self) -> None:
        self._boxes.clear()

    def register(self, box: HitBox) -> None:
        self._boxes.append(box)

    def hit(self, x: float, y: float) -> HitResult | None:
        """Find the innermost box containing (x, y) and compute the drop zone."""
        for box in reversed(self._boxes):
            if box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h:
                zone = self._compute_zone(box, y)
                return HitResult(box=box, zone=zone)
        return None

    @staticmethod
    def _compute_zone(box: HitBox, y: float) -> DropZone:
        """Determine drop intent based on vertical pointer position."""
        relative = (y - box.y) / box.h if box.h > 0 else 0.5
        if relative < 0.25:
            return DropZone.BEFORE
        if relative > 0.75:
            return DropZone.AFTER
        if box.accepts_children:
            return DropZone.INSIDE
        # If the node doesn't accept children, treat middle as AFTER
        return DropZone.AFTER