import flet as ft

from flet_visual_builder.contracts import Node, Project
from flet_visual_builder.app_context import Workspace
from flet_visual_builder.ui.canvas import Canvas
from flet_visual_builder.ui.screens import ScreenStrip
from tests.ui_screens.test_screen_ui import walk, workspace


def test_add_screen_as_initial_and_set_initial_menu():
    ws = workspace()
    strip = ScreenStrip(ws)
    add = next(
        c
        for c in walk(strip.control)
        if isinstance(c, ft.IconButton) and c.tooltip == "Add screen"
    )
    add.on_click(None)
    dialog = ws.page.dialog
    toggle = next(c for c in walk(dialog) if isinstance(c, ft.Switch))
    toggle.value = True
    dialog.actions[1].on_click(None)
    assert ws.project.initial_route == "/screen-3"
    strip.refresh()
    menu = next(c for c in walk(strip.control) if isinstance(c, ft.PopupMenuButton))
    menu.items[1].on_click(None)
    assert ws.project.initial_route == "/"


def test_strip_remains_accessible_when_plan_invalid():
    ws = workspace()
    bad = Node(
        id="bad", type_id="Text", props={"not_a_property": "bad"}, slots={}, events={}
    )
    ws = Workspace(
        ws.page,
        Project(
            name="Broken", page={}, root_ids=("bad",), nodes={"bad": bad}, assets={}
        ),
    )
    canvas = Canvas(ws)
    assert any(
        isinstance(c, ft.IconButton) and c.tooltip == "Add screen"
        for c in walk(canvas.control)
    )
