"""Code view: the exported Python for the current document."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, LG, T, button, empty_state, faint


class CodeView(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.DOCUMENT, Refresh.LAYOUT})

    def build(self) -> ft.Control:
        artifact = self.ws.artifact()
        if artifact is None:
            return empty_state(ft.Icons.CODE_OFF, "No code yet", "The document has blocking diagnostics.")
        source = artifact.source
        lines = source.count("\n") + 1
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            faint("Python", size=11),
                            ft.Container(expand=True),
                            faint(f"{lines} lines · black {artifact.formatter.split('==')[-1]}", size=11),
                            button("Copy", lambda e: self._copy(source), icon=ft.Icons.COPY, compact=True),
                        ],
                        spacing=8,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=ft.Padding(left=LG, top=8, right=LG, bottom=8),
                    bgcolor=T.panel,
                    border=ft.Border(bottom=ft.BorderSide(width=1, color=T.border)),
                ),
                ft.Container(
                    content=ft.Markdown(
                        value=f"```python\n{source}\n```",
                        selectable=True,
                        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
                    ),
                    padding=LG,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _copy(self, source: str) -> None:
        async def run() -> None:
            await ft.Clipboard().set(source)

        try:
            self.ws.page.run_task(run)
            self.ws.toast("Python copied", "success")
        except Exception as exc:
            self.ws.toast(f"Clipboard failed: {exc}", "error")
