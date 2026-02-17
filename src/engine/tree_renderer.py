from __future__ import annotations

import flet as ft

from src.models.enum_map import ENUM_MAP
from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY, enum_key_for

FLET_CLASS_MAP = {
    "Text": ft.Text,
    "Container": ft.Container,
    "Column": ft.Column,
    "Row": ft.Row,
    "ElevatedButton": ft.ElevatedButton,
    "TextField": ft.TextField,
}


class TreeRenderer:
    def render(self, node: WidgetNode) -> ft.Control:
        cls = FLET_CLASS_MAP[node.type]
        props = {k: self._resolve_prop(node.type, k, v) for k, v in node.props.items()}
        control = cls(**props)

        if hasattr(control, "controls"):
            slot_children = [self.render(c) for c in node.children if (c.slot in ("controls", None))]
            if slot_children:
                control.controls = slot_children

        if hasattr(control, "content"):
            content_nodes = [c for c in node.children if c.slot == "content"]
            control.content = self.render(content_nodes[0]) if content_nodes else None

        return control

    def _resolve_prop(self, widget_type: str, prop: str, value):
        pdef = WIDGET_REGISTRY.get(widget_type, {}).get("props", {}).get(prop, {})
        if pdef.get("type") == "enum":
            enum_key = enum_key_for(widget_type, prop)
            if enum_key in ENUM_MAP and value in ENUM_MAP[enum_key]:
                mapped = ENUM_MAP[enum_key][value]
                return eval(mapped, {"ft": ft})
        return value
