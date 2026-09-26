from __future__ import annotations

from src.engine.drop_resolver import (
    DropIntent,
    DropResolution,
    RejectionReason,
    TargetKey,
    normalize_index,
    resolve_drop,
)
from src.engine.tree_ops import insert_child
from src.models.widget_node import WidgetNode


def _column_with(*child_ids: str) -> WidgetNode:
    root = WidgetNode(id="root", type="Column")
    for child_id in child_ids:
        insert_child(root, WidgetNode(id=child_id, type="Text"), slot="controls")
    return root


def _nested() -> WidgetNode:
    root = WidgetNode(id="root", type="Column")
    branch = WidgetNode(id="branch", type="Column")
    leaf = WidgetNode(id="leaf", type="Text")
    insert_child(root, branch, slot="controls")
    insert_child(branch, leaf, slot="controls")
    insert_child(root, WidgetNode(id="sibling", type="Text"), slot="controls")
    return root


def _accepts(node_id: str) -> bool:
    return node_id in {"root", "branch", "holder"}


def _slots(node_id: str) -> tuple[str, ...]:
    if node_id in {"root", "branch"}:
        return ("controls",)
    if node_id == "holder":
        return ("content",)
    return ()


def _resolve(
    root: WidgetNode,
    intent: DropIntent,
    *,
    revision: int = 1,
    current_revision: int = 1,
    committed_keys: frozenset[tuple[str, str | None, int]] | None = None,
    accepts_children=_accepts,
    slots_for=_slots,
    single_child_slots: frozenset[str] = frozenset(),
) -> tuple[DropResolution, WidgetNode]:
    snapshot = root.clone(deep_new_ids=False)
    resolution = resolve_drop(
        root,
        intent,
        revision=revision,
        current_revision=current_revision,
        committed_keys=committed_keys or frozenset(),
        accepts_children=accepts_children,
        slots_for=slots_for,
        single_child_slots=single_child_slots,
    )
    assert root.clone(deep_new_ids=False) == snapshot
    return resolution, snapshot


def _intent(
    source_id: str,
    node_id: str,
    index: int,
    *,
    slot: str | None = "controls",
    inside: bool = False,
) -> DropIntent:
    return DropIntent(
        source_id=source_id,
        target=TargetKey(node_id=node_id, slot=slot, index=index),
        inside=inside,
    )


def test_normalize_index_same_slot_source_before_boundary() -> None:
    intent = _intent("a", "root", 3, slot="controls")
    assert normalize_index(intent, "controls", 1) == 2


def test_normalize_index_same_slot_source_at_or_after_boundary() -> None:
    intent = _intent("a", "root", 2, slot="controls")
    assert normalize_index(intent, "controls", 2) == 2
    assert normalize_index(intent, "controls", 3) == 2


def test_normalize_index_different_slot_keeps_boundary() -> None:
    intent = _intent("a", "root", 3, slot="controls")
    assert normalize_index(intent, "content", 0) == 3


def test_self_drop_rejected() -> None:
    root = _column_with("a", "b")
    resolution, _ = _resolve(root, _intent("a", "a", 0, inside=True))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.SELF_DROP
    assert resolution.intent is None


def test_descendant_drop_rejected() -> None:
    root = _nested()
    resolution, _ = _resolve(root, _intent("branch", "leaf", 0, inside=False))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.DESCENDANT_DROP


def test_vanished_source_rejected() -> None:
    root = _column_with("a")
    resolution, _ = _resolve(root, _intent("missing", "root", 0, inside=True))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.VANISHED_SOURCE


def test_stale_revision_rejected() -> None:
    root = _column_with("a", "b")
    resolution, _ = _resolve(
        root,
        _intent("a", "root", 1, inside=True),
        revision=1,
        current_revision=2,
    )
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.STALE_REVISION


def test_incompatible_slot_inside_without_accepting_children() -> None:
    root = _column_with("a", "b")
    resolution, _ = _resolve(root, _intent("b", "a", 0, slot="controls", inside=True))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.INCOMPATIBLE_SLOT


def test_incompatible_slot_inside_requires_explicit_slot() -> None:
    root = _column_with("a", "b")
    resolution, _ = _resolve(root, _intent("a", "root", 0, slot=None, inside=True))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.INCOMPATIBLE_SLOT


def test_incompatible_slot_not_declared_on_target() -> None:
    root = _column_with("a", "b")
    resolution, _ = _resolve(root, _intent("a", "root", 0, slot="content", inside=True))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.INCOMPATIBLE_SLOT


def test_occupied_single_child_rejected() -> None:
    root = WidgetNode(id="root", type="Column")
    holder = WidgetNode(id="holder", type="Container")
    occupant = WidgetNode(id="occupant", type="Text")
    mover = WidgetNode(id="mover", type="Text")
    insert_child(root, holder, slot="controls")
    insert_child(holder, occupant, slot="content")
    insert_child(root, mover, slot="controls")
    resolution, _ = _resolve(
        root,
        _intent("mover", "holder", 0, slot="content", inside=True),
        single_child_slots=frozenset({"content"}),
    )
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.OCCUPIED_SINGLE_CHILD


def test_invalid_index_rejected() -> None:
    root = _column_with("a", "b")
    resolution, _ = _resolve(root, _intent("a", "root", 3, inside=True))
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.INVALID_INDEX


def test_duplicate_commit_rejected() -> None:
    root = _column_with("a", "b")
    key = ("root", "controls", 1)
    resolution, _ = _resolve(
        root,
        _intent("a", "root", 1, inside=True),
        committed_keys=frozenset({key}),
    )
    assert resolution.accepted is False
    assert resolution.reason is RejectionReason.DUPLICATE_COMMIT


def test_rejected_drop_leaves_tree_structurally_unchanged() -> None:
    root = _nested()
    snapshot = root.clone(deep_new_ids=False)
    resolution = resolve_drop(
        root,
        _intent("branch", "leaf", 0),
        revision=1,
        current_revision=1,
        committed_keys=frozenset(),
        accepts_children=_accepts,
        slots_for=_slots,
    )
    assert resolution.accepted is False
    assert root.clone(deep_new_ids=False) == snapshot


def test_accepted_same_list_normalizes_index_once() -> None:
    root = _column_with("a", "b", "c")
    resolution, snapshot = _resolve(root, _intent("a", "root", 3, inside=True))
    assert resolution.accepted is True
    assert resolution.reason is None
    assert resolution.intent is not None
    # source index 0 < boundary 3, same (root, controls) list → 2
    assert resolution.intent.target.index == 2
    assert root.clone(deep_new_ids=False) == snapshot


def test_accepted_cross_parent_same_slot_name_keeps_boundary() -> None:
    root = _nested()
    # sibling lives under root/controls; destination is branch/controls
    resolution, _ = _resolve(root, _intent("sibling", "branch", 1, inside=True))
    assert resolution.accepted is True
    assert resolution.intent is not None
    assert resolution.intent.target.index == 1


def test_occupied_single_child_allows_moving_the_occupant() -> None:
    root = WidgetNode(id="root", type="Column")
    holder = WidgetNode(id="holder", type="Container")
    occupant = WidgetNode(id="occupant", type="Text")
    insert_child(root, holder, slot="controls")
    insert_child(holder, occupant, slot="content")
    resolution, _ = _resolve(
        root,
        _intent("occupant", "holder", 0, slot="content", inside=True),
        single_child_slots=frozenset({"content"}),
    )
    assert resolution.accepted is True
