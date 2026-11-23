"""Page-independent dialog controls.

``on_select`` receives a newly built Project. The caller owns dismissal and any
unsaved-changes confirmation; these builders never mutate or replace a workspace.
"""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from flet_visual_builder.contracts import Project
from flet_visual_builder.services.templates import TEMPLATES, Template
from flet_visual_builder.ui.theme import LG, MD, R_MD, SM, T, button, muted, pill, text

REPOSITORY_URL = "https://github.com/raffieeey/Flet-Visual-Builder"
VERSION = "0.2.0"
TARGET_FLET = "1.0.1"

# Kept in sync with ui.app._install_shortcuts without importing the app.
SHORTCUTS: tuple[tuple[str, str], ...] = (
    ("Ctrl/Cmd + Z", "Undo"),
    ("Ctrl/Cmd + Shift + Z", "Redo"),
    ("Ctrl/Cmd + Y", "Redo"),
    ("Ctrl/Cmd + S", "Save"),
    ("Ctrl/Cmd + O", "Open"),
    ("Ctrl/Cmd + D", "Duplicate selection"),
    ("Delete / Backspace", "Delete selection (except root)"),
    ("Escape", "Clear selection"),
)


def _template_card(
    template: Template, on_select: Callable[[Project], object]
) -> ft.Control:
    count = len(template.builder().nodes)

    def use_template(event: ft.ControlEvent) -> None:
        on_select(template.builder())

    return ft.Container(
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        text(template.name, weight=ft.FontWeight.W_600, expand=True),
                        pill(template.category),
                    ]
                ),
                muted(template.description),
                ft.Row(
                    controls=[
                        muted(f"{count} nodes", expand=True),
                        button("Use template", use_template, primary=True),
                    ]
                ),
            ],
            spacing=SM,
            tight=True,
        ),
        bgcolor=T.panel,
        border=ft.Border.all(1, T.border),
        border_radius=R_MD,
        padding=MD,
    )


def _choices_dialog(
    title: str, on_select: Callable[[Project], object], on_close: Callable[[], object]
) -> ft.AlertDialog:
    return ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.ListView(
            controls=[_template_card(template, on_select) for template in TEMPLATES],
            width=520,
            height=420,
            spacing=SM,
        ),
        actions=[ft.TextButton("Cancel", on_click=lambda event: on_close())],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def template_gallery_dialog(
    on_select: Callable[[Project], object], on_close: Callable[[], object]
) -> ft.AlertDialog:
    """Browse templates; selecting one supplies a fresh project to the caller."""
    return _choices_dialog("Template gallery", on_select, on_close)


def new_document_dialog(
    on_select: Callable[[Project], object], on_close: Callable[[], object]
) -> ft.AlertDialog:
    """Offer the same designed starting points for a new document."""
    return _choices_dialog("New document", on_select, on_close)


def about_dialog(on_close: Callable[[], object]) -> ft.AlertDialog:
    return ft.AlertDialog(
        title=ft.Text("About Flet Visual Builder"),
        content=ft.Column(
            controls=[
                text(f"Flet Visual Builder {VERSION}", weight=ft.FontWeight.W_600),
                muted(f"Target Flet {TARGET_FLET}"),
                ft.TextButton("View source repository", url=REPOSITORY_URL),
            ],
            spacing=MD,
            tight=True,
            width=400,
        ),
        actions=[ft.TextButton("Close", on_click=lambda event: on_close())],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def shortcuts_dialog(on_close: Callable[[], object]) -> ft.AlertDialog:
    return ft.AlertDialog(
        title=ft.Text("Keyboard shortcuts"),
        content=ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        text(keys, weight=ft.FontWeight.W_600, width=190),
                        muted(description, expand=True),
                    ]
                )
                for keys, description in SHORTCUTS
            ],
            spacing=LG,
            tight=True,
            scroll=ft.ScrollMode.AUTO,
            width=440,
            height=360,
        ),
        actions=[ft.TextButton("Close", on_click=lambda event: on_close())],
        actions_alignment=ft.MainAxisAlignment.END,
    )
