"""All sixteen catalogue widgets lower and construct as real Flet controls."""
from __future__ import annotations

import flet as ft
import pytest

from flet_visual_builder.catalogue.widgets import WIDGET_ORDER
from flet_visual_builder.contracts import RenderMode, Severity
from flet_visual_builder.engine.runtime import iter_controls

from tests.contracts.rendering.helpers import (
    RENDERER,
    lower_ok,
    widget_snapshot,
)


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_each_catalogue_widget_constructs(type_id: str) -> None:
    snapshot = widget_snapshot(type_id)
    plan = lower_ok(snapshot)
    assert plan.nodes["root"].type_id == type_id
    assert plan.nodes["root"].constructor.path == (type_id,)
    result = RENDERER.render_plan(plan)
    errors = [d for d in result.diagnostics if d.severity is Severity.ERROR]
    assert not errors, errors
    assert result.root is not None
    assert result.mode is RenderMode.PREVIEW
    assert result.revision == snapshot.revision
    control = result.by_node["root"]
    expected = getattr(ft, type_id)
    assert isinstance(control, expected)
    assert isinstance(result.root, ft.Pagelet)


def test_sixteen_entries_are_complete() -> None:
    assert len(WIDGET_ORDER) == 16
