"""Compact diagnostics with navigation back to affected nodes."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.contracts import Severity
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, MD, SM, T, faint, pill, text


class DiagnosticsView(BasePanel):
    interests = frozenset({Refresh.DOCUMENT, Refresh.PROJECT})

    def __init__(self, workspace):
        self._expanded = False
        super().__init__(workspace)
        self.control.expand = False

    def _toggle(self, event) -> None:
        self._expanded = not self._expanded
        self.refresh(Refresh.ALL)

    def build(self) -> ft.Control:
        diagnostics = self.ws.diagnostics()
        self.control.visible = bool(diagnostics)
        if not diagnostics:
            self._expanded = False
            return ft.Container(height=0)
        counts = [
            f"{sum(d.severity is severity for d in diagnostics)} {severity.value}"
            for severity in Severity
        ]
        header = ft.Row(
            controls=[
                text("Diagnostics", weight=ft.FontWeight.W_600),
                faint(" · ".join(counts), expand=True),
            ],
            spacing=SM,
        )
        rows = []
        for item in diagnostics if self._expanded else diagnostics[:6]:
            color, background = {
                Severity.ERROR: (T.danger, T.danger_soft),
                Severity.WARNING: (T.warning, T.border_soft),
                Severity.INFO: (T.text_muted, T.border_soft),
            }.get(item.severity, (T.text_muted, T.border_soft))
            body = [text(item.message, size=F_BODY), faint(item.code)]
            if item.path:
                body.append(faint(" / ".join(str(part) for part in item.path)))
            controls = [
                pill(item.severity.value, color=color, bgcolor=background),
                ft.Column(controls=body, spacing=2, expand=True, tight=True),
            ]
            if item.node_id is not None:
                controls.append(
                    ft.TextButton(
                        content="Go to node",
                        on_click=lambda e, node_id=item.node_id: self.ws.select(
                            node_id
                        ),
                    )
                )
            rows.append(
                ft.Row(
                    controls=controls,
                    spacing=SM,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                )
            )
        if len(diagnostics) > 6:
            label = "Show less" if self._expanded else f"Show all ({len(diagnostics)})"
            header.controls.append(ft.TextButton(content=label, on_click=self._toggle))
        return ft.Container(
            content=ft.Column(
                controls=[
                    header,
                    ft.Container(
                        content=ft.Column(
                            controls=rows, spacing=SM, scroll=ft.ScrollMode.AUTO
                        ),
                        height=240 if self._expanded else None,
                    ),
                ],
                spacing=SM,
                tight=True,
            ),
            bgcolor=T.panel,
            padding=ft.Padding(left=MD, top=SM, right=MD, bottom=SM),
            border=ft.Border(top=ft.BorderSide(width=1, color=T.border)),
        )
