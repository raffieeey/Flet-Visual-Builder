from dataclasses import replace
from time import perf_counter
from types import SimpleNamespace as Event
from unittest.mock import patch

import flet as ft

from flet_visual_builder.app_context import Refresh, Workspace
from flet_visual_builder.contracts import Size
from flet_visual_builder.engine.runtime import iter_controls
from flet_visual_builder.interaction import encode_create, encode_move
from flet_visual_builder.services.starter import empty_project, starter_project
from flet_visual_builder.ui.canvas import Canvas
from flet_visual_builder.ui.theme import T
from tests.support.fake_page import FakePage


def make_canvas(project=None):
    ws = Workspace(FakePage(), project or starter_project())
    canvas = Canvas(ws)
    ws.add_panel(canvas)
    return ws, canvas


def event(payload, y):
    # The real Flet DragTargetEvent.src carries the Draggable's data.
    return Event(src=Event(data=payload), data=None, local_position=Event(x=10, y=y))


def test_complete_framed_tree_and_selection_in_place():
    ws, canvas = make_canvas()
    controls = iter_controls(canvas.control)
    assert set(canvas.frames) == set(ws.project.nodes)
    assert all(frame.target in controls for frame in canvas.frames.values())
    assert all(frame.target.group == "fvb-widgets" for frame in canvas.frames.values())
    old = canvas.frames["root"]
    selected = canvas.frames["header_title"]
    assert old.box.border.top.color == T.selection
    selected.box.on_click(None)
    assert canvas.frames["root"] is old and canvas.frames["header_title"] is selected
    assert old.box.border.top.color != T.selection
    assert selected.box.border.top.color == T.selection
    selected.box.on_hover(Event(data="true"))
    assert ws.editor.hover == "header_title"
    selected.box.on_hover(Event(data="false"))
    assert ws.editor.hover is None


def test_create_move_indicators_and_leave():
    ws, canvas = make_canvas()
    frame = canvas.frames["body"]
    frame.box.on_size_change(Event(width=100, height=100))
    create = event(encode_create("Text"), 90)
    frame.target.on_move(create)
    assert frame.indicator.visible and frame.indicator.bottom == 0
    with patch.object(ws, "insert", wraps=ws.insert) as insert:
        frame.target.on_accept(create)
        insert.assert_called_once_with("Text", "root", "controls", 2)
    frame = canvas.frames["body"]
    frame.size = Size(100, 100)
    move = event(encode_move("header"), 90)
    with patch.object(ws, "move", wraps=ws.move) as moving:
        frame.target.on_accept(move)
        moving.assert_called_once_with("header", "root", "controls", 2)
    assert ws.project.nodes["root"].slots["controls"][:2] == ("body", "header")
    frame = canvas.frames["header_col"]
    frame.size = Size(100, 100)
    frame.target.on_move(event(encode_create("Text"), 50))
    assert frame.indicator.visible and frame.indicator.bgcolor == T.drop_soft
    frame.target.on_leave(Event())
    assert not frame.indicator.visible


def test_descendant_rejected_and_empty_root_accepts():
    ws, canvas = make_canvas()
    frame = canvas.frames["header_col"]
    frame.size = Size(100, 100)
    before = ws.snapshot
    with patch.object(ws, "move", wraps=ws.move) as moving:
        frame.target.on_move(event(encode_move("header"), 50))
        assert not frame.indicator.visible
        frame.target.on_accept(event(encode_move("header"), 50))
        moving.assert_not_called()
    assert ws.snapshot == before
    ws, canvas = make_canvas(empty_project())
    frame = canvas.frames["root"]
    frame.size = Size(200, 120)
    with patch.object(ws, "insert", wraps=ws.insert) as insert:
        frame.target.on_accept(event(encode_create("Text"), 50))
        insert.assert_called_once_with("Text", "root", "controls", 0)
    assert len(ws.project.nodes) == 2


def test_rebuild_60_nodes_and_selection_no_render():
    base = empty_project()
    root = base.nodes["root"]
    nodes = {
        "root": replace(root, slots={"controls": tuple(f"text_{i}" for i in range(59))})
    }
    from flet_visual_builder.contracts import Node

    nodes.update(
        {
            f"text_{i}": Node(f"text_{i}", "Text", {"value": str(i)}, {}, {})
            for i in range(59)
        }
    )
    ws, canvas = make_canvas(replace(base, nodes=nodes))
    start = perf_counter()
    canvas.refresh(Refresh.DOCUMENT)
    elapsed = perf_counter() - start
    assert len(canvas.frames) == 60
    assert elapsed < 0.2, f"rebuild took {elapsed:.3f}s"
    with patch.object(
        ws.renderer, "render_plan", wraps=ws.renderer.render_plan
    ) as render:
        ws.select("text_0")
        render.assert_not_called()
