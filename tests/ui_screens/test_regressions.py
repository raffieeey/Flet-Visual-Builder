import flet as ft

from flet_visual_builder.ui.canvas import Canvas
from flet_visual_builder.ui.inspector import Inspector
from flet_visual_builder.ui.preview import Preview
from flet_visual_builder.ui.screens import ScreenStrip
from tests.ui_screens.test_screen_ui import event, walk, workspace


def test_only_active_subtree_reaches_renderer():
    ws = workspace()
    ws.select_screen("settings")
    plans = []
    original = ws.renderer.render_plan
    ws.renderer.render_plan = lambda plan: (plans.append(plan), original(plan))[1]
    Canvas(ws)
    Preview(ws)
    assert all(set(plan.nodes) == {"settings", "settings_text"} for plan in plans)


def test_screen_switch_refreshes_registered_canvas_and_inspector():
    ws = workspace()
    canvas = ws.add_panel(Canvas(ws))
    inspector = ws.add_panel(Inspector(ws))
    tab = next(
        c for c in walk(canvas.control) if c.data == ("screen", "settings", False)
    )
    tab.on_click(event(tab))
    assert set(canvas.frames) == {"settings", "settings_text"}
    assert inspector._node_id == "settings"


def test_validation_and_delete_confirmation():
    ws = workspace()
    strip = ScreenStrip(ws)
    menu = next(c for c in walk(strip.control) if isinstance(c, ft.PopupMenuButton))
    menu.items[0].on_click(None)
    dialog = ws.page.dialog
    fields = [c for c in walk(dialog) if isinstance(c, ft.TextField)]
    fields[1].value = "/screen-2"
    dialog.actions[1].on_click(None)
    assert ws.page.dialog is dialog
    assert any(
        isinstance(c, ft.Text) and c.visible and "already" in (c.value or "")
        for c in walk(dialog)
    )
    fields[1].value = "no-slash"
    dialog.actions[1].on_click(None)
    assert ws.page.dialog is dialog
    dialog.actions[0].on_click(None)
    menu.items[2].on_click(None)
    dialog = ws.page.dialog
    assert "Home" in dialog.title.value
    assert "contents" in dialog.content.value
    dialog.actions[1].on_click(None)
    assert ws.project.root_ids == ("settings",)


def test_navigation_to_handler_and_back_preserves_focus():
    ws = workspace()
    ws.select("home_text")
    ws.set_action("home_text", "on_click", "/screen-2")
    inspector = ws.add_panel(Inspector(ws))
    switch = next(c for c in walk(inspector.control) if c.data == ("event", "on_click"))
    assert not switch.value
    switch.value = True
    switch.on_change(event(switch))
    assert "on_click" not in ws.node("home_text").actions
    assert "on_click" in ws.node("home_text").events
    dropdown = next(
        c for c in walk(inspector.control) if c.data == ("navigation", "on_click")
    )
    dropdown.value = "/"
    dropdown.on_select(event(dropdown))
    assert not switch.value
    assert "on_click" not in ws.node("home_text").events
    dropdown.value = ""
    dropdown.on_select(event(dropdown))
    assert not ws.node("home_text").actions
