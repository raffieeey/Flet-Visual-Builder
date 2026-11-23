"""750 ms property-update coalescing. Clock is injected; no sleeps."""

from __future__ import annotations

from flet_visual_builder.contracts import CommandStatus, Undo, UnsetProperty
from flet_visual_builder.state.history_dispatcher import (
    COALESCE_IDLE_SECONDS,
    HistoryDispatcher,
)
from tests.unit.history.helpers import FakeClock, column_with_texts, run, set_prop


def test_coalesce_idle_constant_is_750ms() -> None:
    assert COALESCE_IDLE_SECONDS == 0.75


def test_adjacent_property_updates_coalesce_for_same_triple() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    first = set_prop(
        dispatcher,
        command_id="p1",
        node_id="t0",
        name="value",
        value="a",
        gesture_id="g1",
    )
    clock.advance(0.749)
    second = set_prop(
        dispatcher,
        command_id="p2",
        node_id="t0",
        name="value",
        value="b",
        gesture_id="g1",
    )
    assert first.status is CommandStatus.COMMITTED
    assert second.status is CommandStatus.COMMITTED
    assert dispatcher.history_length == 1
    assert dispatcher.snapshot.project.nodes["t0"].props["value"] == "b"
    undo = run(dispatcher, Undo(command_id="u"))
    assert undo.status is CommandStatus.COMMITTED
    assert dispatcher.snapshot.project.nodes["t0"].props["value"] == "0"


def test_idle_past_750ms_creates_new_history_entry() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    set_prop(
        dispatcher,
        command_id="p1",
        node_id="t0",
        name="value",
        value="a",
        gesture_id="g1",
    )
    clock.advance(0.751)
    set_prop(
        dispatcher,
        command_id="p2",
        node_id="t0",
        name="value",
        value="b",
        gesture_id="g1",
    )
    assert dispatcher.history_length == 2
    assert dispatcher.snapshot.project.nodes["t0"].props["value"] == "b"


def test_different_gesture_does_not_coalesce() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    set_prop(
        dispatcher, command_id="p1", node_id="t0", name="value", value="a", gesture_id="g1"
    )
    clock.advance(0.1)
    set_prop(
        dispatcher, command_id="p2", node_id="t0", name="value", value="b", gesture_id="g2"
    )
    assert dispatcher.history_length == 2


def test_different_node_does_not_coalesce() -> None:
    from tests.unit.history.helpers import insert_text

    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    insert_text(dispatcher, "t1")
    set_prop(
        dispatcher, command_id="p1", node_id="t0", name="value", value="a", gesture_id="g"
    )
    clock.advance(0.1)
    set_prop(
        dispatcher, command_id="p2", node_id="t1", name="value", value="b", gesture_id="g"
    )
    assert dispatcher.history_length == 3  # insert + two property entries


def test_different_property_does_not_coalesce() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    set_prop(
        dispatcher, command_id="p1", node_id="t0", name="value", value="a", gesture_id="g"
    )
    clock.advance(0.1)
    set_prop(
        dispatcher, command_id="p2", node_id="t0", name="visible", value=False, gesture_id="g"
    )
    assert dispatcher.history_length == 2


def test_missing_gesture_id_does_not_coalesce() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    set_prop(dispatcher, command_id="p1", node_id="t0", name="value", value="a")
    clock.advance(0.1)
    set_prop(dispatcher, command_id="p2", node_id="t0", name="value", value="b")
    assert dispatcher.history_length == 2


def test_page_property_coalesces_on_none_node() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(0), clock=clock)
    set_prop(
        dispatcher,
        command_id="t1",
        node_id=None,
        name="title",
        value="A",
        gesture_id="page",
    )
    clock.advance(0.2)
    set_prop(
        dispatcher,
        command_id="t2",
        node_id=None,
        name="title",
        value="B",
        gesture_id="page",
    )
    assert dispatcher.history_length == 1
    assert dispatcher.snapshot.project.page["title"] == "B"


def test_unset_coalesces_with_set_on_same_triple() -> None:
    clock = FakeClock(0.0)
    dispatcher = HistoryDispatcher(column_with_texts(1), clock=clock)
    set_prop(
        dispatcher, command_id="p1", node_id="t0", name="value", value="z", gesture_id="g"
    )
    clock.advance(0.2)
    result = run(
        dispatcher,
        UnsetProperty(command_id="p2", gesture_id="g", node_id="t0", name="value"),
    )
    assert result.status is CommandStatus.COMMITTED
    assert dispatcher.history_length == 1
    assert "value" not in dispatcher.snapshot.project.nodes["t0"].props
