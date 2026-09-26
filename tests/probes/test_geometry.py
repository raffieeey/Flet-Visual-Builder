from __future__ import annotations

import itertools

from src.engine.geometry import (
    Rect,
    classify_zone,
    in_target_local_bounds,
    rect_contains,
    rect_intersects,
    rect_overlap,
    to_target_local,
)
from src.engine.hit_test import DropZone, HitBox, HitTestEngine


def test_rect_helpers() -> None:
    rect = Rect(x=10.0, y=20.0, w=30.0, h=40.0)
    assert rect.right == 40.0
    assert rect.bottom == 60.0
    assert rect.center_x == 25.0
    assert rect.center_y == 40.0


def test_rect_contains_is_inclusive_on_all_edges() -> None:
    rect = Rect(x=10.0, y=20.0, w=30.0, h=40.0)
    assert rect_contains(rect, 10.0, 20.0)
    assert rect_contains(rect, 40.0, 20.0)
    assert rect_contains(rect, 10.0, 60.0)
    assert rect_contains(rect, 40.0, 60.0)
    assert rect_contains(rect, 25.0, 40.0)
    assert not rect_contains(rect, 9.999, 40.0)
    assert not rect_contains(rect, 40.001, 40.0)
    assert not rect_contains(rect, 25.0, 19.999)
    assert not rect_contains(rect, 25.0, 60.001)


def test_rect_overlap_area_and_none() -> None:
    a = Rect(x=0.0, y=0.0, w=10.0, h=10.0)
    b = Rect(x=5.0, y=5.0, w=10.0, h=10.0)
    assert rect_overlap(a, b) == 25.0
    disjoint = Rect(x=20.0, y=0.0, w=5.0, h=5.0)
    assert rect_overlap(a, disjoint) == 0.0
    touching = Rect(x=10.0, y=0.0, w=5.0, h=10.0)
    assert rect_overlap(a, touching) == 0.0
    inside = Rect(x=1.0, y=1.0, w=2.0, h=3.0)
    assert rect_overlap(a, inside) == 6.0


def test_rect_intersects_includes_shared_edges() -> None:
    a = Rect(x=0.0, y=0.0, w=10.0, h=10.0)
    assert rect_intersects(a, Rect(x=10.0, y=0.0, w=5.0, h=10.0))
    assert rect_intersects(a, Rect(x=5.0, y=5.0, w=1.0, h=1.0))
    assert not rect_intersects(a, Rect(x=10.001, y=0.0, w=5.0, h=10.0))
    assert not rect_intersects(a, Rect(x=0.0, y=10.001, w=10.0, h=5.0))


def test_classify_zone_matches_hit_test_engine_across_sweep() -> None:
    heights = (0.0, 0.5, 1.0, 40.0, 100.0)
    origins = (0.0, 12.5, -8.0)
    accepts_values = (True, False)
    relatives = [i / 20.0 for i in range(-2, 23)] + [0.25, 0.75, 0.249999, 0.750001]
    for h, y0, accepts in itertools.product(heights, origins, accepts_values):
        rect = Rect(x=4.0, y=y0, w=50.0, h=h)
        box = HitBox(
            node_id="n",
            slot=None,
            x=rect.x,
            y=rect.y,
            w=rect.w,
            h=rect.h,
            accepts_children=accepts,
        )
        probe_ys = [y0 + rel * h for rel in relatives] if h > 0 else [y0, y0 - 1.0, y0 + 1.0]
        for y in probe_ys:
            got = classify_zone(rect, y, accepts_children=accepts)
            expected = HitTestEngine._compute_zone(box, y)
            assert got is expected, f"h={h} y0={y0} y={y} accepts={accepts}"


def test_classify_zone_middle_without_children_is_after() -> None:
    rect = Rect(x=0.0, y=0.0, w=10.0, h=100.0)
    assert classify_zone(rect, 10.0, accepts_children=True) is DropZone.BEFORE
    assert classify_zone(rect, 50.0, accepts_children=True) is DropZone.INSIDE
    assert classify_zone(rect, 50.0, accepts_children=False) is DropZone.AFTER
    assert classify_zone(rect, 90.0, accepts_children=True) is DropZone.AFTER


def test_to_target_local_subtracts_origin_without_rounding() -> None:
    aperture = Rect(x=128.25, y=64.5, w=400.0, h=300.0)
    local = to_target_local(129.25, 65.5, aperture)
    assert local == (1.0, 1.0)
    exact = to_target_local(aperture.x, aperture.y, aperture)
    assert exact == (0.0, 0.0)


def test_in_target_local_bounds_inclusive() -> None:
    aperture = Rect(x=10.0, y=20.0, w=30.0, h=40.0)
    assert in_target_local_bounds(aperture, 0.0, 0.0)
    assert in_target_local_bounds(aperture, 30.0, 40.0)
    assert in_target_local_bounds(aperture, 15.0, 20.0)
    assert not in_target_local_bounds(aperture, -0.001, 0.0)
    assert not in_target_local_bounds(aperture, 30.001, 0.0)
    assert not in_target_local_bounds(aperture, 0.0, 40.001)
