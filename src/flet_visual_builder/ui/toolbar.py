"""Compact top bar with document, history, device and mode controls."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import DEVICE_LABELS, DEVICE_WIDTHS, Refresh
from flet_visual_builder.contracts import EditorTab
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import (
    F_BODY,
    F_LABEL,
    MD,
    R_MD,
    T,
    TOOLBAR_H,
    button,
    icon_button,
    text,
)


class Toolbar(BasePanel):
    def __init__(self, workspace, actions=None):
        self.actions = actions
        self._name_focused = False
        super().__init__(workspace)

    def build(self) -> ft.Control:
        ws = self.ws
        self.name = ft.TextField(
            value=ws.project.name,
            dense=True,
            border=ft.NoInputBorder(),
            text_size=F_LABEL,
            width=150,
            content_padding=ft.Padding(left=2, top=0, right=2, bottom=0),
            on_focus=self._focus_name,
            on_submit=self._commit_name,
            on_blur=self._blur_name,
            tooltip="Project name",
        )
        self.dirty = ft.Container(width=7, height=7, border_radius=4)
        self.undo_button = icon_button(
            ft.Icons.UNDO, "Undo (Ctrl+Z / Cmd+Z)", lambda e: ws.undo()
        )
        self.redo_button = icon_button(
            ft.Icons.REDO,
            "Redo (Ctrl+Shift+Z / Ctrl+Y; Cmd equivalents)",
            lambda e: ws.redo(),
        )
        for control in (self.undo_button, self.redo_button):
            control.width = 34
            control.height = 34

        def action(icon, tooltip, method):
            control = icon_button(
                icon,
                tooltip,
                lambda e: self._act(method),
                disabled=self.actions is None,
            )
            control.width = 34
            control.height = 34
            return control

        identity = ft.Row(controls=[self.name, self.dirty], spacing=4, tight=True)
        document = ft.Row(
            controls=[
                action(
                    ft.Icons.NOTE_ADD_OUTLINED,
                    "New document from template",
                    "new_document",
                ),
                action(ft.Icons.GRID_VIEW, "Template gallery", "templates"),
                action(ft.Icons.FOLDER_OPEN, "Open (Ctrl+O / Cmd+O)", "open"),
                action(ft.Icons.SAVE_OUTLINED, "Save (Ctrl+S / Cmd+S)", "save"),
                self.undo_button,
                self.redo_button,
            ],
            spacing=0,
            tight=True,
        )
        self.devices = {
            key: self._device(key) for key in ("phone", "tablet", "laptop", "fill")
        }
        self.tabs = {
            tab: self._tab(title, tab)
            for title, tab in (
                ("Design", EditorTab.DESIGN),
                ("Preview", EditorTab.PREVIEW),
                ("Code", EditorTab.CODE),
            )
        }
        # The flexible spacer absorbs remaining width; right groups never expand.
        result = ft.Container(
            content=ft.Row(
                controls=[
                    identity,
                    document,
                    ft.Container(expand=True),
                    ft.Row(controls=list(self.devices.values()), spacing=0, tight=True),
                    ft.Row(controls=list(self.tabs.values()), spacing=0, tight=True),
                    button(
                        "Export",
                        lambda e: self._act("export_code"),
                        icon=ft.Icons.DOWNLOAD,
                        primary=True,
                        disabled=self.actions is None,
                    ),
                    ft.PopupMenuButton(
                        icon=ft.Icons.MORE_VERT,
                        tooltip="More",
                        disabled=self.actions is None,
                        items=[
                            ft.PopupMenuItem(
                                content="Keyboard shortcuts",
                                icon=ft.Icons.KEYBOARD,
                                on_click=lambda e: self._act("shortcuts"),
                            ),
                            ft.PopupMenuItem(
                                content="About Flet Visual Builder",
                                icon=ft.Icons.INFO_OUTLINE,
                                on_click=lambda e: self._act("about"),
                            ),
                        ],
                    ),
                ],
                spacing=4,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            height=TOOLBAR_H,
            bgcolor=T.panel,
            border=ft.Border(bottom=ft.BorderSide(width=1, color=T.border)),
            padding=ft.Padding(left=MD, top=0, right=MD, bottom=0),
        )
        self._sync()
        return result

    def refresh(self, reason: str) -> None:
        if reason not in (
            Refresh.ALL,
            Refresh.DOCUMENT,
            Refresh.CHROME,
            Refresh.PROJECT,
            Refresh.LAYOUT,
        ):
            return
        self._sync(force_name=reason == Refresh.PROJECT)
        try:
            self.control.update()
        except RuntimeError:
            pass

    def _sync(self, force_name=False) -> None:
        ws = self.ws
        if force_name or not self._name_focused:
            self.name.value = ws.project.name
        self.dirty.bgcolor = T.warning if ws.session.dirty else T.success
        self.dirty.tooltip = "Unsaved changes" if ws.session.dirty else "Saved"
        self.undo_button.disabled = ws.dispatcher.undo_count == 0
        self.redo_button.disabled = ws.dispatcher.redo_count == 0
        for key, control in self.devices.items():
            active = ws.device == key
            control.bgcolor = T.accent_soft if active else None
            control.content.color = T.accent if active else T.text_muted
        for tab, control in self.tabs.items():
            active = ws.editor.active_tab is tab
            control.bgcolor = T.accent_soft if active else None
            control.content.color = T.accent if active else T.text_muted
            control.content.weight = ft.FontWeight.W_600 if active else None

    def _focus_name(self, event) -> None:
        self._name_focused = True
        self.ws.set_text_focus(True)

    def _commit_name(self, event) -> None:
        value = (event.control.value or "").strip() or "Untitled"
        if value != self.ws.project.name:
            self.ws.rename_project(value)
        event.control.value = self.ws.project.name

    def _blur_name(self, event) -> None:
        self._name_focused = False
        self.ws.set_text_focus(False)
        self._commit_name(event)

    def _act(self, name: str) -> None:
        if self.actions is not None:
            getattr(self.actions, name)()

    def _tab(self, title: str, tab: EditorTab) -> ft.Container:
        return ft.Container(
            content=text(title, size=F_BODY),
            border_radius=R_MD,
            padding=ft.Padding(left=8, top=6, right=8, bottom=6),
            on_click=lambda e: self.ws.set_tab(tab),
            tooltip=f"{title} mode",
        )

    def _device(self, key: str) -> ft.Container:
        icons = {
            "phone": ft.Icons.SMARTPHONE,
            "tablet": ft.Icons.TABLET_MAC,
            "laptop": ft.Icons.LAPTOP_MAC,
            "fill": ft.Icons.ASPECT_RATIO,
        }
        width = DEVICE_WIDTHS[key]
        return ft.Container(
            content=ft.Icon(icons[key], size=16),
            border_radius=R_MD,
            padding=ft.Padding(left=7, top=6, right=7, bottom=6),
            on_click=lambda e: self.ws.set_device(key),
            tooltip=f"{DEVICE_LABELS[key]} frame"
            + (f" ({width}px)" if width else " (full width)"),
        )
