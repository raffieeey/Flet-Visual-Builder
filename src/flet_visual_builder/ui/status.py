"""Bottom status bar: document state at a glance."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import T, faint, separator_dot, status_dot


class StatusBar(BasePanel):
    interests = frozenset(
        {
            Refresh.STATUS,
            Refresh.CHROME,
            Refresh.DOCUMENT,
            Refresh.PROJECT,
            Refresh.SELECTION,
        }
    )

    def build(self) -> ft.Control:
        ws = self.ws
        project = ws.project
        diagnostics = ws.diagnostics()
        errors = sum(1 for d in diagnostics if d.severity.value == "error")
        warnings = sum(1 for d in diagnostics if d.severity.value == "warning")
        if ws.session.dirty:
            state = "Draft"
        elif ws.session.path is None:
            state = "New"
        else:
            state = "Saved"

        right: list[ft.Control] = []
        if warnings:
            right.extend([faint(f"{warnings} warnings"), separator_dot()])
        right.extend(
            [
                status_dot(T.danger if errors else T.success),
                faint(f"{errors} errors" if errors else "No errors"),
            ]
        )

        return ft.Row(
            controls=[
                status_dot(T.warning if ws.session.dirty else T.success),
                faint(state),
                separator_dot(),
                faint(ws.session.location()),
                separator_dot(),
                faint(f"{len(project.nodes)} nodes"),
                separator_dot(),
                faint(f"selected: {ws.editor.selection or 'none'}"),
                ft.Container(expand=True),
                *right,
                separator_dot(),
                faint(f"Flet {project.target_flet}"),
            ],
            spacing=6,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
        )
