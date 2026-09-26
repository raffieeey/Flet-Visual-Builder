"""Builders for rendering contract tests."""
from __future__ import annotations

import hashlib
from collections.abc import Mapping

from src.flet_visual_builder.catalogue import catalogue
from src.flet_visual_builder.contracts import (
    Asset,
    ControlPlan,
    Diagnostic,
    DocumentSnapshot,
    EventSymbol,
    JsonValue,
    Node,
    NodeId,
    Project,
    Severity,
)
from src.flet_visual_builder.engine.lowering import Lowering
from src.flet_visual_builder.engine.runtime import RuntimeRenderer

TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"
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
            page=dict(page if page is not None else catalogue.new_page()),
            root_ids=root_ids,
            nodes=mapping,
            assets=dict(assets or {}),
        ),
        revision=revision,
    )


def widget_node(
    type_id: str,
    *,
    node_id: str = "root",
    props: Mapping[str, JsonValue] | None = None,
    slots: Mapping[str, tuple[NodeId, ...]] | None = None,
    events: Mapping[str, EventSymbol] | None = None,
) -> Node:
    merged = catalogue.new_props(type_id)
    if props:
        merged.update(props)
    return make_node(
        node_id, type_id, props=merged, slots=slots, events=events
    )


def widget_snapshot(
    type_id: str,
    *,
    props: Mapping[str, JsonValue] | None = None,
    slots: Mapping[str, tuple[NodeId, ...]] | None = None,
    events: Mapping[str, EventSymbol] | None = None,
    page: Mapping[str, JsonValue] | None = None,
    assets: Mapping[str, Asset] | None = None,
    revision: int = 1,
) -> DocumentSnapshot:
    node = widget_node(
        type_id, props=props, slots=slots, events=events
    )
    return make_snapshot(
        node, page=page, assets=assets, revision=revision
    )


def make_asset(asset_id: str, data: bytes = TINY_PNG, media_type: str = "image/png") -> Asset:
    return Asset(
        id=asset_id,
        media_type=media_type,
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
    )


def lower_ok(snapshot: DocumentSnapshot) -> ControlPlan:
    result = Lowering().lower_project(snapshot, catalogue)
    errors = [d for d in result.diagnostics if d.severity is Severity.ERROR]
    assert result.plan is not None, errors
    assert not errors
    return result.plan


def error_codes(diagnostics: tuple[Diagnostic, ...]) -> set[str]:
    return {d.code for d in diagnostics if d.severity is Severity.ERROR}


LOWERER = Lowering()
RENDERER = RuntimeRenderer()
