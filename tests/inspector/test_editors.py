from types import SimpleNamespace
from unittest.mock import patch

import flet as ft
import pytest

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import Diagnostic, Severity, SetProperty
from flet_visual_builder.ui.inspector import Inspector
from tests.inspector.test_inspector import workspace, tagged, event, walk


def test_all_widget_editors_construct():
    for kind in catalogue.widgets:
        ws = workspace(kind)
        panel = Inspector(ws)
        assert {
            c.data[1]
            for c in walk(panel.control)
            if isinstance(c.data, tuple) and c.data[0] == "property"
        } == set(catalogue.widgets[kind].properties)


def test_page_edit_dispatches_page_property():
    ws = workspace()
    ws.select(None)
    panel = Inspector(ws)
    with patch.object(ws, "dispatch", wraps=ws.dispatch) as dispatch:
        event(tagged(panel, ("editor", "title")), "on_change", "My page")
        command = dispatch.call_args.args[0]
        assert (
            isinstance(command, SetProperty)
            and command.node_id is None
            and command.value == "My page"
        )


def test_real_refresh_keeps_input_identity_during_typing():
    ws = workspace()
    panel = Inspector(ws)
    ws.add_panel(panel)
    field = tagged(panel, ("editor", "value"))
    before = panel.control.content
    event(field, "on_change", "first")
    assert (
        panel.control.content is before and tagged(panel, ("editor", "value")) is field
    )
    assert ws.project.nodes["item"].props["value"] == "first"
    ws.select(None)
    assert panel.control.content is not before


@pytest.mark.parametrize("raw", ["-1", "nan", "inf", "garbage"])
def test_invalid_numbers_are_not_committed(raw):
    ws = workspace()
    panel = Inspector(ws)
    field = tagged(panel, ("editor", "size"))
    with patch.object(ws, "dispatch", wraps=ws.dispatch) as dispatch:
        event(field, "on_change", raw)
        dispatch.assert_not_called()
        assert field.error


def test_defaulted_boolean_displays_actual_flet_default():
    ws = workspace()
    ws.unset_property("item", "visible")
    panel = Inspector(ws)
    assert tagged(panel, ("editor", "visible")).value is True


def test_expand_zero_is_false_and_positive_is_integer():
    ws = workspace()
    panel = Inspector(ws)
    field = tagged(panel, ("editor", "expand"))
    event(field, "on_change", "0")
    assert ws.node("item").props["expand"] is False
    event(field, "on_change", "3")
    assert ws.node("item").props["expand"] == 3
    assert type(ws.node("item").props["expand"]) is int
    event(field, "on_change", "11")
    assert field.error and ws.node("item").props["expand"] == 3


def test_uniform_and_individual_inset_fields_stay_in_sync():
    ws = workspace("Container")
    panel = Inspector(ws)
    uniform = tagged(panel, ("editor", "padding"))
    left = tagged(panel, ("part", "padding", "left"))
    event(uniform, "on_change", "18")
    assert left.value == "18"
    event(left, "on_change", "12")
    assert uniform.value == ""


def test_insets_preserve_sides_and_numeric_values():
    ws = workspace("Container")
    panel = Inspector(ws)
    field = tagged(panel, ("part", "padding", "left"))
    event(field, "on_change", "12.5")
    assert ws.node("item").props["padding"] == {
        "left": 12.5,
        "right": 10,
        "top": 10,
        "bottom": 10,
    }
    event(tagged(panel, ("part", "padding", "right")), "on_change", "2")
    assert ws.node("item").props["padding"]["right"] == 2
    assert ws.node("item").props["padding"]["left"] == 12.5


def test_composites_and_input_border_use_codec_shapes():
    ws = workspace()
    ws.select(None)
    panel = Inspector(ws)
    event(tagged(panel, ("editor", "appbar")), "on_change", "Toolbar")
    assert ws.project.page["appbar"] == {"title": "Toolbar"}
    event(tagged(panel, ("editor", "theme")), "on_change", "BLUE")
    assert ws.project.page["theme"] == {"color_scheme_seed": "BLUE"}
    ws = workspace("TextField")
    panel = Inspector(ws)
    event(tagged(panel, ("editor", "border")), "on_select", "none")
    assert ws.node("item").props["border"] == {"kind": "none"}


def test_diagnostic_is_shown_only_for_matching_property_and_node():
    ws = workspace()
    issues = (
        Diagnostic(
            code="x",
            message="Problem",
            severity=Severity.ERROR,
            node_id="item",
            path=("props", "size"),
        ),
        Diagnostic(
            code="x",
            message="Other",
            severity=Severity.ERROR,
            node_id="other",
            path=("props", "size"),
        ),
    )
    with patch.object(ws, "diagnostics", return_value=issues):
        panel = Inspector(ws)
        row = tagged(panel, ("property", "size"))
        assert any(isinstance(c, ft.Text) and c.value == "Problem" for c in walk(row))
        assert all(not isinstance(c, ft.Text) or c.value != "Other" for c in walk(row))
