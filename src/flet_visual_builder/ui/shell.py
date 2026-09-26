"""Passive editor shell: region hosts, tab activation, and status text.

This module owns workspace mount points. It does not import or implement
palette, tree, inspector, preview, code-preview, catalogue, model, or
persistence features.
"""

from __future__ import annotations

import flet as ft

from src.flet_visual_builder.contracts import (
    EditorTab,
    RegionName,
    ShellMountPoints,
)

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
        status = ft.Text(value="")

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
        self.root = ft.Column(
            controls=[
                toolbar,
                ft.Row(
                    controls=[
                        palette,
                        tree,
                        ft.Stack(
                            controls=[design, preview, code],
                            expand=True,
                        ),
                        inspector,
                    ],
                    expand=True,
                    spacing=0,
                ),
                diagnostics,
                status,
            ],
            expand=True,
            spacing=0,
        )
        self.activate(EditorTab.DESIGN)

    def mount(self, region: RegionName, content: ft.Control | None) -> None:
        getattr(self.mounts, region).content = content

    def activate(self, tab: EditorTab) -> None:
        for editor_tab, region in _EDITOR_TABS:
            getattr(self.mounts, region).visible = editor_tab == tab

    def set_status(self, text: str) -> None:
        self.mounts.status.value = text
