"""Properties panel — dynamic property editor for the selected widget."""
from __future__ import annotations

import flet as ft
from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY


def _handle_float(e, prop_name: str, on_prop_change) -> None:
    val = e.control.value.strip()
    if not val:
        on_prop_change(prop_name, None)
        return
    try:
        on_prop_change(prop_name, float(val))
    except ValueError:
        pass


def build_properties(node: WidgetNode | None, on_prop_change) -> ft.Control:
    if node is None:
        return ft.Container(
            content=ft.Column(controls=[
                ft.Text("Properties", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(height=1),
                ft.Container(
                    content=ft.Text("Select a widget\nto edit properties",
                                    text_align=ft.TextAlign.CENTER, color="#9e9e9e", size=12),
                    alignment=ft.Alignment.CENTER, expand=True,
                ),
            ], spacing=8, expand=True),
            width=260, padding=10, bgcolor="#fafafa",
            border=ft.Border.only(left=ft.BorderSide(1, "#e0e0e0")),
        )

    spec = WIDGET_REGISTRY.get(node.type, {})
    props_spec = spec.get("props", {})
    fields: list[ft.Control] = [
        ft.Container(
            content=ft.Column(controls=[
                ft.Text(node.type, size=14, weight=ft.FontWeight.BOLD),
                ft.Text(f"ID: {node.id}", size=10, color="#9e9e9e"),
            ], spacing=2),
            bgcolor="#e8eaf6", border_radius=6, padding=8,
        )
    ]

    for pname, pdef in props_spec.items():
        ptype = pdef["type"]
        cur = node.props.get(pname, pdef["default"])

        if ptype == "str":
            fields.append(ft.TextField(
                label=pname, value=str(cur) if cur is not None else "",
                dense=True, text_size=13,
                on_change=lambda e, pn=pname: on_prop_change(pn, e.control.value),
            ))
        elif ptype in ("float", "padding"):
            lbl = f"{pname} (all sides)" if ptype == "padding" else pname
            fields.append(ft.TextField(
                label=lbl, value=str(cur) if cur is not None else "",
                dense=True, text_size=13, keyboard_type=ft.KeyboardType.NUMBER,
                on_change=lambda e, pn=pname: _handle_float(e, pn, on_prop_change),
            ))
        elif ptype == "bool":
            fields.append(ft.Row(controls=[
                ft.Text(pname, size=13, expand=True),
                ft.Switch(value=bool(cur) if cur else False,
                          on_change=lambda e, pn=pname: on_prop_change(pn, e.control.value)),
            ], vertical_alignment=ft.CrossAxisAlignment.CENTER))
        elif ptype == "enum":
            opts = pdef.get("options", [])
            fields.append(ft.Dropdown(
                label=pname,
                value=cur if cur in opts else (opts[0] if opts else None),
                options=[ft.dropdown.Option(o) for o in opts],
                dense=True, text_size=13,
                on_select=lambda e, pn=pname: on_prop_change(pn, e.control.value),
            ))
        elif ptype == "color":
            fields.append(ft.TextField(
                label=f"{pname} (hex)", value=str(cur) if cur else "",
                dense=True, text_size=13, hint_text="#FF0000 or red",
                on_change=lambda e, pn=pname: on_prop_change(pn, e.control.value or None),
            ))
        elif ptype == "event":
            fields.append(ft.TextField(
                label=f"{pname} (handler)", value=str(cur) if cur else "",
                dense=True, text_size=13, hint_text="function_name",
                on_change=lambda e, pn=pname: on_prop_change(pn, e.control.value or None),
            ))

    return ft.Container(
        content=ft.Column(controls=[
            ft.Text("Properties", size=16, weight=ft.FontWeight.BOLD),
            ft.Divider(height=1), *fields,
        ], spacing=10, scroll=ft.ScrollMode.AUTO, expand=True),
        width=260, padding=10, bgcolor="#fafafa",
        border=ft.Border.only(left=ft.BorderSide(1, "#e0e0e0")),
    )