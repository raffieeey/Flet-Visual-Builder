"""Diagnostics drawer: validation and rendering problems, in order."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, MD, T, faint, pill, text


class DiagnosticsView(BasePanel):
    interests = frozenset({Refresh.DOCUMENT, Refresh.PROJECT})

    def build(self) -> ft.Control:
        diagnostics = self.ws.diagnostics()
        if not diagnostics:
            self.control.height = 0
            self.control.visible = False
            return ft.Container(height=0)
        self.control.height = None
        self.control.visible = True
        rows: list[ft.Control] = []
        for item in diagnostics[:8]:
            color = {
                "error": (T.danger, T.danger_soft),
                "warning": (T.warning, "#FFF6E5"),
                "info": (T.text_muted, T.border_soft),
            }.get(item.severity.value, (T.text_muted, T.border_soft))
            rows.append(
                ft.Row(
                    controls=[
                        pill(item.severity.value, color=color[0], bgcolor=color[1]),
                        text(item.message, size=F_BODY),
                        ft.Container(expand=True),
                        faint(item.code, size=10),
                    ],
                    spacing=8,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                )
            )
        return ft.Container(
            content=ft.Column(controls=rows, spacing=4),
            bgcolor=T.panel,
            padding=ft.Padding(left=MD, top=8, right=MD, bottom=8),
            border=ft.Border(top=ft.BorderSide(width=1, color=T.border)),
        )
