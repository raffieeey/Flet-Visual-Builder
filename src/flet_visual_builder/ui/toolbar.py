"""Top toolbar: document identity, history, device width, and mode switching."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import DEVICE_LABELS, DEVICE_WIDTHS, Refresh
from flet_visual_builder.contracts import EditorTab
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import (
    F_BODY,
    F_LABEL,
    MD,
    SM,
    STATUS_H,
    T,
    TOOLBAR_H,
    button,
    icon_button,
    pill,
    text,
)


class Toolbar(BasePanel):
    interests = frozenset({Refresh.CHROME, Refresh.PROJECT, Refresh.LAYOUT, Refresh.STATUS})

    def __init__(self, workspace, actions=None) -> None:
        self.actions = actions
        super().__init__(workspace)

    def build(self) -> ft.Control:
        ws = self.ws
        name = ft.TextField(
            value=ws.project.name,
            dense=True,
            border=ft.NoInputBorder(),
            text_size=F_LABEL,
            width=190,
            content_padding=ft.Padding(left=2, top=0, right=2, bottom=0),
            on_submit=lambda e: ws.rename_project(e.control.value),
            on_blur=lambda e: ws.rename_project(e.control.value),
        )
        dirty = ft.Container(
            width=6,
            height=6,
            bgcolor=T.warning if ws.session.dirty else T.success,
            border_radius=3,
            tooltip="Unsaved changes" if ws.session.dirty else "Saved",
        )
        identity = ft.Row(
            controls=[
                ft.Container(
                    content=ft.Icon(ft.Icons.DASHBOARD_CUSTOMIZE, size=16, color=T.panel),
                    width=26,
                    height=26,
                    bgcolor=T.accent,
                    border_radius=6,
                    alignment=ft.Alignment.CENTER,
                ),
                name,
                dirty,
            ],
            spacing=SM,
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            tight=True,
        )

        tabs = ft.Row(
            controls=[
                self._tab("Design", EditorTab.DESIGN, ft.Icons.DESIGN_SERVICES),
                self._tab("Preview", EditorTab.PREVIEW, ft.Icons.PLAY_CIRCLE_OUTLINE),
                self._tab("Code", EditorTab.CODE, ft.Icons.CODE),
            ],
            spacing=2,
            tight=True,
        )

        devices = ft.Row(
            controls=[
                self._device(key)
                for key in ("phone", "tablet", "laptop", "fill")
            ],
            spacing=2,
            tight=True,
        )

        return ft.Container(
            content=ft.Row(
                controls=[
                    identity,
                    ft.Container(width=1, height=22, bgcolor=T.border),
                    icon_button(ft.Icons.NOTE_ADD_OUTLINED, "New document", lambda e: self._act("new_document"), disabled=self.actions is None),
                    icon_button(ft.Icons.FOLDER_OPEN, "Open project (Ctrl+O)", lambda e: self._act("open"), disabled=self.actions is None),
                    icon_button(ft.Icons.SAVE_OUTLINED, "Save (Ctrl+S)", lambda e: self._act("save"), disabled=self.actions is None),
                    ft.Container(width=1, height=22, bgcolor=T.border),
                    icon_button(ft.Icons.UNDO, "Undo (Ctrl+Z)", lambda e: ws.undo(), disabled=ws.dispatcher.undo_count == 0),
                    icon_button(ft.Icons.REDO, "Redo (Ctrl+Shift+Z)", lambda e: ws.redo(), disabled=ws.dispatcher.redo_count == 0),
                    ft.Container(expand=True),
                    devices,
                    ft.Container(width=1, height=22, bgcolor=T.border),
                    tabs,
                    ft.Container(width=1, height=22, bgcolor=T.border),
                    button("Export", lambda e: self._act("export_code"), icon=ft.Icons.DOWNLOAD, primary=True, disabled=self.actions is None),
                ],
                spacing=SM,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=TOOLBAR_H,
            bgcolor=T.panel,
            border=ft.Border(bottom=ft.BorderSide(width=1, color=T.border)),
            padding=ft.Padding(left=MD, top=0, right=MD, bottom=0),
        )

    def _act(self, name: str) -> None:
        if self.actions is None:
            return
        getattr(self.actions, name)()

    def _tab(self, label: str, tab: EditorTab, icon: str) -> ft.Control:
        active = self.ws.editor.active_tab is tab
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(icon, size=14, color=T.accent if active else T.text_muted),
                    text(label, size=F_BODY, weight=ft.FontWeight.W_600 if active else None,
                         color=T.accent if active else T.text_muted),
                ],
                spacing=5,
                tight=True,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            bgcolor=T.accent_soft if active else None,
            border_radius=6,
            padding=ft.Padding(left=10, top=6, right=10, bottom=6),
            on_click=lambda e, value=tab: self.ws.set_tab(value),
            tooltip=f"{label} mode",
        )

    def _device(self, key: str) -> ft.Control:
        active = self.ws.device == key
        width = DEVICE_WIDTHS.get(key)
        return ft.Container(
            content=ft.Icon(
                {
                    "phone": ft.Icons.SMARTPHONE,
                    "tablet": ft.Icons.TABLET_MAC,
                    "laptop": ft.Icons.LAPTOP_MAC,
                    "fill": ft.Icons.ASPECT_RATIO,
                }[key],
                size=15,
                color=T.accent if active else T.text_muted,
            ),
            bgcolor=T.accent_soft if active else None,
            border_radius=6,
            padding=ft.Padding(left=7, top=5, right=7, bottom=5),
            on_click=lambda e, value=key: self.ws.set_device(value),
            tooltip=f"{DEVICE_LABELS[key]} frame" + (f" ({width}px)" if width else " (full width)"),
        )
