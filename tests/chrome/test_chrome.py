from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import Mock

import flet as ft
import pytest

from flet_visual_builder.app_context import Refresh, Workspace
from flet_visual_builder.interaction.protocol import DRAG_GROUP, encode_create
from flet_visual_builder.services.starter import starter_project
from flet_visual_builder.ui.palette import Palette
from flet_visual_builder.ui.toolbar import Toolbar
from flet_visual_builder.ui.tree_view import Outline
from tests.support.fake_page import FakePage


@pytest.fixture
def ws():
    return Workspace(FakePage(), starter_project())


def drags(palette):
    return [row for row in palette.items.controls if isinstance(row, ft.Draggable)]


def test_headless_panels_and_payloads(ws):
    palette, outline, toolbar = Palette(ws), Outline(ws), Toolbar(ws)
    assert all(
        panel.control.content is not None for panel in (palette, outline, toolbar)
    )
    assert {d.data for d in drags(palette)} == {
        encode_create(t) for t in ws.catalogue.widgets
    }
    assert all(d.group == DRAG_GROUP for d in drags(palette))


def test_palette_search_focus_recent_and_live_catalogue(ws):
    widgets = dict(ws.catalogue.widgets)
    widgets.update({f"NewWidget{i:02}": object() for i in range(45)})
    ws.catalogue = SimpleNamespace(widgets=widgets)
    palette = Palette(ws)
    original_search, original_content = palette.search, palette.control.content
    assert len(drags(palette)) == len(widgets)
    palette.search.value = "newwidget1"
    palette.search.on_change(SimpleNamespace(control=palette.search))
    assert {d.data for d in drags(palette)} == {
        encode_create(f"NewWidget{i:02}") for i in range(10, 20)
    }
    palette.refresh(Refresh.DOCUMENT)
    assert (
        palette.search is original_search
        and palette.control.content is original_content
    )
    palette.refresh(Refresh.PROJECT)
    assert palette.search is original_search and palette.search.value == "newwidget1"
    palette.search.value = "not found"
    palette.search.on_change(None)
    assert not drags(palette)
    assert "No widgets" in palette.items.controls[0].content.value
    palette.search.value = "Text"
    palette.search.on_change(None)
    palette._remember("Text")
    assert drags(palette)[0].data == encode_create("Text")
    assert palette.items.controls[0].content.value == "RECENTLY USED"


def test_palette_click_inserts_beside_selection(ws):
    ws.select("header")
    palette = Palette(ws)
    widget = next(x for x in drags(palette) if x.data == encode_create("Text"))
    widget.content.on_click(None)
    assert ws.parent_of(ws.editor.selection) == ("root", "controls", 1)
    assert palette._recent[0] == "Text"


def test_outline_expansion_selection_and_context_actions(ws):
    outline = Outline(ws)
    ws.add_panel(outline)
    assert "header" in [row.data for row in outline.rows.controls]
    outline._toggle("root")
    outline.refresh(Refresh.DOCUMENT)
    assert "root" not in outline._expanded
    ws.select("header_title")
    assert {"root", "header", "header_col"} <= outline._expanded
    assert "header_title" in [row.data for row in outline.rows.controls]
    outline.refresh(Refresh.DOCUMENT)
    assert "header" in outline._expanded
    row = next(row for row in outline.rows.controls if row.data == "header_title")
    menu = next(x for x in row.content.controls if isinstance(x, ft.PopupMenuButton))
    assert [item.content for item in menu.items] == [
        "Duplicate",
        "Wrap in Container",
        "Wrap in Row",
        "Wrap in Column",
        "Wrap in Card",
        "Delete",
    ]
    ws.duplicate, ws.wrap, ws.delete = Mock(), Mock(), Mock()
    menu.items[0].on_click(None)
    ws.duplicate.assert_called_once_with("header_title")
    for item in menu.items[1:5]:
        item.on_click(None)
    assert [call.args for call in ws.wrap.call_args_list] == [
        ("header_title", w) for w in ("Container", "Row", "Column", "Card")
    ]
    menu.items[-1].on_click(None)
    ws.delete.assert_called_once_with("header_title")
    root = next(row for row in outline.rows.controls if row.data == "root")
    root_menu = next(
        x for x in root.content.controls if isinstance(x, ft.PopupMenuButton)
    )
    assert root_menu.items[-1].disabled


def test_outline_missing_root(ws):
    ws.adopt(replace(ws.project, root_ids=(), nodes={}))
    outline = Outline(ws)
    assert "No document structure" in outline.rows.controls[0].content.value


def test_toolbar_history_dirty_name_and_modes(ws):
    toolbar = Toolbar(ws)
    ws.add_panel(toolbar)
    assert toolbar.undo_button.disabled and toolbar.redo_button.disabled
    assert toolbar.dirty.tooltip == "Saved"
    name = toolbar.name
    toolbar._focus_name(None)
    name.value = "Edited"
    ws.set_property("header_title", "value", "Changed")
    assert toolbar.name is name and name.value == "Edited"
    assert not toolbar.undo_button.disabled and toolbar.redo_button.disabled
    assert toolbar.dirty.tooltip == "Unsaved changes"
    original = ws.rename_project
    ws.rename_project = Mock(wraps=original)
    event = SimpleNamespace(control=name)
    name.on_submit(event)
    ws.rename_project.assert_called_once_with("Edited")
    name.on_blur(event)
    ws.rename_project.assert_called_once()
    assert ws.project.name == "Edited"
    # Rename currently resets history in Workspace's ReplaceProject path.
    ws.set_property("header_title", "value", "Another change")
    ws.undo()
    assert not toolbar.redo_button.disabled
    ws.set_device("phone")
    assert toolbar.devices["phone"].bgcolor is not None
    assert toolbar.devices["fill"].bgcolor is None


def test_toolbar_action_callbacks(ws):
    names = ("new_document", "templates", "open", "save", "export_code")
    actions = SimpleNamespace(**{name: Mock() for name in names})
    toolbar = Toolbar(ws, actions)
    row = toolbar.control.content.content
    document = row.controls[1]
    document_buttons = [
        control for control in document.controls if getattr(control, "on_click", None)
    ]
    assert len(document_buttons) >= 4
    for control in document_buttons[:4]:
        control.on_click(None)
    export = next(
        control for control in row.controls if isinstance(control, ft.FilledButton)
    )
    export.on_click(None)
    for method in vars(actions).values():
        method.assert_called_once_with()


def test_palette_covers_every_widget_exactly_once():
    import flet as ft

    from flet_visual_builder.catalogue import WIDGET_SPECS
    from flet_visual_builder.ui.palette import CATEGORIES, ICONS

    listed = [name for names in CATEGORIES.values() for name in names]
    assert len(listed) == len(set(listed)), "a widget is listed twice"
    assert set(listed) == set(WIDGET_SPECS), "palette and catalogue disagree"
    # Every entry resolves an icon at import time; a missing key falls back to a generic icon.
    missing_icons = [name for name in listed if name not in ICONS]
    assert missing_icons == []
