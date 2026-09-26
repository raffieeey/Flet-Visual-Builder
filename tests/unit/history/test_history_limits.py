"""100-entry and 64-MiB history caps."""

from __future__ import annotations

from src.flet_visual_builder.contracts import CommandStatus
from src.flet_visual_builder.state.history_dispatcher import (
    HistoryDispatcher,
    MAX_HISTORY_ENTRIES,
    MAX_HISTORY_STRUCTURAL_BYTES,
)
from tests.unit.history.helpers import column_with_texts, insert_text, set_prop


def test_real_entry_cap_is_100() -> None:
    assert MAX_HISTORY_ENTRIES == 100


def test_real_byte_cap_is_64_mib() -> None:
    assert MAX_HISTORY_STRUCTURAL_BYTES == 64 * 1024 * 1024


def test_101st_entry_trims_oldest() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    for i in range(101):
        result = insert_text(dispatcher, f"n{i}")
        assert result.status is CommandStatus.COMMITTED
    assert dispatcher.history_length == 100
    assert dispatcher.undo_count == 100
    # Current document still has every inserted node; only history is trimmed.
    assert all(f"n{i}" in dispatcher.snapshot.project.nodes for i in range(101))
    # Oldest snapshot (empty column) was dropped, so 100 undos stop after n0.
    from src.flet_visual_builder.contracts import Undo
    from tests.unit.history.helpers import run

    for i in range(100):
        undone = run(dispatcher, Undo(command_id=f"u{i}"))
        assert undone.status is CommandStatus.COMMITTED
    assert dispatcher.undo_count == 0
    assert "n0" in dispatcher.snapshot.project.nodes
    extra = run(dispatcher, Undo(command_id="u-empty"))
    assert extra.status is CommandStatus.NOOP


def test_byte_cap_trims_oldest_with_injectable_limit() -> None:
    dispatcher = HistoryDispatcher(
        column_with_texts(1),
        max_structural_bytes=2500,
    )
    payload = "x" * 400
    for i in range(12):
        value = f"{payload}{i}"
        result = set_prop(
            dispatcher,
            command_id=f"p{i}",
            node_id="t0",
            name="value",
            value=value,
            gesture_id=f"g{i}",
        )
        assert result.status is CommandStatus.COMMITTED
        assert dispatcher.history_structural_bytes() <= 2500
    assert 0 < dispatcher.history_length < 12
    assert dispatcher.snapshot.project.nodes["t0"].props["value"] == f"{payload}11"
