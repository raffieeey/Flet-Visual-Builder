"""Builders for T04 unit tests. Deterministic; no hypothesis."""

from __future__ import annotations

import copy
from collections.abc import Mapping

from src.flet_visual_builder.contracts import (
    Asset,
    DocumentSnapshot,
    EventSymbol,
    JsonValue,
    Node,
    NodeId,
    Project,
)


def make_node(
    node_id: str,
    type_id: str,
    *,
    props: Mapping[str, JsonValue] | None = None,
    slots: Mapping[str, tuple[NodeId, ...]] | None = None,
    events: Mapping[str, EventSymbol] | None = None,
) -> Node:
    return Node(
        id=node_id,
        type_id=type_id,
        props=dict(props or {}),
        slots=dict(slots or {}),
        events=dict(events or {}),
    )


def make_snapshot(
    *nodes: Node,
    root_ids: tuple[NodeId, ...] | None = None,
    page: Mapping[str, JsonValue] | None = None,
    assets: Mapping[str, Asset] | None = None,
    revision: int = 1,
    name: str = "test",
) -> DocumentSnapshot:
    mapping = {node.id: node for node in nodes}
    if root_ids is None:
        root_ids = (nodes[0].id,) if nodes else ()
    return DocumentSnapshot(
        project=Project(
            name=name,
            page=dict(page or {}),
            root_ids=root_ids,
            nodes=mapping,
            assets=dict(assets or {}),
        ),
        revision=revision,
    )


def column_with_texts(count: int, *, revision: int = 1) -> DocumentSnapshot:
    texts = [
        make_node(f"t{i}", "Text", props={"value": str(i)}) for i in range(count)
    ]
    column = make_node(
        "root",
        "Column",
        slots={"controls": tuple(text.id for text in texts)},
    )
    return make_snapshot(column, *texts, revision=revision)


def column_named(ids: tuple[str, ...], *, revision: int = 1) -> DocumentSnapshot:
    texts = [make_node(node_id, "Text", props={"value": node_id}) for node_id in ids]
    column = make_node("root", "Column", slots={"controls": ids})
    return make_snapshot(column, *texts, revision=revision)


def nested_containers(depth: int, *, revision: int = 1) -> DocumentSnapshot:
    """Chain of Containers: c1.content → c2 … → leaf Text. Root depth is 1."""
    if depth < 1:
        raise ValueError("depth must be >= 1")
    nodes: list[Node] = []
    leaf = make_node("leaf", "Text", props={"value": "x"})
    nodes.append(leaf)
    child_id = leaf.id
    # depth=1 is just the leaf as root; depth=2 is container → leaf.
    for level in range(depth - 1, 0, -1):
        node_id = "root" if level == 1 else f"c{level}"
        nodes.append(
            make_node(node_id, "Container", slots={"content": (child_id,)})
        )
        child_id = node_id
    nodes.reverse()
    return make_snapshot(*nodes, root_ids=(nodes[0].id,), revision=revision)


def clone_project(snapshot: DocumentSnapshot) -> Project:
    return copy.deepcopy(snapshot.project)
