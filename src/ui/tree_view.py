"""Tree View panel — hierarchical widget tree display."""
from __future__ import annotations

import flet as ft

from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY


def build_tree_view(
    root: WidgetNode,
    selected_id: str | None,
    on_select: callable,
) -> ft.Control:
    """Build a collapsible tree view of the widget hierarchy."""

    def _build_node(node: WidgetNode, depth: int = 0) -> ft.Control:
        is_selected = node.id == selected_id
        icon_name = WIDGET_REGISTRY.get(node.type, {}).get("icon", "widgets")
        has_children = bool(node.children)

        label = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        "expand_more" if has_children else "remove",
                        size=14, color="#9e9e9e",
                    ),
                    ft.Icon(icon_name, size=14, color="#616161"),
                    ft.Text(
                        node.type, size=12,
                        weight=ft.FontWeight.BOLD if is_selected else ft.FontWeight.NORMAL,
                        color="#1976d2" if is_selected else "#424242",
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.padding.only(left=depth * 16 + 4, top=3, bottom=3, right=4),
            bgcolor="#e3f2fd" if is_selected else None,
            border_radius=4,
            on_click=lambda e, nid=node.id: on_select(nid),
            ink=True,
        )

        items = [label]
        for child in node.children:
            items.append(_build_node(child, depth + 1))
        return ft.Column(controls=items, spacing=0)

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Tree", size=12, weight=ft.FontWeight.BOLD, color="#757575"),
                ft.Divider(height=1),
                _build_node(root),
            ],
            spacing=4,
            scroll=ft.ScrollMode.AUTO,
        ),
        padding=8,
        bgcolor="#fafafa",
        border=ft.border.only(top=ft.BorderSide(1, "#e0e0e0")),
    )