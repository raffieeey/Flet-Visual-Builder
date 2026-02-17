"""Properties panel — dynamic property editor for the selected widget."""
from __future__ import annotations

import flet as ft

from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY


def build_properties(
    node: WidgetNode | None,
    on_prop_change: callable,
) -> ft.Control:
    """Build the property editor panel for the given node.

    Args:
        node: The currently selected WidgetNode, or None.
        on_prop_change: Called with (prop_name, new_value) when a property changes.
    """
    if node is None:
        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("Properties", size=16, weight=ft.FontWeight.BOLD),
                    ft.Divider(height=1),
                    ft.Container(
                        content=ft.Text(
                            "Select a widget\nto edit properties",
                            text_align=ft.TextAlign.CENTER,
                            color="#9e9e9e", size=12,
                        ),
                        alignment=ft.alignment.center,
                        expand=True,
                    ),
                ],
                spacing=8,
                expand=True,
            ),
            width=260,
            padding=10,
            bgcolor="#fafafa",
            border=ft.border.only(left=ft.BorderSide(1, "#e0e0e0")),
        )

    spec = WIDGET_REGISTRY.get(node.type, {})
    props = spec.get("props", {})
    fields: list[ft.Control] = []

    # Node info header
    fields.append(
        ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text(node.type, size=14, weight=ft.FontWeight.BOLD),
                    ft.Text(f"ID: {node.id}", size=10, color="#9e9e9e"),
                ],
                spacing=2,
            ),
            bgcolor="#e8eaf6",
            border_radius=6,
            padding=8,
        )
    )

    for prop_name, prop_def in props.items():
        ptype = prop_def["type"]
        current_val = node.props.get(prop_name, prop_def["default"])

        if ptype == "str":
            field = ft.TextField(
                label=prop_name,
                value=str(current_val) if current_val is not None else "",
                dense=True,
                text_size=13,
                on_change=lambda e, pn=prop_name: on_prop_change(pn, e.control.value),
            )
        elif ptype == "float":
            field = ft.TextField(
                label=prop_name,
                value=str(current_val) if current_val is not None else "",
                dense=True,
                text_size=13,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=lambda e, pn=prop_name: _handle_float(e, pn, on_prop_change),
            )
        elif ptype == "padding":
            field = ft.TextField(
                label=f"{prop_name} (all sides)",
                value=str(current_val) if current_val is not None else "",
                dense=True,
                text_size=13,
                keyboard_type=ft.KeyboardType.NUMBER,
                on_change=lambda e, pn=prop_name: _handle_float(e, pn, on_prop_change),
            )
        elif ptype == "bool":
            field = ft.Row(
                controls=[
                    ft.Text(prop_name, size=13, expand=True),
                    ft.Switch(
                        value=bool(current_val) if current_val else False,
                        on_change=lambda e, pn=prop_name: on_prop_change(pn, e.control.value),
                    ),
                ],
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            )
        elif ptype == "enum":
            options = prop_def.get("options", [])
            field = ft.Dropdown(
                label=prop_name,
                value=current_val if current_val in options else options[0] if options else None,
                options=[ft.dropdown.Option(o) for o in options],
                dense=True,
                text_size=13,
                on_change=lambda e, pn=prop_name: on_prop_change(pn, e.control.value),
            )
        elif ptype == "color":
            field = ft.TextField(
                label=f"{prop_name} (hex)",
                value=str(current_val) if current_val else "",
                dense=True,
                text_size=13,
                hint_text="#FF0000 or red",
                on_change=lambda e, pn=prop_name: on_prop_change(pn, e.control.value or None),
            )
        elif ptype == "event":
            field = ft.TextField(
                label=f"{prop_name} (handler)",
                value=str(current_val) if current_val else "",
                dense=True,
                text_size=13,
                hint_text="function_name",
                on_change=lambda e, pn=prop_name: on_prop_change(pn, e.control.value or None),
            )
        else:
            continue

        fields.append(field)

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Properties", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(height=1),
                *fields,
            ],
            spacing=10,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        width=260,
        padding=10,
        bgcolor="#fafafa",
        border=ft.border.only(left=ft.BorderSide(1, "#e0e0e0")),
    )


def _handle_float(e, prop_name: str, on_prop_change: callable) -> None:
    """Parse float input, pass None for empty string."""
    val = e.control.value.strip()
    if not val:
        on_prop_change(prop_name, None)
        return
    try:
        on_prop_change(prop_name, float(val))
    except ValueError:
        pass  # ignore invalid input while typing