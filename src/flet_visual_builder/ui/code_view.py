"""Selectable, numbered Python export."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.contracts import Severity
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, LG, SM, T, button, faint, text


class CodeView(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.DOCUMENT, Refresh.LAYOUT})

    def __init__(self, workspace):
        self._source_cache = None
        self._numbers = ""
        self._line_count = 0
        self._byte_count = 0
        super().__init__(workspace)

    def build(self) -> ft.Control:
        artifact = self.ws.artifact()
        errors = tuple(
            d
            for d in (
                artifact.diagnostics if artifact is not None else self.ws.diagnostics()
            )
            if d.severity is Severity.ERROR
        )
        if artifact is None or errors:
            details = [text("Code generation unavailable", weight=ft.FontWeight.W_600)]
            details.extend(
                text(f"{d.code}: {d.message}", color=T.danger, selectable=True)
                for d in errors
            )
            if not errors:
                details.append(
                    faint("No artifact is available; check the document diagnostics.")
                )
            return ft.Container(
                content=ft.Column(
                    controls=details, spacing=SM, scroll=ft.ScrollMode.AUTO
                ),
                padding=LG,
                expand=True,
            )

        source = artifact.source
        if source != self._source_cache:
            self._source_cache = source
            self._line_count = len(source.splitlines())
            self._byte_count = len(source.encode("utf-8"))
            self._numbers = "\n".join(str(n) for n in range(1, self._line_count + 1))
        toolbar = ft.Row(
            controls=[
                faint(
                    f"Python · Flet {artifact.target_flet} · {artifact.formatter}",
                    expand=True,
                ),
                faint(f"{self._line_count} lines · {self._byte_count} bytes"),
                button("Copy", lambda e: self._copy(source), icon=ft.Icons.COPY),
            ],
            spacing=SM,
        )
        code = ft.Row(
            controls=[
                ft.Text(
                    self._numbers,
                    text_align=ft.TextAlign.RIGHT,
                    font_family="monospace",
                    size=F_BODY,
                    color=T.text_faint,
                    no_wrap=True,
                ),
                ft.Text(
                    source,
                    font_family="monospace",
                    size=F_BODY,
                    color=T.text,
                    selectable=True,
                    no_wrap=True,
                ),
            ],
            spacing=LG,
            vertical_alignment=ft.CrossAxisAlignment.START,
            scroll=ft.ScrollMode.AUTO,
        )
        return ft.Column(
            controls=[
                ft.Container(
                    content=toolbar,
                    padding=LG,
                    bgcolor=T.panel,
                    border=ft.Border(bottom=ft.BorderSide(width=1, color=T.border)),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=[code], scroll=ft.ScrollMode.AUTO, expand=True
                    ),
                    padding=LG,
                    bgcolor=T.panel,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _copy(self, source: str) -> None:
        async def copy() -> None:
            try:
                await ft.Clipboard().set(source)
            except Exception as exc:
                self.ws.toast(f"Clipboard failed: {exc}", "error")
            else:
                self.ws.toast("Python copied", "success")

        try:
            self.ws.page.run_task(copy)
        except Exception as exc:
            self.ws.toast(f"Clipboard failed: {exc}", "error")
