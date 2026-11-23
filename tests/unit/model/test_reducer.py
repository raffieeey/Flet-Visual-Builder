"""Command reduction semantics. Headless; no Flet."""

from __future__ import annotations

import copy

import pytest

from flet_visual_builder.contracts import (
    Command,
    CommandReducer,
    CommandStatus,
    DeleteNode,
    DropIntent,
    EventSymbol,
    InsertNode,
    MoveNode,
    Redo,
    ReplaceProject,
    SetEvent,
    SetProperty,
    Undo,
    UnsetProperty,
    WrapNode,
)
from flet_visual_builder.model.reducer import Reducer, apply
from flet_visual_builder.model.validation import MAX_DEPTH, MAX_NODES, validate_project
from tests.unit.model.helpers import (
    clone_project,
    column_named,
    column_with_texts,
    make_node,
    make_snapshot,
    nested_containers,
)


def _root_controls(snapshot) -> tuple[str, ...]:
    return snapshot.project.nodes["root"].slots["controls"]


def test_reducer_satisfies_protocol() -> None:
    reducer: CommandReducer = Reducer()
    snap = column_with_texts(0)
    node = make_node("t0", "Text")
    result = reducer.apply(
        snap,
        InsertNode(
            command_id="i",
            node=node,
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.before_revision == snap.revision
    assert result.snapshot.revision == snap.revision + 1


def test_insert_appends_and_advances_revision() -> None:
    snap = column_with_texts(1)
    before = clone_project(snap)
    node = make_node("t1", "Text", props={"value": "1"})
    result = apply(
        snap,
        InsertNode(
            command_id="ins",
            node=node,
            destination=DropIntent(parent_id="root", slot_name="controls", index=1),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.revision == 2
    assert _root_controls(result.snapshot) == ("t0", "t1")
    assert snap.project == before
    assert snap.revision == 1
    assert validate_project(result.snapshot.project) == ()


def test_insert_duplicate_id_rejects_without_mutation() -> None:
    snap = column_with_texts(1)
    before = clone_project(snap)
    result = apply(
        snap,
        InsertNode(
            command_id="dup",
            node=make_node("t0", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=1),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot is snap
    assert result.snapshot.revision == 1
    assert snap.project == before


def test_insert_nonempty_slots_rejected() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap,
        InsertNode(
            command_id="graft",
            node=make_node("c", "Column", slots={"controls": ("ghost",)}),
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_insert_into_occupied_single_child_slot_rejected() -> None:
    child = make_node("t0", "Text")
    box = make_node("root", "Container", slots={"content": ("t0",)})
    snap = make_snapshot(box, child)
    result = apply(
        snap,
        InsertNode(
            command_id="full",
            node=make_node("t1", "Text"),
            destination=DropIntent(parent_id="root", slot_name="content", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot.revision == snap.revision


def test_insert_into_leaf_slot_rejected() -> None:
    snap = column_with_texts(1)
    result = apply(
        snap,
        InsertNode(
            command_id="leaf",
            node=make_node("x", "Text"),
            destination=DropIntent(parent_id="t0", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_insert_root_list_requires_controls_slot() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap,
        InsertNode(
            command_id="rootslot",
            node=make_node("extra", "Column", slots={"controls": ()}),
            destination=DropIntent(parent_id=None, slot_name="content", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_insert_into_root_list() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap,
        InsertNode(
            command_id="root",
            node=make_node("other", "Column", slots={"controls": ()}),
            destination=DropIntent(parent_id=None, slot_name="controls", index=1),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.project.root_ids == ("root", "other")


def test_delete_removes_subtree_and_dangling_refs() -> None:
    inner = make_node("t0", "Text")
    mid = make_node("box", "Container", slots={"content": ("t0",)})
    root = make_node("root", "Column", slots={"controls": ("box",)})
    snap = make_snapshot(root, mid, inner)
    before = clone_project(snap)
    result = apply(snap, DeleteNode(command_id="del", node_id="box"))
    assert result.status is CommandStatus.COMMITTED
    assert "box" not in result.snapshot.project.nodes
    assert "t0" not in result.snapshot.project.nodes
    assert result.snapshot.project.nodes["root"].slots["controls"] == ()
    assert validate_project(result.snapshot.project) == ()
    assert snap.project == before


def test_delete_missing_rejects() -> None:
    snap = column_with_texts(0)
    before = clone_project(snap)
    result = apply(snap, DeleteNode(command_id="ghost", node_id="nope"))
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot is snap
    assert snap.project == before


def test_move_same_slot_uses_post_removal_index_not_double_corrected() -> None:
    """§2.5.5: reducer consumes DropIntent.index as already post-removal.

    Original [n0, n1, n2, n3]. Move n1 to sit before n3.
    TargetKey boundary index = 3; source index 1 < 3 so post-removal = 2.
    Result must be [n0, n2, n1, n3]. Subtracting again would yield [n0, n1, n2, n3].
    """
    snap = column_named(("n0", "n1", "n2", "n3"))
    before = clone_project(snap)
    result = apply(
        snap,
        MoveNode(
            command_id="mv",
            node_id="n1",
            destination=DropIntent(parent_id="root", slot_name="controls", index=2),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert _root_controls(result.snapshot) == ("n0", "n2", "n1", "n3")
    assert snap.project == before


def test_move_source_to_end_post_removal_index() -> None:
    snap = column_named(("n0", "n1", "n2", "n3"))
    result = apply(
        snap,
        MoveNode(
            command_id="end",
            node_id="n0",
            destination=DropIntent(parent_id="root", slot_name="controls", index=3),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert _root_controls(result.snapshot) == ("n1", "n2", "n3", "n0")


def test_move_later_item_to_front_post_removal_index() -> None:
    snap = column_named(("n0", "n1", "n2", "n3"))
    result = apply(
        snap,
        MoveNode(
            command_id="front",
            node_id="n3",
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert _root_controls(result.snapshot) == ("n3", "n0", "n1", "n2")


def test_move_same_position_is_noop() -> None:
    snap = column_named(("n0", "n1", "n2"))
    result = apply(
        snap,
        MoveNode(
            command_id="stay",
            node_id="n1",
            destination=DropIntent(parent_id="root", slot_name="controls", index=1),
        ),
    )
    assert result.status is CommandStatus.NOOP
    assert result.snapshot.revision == snap.revision
    assert result.snapshot.project == snap.project


def test_move_into_descendant_rejected() -> None:
    snap = nested_containers(3)
    before = clone_project(snap)
    # root (container) → c2 → leaf. Move root into c2.
    result = apply(
        snap,
        MoveNode(
            command_id="cycle",
            node_id="root",
            destination=DropIntent(parent_id="c2", slot_name="content", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert any("descendant" in d.message.lower() for d in result.diagnostics)
    assert result.snapshot is snap
    assert snap.project == before


def test_move_into_self_rejected() -> None:
    snap = nested_containers(2)
    result = apply(
        snap,
        MoveNode(
            command_id="self",
            node_id="root",
            destination=DropIntent(parent_id="root", slot_name="content", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_move_cross_parent() -> None:
    a = make_node("a", "Text")
    b = make_node("b", "Text")
    left = make_node("left", "Column", slots={"controls": ("a",)})
    right = make_node("right", "Column", slots={"controls": ("b",)})
    root = make_node("root", "Row", slots={"controls": ("left", "right")})
    snap = make_snapshot(root, left, right, a, b)
    result = apply(
        snap,
        MoveNode(
            command_id="cross",
            node_id="a",
            destination=DropIntent(parent_id="right", slot_name="controls", index=1),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.project.nodes["left"].slots["controls"] == ()
    assert result.snapshot.project.nodes["right"].slots["controls"] == ("b", "a")
    assert validate_project(result.snapshot.project) == ()


def test_move_invalid_index_rejected() -> None:
    snap = column_named(("n0", "n1"))
    result = apply(
        snap,
        MoveNode(
            command_id="idx",
            node_id="n0",
            destination=DropIntent(parent_id="root", slot_name="controls", index=5),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_wrap_replaces_owner_and_places_node_at_index_zero() -> None:
    snap = column_named(("n0", "n1", "n2"))
    wrapper = make_node("wrap", "Container", slots={"content": ()})
    result = apply(
        snap,
        WrapNode(
            command_id="w",
            node_id="n1",
            wrapper=wrapper,
            wrapper_slot="content",
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert _root_controls(result.snapshot) == ("n0", "wrap", "n2")
    assert result.snapshot.project.nodes["wrap"].slots["content"] == ("n1",)
    assert "n1" in result.snapshot.project.nodes
    assert validate_project(result.snapshot.project) == ()


def test_wrap_root_preserves_root_list_position() -> None:
    first = make_node("first", "Column", slots={"controls": ()})
    second = make_node("second", "Column", slots={"controls": ()})
    snap = make_snapshot(first, second, root_ids=("first", "second"))
    wrapper = make_node("box", "Container", slots={"content": ()})
    result = apply(
        snap,
        WrapNode(
            command_id="wroot",
            node_id="second",
            wrapper=wrapper,
            wrapper_slot="content",
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.project.root_ids == ("first", "box")
    assert result.snapshot.project.nodes["box"].slots["content"] == ("second",)


def test_wrap_nonempty_wrapper_rejected() -> None:
    snap = column_with_texts(1)
    result = apply(
        snap,
        WrapNode(
            command_id="fullwrap",
            node_id="t0",
            wrapper=make_node("box", "Container", slots={"content": ("ghost",)}),
            wrapper_slot="content",
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_wrap_missing_node_rejected() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap,
        WrapNode(
            command_id="miss",
            node_id="nope",
            wrapper=make_node("box", "Container", slots={"content": ()}),
            wrapper_slot="content",
        ),
    )
    assert result.status is CommandStatus.REJECTED


@pytest.mark.parametrize(
    "value",
    [None, False, True, 0, 0.0, "", "x"],
)
def test_set_property_retains_distinct_json_values(value: object) -> None:
    snap = column_with_texts(1)
    result = apply(
        snap,
        SetProperty(command_id="p", node_id="t0", name="flag", value=value),  # type: ignore[arg-type]
    )
    assert result.status is CommandStatus.COMMITTED
    stored = result.snapshot.project.nodes["t0"].props["flag"]
    assert stored == value
    assert type(stored) is type(value)


def test_unset_null_false_zero_remain_distinct() -> None:
    snap = column_with_texts(1)
    reducer = Reducer()
    s_null = reducer.apply(
        snap, SetProperty(command_id="n", node_id="t0", name="k", value=None)
    )
    s_false = reducer.apply(
        snap, SetProperty(command_id="f", node_id="t0", name="k", value=False)
    )
    s_zero = reducer.apply(
        snap, SetProperty(command_id="z", node_id="t0", name="k", value=0)
    )
    s_unset = reducer.apply(
        snap, UnsetProperty(command_id="u", node_id="t0", name="k")
    )
    assert s_null.snapshot.project.nodes["t0"].props["k"] is None
    assert s_false.snapshot.project.nodes["t0"].props["k"] is False
    assert s_zero.snapshot.project.nodes["t0"].props["k"] == 0
    assert "k" not in s_unset.snapshot.project.nodes["t0"].props
    # Setting null is not an unset.
    assert "k" in s_null.snapshot.project.nodes["t0"].props
    # Unset of a missing key is NOOP.
    assert s_unset.status is CommandStatus.NOOP


def test_set_property_same_value_is_noop() -> None:
    snap = column_with_texts(1)
    result = apply(
        snap, SetProperty(command_id="same", node_id="t0", name="value", value="0")
    )
    assert result.status is CommandStatus.NOOP
    assert result.snapshot.revision == snap.revision


def test_set_false_is_not_noop_for_zero() -> None:
    text = make_node("t0", "Text", props={"k": 0})
    root = make_node("root", "Column", slots={"controls": ("t0",)})
    snap = make_snapshot(root, text)
    result = apply(
        snap, SetProperty(command_id="b", node_id="t0", name="k", value=False)
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.project.nodes["t0"].props["k"] is False


def test_page_property_uses_none_node_id() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap, SetProperty(command_id="page", node_id=None, name="title", value="Hi")
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.project.page["title"] == "Hi"
    unset = apply(result.snapshot, UnsetProperty(command_id="up", node_id=None, name="title"))
    assert unset.status is CommandStatus.COMMITTED
    assert "title" not in unset.snapshot.project.page


def test_set_property_missing_node_rejected() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap, SetProperty(command_id="miss", node_id="ghost", name="x", value=1)
    )
    assert result.status is CommandStatus.REJECTED


def test_set_event_syntax_and_remove() -> None:
    snap = column_with_texts(1)
    symbol = EventSymbol("handle_t0_click")
    bound = apply(
        snap,
        SetEvent(command_id="e", node_id="t0", event_name="on_click", symbol=symbol),
    )
    assert bound.status is CommandStatus.COMMITTED
    assert bound.snapshot.project.nodes["t0"].events["on_click"].name == "handle_t0_click"
    removed = apply(
        bound.snapshot,
        SetEvent(command_id="e2", node_id="t0", event_name="on_click", symbol=None),
    )
    assert removed.status is CommandStatus.COMMITTED
    assert "on_click" not in removed.snapshot.project.nodes["t0"].events


def test_set_event_wrong_symbol_rejected() -> None:
    snap = column_with_texts(1)
    result = apply(
        snap,
        SetEvent(
            command_id="bad",
            node_id="t0",
            event_name="on_click",
            symbol=EventSymbol("handle_other_click"),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot is snap


def test_set_event_remove_missing_is_noop() -> None:
    snap = column_with_texts(1)
    result = apply(
        snap,
        SetEvent(command_id="none", node_id="t0", event_name="on_click", symbol=None),
    )
    assert result.status is CommandStatus.NOOP


def test_replace_project_commits_valid_document() -> None:
    snap = column_with_texts(0)
    other = column_with_texts(2, revision=99)
    result = apply(
        snap, ReplaceProject(command_id="rp", project=other.project)
    )
    assert result.status is CommandStatus.COMMITTED
    assert result.snapshot.revision == snap.revision + 1
    assert result.snapshot.project.nodes["root"].slots["controls"] == ("t0", "t1")


def test_replace_project_invalid_rejected() -> None:
    snap = column_with_texts(0)
    dangling = make_snapshot(
        make_node("root", "Column", slots={"controls": ("missing",)})
    )
    result = apply(snap, ReplaceProject(command_id="bad", project=dangling.project))
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot is snap


def test_replace_project_identical_is_noop() -> None:
    snap = column_with_texts(1)
    result = apply(snap, ReplaceProject(command_id="same", project=snap.project))
    assert result.status is CommandStatus.NOOP


@pytest.mark.parametrize("cls", [Undo, Redo])
def test_undo_redo_rejected_no_history_stack(cls: type) -> None:
    snap = column_with_texts(0)
    before = clone_project(snap)
    result = apply(snap, cls(command_id="hist"))
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot.revision == snap.revision
    assert snap.project == before
    assert any(d.code == "history.unsupported" for d in result.diagnostics)


def test_unknown_command_rejected() -> None:
    snap = column_with_texts(0)
    result = apply(snap, Command(command_id="bare"))  # type: ignore[arg-type]
    assert result.status is CommandStatus.REJECTED


def test_rejected_and_noop_do_not_advance_revision() -> None:
    snap = column_with_texts(1, revision=7)
    rejected = apply(snap, DeleteNode(command_id="x", node_id="missing"))
    noop = apply(
        snap, SetProperty(command_id="y", node_id="t0", name="value", value="0")
    )
    assert rejected.status is CommandStatus.REJECTED
    assert noop.status is CommandStatus.NOOP
    assert rejected.snapshot.revision == 7
    assert noop.snapshot.revision == 7
    assert rejected.before_revision == 7
    assert noop.before_revision == 7


def test_insert_invalid_index_rejected() -> None:
    snap = column_with_texts(1)
    result = apply(
        snap,
        InsertNode(
            command_id="idx",
            node=make_node("t1", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=-1),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_insert_invalid_node_id_rejected() -> None:
    snap = column_with_texts(0)
    result = apply(
        snap,
        InsertNode(
            command_id="hyphen",
            node=make_node("node-1", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED


def test_insert_beyond_max_nodes_rejected() -> None:
    texts = [make_node(f"n{i}", "Text") for i in range(MAX_NODES - 1)]
    root = make_node(
        "root", "Column", slots={"controls": tuple(t.id for t in texts)}
    )
    snap = make_snapshot(root, *texts)
    assert len(snap.project.nodes) == MAX_NODES
    result = apply(
        snap,
        InsertNode(
            command_id="overflow",
            node=make_node("extra", "Text"),
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot.revision == snap.revision
    assert len(snap.project.nodes) == MAX_NODES


def test_wrap_beyond_max_depth_rejected() -> None:
    snap = nested_containers(MAX_DEPTH)
    assert validate_project(snap.project) == ()
    result = apply(
        snap,
        WrapNode(
            command_id="deep",
            node_id="leaf",
            wrapper=make_node("box", "Container", slots={"content": ()}),
            wrapper_slot="content",
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert result.snapshot.revision == snap.revision


def test_deep_copy_compare_on_stale_move() -> None:
    snap = column_named(("a", "b"))
    frozen = copy.deepcopy(snap)
    result = apply(
        snap,
        MoveNode(
            command_id="gone",
            node_id="missing",
            destination=DropIntent(parent_id="root", slot_name="controls", index=0),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert copy.deepcopy(snap) == frozen
