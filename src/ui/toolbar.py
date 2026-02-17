"""Toolbar — top action bar for the builder."""
from __future__ import annotations

import flet as ft

_TAB_VALUES = ["design", "preview", "code"]
_TAB_LABELS = ["Design", "Preview", "Code"]


def build_toolbar(
    project_name: str,
    on_undo: callable,
    on_redo: callable,
    on_save: callable,
    on_load: callable,
    on_tab_change: callable,
    current_tab: int,
    can_undo: bool,
    can_redo: bool,
) -> ft.Control:
    """Build the top toolbar."""

    def _handle_tab(e):
        selected = e.control.selected
        if selected:
            val = selected[0] if isinstance(selected, list) else list(selected)[0]
            idx = _TAB_VALUES.index(val) if val in _TAB_VALUES else 0
            on_tab_change(idx)

    return ft.Container(
        content=ft.Row(
            controls=[
                # Logo / project name
                ft.Row(
                    controls=[
                        ft.Icon("dashboard_customize", color="#1976d2", size=24),
                        ft.Text(
                            "FVB",
                            size=18,
                            weight=ft.FontWeight.BOLD,
                            color="#1976d2",
                        ),
                        ft.VerticalDivider(width=1),
                        ft.Text(project_name, size=14, color="#616161"),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                ft.Container(expand=True),
                # View switcher
                ft.SegmentedButton(
                    segments=[
                        ft.Segment(value=v, label=l)
                        for v, l in zip(_TAB_VALUES, _TAB_LABELS)
                    ],
                    selected=[_TAB_VALUES[current_tab]],
                    show_selected_icon=False,
                    on_change=_handle_tab,
                ),
                ft.Container(expand=True),
                # Actions
                ft.Row(
                    controls=[
                        ft.IconButton(
                            icon="undo", tooltip="Undo (Ctrl+Z)",
                            on_click=lambda e: on_undo(),
                            disabled=not can_undo,
                            icon_size=20,
                        ),
                        ft.IconButton(
                            icon="redo", tooltip="Redo (Ctrl+Y)",
                            on_click=lambda e: on_redo(),
                            disabled=not can_redo,
                            icon_size=20,
                        ),
                        ft.VerticalDivider(width=1),
                        ft.IconButton(
                            icon="folder_open", tooltip="Load project",
                            on_click=lambda e: on_load(),
                            icon_size=20,
                        ),
                        ft.IconButton(
                            icon="save", tooltip="Save project",
                            on_click=lambda e: on_save(),
                            icon_size=20,
                        ),
                    ],
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            ],
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        height=50,
        padding=ft.Padding(12, 0, 12, 0),
        bgcolor="#ffffff",
        border=ft.Border.only(bottom=ft.BorderSide(1, "#e0e0e0")),
    )