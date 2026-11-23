"""Live preview: the document rendered exactly as it will ship."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import LG, T, empty_state


class Preview(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.DOCUMENT, Refresh.LAYOUT})

    def build(self) -> ft.Control:
        plan = self.ws.plan()
        if plan is None:
            return empty_state(ft.Icons.ERROR_OUTLINE, "Preview unavailable", "Fix the diagnostics first.")
        rendered = self.ws.renderer.render_plan(plan)
        if rendered.root is None:
            return empty_state(ft.Icons.ERROR_OUTLINE, "Preview unavailable", "The renderer reports an error.")
        return ft.Container(
            content=rendered.root,
            expand=True,
            bgcolor=T.panel,
            padding=0,
        )
