from __future__ import annotations

from dataclasses import dataclass


@dataclass
class HitBox:
    node_id: str
    slot: str | None
    x: float
    y: float
    w: float
    h: float


class HitTestEngine:
    def __init__(self) -> None:
        self._boxes: list[HitBox] = []

    def clear(self) -> None:
        self._boxes.clear()

    def register(self, box: HitBox) -> None:
        self._boxes.append(box)

    def hit(self, x: float, y: float) -> HitBox | None:
        for box in reversed(self._boxes):
            if box.x <= x <= box.x + box.w and box.y <= y <= box.y + box.h:
                return box
        return None
