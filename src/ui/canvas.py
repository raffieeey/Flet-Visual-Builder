"""Canvas panel — interactive tree-based design surface."""
from __future__ import annotations

import flet as ft

from src.models.widget_node import WidgetNode
from src.models.widget_registry import WIDGET_REGISTRY, accepts_children


# Nesting depth colors
_DEPTH_COLORS = [
    "#e3f2fd", "#bbdefb", "#90caf9", "#64b5f6",
    "#42a5f5", "#2196f3", "#1e88e5", "#1976d2",
]


def _label_for(node: WidgetNode) -> str:
    """Build a short display label for a node."""
    spec = WIDGET_REGISTRY.get(node.type, {})
    props = node.props
    # Pick the most descriptive prop to show
    if node.type == "Text":
        val = props.get("value", "")
        return f'Text: "{val[:20]}"' if val else "Text"
    if node.type in ("ElevatedButton", "IconButton"):
        return f'{node.type}: "{props.get("text", props.get("icon", ""))}"'
    if node.type == "TextField":
        return f'TextField: "{props.get("label", "")}"'
    if node.type in ("Checkbox", "Switch"):
        return f'{node.type}: "{props.get("label", "")}"'
    return node.type


def build_canvas(
    root: WidgetNode,
    selected_id: str | None,
    on_select: callable,
    on_delete: callable,
    on_move_up: callable,
    on_move_down: callable,
    on_wrap: callable,
) -> ft.Control:
    """Build the canvas panel showing widget tree as interactive blocks."""

    def _render_block(node: WidgetNode, depth: int = 0) -> ft.Control:
        is_selected = node.id == selected_id
        is_layout = accepts_children(node.type)
        color = _DEPTH_COLORS[min(depth, len(_DEPTH_COLORS) - 1)]
        icon_name = WIDGET_REGISTRY.get(node.type, {}).get("icon", "widgets")

        # Build children blocks
        child_controls = []
        if node.children:
            for child in node.children:
                child_controls.append(_render_block(child, depth + 1))

        # Empty drop zone indicator for layout widgets with no children
        if is_layout and not node.children:
            child_controls.append(
                ft.Container(
                    content=ft.Text(
                        "Drop widgets here", size=11,
                        color="#9e9e9e", italic=True,
                        text_align=ft.TextAlign.CENTER,
                    ),
                    height=40,
                    border=ft.border.all(1, "#e0e0e0"),
                    border_radius=4,
                    bgcolor="#fafafa",
                    alignment=ft.alignment.center,
                    padding=4,
                )
            )

        # The node block itself
        header = ft.Row(
            controls=[
                ft.Icon(icon_name, size=14, color="#616161"),
                ft.Text(
                    _label_for(node), size=12,
                    weight=ft.FontWeight.BOLD if is_layout else ft.FontWeight.NORMAL,
                    color="#212121",
                    expand=True,
                    no_wrap=True,
                    max_lines=1,
                ),
                ft.Text(
                    node.id.split("-")[-1] if "-" in node.id else node.id,
                    size=9, color="#9e9e9e",
                ),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )

        children_col = ft.Column(
            controls=child_controls,
            spacing=4,
        ) if child_controls else None

        block_content = ft.Column(
            controls=[header] + ([children_col] if children_col else []),
            spacing=6,
        )

        return ft.Container(
            content=block_content,
            padding=ft.padding.only(left=10, right=8, top=6, bottom=6),
            bgcolor=color if not is_selected else "#fff9c4",
            border=ft.border.all(
                2 if is_selected else 1,
                "#f57f17" if is_selected else "#bdbdbd",
            ),
            border_radius=6,
            on_click=lambda e, nid=node.id: on_select(nid),
            animate=ft.Animation(150, ft.AnimationCurve.EASE_OUT),
        )

    # Build the canvas
    tree_view = _render_block(root)

    # Action bar for selected node
    action_bar = ft.Row(
        controls=[
            ft.IconButton(
                icon="arrow_upward", icon_size=18, tooltip="Move up",
                on_click=lambda e: on_move_up(),
            ),
            ft.IconButton(
                icon="arrow_downward", icon_size=18, tooltip="Move down",
                on_click=lambda e: on_move_down(),
            ),
            ft.IconButton(
                icon="crop_square", icon_size=18, tooltip="Wrap in Container",
                on_click=lambda e: on_wrap("Container"),
            ),
            ft.IconButton(
                icon="view_agenda", icon_size=18, tooltip="Wrap in Column",
                on_click=lambda e: on_wrap("Column"),
            ),
            ft.IconButton(
                icon="view_week", icon_size=18, tooltip="Wrap in Row",
                on_click=lambda e: on_wrap("Row"),
            ),
            ft.IconButton(
                icon="delete_outline", icon_size=18, tooltip="Delete",
                icon_color="#d32f2f",
                on_click=lambda e: on_delete(),
            ),
        ],
        spacing=0,
        alignment=ft.MainAxisAlignment.CENTER,
    ) if selected_id and selected_id != root.id else ft.Container()

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Canvas", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.Text("Click a widget to select", size=11, color="#9e9e9e"),
                    ],
                ),
                ft.Divider(height=1),
                action_bar,
                ft.Container(
                    content=tree_view,
                    expand=True,
                    padding=8,
                ),
            ],
            spacing=8,
            scroll=ft.ScrollMode.AUTO,
            expand=True,
        ),
        expand=True,
        padding=10,
        bgcolor="#ffffff",
    )