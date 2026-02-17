"""Widget Palette panel — displays available widgets grouped by category."""
from __future__ import annotations

import flet as ft

from src.models.widget_registry import WIDGET_REGISTRY


# Category colors for visual grouping
_CAT_COLORS = {
    "Basic": "#e3f2fd",
    "Input": "#f3e5f5",
    "Buttons": "#fff3e0",
    "Layout": "#e8f5e9",
}


def build_palette(on_add_widget: callable) -> ft.Control:
    """Build the widget palette panel.

    Args:
        on_add_widget: Called with (widget_type: str) when a tile is clicked.
    """
    # Group widgets by category
    categories: dict[str, list[tuple[str, dict]]] = {}
    for wtype, spec in WIDGET_REGISTRY.items():
        cat = spec["category"]
        categories.setdefault(cat, []).append((wtype, spec))

    sections: list[ft.Control] = []
    for cat, widgets in categories.items():
        tiles = []
        for wtype, spec in widgets:
            icon_name = spec.get("icon", "widgets")
            tile = ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Icon(icon_name, size=20, color="#424242"),
                        ft.Text(wtype, size=10, text_align=ft.TextAlign.CENTER,
                                color="#424242", no_wrap=True, max_lines=1),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=2,
                ),
                width=70,
                height=60,
                bgcolor=_CAT_COLORS.get(cat, "#f5f5f5"),
                border_radius=8,
                padding=ft.padding.all(4),
                alignment=ft.alignment.center,
                on_click=lambda e, wt=wtype: on_add_widget(wt),
                ink=True,
                tooltip=f"Add {wtype}",
            )
            tiles.append(tile)

        section = ft.Column(
            controls=[
                ft.Text(cat, size=11, weight=ft.FontWeight.BOLD, color="#757575"),
                ft.Row(controls=tiles, wrap=True, spacing=6, run_spacing=6),
            ],
            spacing=6,
        )
        sections.append(section)

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Text("Widgets", size=16, weight=ft.FontWeight.BOLD),
                ft.Divider(height=1),
                *sections,
            ],
            spacing=12,
            scroll=ft.ScrollMode.AUTO,
        ),
        width=200,
        padding=10,
        bgcolor="#fafafa",
        border=ft.border.only(right=ft.BorderSide(1, "#e0e0e0")),
    )