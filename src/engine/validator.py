from __future__ import annotations

from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY


class ValidationError(ValueError):
    pass


def validate_tree(root: WidgetNode) -> None:
    """Validate the entire widget tree.  Raises ValidationError on first failure."""
    _validate_node(root)


def _validate_node(node: WidgetNode) -> None:
    if node.type not in WIDGET_REGISTRY:
        raise ValidationError(f"Unknown widget type: {node.type}")

    spec = WIDGET_REGISTRY[node.type]
    props = spec["props"]

    # --- property checks ---
    for key, value in node.props.items():
        if key not in props:
            raise ValidationError(f"Unknown property '{key}' on {node.type}")
        pdef = props[key]
        if pdef["type"] == "enum" and value is not None and value not in pdef["options"]:
            raise ValidationError(f"Invalid value '{value}' for {node.type}.{key}")

    # --- children / slot checks ---
    slots = spec["children"]
    declared_slot_names = {s["slot"] for s in slots}

    if not slots and node.children:
        raise ValidationError(f"{node.type} does not accept children")

    # Check each child is in a valid slot
    slot_counts: dict[str, int] = {}
    for child in node.children:
        child_slot = child.slot
        # If slot is None, try to infer the default (only valid if exactly one slot exists)
        if child_slot is None:
            if len(slots) == 1:
                child_slot = slots[0]["slot"]
            elif slots:
                raise ValidationError(
                    f"Child '{child.id}' under {node.type} has no slot assigned "
                    f"and parent has multiple slots: {declared_slot_names}"
                )

        if child_slot not in declared_slot_names:
            raise ValidationError(
                f"Child '{child.id}' assigned to slot '{child_slot}' "
                f"which is not declared on {node.type} "
                f"(valid slots: {declared_slot_names})"
            )
        slot_counts[child_slot] = slot_counts.get(child_slot, 0) + 1

    # Check max-children constraints per slot
    for slot_def in slots:
        slot_name = slot_def["slot"]
        max_children = slot_def["max"]
        count = slot_counts.get(slot_name, 0)
        if max_children is not None and count > max_children:
            raise ValidationError(
                f"{node.type}.{slot_name} allows {max_children} child, found {count}"
            )

    # Recurse
    for child in node.children:
        _validate_node(child)