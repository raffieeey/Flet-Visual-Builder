"""HistoryDispatcher: delegation, revisions, undo/redo, stale/duplicate guards."""

from __future__ import annotations

import copy

from flet_visual_builder.contracts import (
    Command,
    CommandDispatcher,
    CommandResult,
    CommandStatus,
    DeleteNode,
    DropIntent,
    InsertNode,
    Redo,
    ReplaceProject,
    SetProperty,
    Undo,
)
from flet_visual_builder.model.reducer import Reducer
from flet_visual_builder.state.history_dispatcher import HistoryDispatcher
from tests.unit.history.helpers import column_with_texts, insert_text, make_node, run
from tests.unit.model.helpers import clone_project, make_snapshot


class _RecordingReducer:
    def __init__(self) -> None:
        self.inner = Reducer()
        self.seen: list[object] = []

    def apply(self, snapshot, command):
        self.seen.append(command)
        return self.inner.apply(snapshot, command)


class _StaleReducer:
    def __init__(self) -> None:
        self.inner = Reducer()

    def apply(self, snapshot, command):
        real = self.inner.apply(snapshot, command)
        if real.status is not CommandStatus.COMMITTED:
            return real
        return CommandResult(
            command_id=real.command_id,
            status=real.status,
            before_revision=snapshot.revision - 1,
            snapshot=real.snapshot,
            affected_ids=real.affected_ids,
            diagnostics=real.diagnostics,
        )


def test_dispatcher_satisfies_protocol() -> None:
    dispatcher: CommandDispatcher = HistoryDispatcher(column_with_texts(0))
    result = dispatcher.execute(
        InsertNode(
            command_id="i",
            node=make_node("t0", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
        expected_revision=dispatcher.snapshot.revision,
    )
    assert isinstance(result, CommandResult)
    assert result.status is CommandStatus.COMMITTED


def test_delegates_structural_transforms_to_reducer() -> None:
    recorder = _RecordingReducer()
    dispatcher = HistoryDispatcher(column_with_texts(0), reducer=recorder)
    result = insert_text(dispatcher, "t0")
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.revision == 2
    assert len(recorder.seen) == 1
    assert isinstance(recorder.seen[0], InsertNode)
    assert "t0" in result.snapshot.project.nodes


def test_undo_redo_are_not_passed_to_reducer() -> None:
    recorder = _RecordingReducer()
    dispatcher = HistoryDispatcher(column_with_texts(0), reducer=recorder)
    insert_text(dispatcher, "t0")
    undo = run(dispatcher, Undo(command_id="u1"))
    redo = run(dispatcher, Redo(command_id="r1"))
    assert undo.status is CommandStatus.COMMITTED
    assert redo.status is CommandStatus.COMMITTED
    assert all(not isinstance(cmd, (Undo, Redo)) for cmd in recorder.seen)


def test_stale_expected_revision_rejects_without_mutation() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    insert_text(dispatcher, "t0")
    frozen = copy.deepcopy(dispatcher.snapshot)
    result = dispatcher.execute(
        InsertNode(
            command_id="late",
            node=make_node("t1", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=1),
        ),
        expected_revision=frozen.revision - 1,
    )
    assert result.status is CommandStatus.REJECTED
    assert any(d.code == "revision.stale" for d in result.diagnostics)
    assert dispatcher.snapshot == frozen
    assert dispatcher.history_length == 1


def test_stale_retry_with_current_revision_commits() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    cmd = InsertNode(
        command_id="retry",
        node=make_node("t0", "Text"),
        destination=DropIntent(parent_id="root", slot_name="controls", index=0),
    )
    missed = dispatcher.execute(cmd, expected_revision=dispatcher.snapshot.revision + 1)
    assert missed.status is CommandStatus.REJECTED
    ok = dispatcher.execute(cmd, expected_revision=dispatcher.snapshot.revision)
    assert ok.status is CommandStatus.COMMITTED
    assert "t0" in dispatcher.snapshot.project.nodes


def test_committed_advances_revision_by_one() -> None:
    snap = column_with_texts(0, revision=4)
    dispatcher = HistoryDispatcher(snap)
    result = insert_text(dispatcher, "t0")
    assert result.status is CommandStatus.COMMITTED
    assert result.before_revision == 4
    assert result.snapshot.revision == 5
    assert dispatcher.snapshot.revision == 5


def test_rejected_and_noop_do_not_create_history_or_advance() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(1, revision=7))
    before = copy.deepcopy(dispatcher.snapshot)
    rejected = run(dispatcher, DeleteNode(command_id="missing", node_id="nope"))
    noop = run(
        dispatcher,
        SetProperty(command_id="same", node_id="t0", name="value", value="0"),
    )
    assert rejected.status is CommandStatus.REJECTED
    assert noop.status is CommandStatus.NOOP
    assert dispatcher.snapshot.revision == 7
    assert dispatcher.history_length == 0
    assert dispatcher.snapshot.project == before.project


def test_duplicate_committed_command_id_does_not_execute_twice() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    first = insert_text(dispatcher, "t0", command_id="same-id")
    frozen = copy.deepcopy(dispatcher.snapshot)
    second = insert_text(dispatcher, "t1", command_id="same-id")
    assert first.status is CommandStatus.COMMITTED
    assert second.status is CommandStatus.REJECTED
    assert any(d.code == "command.duplicate" for d in second.diagnostics)
    assert dispatcher.snapshot == frozen
    assert "t1" not in dispatcher.snapshot.project.nodes


def test_undo_redo_restore_content_and_advance_revision() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0, revision=1))
    insert_text(dispatcher, "t0")
    insert_text(dispatcher, "t1")
    after_two = clone_project(dispatcher.snapshot)
    rev_after_two = dispatcher.snapshot.revision
    assert rev_after_two == 3

    undo1 = run(dispatcher, Undo(command_id="u1"))
    assert undo1.status is CommandStatus.COMMITTED
    assert dispatcher.snapshot.revision == 4
    assert "t1" not in dispatcher.snapshot.project.nodes
    assert "t0" in dispatcher.snapshot.project.nodes
    assert dispatcher.snapshot.project != after_two

    undo2 = run(dispatcher, Undo(command_id="u2"))
    assert undo2.status is CommandStatus.COMMITTED
    assert dispatcher.snapshot.revision == 5
    assert dispatcher.snapshot.project.nodes["root"].slots["controls"] == ()

    redo1 = run(dispatcher, Redo(command_id="r1"))
    assert redo1.status is CommandStatus.COMMITTED
    assert dispatcher.snapshot.revision == 6
    assert "t0" in dispatcher.snapshot.project.nodes
    assert "t1" not in dispatcher.snapshot.project.nodes

    redo2 = run(dispatcher, Redo(command_id="r2"))
    assert redo2.status is CommandStatus.COMMITTED
    assert dispatcher.snapshot.revision == 7
    assert dispatcher.snapshot.project.nodes["root"].slots["controls"] == ("t0", "t1")
    assert dispatcher.snapshot.project == after_two


def test_empty_undo_redo_are_noop() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0, revision=2))
    u = run(dispatcher, Undo(command_id="u"))
    r = run(dispatcher, Redo(command_id="r"))
    assert u.status is CommandStatus.NOOP
    assert r.status is CommandStatus.NOOP
    assert dispatcher.snapshot.revision == 2
    assert dispatcher.history_length == 0


def test_new_command_after_undo_clears_redo() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    insert_text(dispatcher, "t0")
    insert_text(dispatcher, "t1")
    run(dispatcher, Undo(command_id="u1"))
    assert dispatcher.redo_count == 1
    insert_text(dispatcher, "t2")
    assert dispatcher.redo_count == 0
    redo = run(dispatcher, Redo(command_id="r-gone"))
    assert redo.status is CommandStatus.NOOP
    assert "t1" not in dispatcher.snapshot.project.nodes
    assert "t2" in dispatcher.snapshot.project.nodes


def test_replace_project_resets_history() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    insert_text(dispatcher, "t0")
    other = column_with_texts(2)
    result = run(dispatcher, ReplaceProject(command_id="open", project=other.project))
    assert result.status is CommandStatus.COMMITTED
    assert dispatcher.history_length == 0
    assert dispatcher.snapshot.project.nodes["root"].slots["controls"] == ("t0", "t1")
    undo = run(dispatcher, Undo(command_id="u-after-open"))
    assert undo.status is CommandStatus.NOOP


def test_unknown_command_is_rejected() -> None:
    dispatcher = HistoryDispatcher(column_with_texts(0))
    result = run(dispatcher, Command(command_id="bare"))  # type: ignore[arg-type]
    assert result.status is CommandStatus.REJECTED
    assert dispatcher.history_length == 0


def test_stale_reducer_result_is_discarded() -> None:
    snap = column_with_texts(0)
    dispatcher = HistoryDispatcher(snap, reducer=_StaleReducer())
    frozen = copy.deepcopy(dispatcher.snapshot)
    result = insert_text(dispatcher, "t0")
    assert result.status is CommandStatus.REJECTED
    assert any(d.code == "revision.stale" for d in result.diagnostics)
    assert dispatcher.snapshot == frozen
    assert "t0" not in dispatcher.snapshot.project.nodes
    assert dispatcher.history_length == 0


def test_out_of_order_apply_result_is_discarded() -> None:
    snap = column_with_texts(0)
    pending = Reducer().apply(
        snap,
        InsertNode(
            command_id="bg",
            node=make_node("ghost", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert pending.status is CommandStatus.COMMITTED
    dispatcher = HistoryDispatcher(snap)
    insert_text(dispatcher, "live")
    frozen = copy.deepcopy(dispatcher.snapshot)
    discarded = dispatcher.apply_result(pending)
    assert discarded.status is CommandStatus.REJECTED
    assert any(d.code == "revision.stale" for d in discarded.diagnostics)
    assert dispatcher.snapshot == frozen
    assert "ghost" not in dispatcher.snapshot.project.nodes


def test_apply_result_installs_when_revision_is_current() -> None:
    snap = column_with_texts(0)
    dispatcher = HistoryDispatcher(snap)
    pending = Reducer().apply(
        dispatcher.snapshot,
        InsertNode(
            command_id="bg-ok",
            node=make_node("kept", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    applied = dispatcher.apply_result(pending)
    assert applied.status is CommandStatus.COMMITTED
    assert "kept" in dispatcher.snapshot.project.nodes
    assert dispatcher.history_length == 1
