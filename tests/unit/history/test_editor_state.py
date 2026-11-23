"""EditorState holds chrome fields and never creates document history."""

from __future__ import annotations

import copy

from flet_visual_builder.contracts import EditorTab
from flet_visual_builder.state.editor_state import EditorState
from flet_visual_builder.state.history_dispatcher import HistoryDispatcher
from tests.unit.history.helpers import column_with_texts, insert_text


def test_editor_state_holds_selection_hover_tab_status() -> None:
    state = EditorState()
    assert state.selection is None
    assert state.hover is None
    assert state.active_tab is EditorTab.DESIGN
    assert state.status == ""

    state.select_node("t0")
    state.set_hover("t1")
    state.activate(EditorTab.CODE)
    state.set_status("saved")

    assert state.selection == "t0"
    assert state.hover == "t1"
    assert state.active_tab is EditorTab.CODE
    assert state.status == "saved"


def test_editor_state_does_not_touch_history() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(1))
    insert_text(dispatcher, "extra")
    frozen = copy.deepcopy(dispatcher.snapshot)
    hist = dispatcher.history_length

    state = EditorState()
    state.select_node("extra")
    state.set_hover("root")
    state.activate(EditorTab.PREVIEW)
    state.set_status("hover")
    state.note_preview_error(frozen.revision)
    state.apply_background_result(frozen.revision - 1, frozen.revision)

    assert dispatcher.snapshot == frozen
    assert dispatcher.history_length == hist
    assert state.visible_stale_revision == frozen.revision


def test_background_result_applied_only_if_revision_current() -> None:
    state = EditorState()
    assert state.apply_background_result(3, 4) is False
    assert state.last_successful_projection_revision is None

    assert state.apply_background_result(4, 4) is True
    assert state.last_successful_projection_revision == 4
    assert state.visible_stale_revision is None


def test_preview_error_preserves_visible_stale_revision() -> None:
    state = EditorState()
    state.apply_background_result(2, 2)
    state.note_preview_error(2)
    assert state.last_successful_projection_revision == 2
    assert state.visible_stale_revision == 2
    # A stale background success must not clobber the last good projection.
    assert state.apply_background_result(1, 2) is False
    assert state.last_successful_projection_revision == 2
    assert state.visible_stale_revision == 2
