"""Lower a validated DocumentSnapshot into one authoritative ControlPlan.

No Flet import. Constructor and enum symbols are allowlisted from the frozen
catalogue; project strings never become getattr/eval targets.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

from flet_visual_builder.catalogue.enum_manifest import (
    COLORS,
    CONTROL_STATE,
    ENUM_FAMILIES,
    ICONS,
)
from flet_visual_builder.catalogue.widgets import WIDGET_ORDER
from flet_visual_builder.contracts import (
    AssetValue,
    ActionADT,
    CallValue,
    Catalogue,
    ControlPlan,
    Diagnostic,
    DocumentSnapshot,
    LiteralValue,
    LoweringResult,
    MappingValue,
    Node,
    NodeId,
    NodePlan,
    PlannedScreen,
    Project,
    SequenceValue,
    Severity,
    SymbolRef,
    ValueExpr,
)
from flet_visual_builder.model.screens import screen_entries
from flet_visual_builder.model.validation import validate_project


CODE_SYMBOL_NOT_ALLOWLISTED = "ENGINE_SYMBOL_NOT_ALLOWLISTED"
CODE_ASSET_MISSING = "ENGINE_ASSET_MISSING"
CODE_VERSION = "ENGINE_VERSION"

# Compound constructors emitted by T05 codecs (paths relative to ft).
VALUE_CONSTRUCTOR_PATHS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("Padding",),
        ("Padding", "all"),
        ("Margin",),
        ("Margin", "all"),
        ("BorderRadius",),
        ("BorderRadius", "all"),
        ("Border",),
        ("Border", "all"),
        ("Border", "only"),
        ("BorderSide",),
        ("OutlineInputBorder",),
        ("UnderlineInputBorder",),
        ("NoInputBorder",),
        ("Theme",),
        ("AppBar",),
        ("Text",),
    }
)


def _build_allowed_symbol_paths() -> frozenset[tuple[str, ...]]:
    paths: set[tuple[str, ...]] = set(VALUE_CONSTRUCTOR_PATHS)
    for type_id in WIDGET_ORDER:
        paths.add((type_id,))
    for family, members in ENUM_FAMILIES.items():
        for member in members:
            paths.add((family, member))
    for name in COLORS:
        paths.add(("Colors", name))
    for name in ICONS:
        paths.add(("Icons", name))
    for name in CONTROL_STATE:
        paths.add(("ControlState", name))
    return frozenset(paths)


ALLOWED_SYMBOL_PATHS: frozenset[tuple[str, ...]] = _build_allowed_symbol_paths()


def is_allowlisted(path: tuple[str, ...]) -> bool:
    """True iff ``path`` is a frozen catalogue constructor/enum symbol."""
    return path in ALLOWED_SYMBOL_PATHS


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


def _has_error(diagnostics: tuple[Diagnostic, ...] | list[Diagnostic]) -> bool:
    return any(d.severity is Severity.ERROR for d in diagnostics)


def _to_jsonable(value: object) -> object:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, tuple):
        return [_to_jsonable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _to_jsonable(item) for key, item in value.items()}
    raise TypeError(f"Unsupported document value {type(value)!r}")


def document_sha256(project: Project) -> str:
    """Deterministic SHA-256 of the canonical project document."""
    nodes: dict[str, object] = {}
    for key, node in project.nodes.items():
        nodes[str(key)] = {
            "id": node.id,
            "type_id": node.type_id,
            "props": _to_jsonable(dict(node.props)),
            "slots": {slot: list(ids) for slot, ids in node.slots.items()},
            "events": {event: symbol.name for event, symbol in node.events.items()},
            "actions": {
                event: {"type": "navigate", "route": action.route}
                for event, action in node.actions.items()
            },
        }
    assets = {
        str(key): {
            "id": asset.id,
            "media_type": asset.media_type,
            "sha256": asset.sha256.lower(),
        }
        for key, asset in project.assets.items()
    }
    payload = {
        "name": project.name,
        "page": _to_jsonable(dict(project.page)),
        "root_ids": list(project.root_ids),
        "nodes": nodes,
        "assets": assets,
        "screens": {
            root_id: {"title": meta.title, "route": meta.route}
            for root_id, meta in project.screens.items()
        },
        "initial_route": project.initial_route,
        "schema_version": project.schema_version,
        "catalogue_version": project.catalogue_version,
        "target_flet": project.target_flet,
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def iter_symbols(expr: ValueExpr) -> Iterator[SymbolRef]:
    """Yield every SymbolRef in a lowered value, including CallValue constructors."""
    if isinstance(expr, SymbolRef):
        yield expr
        return
    if isinstance(expr, CallValue):
        yield expr.constructor
        for arg in expr.args:
            yield from iter_symbols(arg)
        for value in expr.kwargs.values():
            yield from iter_symbols(value)
        return
    if isinstance(expr, SequenceValue):
        for item in expr.items:
            yield from iter_symbols(item)
        return
    if isinstance(expr, MappingValue):
        for key, value in expr.items:
            yield from iter_symbols(key)
            yield from iter_symbols(value)


def iter_asset_ids(expr: ValueExpr) -> Iterator[str]:
    if isinstance(expr, AssetValue):
        yield expr.asset_id
        return
    if isinstance(expr, CallValue):
        for arg in expr.args:
            yield from iter_asset_ids(arg)
        for value in expr.kwargs.values():
            yield from iter_asset_ids(value)
        return
    if isinstance(expr, SequenceValue):
        for item in expr.items:
            yield from iter_asset_ids(item)
        return
    if isinstance(expr, MappingValue):
        for key, value in expr.items:
            yield from iter_asset_ids(key)
            yield from iter_asset_ids(value)


def _check_expr(
    expr: ValueExpr,
    *,
    project: Project,
    node_id: NodeId | None,
    path: tuple[str | int, ...],
) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for symbol in iter_symbols(expr):
        if not is_allowlisted(symbol.path):
            diags.append(
                _error(
                    CODE_SYMBOL_NOT_ALLOWLISTED,
                    "constructor/enum symbol is not in the catalogue allowlist: "
                    + ".".join(symbol.path),
                    path=path,
                    node_id=node_id,
                )
            )
    for asset_id in iter_asset_ids(expr):
        if asset_id not in project.assets:
            diags.append(
                _error(
                    CODE_ASSET_MISSING,
                    f"asset {asset_id!r} is not in the document",
                    path=path,
                    node_id=node_id,
                )
            )
    return diags


def _lower_value(catalogue: Catalogue, spec: Any, value: Any) -> ValueExpr:
    lower_value = getattr(catalogue, "lower_value", None)
    if callable(lower_value):
        return lower_value(spec, value)  # type: ignore[no-any-return]
    if value is None:
        return LiteralValue(None)
    return catalogue.codecs[spec.codec_id].lower(value)


def _validate_page(
    catalogue: Catalogue, page: Mapping[str, Any]
) -> tuple[Diagnostic, ...]:
    validate_page = getattr(catalogue, "validate_page", None)
    if callable(validate_page):
        return tuple(validate_page(page))  # type: ignore[arg-type]
    diags: list[Diagnostic] = []
    for key, value in page.items():
        if key not in catalogue.page_properties:
            diags.append(
                _error(
                    "CATALOGUE_UNKNOWN_PROPERTY",
                    f"Unknown property {key!r} on PageSpec",
                    path=("page", key),
                )
            )
            continue
        prop = catalogue.page_properties[key]
        if value is None:
            if not prop.nullable:
                diags.append(
                    _error(
                        "CATALOGUE_NULL_NOT_ALLOWED",
                        f"property {prop.name!r} does not allow null",
                        path=("page", key),
                    )
                )
            continue
        codec = catalogue.codecs[prop.codec_id]
        for diagnostic in codec.validate(value):
            diags.append(
                Diagnostic(
                    code=diagnostic.code,
                    message=diagnostic.message,
                    severity=diagnostic.severity,
                    path=("page", key) + diagnostic.path,
                    node_id=diagnostic.node_id,
                )
            )
    return tuple(diags)


def _validate_node(
    catalogue: Catalogue,
    node: Node,
    nodes: Mapping[NodeId, Node],
) -> tuple[Diagnostic, ...]:
    validate_node = getattr(catalogue, "validate_node", None)
    if callable(validate_node):
        return tuple(validate_node(node, nodes=nodes))  # type: ignore[arg-type]
    if node.type_id not in catalogue.widgets:
        return (
            _error(
                "CATALOGUE_UNKNOWN_WIDGET",
                f"Unknown widget type {node.type_id!r}",
                node_id=node.id,
            ),
        )
    spec = catalogue.widgets[node.type_id]
    diags: list[Diagnostic] = []
    for key, value in node.props.items():
        if key not in spec.properties:
            diags.append(
                _error(
                    "CATALOGUE_UNKNOWN_PROPERTY",
                    f"Unknown property {key!r} on {node.type_id}",
                    path=("props", key),
                    node_id=node.id,
                )
            )
            continue
        prop = spec.properties[key]
        if value is None:
            if not prop.nullable:
                diags.append(
                    _error(
                        "CATALOGUE_NULL_NOT_ALLOWED",
                        f"property {prop.name!r} does not allow null",
                        path=("props", key),
                        node_id=node.id,
                    )
                )
            continue
        for diagnostic in catalogue.codecs[prop.codec_id].validate(value):
            diags.append(
                Diagnostic(
                    code=diagnostic.code,
                    message=diagnostic.message,
                    severity=diagnostic.severity,
                    path=("props", key) + diagnostic.path,
                    node_id=node.id,
                )
            )
    for name, prop in spec.properties.items():
        if prop.required and name not in node.props:
            diags.append(
                _error(
                    "CATALOGUE_REQUIRED_PROPERTY",
                    f"required property {name!r} is missing on {node.type_id}",
                    path=("props", name),
                    node_id=node.id,
                )
            )
    for event_name in node.events:
        if event_name not in spec.events:
            diags.append(
                _error(
                    "CATALOGUE_UNKNOWN_EVENT",
                    f"Unknown event {event_name!r} on {node.type_id}",
                    path=("events", event_name),
                    node_id=node.id,
                )
            )
    return tuple(diags)


class Lowering:
    """Catalogue-driven Lowerer. One ControlPlan for a valid snapshot."""

    def lower_project(
        self, snapshot: DocumentSnapshot, catalogue: Catalogue
    ) -> LoweringResult:
        project = snapshot.project
        diagnostics: list[Diagnostic] = []
        diagnostics.extend(validate_project(project))

        if project.catalogue_version != catalogue.version:
            diagnostics.append(
                _error(
                    CODE_VERSION,
                    "catalogue_version does not match the loaded catalogue",
                    path=("catalogue_version",),
                )
            )
        if project.target_flet != catalogue.target_flet:
            diagnostics.append(
                _error(
                    CODE_VERSION,
                    "target_flet does not match the loaded catalogue",
                    path=("target_flet",),
                )
            )

        diagnostics.extend(_validate_page(catalogue, project.page))

        for node in project.nodes.values():
            if node.type_id not in WIDGET_ORDER:
                diagnostics.append(
                    _error(
                        CODE_SYMBOL_NOT_ALLOWLISTED,
                        f"widget type {node.type_id!r} is not an allowlisted constructor",
                        path=("nodes", node.id, "type_id"),
                        node_id=node.id,
                    )
                )
            diagnostics.extend(_validate_node(catalogue, node, project.nodes))
            if node.type_id in catalogue.widgets:
                spec = catalogue.widgets[node.type_id]
                if not is_allowlisted(spec.constructor.path):
                    diagnostics.append(
                        _error(
                            CODE_SYMBOL_NOT_ALLOWLISTED,
                            "widget constructor is not in the catalogue allowlist: "
                            + ".".join(spec.constructor.path),
                            path=("nodes", node.id, "type_id"),
                            node_id=node.id,
                        )
                    )

        if _has_error(diagnostics):
            return LoweringResult(plan=None, diagnostics=tuple(diagnostics))

        page_properties: dict[str, ValueExpr] = {}
        for name in catalogue.page_properties:
            if name not in project.page:
                continue
            prop = catalogue.page_properties[name]
            expr = _lower_value(catalogue, prop, project.page[name])
            diagnostics.extend(
                _check_expr(
                    expr,
                    project=project,
                    node_id=None,
                    path=("page", name),
                )
            )
            page_properties[name] = expr

        nodes: dict[NodeId, NodePlan] = {}
        for node in project.nodes.values():
            spec = catalogue.widget(node.type_id)
            properties: dict[str, ValueExpr] = {}
            for name in spec.properties:
                if name not in node.props:
                    continue
                expr = _lower_value(catalogue, spec.properties[name], node.props[name])
                diagnostics.extend(
                    _check_expr(
                        expr,
                        project=project,
                        node_id=node.id,
                        path=("nodes", node.id, "props", name),
                    )
                )
                properties[name] = expr
            if not is_allowlisted(spec.constructor.path):
                diagnostics.append(
                    _error(
                        CODE_SYMBOL_NOT_ALLOWLISTED,
                        "widget constructor is not in the catalogue allowlist: "
                        + ".".join(spec.constructor.path),
                        node_id=node.id,
                    )
                )
            nodes[node.id] = NodePlan(
                node_id=node.id,
                type_id=node.type_id,
                constructor=spec.constructor,
                properties=properties,
                slots={slot: tuple(ids) for slot, ids in node.slots.items()},
                events=dict(node.events),
                actions=dict(node.actions),
            )

        screens = tuple(
            PlannedScreen(root_id, meta.title, meta.route)
            for root_id, meta in screen_entries(project)
        )
        for screen in screens:
            if screen.root_id not in nodes:
                diagnostics.append(
                    _error(
                        "ENGINE_UNKNOWN_SCREEN_ROOT",
                        f"screen root {screen.root_id!r} is not in the plan",
                        path=("screens", screen.root_id),
                        node_id=screen.root_id,
                    )
                )

        if _has_error(diagnostics):
            return LoweringResult(plan=None, diagnostics=tuple(diagnostics))

        plan = ControlPlan(
            revision=snapshot.revision,
            document_sha256=document_sha256(project),
            target_flet=project.target_flet,
            catalogue_version=project.catalogue_version,
            page_properties=page_properties,
            root_ids=tuple(project.root_ids),
            nodes=nodes,
            assets=dict(project.assets),
            screens=screens,
            initial_route=project.initial_route,
        )
        return LoweringResult(plan=plan, diagnostics=tuple(diagnostics))


__all__ = [
    "ALLOWED_SYMBOL_PATHS",
    "CODE_ASSET_MISSING",
    "CODE_SYMBOL_NOT_ALLOWLISTED",
    "CODE_VERSION",
    "Lowering",
    "VALUE_CONSTRUCTOR_PATHS",
    "document_sha256",
    "is_allowlisted",
    "iter_asset_ids",
    "iter_symbols",
]
