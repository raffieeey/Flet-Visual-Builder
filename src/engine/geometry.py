from __future__ import annotations

from dataclasses import dataclass

from src.engine.hit_test import DropZone


@dataclass(frozen=True)
class Rect:
    """Axis-aligned rectangle in canvas coordinates."""

    x: float
    y: float
    w: float
    h: float

    @property
    def right(self) -> float:
        return self.x + self.w

    @property
    def bottom(self) -> float:
        return self.y + self.h

    @property
    def center_x(self) -> float:
        return self.x + self.w / 2.0

    @property
    def center_y(self) -> float:
        return self.y + self.h / 2.0


def rect_contains(rect: Rect, x: float, y: float) -> bool:
    """Return True if (x, y) lies inside *rect*, inclusive on all four edges."""
    return rect.x <= x <= rect.right and rect.y <= y <= rect.bottom


def rect_overlap(a: Rect, b: Rect) -> float:
    """Area of intersection of *a* and *b*, or 0.0 if they do not overlap."""
    dx = min(a.right, b.right) - max(a.x, b.x)
    dy = min(a.bottom, b.bottom) - max(a.y, b.y)
    if dx <= 0.0 or dy <= 0.0:
        return 0.0
    return dx * dy


def rect_intersects(a: Rect, b: Rect) -> bool:
    """Return True if *a* and *b* share any point (edges inclusive)."""
    return a.x <= b.right and b.x <= a.right and a.y <= b.bottom and b.y <= a.bottom


def classify_zone(
    rect: Rect,
    y: float,
    *,
    accepts_children: bool,
    before_ratio: float = 0.25,
    after_ratio: float = 0.75,
) -> DropZone:
    """Determine drop intent from the vertical pointer position inside *rect*.

    Mirrors ``HitTestEngine._compute_zone`` when called with the default ratios.
    """
    relative = (y - rect.y) / rect.h if rect.h > 0 else 0.5
    if relative < before_ratio:
        return DropZone.BEFORE
    if relative > after_ratio:
        return DropZone.AFTER
    if accepts_children:
        return DropZone.INSIDE
    return DropZone.AFTER


def to_target_local(global_x: float, global_y: float, aperture: Rect) -> tuple[float, float]:
    """Translate global canvas coordinates into the aperture's local space.

    Subtracts the aperture origin only — no scaling, rounding, or other transform.
    """
    return (global_x - aperture.x, global_y - aperture.y)


def in_target_local_bounds(aperture: Rect, local_x: float, local_y: float) -> bool:
    """Return True if local coordinates lie in the aperture, edges inclusive."""
    return 0.0 <= local_x <= aperture.w and 0.0 <= local_y <= aperture.h
