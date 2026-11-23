from types import SimpleNamespace
from unittest.mock import patch

import flet as ft
import pytest

from flet_visual_builder.app_context import Refresh, Workspace
from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import (
    Node,
    Project,
    SetEvent,
    SetProperty,
    UnsetProperty,
)
from flet_visual_builder.ui.inspector import Inspector
from tests.support.fake_page import FakePage


def workspace(kind="Text"):
    spec = catalogue.widgets[kind]
    node = Node(
        id="item",
        type_id=kind,
        props=catalogue.new_props(kind),
        slots={s: () for s in spec.slots},
        events={},
    )
    ws = Workspace(
        FakePage(),
        Project(
            name="Test",
            page=catalogue.new_page(),
            root_ids=(node.id,),
            nodes={node.id: node},
            assets={},
        ),
    )
    return ws


def walk(control):
    yield control
    for attr in ("content", "controls"):
        child = getattr(control, attr, None)
        if isinstance(child, ft.Control):
            yield from walk(child)
        elif isinstance(child, list):
            for c in child:
                if isinstance(c, ft.Control):
                    yield from walk(c)


def tagged(panel, tag):
    return next(c for c in walk(panel.control) if c.data == tag)


def event(control, handler, value=None):
    if value is not None:
        control.value = value
    getattr(control, handler)(SimpleNamespace(control=control))


def test_text_and_container_properties_and_page_mode():
    for kind in ("Text", "Container"):
        ws = workspace(kind)
        panel = Inspector(ws)
        rows = {
            c.data[1]
            for c in walk(panel.control)
            if isinstance(c.data, tuple) and c.data[0] == "property"
        }
        assert rows == set(catalogue.widgets[kind].properties)
    ws = workspace()
    ws.select(None)
    panel = Inspector(ws)
    assert any(
        isinstance(c, ft.Text) and c.value == "Page" for c in walk(panel.control)
    )
    assert {
        c.data[1]
        for c in walk(panel.control)
        if isinstance(c.data, tuple) and c.data[0] == "property"
    } == set(catalogue.page_properties)


def test_edits_and_reset_dispatch_commands():
    ws = workspace()
    panel = Inspector(ws)
    with patch.object(ws, "dispatch", wraps=ws.dispatch) as dispatch:
        event(tagged(panel, ("editor", "value")), "on_change", "Hello")
        cmd = dispatch.call_args.args[0]
        assert isinstance(cmd, SetProperty) and cmd.value == "Hello"
        event(tagged(panel, ("editor", "size")), "on_change", "12.5")
        cmd = dispatch.call_args.args[0]
        assert (
            isinstance(cmd, SetProperty)
            and cmd.value == 12.5
            and isinstance(cmd.value, float)
        )
        dropdown = tagged(panel, ("editor", "weight"))
        assert isinstance(dropdown, ft.Dropdown) and dropdown.on_select
        event(dropdown, "on_select", "BOLD")
        assert dispatch.call_args.args[0].value == "BOLD"
        event(tagged(panel, ("reset", "size")), "on_click")
        assert isinstance(dispatch.call_args.args[0], UnsetProperty)


def test_event_binding_and_focus_refresh():
    ws = workspace("TextField")
    panel = Inspector(ws)
    with patch.object(ws, "dispatch", wraps=ws.dispatch) as dispatch:
        event(tagged(panel, ("event", "on_change")), "on_change", True)
        cmd = dispatch.call_args.args[0]
        assert isinstance(cmd, SetEvent) and cmd.symbol.name == "handle_item_change"
    with patch.object(panel, "build", wraps=panel.build) as build:
        panel.refresh(Refresh.DOCUMENT)
        build.assert_not_called()
        panel.refresh(Refresh.SELECTION)
        build.assert_called_once()


def test_invalid_numeric_is_inline_and_never_dispatched():
    ws = workspace()
    panel = Inspector(ws)
    field = tagged(panel, ("editor", "size"))
    with patch.object(ws, "dispatch", wraps=ws.dispatch) as dispatch:
        event(field, "on_change", "-1")
        dispatch.assert_not_called()
        assert field.error
