"""Leaf samples, fresh instances, and absence of design chrome."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.contracts import RenderMode, Severity
from flet_visual_builder.engine.runtime import CODE_OCCUPIED_SLOT, iter_controls

from tests.contracts.rendering.helpers import (
    RENDERER,
    lower_ok,
    make_snapshot,
    widget_node,
    widget_snapshot,
)


def test_leaf_sample_rejects_occupied_child_slot() -> None:
    child = widget_node("Text", node_id="inner", props={"value": "x"})
    box = widget_node("Container", slots={"content": ("inner",)})
    plan = lower_ok(make_snapshot(box, child))
    result = RENDERER.render_leaf_sample(plan, "root")
    assert result.root is None
    assert result.by_node == {}
    assert result.mode is RenderMode.DESIGN_SAMPLE
    errors = [d for d in result.diagnostics if d.severity is Severity.ERROR]
    assert errors
    assert any(d.code == CODE_OCCUPIED_SLOT for d in errors)
    assert "occupied child slots" in errors[0].message


def test_leaf_sample_rejects_occupied_controls_slot() -> None:
    child = widget_node("Text", node_id="t0", props={"value": "0"})
    column = widget_node("Column", slots={"controls": ("t0",)})
    plan = lower_ok(make_snapshot(column, child))
    result = RENDERER.render_leaf_sample(plan, "root")
    assert result.root is None
    assert any(d.code == CODE_OCCUPIED_SLOT for d in result.diagnostics)


def test_leaf_sample_of_empty_layout_constructs() -> None:
    plan = lower_ok(widget_snapshot("Column"))
    result = RENDERER.render_leaf_sample(plan, "root")
    assert result.root is not None
    assert isinstance(result.root, ft.Column)
    assert result.mode is RenderMode.DESIGN_SAMPLE
    assert result.by_node["root"] is result.root


def test_leaf_samples_are_fresh_instances() -> None:
    plan = lower_ok(widget_snapshot("Button"))
    first = RENDERER.render_leaf_sample(plan, "root")
    second = RENDERER.render_leaf_sample(plan, "root")
    assert first.root is not None and second.root is not None
    assert first.root is not second.root
    assert id(first.root) != id(second.root)


def test_render_plan_fresh_instances() -> None:
    plan = lower_ok(widget_snapshot("Text", props={"value": "hi"}))
    first = RENDERER.render_plan(plan)
    second = RENDERER.render_plan(plan)
    assert first.root is not None and second.root is not None
    assert first.root is not second.root
    assert first.by_node["root"] is not second.by_node["root"]
    assert id(first.by_node["root"]) != id(second.by_node["root"])


def test_clean_preview_has_no_drag_targets_or_handles() -> None:
    child = widget_node("Text", node_id="inner", props={"value": "x"})
    box = widget_node("Container", slots={"content": ("inner",)})
    result = RENDERER.render_plan(lower_ok(make_snapshot(box, child)))
    assert result.root is not None
    tree = iter_controls(result.root)
    assert tree
    assert not any(isinstance(control, ft.DragTarget) for control in tree)
    assert not any(isinstance(control, ft.Draggable) for control in tree)
    assert not any(
        type(control).__name__ in {"DragTarget", "Draggable"} for control in tree
    )
    # PageSpec adapter only: Pagelet + themed Container, no per-node frames.
    pagelets = [c for c in tree if isinstance(c, ft.Pagelet)]
    assert len(pagelets) == 1
    assert result.by_node["root"] in tree
    assert result.by_node["inner"] in tree
