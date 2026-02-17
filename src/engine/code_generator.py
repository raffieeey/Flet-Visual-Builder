from __future__ import annotations

from src.models.enum_map import ENUM_MAP
from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY, enum_key_for


def _format_value(enum_key: str | None, value):
    if value is None:
        return "None"
    if isinstance(value, str):
        if enum_key and enum_key in ENUM_MAP and value in ENUM_MAP[enum_key]:
            return ENUM_MAP[enum_key][value]
        return repr(value)
    if isinstance(value, bool):
        return "True" if value else "False"
    return str(value)


def _props_to_code(node: WidgetNode) -> list[str]:
    defaults = {k: v["default"] for k, v in WIDGET_REGISTRY[node.type]["props"].items()}
    pairs = []
    for key, value in node.props.items():
        if key in defaults and value == defaults[key]:
            continue
        enum_key = enum_key_for(node.type, key) if WIDGET_REGISTRY[node.type]["props"][key]["type"] == "enum" else None
        pairs.append(f"{key}={_format_value(enum_key, value)}")
    return pairs


def _render_node(node: WidgetNode, indent: int = 2) -> str:
    space = " " * (indent * 4)
    child_space = " " * ((indent + 1) * 4)
    props = _props_to_code(node)

    slots = WIDGET_REGISTRY[node.type]["children"]
    slot_map: dict[str, list[WidgetNode]] = {}
    for child in node.children:
        slot_map.setdefault(child.slot or "controls", []).append(child)

    for slot in slots:
        name = slot["slot"]
        children = slot_map.get(name, [])
        if slot["max"] == 1:
            if children:
                props.append(f"{name}={_render_node(children[0], indent + 1).strip()}")
        else:
            if children:
                rendered = ",\n".join(_render_node(c, indent + 2) for c in children)
                props.append(f"{name}=[\n{rendered}\n{child_space}]")

    if not props:
        return f"{space}ft.{node.type}()"
    joined = f",\n{child_space}".join(props)
    return f"{space}ft.{node.type}(\n{child_space}{joined}\n{space})"


def generate_code(root: WidgetNode) -> str:
    handlers = sorted({v for n in _walk(root) for k, v in n.props.items() if k.startswith("on_") and isinstance(v, str) and v})

    lines = [
        "import flet as ft",
        "",
        "def main(page: ft.Page):",
        '    page.title = "My App"',
        "    page.theme_mode = ft.ThemeMode.LIGHT",
        "",
        "    page.add(",
        _render_node(root, indent=2),
        "    )",
        "",
    ]

    for name in handlers:
        lines.extend([f"def {name}(e: ft.ControlEvent):", "    pass", ""])

    lines.extend(["ft.app(target=main)"])
    return "\n".join(lines)


def _walk(node: WidgetNode):
    yield node
    for c in node.children:
        yield from _walk(c)
