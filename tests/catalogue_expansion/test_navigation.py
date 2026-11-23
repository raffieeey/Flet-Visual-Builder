import flet as ft

from flet_visual_builder.engine.runtime import RuntimeRenderer
from tests.contracts.rendering.helpers import lower_ok, widget_snapshot


def test_navigation_bar_starts_with_visible_destinations():
    plan = lower_ok(widget_snapshot("NavigationBar"))
    rendered = RuntimeRenderer().render_plan(plan)
    assert rendered.root is not None, rendered.diagnostics
    destinations = rendered.by_node["root"].destinations
    assert len(destinations) >= 2
    assert all(isinstance(item, ft.NavigationBarDestination) for item in destinations)
