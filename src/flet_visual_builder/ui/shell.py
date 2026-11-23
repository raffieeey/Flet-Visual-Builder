"""Passive editor shell: region hosts, tab activation, and status text.

This module owns workspace mount points. It does not import or implement
palette, tree, inspector, preview, code-preview, catalogue, model, or
persistence features.
"""

from __future__ import annotations

from typing import Literal

import flet as ft

from flet_visual_builder.contracts import (
    EditorTab,
    RegionName,
    ShellMountPoints,
)
from flet_visual_builder.ui.theme import INSPECTOR_W, RAIL_W, STATUS_H, T

_EDITOR_TABS: tuple[tuple[EditorTab, str], ...] = (
    (EditorTab.DESIGN, "design"),
    (EditorTab.PREVIEW, "preview"),
    (EditorTab.CODE, "code"),
)


class ShellImpl:
    """Stable workspace hosts. Features mount in; the shell does not own them."""

    mounts: ShellMountPoints
    root: ft.Control

    def __init__(self) -> None:
        toolbar = ft.Container(data="toolbar")
        palette = ft.Container(data="palette")
        tree = ft.Container(data="tree")
        inspector = ft.Container(data="inspector")
        design = ft.Container(data="design", expand=True)
        preview = ft.Container(data="preview", expand=True)
        code = ft.Container(data="code", expand=True)
        diagnostics = ft.Container(data="diagnostics")
        status = ft.Container(data="status", expand=True)

        self.mounts = ShellMountPoints(
            toolbar=toolbar,
            palette=palette,
            tree=tree,
            inspector=inspector,
            design=design,
            preview=preview,
            code=code,
            diagnostics=diagnostics,
            status=status,
        )
        left_rail = ft.Container(
            content=ft.Column(
                controls=[
                    ft.Container(content=palette, expand=3),
                    ft.Container(height=1, bgcolor=T.border_soft),
                    ft.Container(content=tree, expand=2),
                ],
                spacing=0,
                expand=True,
            ),
            width=RAIL_W,
            bgcolor=T.rail,
        )
        centre = ft.Container(
            content=ft.Stack(controls=[design, preview, code], expand=True),
            expand=True,
            bgcolor=T.canvas_bg,
        )
        self.root = ft.Column(
            controls=[
                toolbar,
                ft.Row(
                    controls=[
                        left_rail,
                        ft.Container(width=1, bgcolor=T.border, height=None),
                        centre,
                        ft.Container(width=1, bgcolor=T.border, height=None),
                        ft.Container(
                            content=inspector, width=INSPECTOR_W, bgcolor=T.panel
                        ),
                    ],
                    expand=True,
                    spacing=0,
                    vertical_alignment=ft.CrossAxisAlignment.STRETCH,
                ),
                diagnostics,
                ft.Container(
                    content=status,
                    height=STATUS_H,
                    bgcolor=T.panel,
                    border=ft.Border(top=ft.BorderSide(width=1, color=T.border)),
                    padding=ft.Padding(left=12, top=0, right=12, bottom=0),
                    alignment=ft.Alignment.CENTER_LEFT,
                ),
            ],
            expand=True,
            spacing=0,
        )
        self.activate(EditorTab.DESIGN)

    def mount(self, region: str, content: ft.Control | None) -> None:
        host = getattr(self.mounts, region, None)
        if host is None:
            raise ValueError(f"unknown shell region {region!r}")
        host.content = content

    def activate(self, tab: EditorTab) -> None:
        for editor_tab, region in _EDITOR_TABS:
            getattr(self.mounts, region).visible = editor_tab == tab
