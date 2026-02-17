"""Code Preview panel — shows generated Flet Python code."""
from __future__ import annotations

import flet as ft

from src.engine.code_generator import generate_code
from src.engine.validator import ValidationError, validate_tree
from src.models.widget_node import WidgetNode


def build_code_preview(
    root: WidgetNode,
    on_copy: callable,
    on_export: callable,
) -> ft.Control:
    """Build the code preview panel."""
    # Validate first
    error_msg = None
    try:
        validate_tree(root)
    except ValidationError as ex:
        error_msg = str(ex)

    code = generate_code(root)

    error_banner = ft.Container(
        content=ft.Row(
            controls=[
                ft.Icon("warning_amber", color="#e65100", size=16),
                ft.Text(error_msg, size=11, color="#e65100", expand=True),
            ],
            spacing=6,
        ),
        bgcolor="#fff3e0",
        border_radius=6,
        padding=8,
    ) if error_msg else ft.Container(height=0)

    code_display = ft.TextField(
        value=code,
        multiline=True,
        read_only=True,
        min_lines=20,
        max_lines=50,
        text_size=12,
        text_style=ft.TextStyle(font_family="Courier New"),
        border_color="#e0e0e0",
        expand=True,
    )

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        ft.Text("Code", size=16, weight=ft.FontWeight.BOLD),
                        ft.Container(expand=True),
                        ft.ElevatedButton(
                            "Copy",
                            icon="content_copy",
                            on_click=lambda e: on_copy(code),
                            height=32,
                        ),
                        ft.ElevatedButton(
                            "Export .py",
                            icon="download",
                            on_click=lambda e: on_export(code),
                            height=32,
                            color="white",
                            bgcolor="#1976d2",
                        ),
                    ],
                    spacing=8,
                ),
                ft.Divider(height=1),
                error_banner,
                code_display,
            ],
            spacing=8,
            expand=True,
        ),
        expand=True,
        padding=10,
        bgcolor="#fafafa",
    )