"""Legacy v0.0/v0.1 → v2 adapters. No Flet imports. Never overwrite input."""

from __future__ import annotations

import copy
import keyword
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.catalogue.enum_manifest import ENUM_FAMILIES, ICONS
from flet_visual_builder.contracts import Diagnostic, Severity
from flet_visual_builder.model.validation import event_symbol_name

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_CAMEL = re.compile(r"([a-z0-9])([A-Z])")
_LETTER_DIGIT = re.compile(r"([A-Za-z])(\d)")

TYPE_ALIASES: dict[str, str] = {
    "ElevatedButton": "Button",
}

# Applied after type aliasing.
PROP_ALIASES: dict[tuple[str, str], str] = {
    ("Button", "text"): "content",
    ("Icon", "name"): "icon",
    ("Card", "color"): "bgcolor",
}

EVENT_PROP_NAMES: frozenset[str] = frozenset({"on_click", "on_change"})

SUPPORTED_SCHEMA_VERSION = 3
SUPPORTED_CATALOGUE_VERSION = 1
SUPPORTED_TARGET_FLET = "1.0.1"


@dataclass(frozen=True, slots=True)
class EditorHints:
    device_frame: str | None = None
    selected_node_id: str | None = None


@dataclass(frozen=True, slots=True)
class MigrationOutcome:
    document: dict[str, Any] | None
    diagnostics: tuple[Diagnostic, ...]
    editor_hints: EditorHints | None
    source_version: str | int | None


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    node_id: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
        node_id=node_id,
    )


def canonicalize_enum(value: str, members: frozenset[str]) -> str | None:
    if value in members:
        return value
    camel = _CAMEL.sub(r"\1_\2", value)
    upper = camel.upper()
    if upper in members:
        return upper
    split = _LETTER_DIGIT.sub(r"\1_\2", upper)
    if split in members:
        return split
    return None


def canonicalize_icon(value: str) -> str:
    if value in ICONS:
        return value
    upper = value.upper()
    if upper in ICONS:
        return upper
    snake = value.replace("-", "_").upper()
    if snake in ICONS:
        return snake
    return value


def migrate_0_0_to_0_1(data: Mapping[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(dict(data))
    out["schema_version"] = "0.1"
    out.setdefault("theme", "light")
    out.setdefault("device_frame", "desktop")
    return out


def migrate_to_v2(data: Mapping[str, Any]) -> MigrationOutcome:
    """Chain 0.0 → 0.1 → 2. Does not mutate ``data``."""
    raw = dict(data)
    working = copy.deepcopy(raw)
    if "schema_version" not in raw or raw.get("schema_version") == "0.0":
        source: str | int | None = "0.0"
        working = migrate_0_0_to_0_1(working)
        version = "0.1"
    else:
        source = raw.get("schema_version")
        version = source
    if version != "0.1":
        return MigrationOutcome(
            document=None,
            diagnostics=(
                _error(
                    "schema.unsupported",
                    f"Unrecognized schema_version {version!r}",
                    path=("schema_version",),
                ),
            ),
            editor_hints=None,
            source_version=source if isinstance(source, (str, int)) else None,
        )
    document, diags, hints = _migrate_0_1_to_v2(working)
    return MigrationOutcome(
        document=document,
        diagnostics=diags,
        editor_hints=hints,
        source_version=source if isinstance(source, (str, int)) else "0.1",
    )


def _migrate_0_1_to_v2(
    data: dict[str, Any],
) -> tuple[dict[str, Any] | None, tuple[Diagnostic, ...], EditorHints | None]:
    errors: list[Diagnostic] = []
    tree = data.get("tree")
    if not isinstance(tree, dict):
        errors.append(
            _error(
                "migration.tree",
                "Legacy document is missing a tree object",
                path=("tree",),
            )
        )
        return None, tuple(errors), None

    name = data.get("name")
    if not isinstance(name, str):
        errors.append(
            _error(
                "migration.name",
                "Legacy document name must be a string",
                path=("name",),
            )
        )
        name = ""

    hints = EditorHints(
        device_frame=(
            data["device_frame"] if isinstance(data.get("device_frame"), str) else None
        ),
        selected_node_id=(
            data["selected_node_id"]
            if isinstance(data.get("selected_node_id"), str)
            else None
        ),
    )

    page: dict[str, Any] = {}
    theme = data.get("theme")
    if isinstance(theme, str):
        converted = canonicalize_enum(theme, ENUM_FAMILIES["ThemeMode"])
        if converted is None:
            errors.append(
                _error(
                    "migration.theme",
                    f"Legacy theme {theme!r} is not a ThemeMode member",
                    path=("theme",),
                )
            )
        else:
            page["theme_mode"] = converted

    parsed, parse_errors = _parse_legacy_node(tree, ("tree",))
    errors.extend(parse_errors)
    if parsed is None:
        return None, tuple(errors), hints

    nodes_v2, flatten_errors = _flatten_tree(parsed)
    errors.extend(flatten_errors)
    if errors:
        return None, tuple(errors), hints

    document: dict[str, Any] = {
        "name": name,
        "page": page,
        "root_ids": [parsed.id],
        "nodes": nodes_v2,
        "assets": {},
        "screens": {},
        "initial_route": "/",
        "schema_version": SUPPORTED_SCHEMA_VERSION,
        "catalogue_version": SUPPORTED_CATALOGUE_VERSION,
        "target_flet": SUPPORTED_TARGET_FLET,
    }
    return document, (), hints


@dataclass
class _LegacyNode:
    id: str
    type: str
    props: dict[str, Any]
    children: list[_LegacyNode]
    parent_id: Any
    order: Any
    slot: Any
    path: tuple[str | int, ...]


def _parse_legacy_node(
    raw: object, path: tuple[str | int, ...]
) -> tuple[_LegacyNode | None, list[Diagnostic]]:
    errors: list[Diagnostic] = []
    if not isinstance(raw, dict):
        errors.append(
            _error(
                "migration.tree",
                "Legacy node must be an object",
                path=path,
            )
        )
        return None, errors
    node_id = raw.get("id")
    if not isinstance(node_id, str) or not node_id:
        errors.append(
            _error(
                "migration.id",
                "Legacy node id must be a non-empty string",
                path=path + ("id",),
            )
        )
        return None, errors
    type_name = raw.get("type")
    if not isinstance(type_name, str) or not type_name:
        errors.append(
            _error(
                "migration.type",
                f"Legacy node {node_id!r} is missing a type",
                path=path + ("type",),
                node_id=node_id,
            )
        )
        return None, errors
    props = raw.get("props", {})
    if props is None:
        props = {}
    if not isinstance(props, dict):
        errors.append(
            _error(
                "migration.props",
                f"Legacy node {node_id!r} props must be an object",
                path=path + ("props",),
                node_id=node_id,
            )
        )
        return None, errors
    children_raw = raw.get("children", [])
    if children_raw is None:
        children_raw = []
    if not isinstance(children_raw, list):
        errors.append(
            _error(
                "migration.children",
                f"Legacy node {node_id!r} children must be an array",
                path=path + ("children",),
                node_id=node_id,
            )
        )
        return None, errors
    children: list[_LegacyNode] = []
    for index, child_raw in enumerate(children_raw):
        child, child_errors = _parse_legacy_node(child_raw, path + ("children", index))
        errors.extend(child_errors)
        if child is not None:
            children.append(child)
    if errors:
        return None, errors
    return (
        _LegacyNode(
            id=node_id,
            type=type_name,
            props=dict(props),
            children=children,
            parent_id=raw.get("parent_id"),
            order=raw.get("order"),
            slot=raw.get("slot"),
            path=path,
        ),
        errors,
    )


def _alias_type(type_name: str) -> str:
    return TYPE_ALIASES.get(type_name, type_name)


def _slot_names(type_id: str) -> tuple[str, ...] | None:
    spec = catalogue.widgets.get(type_id)
    if spec is None:
        return None
    return tuple(spec.slots)


def _infer_slot(parent_type: str) -> str | None:
    names = _slot_names(parent_type)
    if names is None:
        return None
    if len(names) == 1:
        return names[0]
    return None


def _flatten_tree(
    root: _LegacyNode,
) -> tuple[dict[str, Any], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    nodes: dict[str, Any] = {}

    if root.parent_id not in (None,):
        errors.append(
            _error(
                "migration.ambiguous_ownership",
                (
                    f"Root node {root.id!r} has parent_id {root.parent_id!r}; "
                    "expected null"
                ),
                path=root.path + ("parent_id",),
                node_id=root.id,
            )
        )
    if root.slot not in (None,):
        errors.append(
            _error(
                "migration.ambiguous_ownership",
                (f"Root node {root.id!r} has slot {root.slot!r}; " "expected null"),
                path=root.path + ("slot",),
                node_id=root.id,
            )
        )

    def visit(node: _LegacyNode, parent: _LegacyNode | None) -> None:
        if node.id in nodes:
            errors.append(
                _error(
                    "migration.duplicate_id",
                    f"Duplicate legacy node id {node.id!r}",
                    path=node.path + ("id",),
                    node_id=node.id,
                )
            )
            return
        type_id = _alias_type(node.type)
        if type_id not in catalogue.widgets:
            errors.append(
                _error(
                    "migration.unknown_type",
                    f"Legacy type {node.type!r} is not in catalogue version 1",
                    path=node.path + ("type",),
                    node_id=node.id,
                )
            )
            return
        if parent is not None:
            if node.parent_id not in (None,) and node.parent_id != parent.id:
                errors.append(
                    _error(
                        "migration.ambiguous_ownership",
                        (
                            f"Node {node.id!r} parent_id {node.parent_id!r} "
                            f"conflicts with nesting parent {parent.id!r}"
                        ),
                        path=node.path + ("parent_id",),
                        node_id=node.id,
                    )
                )

        props, events, prop_errors = _convert_props(type_id, node.id, node.props)
        errors.extend(prop_errors)

        slot_map, slot_errors = _assign_child_slots(node, type_id)
        errors.extend(slot_errors)

        nodes[node.id] = {
            "id": node.id,
            "type_id": type_id,
            "props": props,
            "slots": slot_map,
            "events": events,
        }
        for child in node.children:
            visit(child, node)

    visit(root, None)
    return nodes, errors


def _assign_child_slots(
    parent: _LegacyNode, parent_type: str
) -> tuple[dict[str, list[str]], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    declared = _slot_names(parent_type)
    if declared is None:
        return {}, errors
    slot_map: dict[str, list[str]] = {name: [] for name in declared}
    if not parent.children:
        return slot_map, errors

    grouped: dict[str, list[tuple[int, Any, str, _LegacyNode]]] = {}
    for index, child in enumerate(parent.children):
        slot = child.slot
        if slot is None:
            inferred = _infer_slot(parent_type)
            if inferred is None:
                errors.append(
                    _error(
                        "migration.ambiguous_ownership",
                        (
                            f"Node {child.id!r} is missing slot and "
                            f"{parent_type} does not have exactly one "
                            "destination slot"
                        ),
                        path=child.path + ("slot",),
                        node_id=child.id,
                    )
                )
                continue
            slot = inferred
        elif not isinstance(slot, str):
            errors.append(
                _error(
                    "migration.ambiguous_ownership",
                    f"Node {child.id!r} slot {slot!r} is not a string",
                    path=child.path + ("slot",),
                    node_id=child.id,
                )
            )
            continue
        elif slot not in declared:
            errors.append(
                _error(
                    "migration.ambiguous_ownership",
                    (
                        f"Node {child.id!r} slot {slot!r} is not a valid "
                        f"destination on {parent_type}"
                    ),
                    path=child.path + ("slot",),
                    node_id=child.id,
                )
            )
            continue
        grouped.setdefault(slot, []).append((index, child.order, child.id, child))

    for slot, items in grouped.items():
        orders = [order for _, order, _, _ in items]
        if all(order is None for order in orders):
            slot_map[slot] = [cid for _, _, cid, _ in items]
            continue
        if any(order is None for order in orders):
            errors.append(
                _error(
                    "migration.ambiguous_ownership",
                    (
                        f"Slot {slot!r} on {parent.id} mixes missing and "
                        "explicit order values"
                    ),
                    path=parent.path + ("children",),
                    node_id=parent.id,
                )
            )
            continue
        if not all(
            isinstance(order, int) and not isinstance(order, bool) for order in orders
        ):
            errors.append(
                _error(
                    "migration.ambiguous_ownership",
                    f"Slot {slot!r} on {parent.id} has a non-integer order",
                    path=parent.path + ("children",),
                    node_id=parent.id,
                )
            )
            continue
        if len(set(orders)) != len(orders):
            errors.append(
                _error(
                    "migration.ambiguous_ownership",
                    (f"Slot {slot!r} on {parent.id} has duplicate order " "values"),
                    path=parent.path + ("children",),
                    node_id=parent.id,
                )
            )
            continue
        by_order = [cid for _, _, cid, _ in sorted(items, key=lambda row: row[1])]
        by_array = [cid for _, _, cid, _ in items]
        if by_order != by_array:
            errors.append(
                _error(
                    "migration.ambiguous_ownership",
                    (
                        f"Slot {slot!r} on {parent.id}: explicit order "
                        "conflicts with children array order"
                    ),
                    path=parent.path + ("children",),
                    node_id=parent.id,
                )
            )
            continue
        slot_map[slot] = by_array
    return slot_map, errors


def _convert_props(
    type_id: str, node_id: str, props: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, Any], list[Diagnostic]]:
    errors: list[Diagnostic] = []
    working = dict(props)
    for (alias_type, old), new in PROP_ALIASES.items():
        if alias_type != type_id or old not in working:
            continue
        if new in working and working[new] != working[old]:
            errors.append(
                _error(
                    "migration.prop_conflict",
                    (
                        f"Node {node_id!r} has conflicting {old!r} and "
                        f"{new!r} properties"
                    ),
                    path=("nodes", node_id, "props", old),
                    node_id=node_id,
                )
            )
            working.pop(old)
            continue
        working[new] = working.pop(old)

    events: dict[str, Any] = {}
    spec = catalogue.widgets.get(type_id)
    for key in list(working):
        if key not in EVENT_PROP_NAMES:
            continue
        raw = working.pop(key)
        if raw is None:
            continue
        if not isinstance(raw, str) or IDENT.fullmatch(raw) is None:
            errors.append(
                _error(
                    "migration.event",
                    (
                        f"Event property {key!r} on {node_id} contains "
                        "non-identifier / executable text; refusing migration"
                    ),
                    path=("nodes", node_id, "props", key),
                    node_id=node_id,
                )
            )
            continue
        if spec is not None and key not in spec.events:
            errors.append(
                _error(
                    "migration.event",
                    f"Event {key!r} is not allowed on {type_id}",
                    path=("nodes", node_id, "events", key),
                    node_id=node_id,
                )
            )
            continue
        symbol_name = event_symbol_name(node_id, key)
        if (
            IDENT.fullmatch(symbol_name) is None
            or keyword.iskeyword(symbol_name)
            or not symbol_name.startswith("handle_")
        ):
            errors.append(
                _error(
                    "migration.event",
                    (
                        f"Canonical event symbol {symbol_name!r} is not a "
                        "valid EventSymbol"
                    ),
                    path=("nodes", node_id, "events", key),
                    node_id=node_id,
                )
            )
            continue
        events[key] = {"name": symbol_name}

    converted: dict[str, Any] = {}
    for key, value in working.items():
        if spec is not None and key in spec.properties:
            prop = spec.properties[key]
            if (
                prop.codec_id == "enum.ScrollMode"
                and isinstance(value, str)
                and value.lower() == "none"
            ):
                continue
            if prop.codec_id.startswith("enum.") and isinstance(value, str):
                family = prop.codec_id.split(".", 1)[1]
                members = ENUM_FAMILIES.get(family)
                if members is not None:
                    canon = canonicalize_enum(value, members)
                    if canon is None:
                        errors.append(
                            _error(
                                "migration.enum",
                                (
                                    f"Property {key!r} on {node_id} has "
                                    f"unrecognized enum value {value!r}"
                                ),
                                path=("nodes", node_id, "props", key),
                                node_id=node_id,
                            )
                        )
                        converted[key] = value
                        continue
                    converted[key] = canon
                    continue
            if prop.codec_id == "icon" and isinstance(value, str):
                converted[key] = canonicalize_icon(value)
                continue
        converted[key] = value
    return converted, events, errors
