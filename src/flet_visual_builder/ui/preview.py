"""Live, device-framed projection of the current document."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import DEVICE_LABELS, Refresh
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.screens import active_screen_plan
from flet_visual_builder.ui.theme import (
    LG,
    MD,
    R_LG,
    SM,
    T,
    empty_state,
    faint,
    icon_button,
    pill,
    text,
)


class Preview(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.DOCUMENT, Refresh.LAYOUT})

    def build(self) -> ft.Control:
        plan = self.ws.plan()
        diagnostics = self.ws.diagnostics()
        root = None
        failure = None
        detail = "No preview root was produced (no diagnostic available)."
        if plan is not None:
            try:
                active = self.ws.active_screen()
                active_plan = active_screen_plan(plan, active)
                rendered = self.ws.renderer.render_plan(active_plan)
                root = rendered.root
                if root is None:
                    failure = rendered.diagnostics[0] if rendered.diagnostics else None
            except Exception as exc:
                failure = None
                detail = f"Preview render failed: {exc}"
        else:
            detail = "The document could not be rendered."

        failed = root is None
        if failed:
            diagnostic = failure or (diagnostics[0] if diagnostics else None)
            if diagnostic is not None:
                detail = f"{diagnostic.code}: {diagnostic.message}"
            root = empty_state(ft.Icons.ERROR_OUTLINE, "Preview unavailable", detail)

        meta = self.ws.screen_meta(self.ws.active_screen())
        title = meta.title if meta else "Screen"
        route = meta.route if meta else ""
        width = self.ws.device_width()
        toolbar = ft.Row(
            controls=[
                text(
                    str(title),
                    weight=ft.FontWeight.W_600,
                    expand=True,
                    max_lines=1,
                    overflow=ft.TextOverflow.ELLIPSIS,
                ),
                faint(route),
                faint(str(self.ws.project.page.get("title") or self.ws.project.name)),
                faint(DEVICE_LABELS.get(self.ws.device, self.ws.device)),
                (
                    pill("Stale", color=T.danger, bgcolor=T.danger_soft)
                    if failed
                    else faint("Live")
                ),
                icon_button(
                    ft.Icons.REFRESH,
                    "Refresh preview",
                    lambda e: self.refresh(Refresh.ALL),
                ),
            ],
            spacing=SM,
        )
        frame = ft.Container(
            content=root,
            width=width,
            expand=width is None,
            bgcolor=T.panel,
            border=ft.Border.all(1, T.border_strong),
            border_radius=R_LG,
            clip_behavior=ft.ClipBehavior.HARD_EDGE,
        )
        viewport = (
            frame
            if width is None
            else ft.Row(
                controls=[frame],
                expand=True,
                spacing=0,
                alignment=ft.MainAxisAlignment.CENTER,
                vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                scroll=ft.ScrollMode.AUTO,
            )
        )
        return ft.Column(
            controls=[
                ft.Container(
                    content=toolbar,
                    padding=ft.Padding(left=LG, top=SM, right=MD, bottom=SM),
                    bgcolor=T.panel,
                ),
                ft.Container(
                    content=viewport, padding=LG, bgcolor=T.canvas_bg, expand=True
                ),
            ],
            spacing=0,
            expand=True,
        )
