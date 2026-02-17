from __future__ import annotations

from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY


class ValidationError(ValueError):
    pass


def validate_tree(root: WidgetNode) -> None:
    _validate_node(root)


def _validate_node(node: WidgetNode) -> None:
    if node.type not in WIDGET_REGISTRY:
        raise ValidationError(f"Unknown widget type: {node.type}")

    spec = WIDGET_REGISTRY[node.type]
    props = spec["props"]

    for key, value in node.props.items():
        if key not in props:
            raise ValidationError(f"Unknown property '{key}' on {node.type}")
        pdef = props[key]
        if pdef["type"] == "enum" and value is not None and value not in pdef["options"]:
            raise ValidationError(f"Invalid value '{value}' for {node.type}.{key}")

    slots = spec["children"]
    if not slots and node.children:
        raise ValidationError(f"{node.type} does not accept children")

    slot_counts: dict[str | None, int] = {}
    for child in node.children:
        slot_counts[child.slot] = slot_counts.get(child.slot, 0) + 1

    for slot in slots:
        slot_name = slot["slot"]
        max_children = slot["max"]
        count = slot_counts.get(slot_name, 0)
        if max_children == 1 and count > 1:
            raise ValidationError(f"{node.type}.{slot_name} allows 1 child, found {count}")

    for child in node.children:
        _validate_node(child)
