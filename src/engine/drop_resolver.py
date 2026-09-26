from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from src.engine.tree_ops import find_node, find_parent, is_ancestor
from src.models.widget_node import WidgetNode


@dataclass(frozen=True)
class TargetKey:
    node_id: str
    slot: str | None
    index: int  # a boundary in the current list


@dataclass(frozen=True)
class DropIntent:
    source_id: str
    target: TargetKey
    inside: bool


class RejectionReason(Enum):
    SELF_DROP = auto()
    DESCENDANT_DROP = auto()
    VANISHED_SOURCE = auto()
    STALE_REVISION = auto()
    INCOMPATIBLE_SLOT = auto()
    OCCUPIED_SINGLE_CHILD = auto()
    INVALID_INDEX = auto()
    DUPLICATE_COMMIT = auto()


@dataclass(frozen=True)
class DropResolution:
    accepted: bool
    intent: DropIntent | None
    reason: RejectionReason | None
    message: str


def normalize_index(intent: DropIntent, source_slot: str | None, source_index: int) -> int:
    """Map a pre-removal boundary index to a post-removal insert index.

    TargetKey.index is a boundary in the current list. The value returned here
    is the index after source removal (DropIntent.index after correction).

    Same-list test: the destination list is the source's current list when both
    resolve to the same ``(owning node id, slot)`` pair. Destination owner and
    slot are ``intent.target.node_id`` and ``intent.target.slot``. This function
    receives ``source_slot`` for the slot half of that pair; without the source
    parent id, same-list here is ``source_slot == intent.target.slot``.
    ``resolve_drop`` applies the owning-node half (source parent id must equal
    ``intent.target.node_id``) so a same-named slot on a different parent is
    not treated as the same list.

    This correction happens ONCE, in the resolver — the move reducer must not
    repeat it.
    """
    boundary = intent.target.index
    same_list = source_slot == intent.target.slot
    if same_list and source_index < boundary:
        return boundary - 1
    return boundary


def resolve_drop(
    root: WidgetNode,
    intent: DropIntent,
    *,
    revision: int,
    current_revision: int,
    committed_keys: frozenset[tuple[str, str | None, int]],
    accepts_children: Callable[[str], bool],
    slots_for: Callable[[str], tuple[str, ...]],
    single_child_slots: frozenset[str] = frozenset(),
) -> DropResolution:
    """Accept or reject *intent* against *root* without mutating the tree.

    Index correction (pre-removal boundary → post-removal insert index) happens
    ONCE here. The move reducer must use the index on the returned intent and
    must not apply ``normalize_index`` again.
    """
    if revision != current_revision:
        return _reject(
            RejectionReason.STALE_REVISION,
            "Drop rejected because the tree revision is stale.",
        )

    source = find_node(root, intent.source_id)
    if source is None:
        return _reject(
            RejectionReason.VANISHED_SOURCE,
            "Source node is not present in the tree.",
        )

    if intent.source_id == intent.target.node_id:
        return _reject(
            RejectionReason.SELF_DROP,
            "Cannot drop a node onto itself.",
        )

    if is_ancestor(root, intent.source_id, intent.target.node_id):
        return _reject(
            RejectionReason.DESCENDANT_DROP,
            "Cannot drop a node onto its own descendant.",
        )

    target_id = intent.target.node_id
    slot = intent.target.slot

    if intent.inside and not accepts_children(target_id):
        return _reject(
            RejectionReason.INCOMPATIBLE_SLOT,
            "Destination slot is incompatible with this drop.",
        )

    if intent.inside and slot is None:
        return _reject(
            RejectionReason.INCOMPATIBLE_SLOT,
            "An inside destination requires one explicitly identified slot.",
        )

    if slot is not None and slot not in slots_for(target_id):
        return _reject(
            RejectionReason.INCOMPATIBLE_SLOT,
            "Destination slot is incompatible with this drop.",
        )

    dest_list = _destination_list(root, intent.target)

    if slot is not None and slot in single_child_slots:
        occupied = [child for child in dest_list if child.id != intent.source_id]
        if occupied:
            return _reject(
                RejectionReason.OCCUPIED_SINGLE_CHILD,
                "Destination slot already holds a child.",
            )

    if intent.target.index < 0 or intent.target.index > len(dest_list):
        return _reject(
            RejectionReason.INVALID_INDEX,
            "Drop index is outside the destination list.",
        )

    commit_key = (intent.target.node_id, intent.target.slot, intent.target.index)
    if commit_key in committed_keys:
        return _reject(
            RejectionReason.DUPLICATE_COMMIT,
            "This drop was already committed.",
        )

    source_parent = find_parent(root, intent.source_id)
    source_index = _index_in_slot_list(source_parent, source) if source_parent else 0
    same_owner = source_parent is not None and source_parent.id == intent.target.node_id
    # Owning-node half of the same-list pair; slot half is inside normalize_index.
    if same_owner:
        new_index = normalize_index(intent, source.slot, source_index)
    else:
        new_index = intent.target.index

    accepted_intent = DropIntent(
        source_id=intent.source_id,
        target=TargetKey(
            node_id=intent.target.node_id,
            slot=intent.target.slot,
            index=new_index,
        ),
        inside=intent.inside,
    )
    return DropResolution(
        accepted=True,
        intent=accepted_intent,
        reason=None,
        message="",
    )


def _reject(reason: RejectionReason, message: str) -> DropResolution:
    return DropResolution(accepted=False, intent=None, reason=reason, message=message)


def _destination_list(root: WidgetNode, target: TargetKey) -> list[WidgetNode]:
    node = find_node(root, target.node_id)
    if node is None:
        return []
    return [child for child in node.children if child.slot == target.slot]


def _index_in_slot_list(parent: WidgetNode, source: WidgetNode) -> int:
    siblings = [child for child in parent.children if child.slot == source.slot]
    for index, child in enumerate(siblings):
        if child.id == source.id:
            return index
    for index, child in enumerate(parent.children):
        if child.id == source.id:
            return index
    return 0
