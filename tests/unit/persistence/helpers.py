"""Shared builders for persistence tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.flet_visual_builder.contracts import (
    Asset,
    Diagnostic,
    EventSymbol,
    JsonValue,
    Node,
    NodeId,
    Project,
    Severity,
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


def make_project(
    *nodes: Node,
    root_ids: tuple[NodeId, ...] | None = None,
    page: Mapping[str, JsonValue] | None = None,
    assets: Mapping[str, Asset] | None = None,
    name: str = "test",
) -> Project:
    mapping = {node.id: node for node in nodes}
    if root_ids is None:
        root_ids = (nodes[0].id,) if nodes else ()
    return Project(
        name=name,
        page=dict(page or {}),
        root_ids=root_ids,
        nodes=mapping,
        assets=dict(assets or {}),
    )


def sample_project() -> Project:
    """Valid catalogue document exercising unset / null / false / 0."""
    root = make_node(
        "root",
        "Column",
        props={"spacing": 0, "tight": False, "scroll": None},
        slots={"controls": ("label", "save")},
    )
    label = make_node(
        "label",
        "Text",
        props={"value": "", "size": None, "visible": False},
    )
    save = make_node(
        "save",
        "Button",
        props={"content": "Save"},
        slots={"content": ()},
        events={"on_click": EventSymbol("handle_save_click")},
    )
    return make_project(
        root,
        label,
        save,
        page={"title": "T", "padding": 0, "appbar": None},
        name="Round trip",
    )


def v2_envelope(
    nodes: dict[str, Any],
    root_ids: list[str],
    *,
    page: dict[str, Any] | None = None,
    assets: dict[str, Any] | None = None,
    name: str = "t",
) -> dict[str, Any]:
    return {
        "name": name,
        "page": page or {},
        "root_ids": root_ids,
        "nodes": nodes,
        "assets": assets or {},
        "schema_version": 2,
        "catalogue_version": 1,
        "target_flet": "1.0.1",
    }


def text_node(node_id: str, value: str = "x") -> dict[str, Any]:
    return {
        "id": node_id,
        "type_id": "Text",
        "props": {"value": value},
        "slots": {},
        "events": {},
    }


def diagnostic_blob(diagnostics: tuple[Diagnostic, ...] | list[Diagnostic]) -> str:
    return " ".join(f"{d.code} {d.message}" for d in diagnostics).lower()


def has_error_named(
    diagnostics: tuple[Diagnostic, ...] | list[Diagnostic], *needles: str
) -> bool:
    blob = diagnostic_blob(diagnostics)
    return all(needle.lower() in blob for needle in needles) and any(
        d.severity == Severity.ERROR for d in diagnostics
    )
