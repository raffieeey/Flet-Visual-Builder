"""Design canvas: the document rendered inside a device frame."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import DEVICE_LABELS, Refresh
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import LG, T, empty_state, faint


class Canvas(BasePanel):
    interests = frozenset(
        {Refresh.PROJECT, Refresh.DOCUMENT, Refresh.SELECTION, Refresh.LAYOUT}
    )

    def build(self) -> ft.Control:
        ws = self.ws
        plan = ws.plan()
        if plan is None:
            return empty_state(
                ft.Icons.ERROR_OUTLINE,
                "This document cannot be rendered",
                "Open the diagnostics panel for the first blocking error.",
            )

        rendered = ws.renderer.render_plan(plan)
        if rendered.root is None:
            codes = ", ".join(sorted({d.code for d in rendered.diagnostics})) or "unknown error"
            return empty_state(ft.Icons.ERROR_OUTLINE, "Preview unavailable", codes)

        width = ws.device_width()
        frame = ft.Container(
            content=rendered.root,
            width=width,
            expand=width is None,
            bgcolor=T.panel,
            border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shadow=ft.BoxShadow(
                blur_radius=24,
                spread_radius=0,
                color=T.shadow,
                offset=ft.Offset(0, 6),
            ),
        )

        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        faint("Design", size=11),
                        ft.Container(expand=True),
                        faint(DEVICE_LABELS.get(ws.device, "Fill"), size=11),
                    ],
                ),
                ft.Container(
                    content=frame,
                    alignment=ft.Alignment.TOP_CENTER,
                    expand=True,
                    bgcolor=T.canvas_bg,
                    padding=LG,
                ),
            ],
            spacing=0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
