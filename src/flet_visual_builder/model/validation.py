"""Structural document invariants for §2.3.4.

Catalogue allowlists (unknown keys, event membership, codecs) are T05.
This module enforces graph/document structure plus the EventSymbol syntax gate.
"""

from __future__ import annotations

import hashlib
import keyword
import re
from collections.abc import Mapping
from typing import Final

from src.flet_visual_builder.contracts import (
    Asset,
    Diagnostic,
    Node,
    NodeId,
    Project,
    Severity,
    SlotSpec,
)

MAX_NODES: Final[int] = 1000
MAX_DEPTH: Final[int] = 64
MAX_NODE_ID_LENGTH: Final[int] = 64
MAX_ASSET_BYTES: Final[int] = 4 * 1024 * 1024
MAX_TOTAL_ASSET_BYTES: Final[int] = 16 * 1024 * 1024
ROOT_SLOT: Final[str] = "controls"
SUPPORTED_SCHEMA_VERSION: Final[int] = 2
SUPPORTED_CATALOGUE_VERSION: Final[int] = 1
SUPPORTED_TARGET_FLET: Final[str] = "1.0.1"

NODE_ID_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)

# Structural occupancy from TDD §2.4.3. Not the T05 catalogue: no properties,
# events, defaults, or codecs. Unknown type_ids skip these checks. accepted_types
# is None (any visual type) for every current slot.


def _slot(name: str, maximum: int | None) -> SlotSpec:
    return SlotSpec(
        name=name, minimum=0, maximum=maximum, accepted_types=None
    )


STRUCTURAL_SLOTS: Final[Mapping[str, Mapping[str, SlotSpec]]] = {
    "Text": {},
    "Icon": {},
    "Image": {"error_content": _slot("error_content", 1)},
    "Divider": {},
    "ProgressBar": {},
    "TextField": {},
    "Checkbox": {},
    "Switch": {},
    "Button": {"content": _slot("content", 1)},
    "IconButton": {},
    "Container": {"content": _slot("content", 1)},
    "Column": {"controls": _slot("controls", None)},
    "Row": {"controls": _slot("controls", None)},
    "Card": {"content": _slot("content", 1)},
    "ListView": {"controls": _slot("controls", None)},
    "TextButton": {"content": _slot("content", 1)},
}


def is_identifier_safe_node_id(node_id: str) -> bool:
    return (
        bool(node_id)
        and len(node_id) <= MAX_NODE_ID_LENGTH
        and NODE_ID_PATTERN.fullmatch(node_id) is not None
        and not keyword.iskeyword(node_id)
    )


def event_symbol_name(node_id: str, event_name: str) -> str:
    """Syntax form: handle_{node_id}_{event_name without leading on_}."""
    rest = event_name[3:] if event_name.startswith("on_") else event_name
    return f"handle_{node_id}_{rest}"


def structural_slot_spec(type_id: str, slot_name: str) -> SlotSpec | None:
    """Return the occupancy spec, or None if the type is unknown to T04."""
    table = STRUCTURAL_SLOTS.get(type_id)
    if table is None:
        return None
    return table.get(slot_name)


def type_slot_table(type_id: str) -> Mapping[str, SlotSpec] | None:
    return STRUCTURAL_SLOTS.get(type_id)


def slot_accepts(spec: SlotSpec, type_id: str) -> bool:
    if spec.accepted_types is None:
        return True
    return type_id in spec.accepted_types


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    node_id: NodeId | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
        node_id=node_id,
    )


def children_of(node: Node) -> tuple[NodeId, ...]:
    out: list[NodeId] = []
    for ids in node.slots.values():
        out.extend(ids)
    return tuple(out)


def subtree_ids(project: Project, node_id: NodeId) -> frozenset[NodeId]:
    if node_id not in project.nodes:
        return frozenset()
    found: set[NodeId] = set()
    stack = [node_id]
    while stack:
        current = stack.pop()
        if current in found:
            continue
        found.add(current)
        node = project.nodes.get(current)
        if node is None:
            continue
        for child in children_of(node):
            if child not in found:
                stack.append(child)
    return frozenset(found)


def descendants_of(project: Project, node_id: NodeId) -> frozenset[NodeId]:
    return subtree_ids(project, node_id) - {node_id}


def owner_of(
    project: Project, node_id: NodeId
) -> tuple[NodeId | None, str, int] | None:
    """Return (parent_id, slot_name, index) or None if unowned.

    parent_id is None for an entry in the root list (slot ROOT_SLOT).
    """
    for index, root_id in enumerate(project.root_ids):
        if root_id == node_id:
            return (None, ROOT_SLOT, index)
    for parent in project.nodes.values():
        for slot_name, ids in parent.slots.items():
            for index, child_id in enumerate(ids):
                if child_id == node_id:
                    return (parent.id, slot_name, index)
    return None


def slot_children(
    project: Project, parent_id: NodeId | None, slot_name: str
) -> tuple[NodeId, ...] | None:
    """Children of a destination slot. None if the parent node is missing."""
    if parent_id is None:
        if slot_name != ROOT_SLOT:
            return None
        return project.root_ids
    parent = project.nodes.get(parent_id)
    if parent is None:
        return None
    return tuple(parent.slots.get(slot_name, ()))


def node_depth(project: Project, node_id: NodeId) -> int | None:
    """Depth of node_id counting roots as 1. None if unreachable."""
    depths: dict[NodeId, int] = {}
    stack: list[tuple[NodeId, int]] = [(rid, 1) for rid in project.root_ids]
    seen: set[NodeId] = set()
    while stack:
        current, depth = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        depths[current] = depth
        node = project.nodes.get(current)
        if node is None:
            continue
        for child in children_of(node):
            stack.append((child, depth + 1))
    return depths.get(node_id)


def subtree_height(project: Project, node_id: NodeId) -> int:
    """Height in nodes; a leaf is 1. Cycles yield a conservative MAX_DEPTH+1."""

    visiting: set[NodeId] = set()

    def _height(nid: NodeId) -> int:
        if nid in visiting:
            return MAX_DEPTH + 1
        node = project.nodes.get(nid)
        if node is None:
            return 1
        visiting.add(nid)
        child_heights = [_height(cid) for cid in children_of(node)]
        visiting.remove(nid)
        return 1 + max(child_heights, default=0)

    return _height(node_id)


def destination_depth(
    project: Project, parent_id: NodeId | None
) -> int | None:
    """Depth a newly placed child would have under parent_id."""
    if parent_id is None:
        return 1
    parent_depth = node_depth(project, parent_id)
    if parent_depth is None:
        return None
    return parent_depth + 1


def validate_index(index: int, length: int) -> Diagnostic | None:
    if index < 0 or index > length:
        return _error(
            "slot.index",
            f"Index {index} is outside 0..{length}",
            path=("index",),
        )
    return None


def validate_occupancy(
    *,
    parent_type: str | None,
    slot_name: str,
    count: int,
    child_type: str | None = None,
    node_id: NodeId | None = None,
) -> tuple[Diagnostic, ...]:
    """Check min/max and accepted_types when a structural spec exists."""
    errors: list[Diagnostic] = []
    if parent_type is None:
        if slot_name != ROOT_SLOT:
            errors.append(
                _error(
                    "slot.unknown",
                    f"Root list slot must be {ROOT_SLOT!r}, got {slot_name!r}",
                    node_id=node_id,
                )
            )
        return tuple(errors)
    table = type_slot_table(parent_type)
    if table is None:
        return ()
    spec = table.get(slot_name)
    if spec is None:
        errors.append(
            _error(
                "slot.unknown",
                f"{parent_type} does not declare slot {slot_name!r}",
                node_id=node_id,
            )
        )
        return tuple(errors)
    if count < spec.minimum:
        errors.append(
            _error(
                "slot.cardinality",
                f"{parent_type}.{slot_name} requires at least {spec.minimum}, "
                f"found {count}",
                node_id=node_id,
            )
        )
    if spec.maximum is not None and count > spec.maximum:
        errors.append(
            _error(
                "slot.cardinality",
                f"{parent_type}.{slot_name} allows at most {spec.maximum}, "
                f"found {count}",
                node_id=node_id,
            )
        )
    if child_type is not None and not slot_accepts(spec, child_type):
        errors.append(
            _error(
                "slot.accepted_type",
                f"{parent_type}.{slot_name} does not accept type {child_type!r}",
                node_id=node_id,
            )
        )
    return tuple(errors)


def _validate_versions(project: Project) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    if project.schema_version != SUPPORTED_SCHEMA_VERSION:
        errors.append(
            _error(
                "version.unsupported",
                f"schema_version {project.schema_version!r} is not supported",
                path=("schema_version",),
            )
        )
    if project.catalogue_version != SUPPORTED_CATALOGUE_VERSION:
        errors.append(
            _error(
                "version.unsupported",
                f"catalogue_version {project.catalogue_version!r} is not supported",
                path=("catalogue_version",),
            )
        )
    if project.target_flet != SUPPORTED_TARGET_FLET:
        errors.append(
            _error(
                "version.unsupported",
                f"target_flet {project.target_flet!r} is not supported",
                path=("target_flet",),
            )
        )
    return errors


def _validate_assets(assets: Mapping[str, Asset]) -> list[Diagnostic]:
    errors: list[Diagnostic] = []
    total = 0
    for key, asset in assets.items():
        path = ("assets", key)
        if asset.id != key:
            errors.append(
                _error(
                    "asset.id",
                    f"Asset key {key!r} does not match asset.id {asset.id!r}",
                    path=path,
                )
            )
        digest = hashlib.sha256(asset.data).hexdigest()
        if asset.sha256.lower() != digest:
            errors.append(
                _error(
                    "asset.hash",
                    f"Asset {key!r} sha256 does not match data",
                    path=path,
                )
            )
        size = len(asset.data)
        total += size
        if size > MAX_ASSET_BYTES:
            errors.append(
                _error(
                    "asset.size",
                    f"Asset {key!r} exceeds {MAX_ASSET_BYTES} bytes",
                    path=path,
                )
            )
        if not asset.media_type:
            errors.append(
                _error(
                    "asset.media_type",
                    f"Asset {key!r} has an empty media_type",
                    path=path,
                )
            )
    if total > MAX_TOTAL_ASSET_BYTES:
        errors.append(
            _error(
                "asset.size",
                f"Total asset bytes {total} exceed {MAX_TOTAL_ASSET_BYTES}",
                path=("assets",),
            )
        )
    return errors


def validate_project(project: Project) -> tuple[Diagnostic, ...]:
    """Return ERROR diagnostics for every violated §2.3.4 invariant."""
    errors: list[Diagnostic] = []
    errors.extend(_validate_versions(project))
    errors.extend(_validate_assets(project.assets))

    nodes = project.nodes
    if len(nodes) > MAX_NODES:
        errors.append(
            _error(
                "node.limit",
                f"Document has {len(nodes)} nodes; maximum is {MAX_NODES}",
                path=("nodes",),
            )
        )

    for key, node in nodes.items():
        if node.id != key:
            errors.append(
                _error(
                    "id.mismatch",
                    f"Node map key {key!r} does not match node.id {node.id!r}",
                    path=("nodes", key),
                    node_id=node.id,
                )
            )
        if not is_identifier_safe_node_id(node.id):
            errors.append(
                _error(
                    "id.invalid",
                    f"Node id {node.id!r} is not a bounded identifier-safe name",
                    path=("nodes", key),
                    node_id=node.id,
                )
            )
        if not node.type_id:
            errors.append(
                _error(
                    "node.type",
                    "Node type_id must be non-empty",
                    path=("nodes", key, "type_id"),
                    node_id=node.id,
                )
            )
        table = type_slot_table(node.type_id)
        if table is not None:
            for slot_name in node.slots:
                if slot_name not in table:
                    errors.append(
                        _error(
                            "slot.unknown",
                            f"{node.type_id} does not declare slot {slot_name!r}",
                            path=("nodes", key, "slots", slot_name),
                            node_id=node.id,
                        )
                    )
            for slot_name, spec in table.items():
                count = len(node.slots.get(slot_name, ()))
                if count < spec.minimum or (
                    spec.maximum is not None and count > spec.maximum
                ):
                    errors.append(
                        _error(
                            "slot.cardinality",
                            f"{node.type_id}.{slot_name} occupancy {count} "
                            f"is outside {spec.minimum}..{spec.maximum}",
                            path=("nodes", key, "slots", slot_name),
                            node_id=node.id,
                        )
                    )
        for slot_name, ids in node.slots.items():
            if len(ids) != len(set(ids)):
                errors.append(
                    _error(
                        "ownership.duplicate",
                        f"Slot {slot_name!r} on {node.id} contains duplicate ids",
                        path=("nodes", key, "slots", slot_name),
                        node_id=node.id,
                    )
                )
            spec = structural_slot_spec(node.type_id, slot_name)
            for child_id in ids:
                child = nodes.get(child_id)
                if child is None:
                    continue
                if spec is not None and not slot_accepts(spec, child.type_id):
                    errors.append(
                        _error(
                            "slot.accepted_type",
                            f"{node.type_id}.{slot_name} does not accept "
                            f"type {child.type_id!r}",
                            path=("nodes", key, "slots", slot_name),
                            node_id=node.id,
                        )
                    )
        for event_name, symbol in node.events.items():
            expected = event_symbol_name(node.id, event_name)
            if symbol.name != expected:
                errors.append(
                    _error(
                        "event.symbol",
                        f"Event {event_name!r} on {node.id} requires symbol "
                        f"{expected!r}, got {symbol.name!r}",
                        path=("nodes", key, "events", event_name),
                        node_id=node.id,
                    )
                )

    owners: dict[NodeId, list[tuple[NodeId | None, str, int]]] = {
        nid: [] for nid in nodes
    }
    dangling: list[tuple[NodeId | None, str, NodeId]] = []

    if len(project.root_ids) != len(set(project.root_ids)):
        errors.append(
            _error(
                "ownership.duplicate",
                "root_ids contains duplicate node ids",
                path=("root_ids",),
            )
        )
    for index, root_id in enumerate(project.root_ids):
        if root_id not in nodes:
            dangling.append((None, ROOT_SLOT, root_id))
        else:
            owners.setdefault(root_id, []).append((None, ROOT_SLOT, index))

    for node in nodes.values():
        for slot_name, ids in node.slots.items():
            for index, child_id in enumerate(ids):
                if child_id not in nodes:
                    dangling.append((node.id, slot_name, child_id))
                else:
                    owners.setdefault(child_id, []).append(
                        (node.id, slot_name, index)
                    )

    for parent_id, slot_name, child_id in dangling:
        errors.append(
            _error(
                "ref.dangling",
                f"Slot {slot_name!r} references missing node {child_id!r}",
                path=("nodes", parent_id or "root_ids", slot_name),
                node_id=parent_id,
            )
        )

    for nid, places in owners.items():
        if len(places) > 1:
            errors.append(
                _error(
                    "ownership.multiple",
                    f"Node {nid!r} has {len(places)} owners",
                    path=("nodes", nid),
                    node_id=nid,
                )
            )

    # Acyclicity + reachability from roots.
    def _cycles_from(start_ids: tuple[NodeId, ...] | list[NodeId]) -> set[NodeId]:
        visited: set[NodeId] = set()
        rec_stack: set[NodeId] = set()

        def dfs(nid: NodeId) -> None:
            if nid not in nodes:
                return
            if nid in rec_stack:
                errors.append(
                    _error(
                        "graph.cycle",
                        f"Cycle detected at node {nid!r}",
                        path=("nodes", nid),
                        node_id=nid,
                    )
                )
                return
            if nid in visited:
                return
            rec_stack.add(nid)
            visited.add(nid)
            for child in children_of(nodes[nid]):
                dfs(child)
            rec_stack.remove(nid)

        for start in start_ids:
            dfs(start)
        return visited

    reachable = _cycles_from(project.root_ids)
    leftover = [nid for nid in nodes if nid not in reachable]
    if leftover:
        _cycles_from(leftover)
        for nid in leftover:
            errors.append(
                _error(
                    "ref.orphan",
                    f"Node {nid!r} is not reachable from root_ids",
                    path=("nodes", nid),
                    node_id=nid,
                )
            )

    stack: list[tuple[NodeId, int]] = [(rid, 1) for rid in project.root_ids]
    seen_depth: set[NodeId] = set()
    while stack:
        current, depth = stack.pop()
        if current in seen_depth:
            continue
        seen_depth.add(current)
        if depth > MAX_DEPTH:
            errors.append(
                _error(
                    "node.depth",
                    f"Node {current!r} exceeds maximum depth {MAX_DEPTH}",
                    path=("nodes", current),
                    node_id=current,
                )
            )
        node = nodes.get(current)
        if node is None:
            continue
        for child in children_of(node):
            stack.append((child, depth + 1))

    return tuple(errors)


def slots_are_empty(node: Node) -> bool:
    return all(len(ids) == 0 for ids in node.slots.values())
