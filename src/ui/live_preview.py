"""Live Preview panel — renders real Flet controls from the widget tree."""
from __future__ import annotations

import flet as ft

from src.engine.tree_renderer import TreeRenderer
from src.models.widget_node import WidgetNode


_renderer = TreeRenderer()


def build_live_preview(root: WidgetNode, theme: str = "light") -> ft.Control:
    """Build the live preview panel rendering actual Flet widgets."""
    try:
        rendered = _renderer.render(root)
    except Exception as ex:
        rendered = ft.Text(f"Preview error: {ex}", color="red", size=12)

    # Phone frame
    phone_frame = ft.Container(
        content=ft.Container(
            content=rendered,
            padding=12,
            expand=True,
            bgcolor="#ffffff" if theme == "light" else "#121212",
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        ),
        width=320,
        height=568,
        border_radius=24,
        border=ft.border.all(3, "#424242"),
        bgcolor="#212121",
        padding=ft.padding.only(top=28, bottom=28, left=4, right=4),
        shadow=ft.BoxShadow(
            spread_radius=1, blur_radius=12,
            color="#00000033", offset=ft.Offset(0, 4),
        ),
        clip_behavior=ft.ClipBehavior.HARD_EDGE,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Live Preview", size=16, weight=ft.FontWeight.BOLD),
                    ],
                ),
                ft.Divider(height=1),
                ft.Container(
                    content=phone_frame,
                    alignment=ft.alignment.top_center,
                    expand=True,
                    padding=ft.padding.only(top=10),
                ),
            ],
            spacing=8,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        expand=True,
        padding=10,
        bgcolor="#f5f5f5",
    )