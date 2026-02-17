from __future__ import annotations

from src.models.enum_map import ENUM_MAP
from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY, enum_key_for


def _is_event_prop(widget_type: str, key: str) -> bool:
    """Check if a property is an event handler."""
    pdef = WIDGET_REGISTRY.get(widget_type, {}).get("props", {}).get(key, {})
    return pdef.get("type") == "event"


def _format_value(enum_key: str | None, value):
    """Format a property value for code output."""
    if value is None:
        return "None"
    # bool MUST be checked before int (True/False are instances of int)
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, str):
        if enum_key and enum_key in ENUM_MAP and value in ENUM_MAP[enum_key]:
            return ENUM_MAP[enum_key][value]
        return repr(value)
    if isinstance(value, (int, float)):
        return str(value)
    return repr(value)


def _props_to_code(node: WidgetNode) -> list[str]:
    """Build list of 'key=value' strings for non-default properties."""
    spec = WIDGET_REGISTRY[node.type]
    defaults = {k: v["default"] for k, v in spec["props"].items()}
    pairs: list[str] = []

    for key, value in node.props.items():
        if key not in spec["props"]:
            continue
        # Skip values that match the default
        if key in defaults and value == defaults[key]:
            continue

        pdef = spec["props"][key]

        # Event handlers: render as bare function names, not strings
        if pdef["type"] == "event":
            if value:
                pairs.append(f"{key}={value}")
            continue

        enum_key = (
            enum_key_for(node.type, key)
            if pdef["type"] == "enum"
            else None
        )
        pairs.append(f"{key}={_format_value(enum_key, value)}")

    return pairs


def _render_node(node: WidgetNode, indent: int = 2) -> str:
    """Recursively render a node as Flet constructor code."""
    space = " " * (indent * 4)
    child_space = " " * ((indent + 1) * 4)
    props = _props_to_code(node)

    # Build children grouped by slot
    slots = WIDGET_REGISTRY[node.type]["children"]
    slot_map: dict[str, list[WidgetNode]] = {}
    for child in node.children:
        slot_map.setdefault(child.slot or "controls", []).append(child)

    for slot in slots:
        name = slot["slot"]
        children = slot_map.get(name, [])
        if slot["max"] == 1:
            if children:
                props.append(
                    f"{name}={_render_node(children[0], indent + 1).strip()}"
                )
        else:
            if children:
                rendered = ",\n".join(
                    _render_node(c, indent + 2) for c in children
                )
                props.append(f"{name}=[\n{rendered}\n{child_space}]")

    if not props:
        return f"{space}ft.{node.type}()"
    joined = f",\n{child_space}".join(props)
    return f"{space}ft.{node.type}(\n{child_space}{joined}\n{space})"


def generate_code(root: WidgetNode) -> str:
    """Generate a complete runnable Flet script from a widget tree."""
    # Collect unique event handler names
    handlers = sorted(
        {
            v
            for n in _walk(root)
            for k, v in n.props.items()
            if _is_event_prop(n.type, k) and isinstance(v, str) and v
        }
    )

    # Handler stubs must be defined BEFORE main() so the names are in scope
    # when page.add() builds the control tree.
    lines: list[str] = [
        "import flet as ft",
        "",
    ]

    for name in handlers:
        lines.extend([f"def {name}(e: ft.ControlEvent):", "    pass", ""])

    lines.extend([
        "def main(page: ft.Page):",
        '    page.title = "My App"',
        "    page.theme_mode = ft.ThemeMode.LIGHT",
        "",
        "    page.add(",
        _render_node(root, indent=2),
        "    )",
        "",
        "",
        "ft.app(target=main)",
    ])

    return "\n".join(lines)


def _walk(node: WidgetNode):
    """Yield all nodes in the tree (depth-first)."""
    yield node
    for c in node.children:
        yield from _walk(c)