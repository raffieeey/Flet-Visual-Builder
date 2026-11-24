from types import SimpleNamespace
from unittest.mock import patch

import flet as ft

from flet_visual_builder.app_context import Workspace
from flet_visual_builder.contracts import Navigate, Node, Project, SetAction
from flet_visual_builder.ui.canvas import Canvas
from flet_visual_builder.ui.inspector import Inspector
from flet_visual_builder.ui.preview import Preview


def workspace():
    def node(id, type_id, slots=None):
        return Node(
            id=id,
            type_id=type_id,
            props={"content": "Open"} if type_id == "TextButton" else {},
            slots=slots or {},
            events={},
        )

    project = Project(
        name="App",
        page={},
        root_ids=("home", "settings"),
        nodes={
            "home": node("home", "Column", {"controls": ("home_text",)}),
            "home_text": node("home_text", "TextButton"),
            "settings": node("settings", "Column", {"controls": ("settings_text",)}),
            "settings_text": node("settings_text", "Text"),
        },
        assets={},
    )

    class Page:
        def update(self):
            pass

        def show_dialog(self, dialog):
            self.dialog = dialog

        def pop_dialog(self):
            self.dialog = None

    return Workspace(Page(), project)


def walk(control):
    yield control
    for name in ("content", "controls", "items", "actions"):
        value = getattr(control, name, None)
        if isinstance(value, ft.Control):
            yield from walk(value)
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, ft.Control):
                    yield from walk(child)


def event(control):
    return SimpleNamespace(control=control)


def test_canvas_and_preview_show_active_screen_only():
    ws = workspace()
    ws.select_screen("settings")
    canvas = Canvas(ws)
    assert set(canvas.frames) == {"settings", "settings_text"}
    preview = Preview(ws)
    values = [x.value for x in walk(preview.control) if isinstance(x, ft.Text)]
    assert "Screen 2" in values and "/screen-2" in values
    # Observe the actual plan sent to the renderer, not just header labels.
    plans = []
    original = ws.renderer.render_plan

    def record(plan):
        plans.append(plan)
        return original(plan)

    ws.renderer.render_plan = record
    Preview(ws)
    assert plans[-1].root_ids == ("settings",)


def test_inspector_navigation_dispatches_and_displaces_handler():
    ws = workspace()
    ws.select("home_text")
    ws.set_event("home_text", "on_click", True)
    inspector = Inspector(ws)
    dropdowns = [
        c
        for c in walk(inspector.control)
        if isinstance(c, ft.Dropdown) and c.label == "Navigation"
    ]
    assert len(dropdowns) == len(ws.spec("TextButton").events)
    dropdown = next(c for c in dropdowns if c.data == ("navigation", "on_click"))
    assert {o.key for o in dropdown.options} == {"", "/", "/screen-2"}
    dropdown.value = "/screen-2"
    with patch.object(ws, "dispatch", wraps=ws.dispatch) as dispatch:
        dropdown.on_select(event(dropdown))
    commands = [call.args[0] for call in dispatch.call_args_list]
    assert any(
        isinstance(command, SetAction) and command.action == Navigate("/screen-2")
        for command in commands
    )
    assert ws.node("home_text").actions["on_click"] == Navigate("/screen-2")
    assert "on_click" not in ws.node("home_text").events
    assert any(
        isinstance(c, ft.Text) and "/screen-2" in (c.value or "")
        for c in walk(inspector.control)
    )


def test_screen_strip_and_dialogs():
    from flet_visual_builder.ui.screens import ScreenStrip

    ws = workspace()
    strip = ScreenStrip(ws)
    tabs = [
        c
        for c in walk(strip.control)
        if isinstance(c, ft.Container)
        and isinstance(c.data, tuple)
        and c.data[0] == "screen"
    ]
    assert [c.data for c in tabs] == [
        ("screen", "home", True),
        ("screen", "settings", False),
    ]
    tabs[1].on_click(event(tabs[1]))
    assert ws.active_screen() == "settings"
    strip.refresh()
    menus = [c for c in walk(strip.control) if isinstance(c, ft.PopupMenuButton)]
    assert [item.content for item in menus[0].items] == [
        "Rename",
        "Set as initial",
        "Delete",
    ]
    menus[1].items[0].on_click(event(menus[1].items[0]))
    dialog = ws.page.dialog
    fields = [c for c in walk(dialog) if isinstance(c, ft.TextField)]
    fields[0].value, fields[1].value = "Preferences", "/prefs"
    next(c for c in dialog.actions if c.content == "Save").on_click(None)
    assert ws.screen_meta("settings").title == "Preferences"
    assert ws.screen_meta("settings").route == "/prefs"
    add = next(
        c
        for c in walk(strip.control)
        if isinstance(c, ft.IconButton) and c.tooltip == "Add screen"
    )
    add.on_click(event(add))
    next(c for c in ws.page.dialog.actions if c.content == "Save").on_click(None)
    assert len(ws.project.root_ids) == 3
    ws.delete_screen("settings")
    ws.delete_screen(ws.project.root_ids[-1])
    strip.refresh()
    menu = next(c for c in walk(strip.control) if isinstance(c, ft.PopupMenuButton))
    assert menu.items[-1].disabled
