import flet as ft

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.engine.runtime import RuntimeRenderer
from tests.contracts.rendering.helpers import lower_ok, widget_snapshot


def test_tabs_default_is_a_complete_flet_1_tabs_hierarchy():
    assert "Tabs" in catalogue.widgets
    plan = lower_ok(widget_snapshot("Tabs"))
    result = RuntimeRenderer().render_plan(plan)
    assert result.root is not None, result.diagnostics
    tabs = result.by_node["root"]
    assert isinstance(tabs, ft.Tabs)
    assert tabs.length == 1
    assert isinstance(tabs.content, ft.Column)
    bar, view = tabs.content.controls
    assert isinstance(bar, ft.TabBar) and isinstance(bar.tabs[0], ft.Tab)
    assert isinstance(view, ft.TabBarView) and len(view.controls) == 1


def test_tabbar_tab_records_are_lowered():
    plan = lower_ok(
        widget_snapshot("TabBar", props={"tabs": ({"label": "First", "icon": "HOME"},)})
    )
    result = RuntimeRenderer().render_plan(plan)
    assert result.root is not None, result.diagnostics
    assert isinstance(result.by_node["root"].tabs[0], ft.Tab)
    assert result.by_node["root"].tabs[0].label == "First"
