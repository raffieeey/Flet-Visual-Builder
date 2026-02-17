from __future__ import annotations

import operator
from functools import reduce

import flet as ft

from src.models.enum_map import ENUM_MAP
from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY, enum_key_for
from src.utils.icons import resolve_icon

FLET_CLASS_MAP: dict[str, type] = {
    "Text": ft.Text,
    "Container": ft.Container,
    "Column": ft.Column,
    "Row": ft.Row,
    "ElevatedButton": ft.ElevatedButton,
    "TextField": ft.TextField,
}


def _resolve_flet_constant(dotted: str):
    """Safely resolve a string like 'ft.FontWeight.BOLD' to the real object.

    Only traverses attributes on the ``flet`` module — no eval().
    """
    parts = dotted.split(".")
    if not parts or parts[0] != "ft":
        raise ValueError(f"Cannot resolve non-ft constant: {dotted}")
    try:
        return reduce(getattr, parts[1:], ft)
    except AttributeError:
        raise ValueError(f"Unknown flet constant: {dotted}")


class TreeRenderer:
    """Convert a WidgetNode tree into real Flet controls."""

    def render(self, node: WidgetNode) -> ft.Control:
        cls = FLET_CLASS_MAP.get(node.type)
        if cls is None:
            raise ValueError(f"No Flet class mapped for widget type: {node.type}")

        # Resolve props — skip event props (they are handler name strings,
        # not meaningful for live preview).
        props: dict = {}
        for k, v in node.props.items():
            pdef = WIDGET_REGISTRY.get(node.type, {}).get("props", {}).get(k, {})
            if pdef.get("type") == "event":
                continue  # skip event handlers in preview
            props[k] = self._resolve_prop(node.type, k, v)

        control = cls(**props)

        # Apply children respecting slot definitions from the registry
        spec = WIDGET_REGISTRY.get(node.type, {})
        slots = spec.get("children", [])
        slot_map: dict[str, list[WidgetNode]] = {}
        for child in node.children:
            slot_map.setdefault(child.slot or "controls", []).append(child)

        for slot_def in slots:
            slot_name = slot_def["slot"]
            children = slot_map.get(slot_name, [])
            rendered = [self.render(c) for c in children]

            if slot_def["max"] == 1:
                setattr(control, slot_name, rendered[0] if rendered else None)
            else:
                setattr(control, slot_name, rendered)

        return control

    def _resolve_prop(self, widget_type: str, prop: str, value):
        """Map enum string values to real Flet constants."""
        pdef = WIDGET_REGISTRY.get(widget_type, {}).get("props", {}).get(prop, {})
        if pdef.get("type") == "enum" and isinstance(value, str):
            ek = enum_key_for(widget_type, prop)
            mapped = ENUM_MAP.get(ek, {}).get(value)
            if mapped:
                return _resolve_flet_constant(mapped)
        if (widget_type, prop) in {("Icon", "name"), ("IconButton", "icon"), ("ElevatedButton", "icon")}:
            return resolve_icon(value)

        return value
