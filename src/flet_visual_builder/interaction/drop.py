"""Pure canvas drop geometry and destination validation.

Indices returned here are *before* source removal, as required by Workspace.move.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from flet_visual_builder.contracts import Catalogue, Point, Project, Size

Zone = Literal["before", "inside", "after"]


@dataclass(frozen=True, slots=True)
class ResolvedDrop:
    zone: Zone
    parent_id: str
    slot_name: str
    index: int  # raw index, before removal


def resolve_drop(
    project: Project,
    catalogue: Catalogue,
    anchor_id: str,
    point: Point,
    size: Size,
    kind: str,
    value: str,
) -> ResolvedDrop | None:
    """Resolve and validate a drop, returning the raw Workspace index.

    Missing measurements are rejected rather than guessing a drop position.
    A root has no siblings, so all of its zones resolve inside its default slot.
    """
    anchor = project.nodes.get(anchor_id)
    if anchor is None or size.width <= 0 or size.height <= 0:
        return None
    if kind == "create":
        type_id = value
    elif kind == "move":
        source = project.nodes.get(value)
        if source is None or value in project.root_ids:
            return None
        type_id = source.type_id
    else:
        return None
    if type_id not in catalogue.widgets:
        return None

    parents: dict[str, tuple[str, str, int]] = {}
    for node in project.nodes.values():
        for slot, ids in node.slots.items():
            for i, child in enumerate(ids):
                parents[child] = (node.id, slot, i)
    anchor_spec = catalogue.widgets.get(anchor.type_id)
    if anchor_spec is None:
        return None
    slots = anchor_spec.slots
    default = (
        "content"
        if "content" in slots
        else "controls" if "controls" in slots else next(iter(slots), None)
    )
    ratio = point.y / size.height
    zone: Zone = (
        "before"
        if ratio < 0.25
        else "after" if ratio >= 0.75 else "inside" if default else "after"
    )
    if anchor_id not in parents:
        zone = "inside"
    if zone == "inside":
        if default is None:
            return None
        parent_id, slot_name, index = (
            anchor_id,
            default,
            len(anchor.slots.get(default, ())),
        )
    else:
        parent_id, slot_name, index = parents[anchor_id]
        index += zone == "after"

    if kind == "move":
        cursor: str | None = parent_id
        seen: set[str] = set()
        while cursor is not None:
            if cursor == value or cursor in seen:
                return None
            seen.add(cursor)
            parent = parents.get(cursor)
            cursor = parent[0] if parent else None
    parent_node = project.nodes[parent_id]
    spec = catalogue.widgets[parent_node.type_id].slots.get(slot_name)
    if spec is None or (
        spec.accepted_types is not None and type_id not in spec.accepted_types
    ):
        return None
    count = len(parent_node.slots.get(slot_name, ()))
    source_parent = parents.get(value) if kind == "move" else None
    if source_parent and source_parent[:2] == (parent_id, slot_name):
        count -= 1
    if spec.maximum is not None and count >= spec.maximum:
        return None
    return ResolvedDrop(zone, parent_id, slot_name, index)
