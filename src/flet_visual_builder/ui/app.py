"""Composition root and entry point (mirrors the public :mod:`flet_visual_builder.app`)."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from flet_visual_builder.app_context import Refresh, Workspace
from flet_visual_builder.contracts import EditorTab
from flet_visual_builder.persistence.json_repository import JsonRepository
from flet_visual_builder.services.session import ProjectSession
from flet_visual_builder.services.starter import starter_project
from flet_visual_builder.ui.actions import FileActions
from flet_visual_builder.ui.canvas import Canvas
from flet_visual_builder.ui.code_view import CodeView
from flet_visual_builder.ui.diagnostics import DiagnosticsView
from flet_visual_builder.ui.inspector import Inspector
from flet_visual_builder.ui.palette import Palette
from flet_visual_builder.ui.preview import Preview
from flet_visual_builder.ui.shell import ShellImpl
from flet_visual_builder.ui.status import StatusBar
from flet_visual_builder.ui.theme import T, page_theme
from flet_visual_builder.ui.toolbar import Toolbar
from flet_visual_builder.ui.tree_view import Outline


class _ShellSync:
    """Keeps shell region visibility in step with the active editor tab."""

    def __init__(self, ws: Workspace, shell: ShellImpl) -> None:
        self.ws = ws
        self.shell = shell
        self.control = ft.Container(width=0, height=0)

    def refresh(self, reason: str) -> None:
        if reason in (Refresh.ALL, Refresh.LAYOUT, Refresh.PROJECT, Refresh.CHROME):
            self.shell.activate(self.ws.editor.active_tab)


def _boot_project(path: str | Path | None, session: ProjectSession):
    """Choose the initial document: explicit path, then recovery copy, then starter."""
    repository = JsonRepository()
    notice = ""
    if path is not None:
        result = repository.load(path)
        if result.ok and result.project is not None:
            session.set_path(path, saved=True)
            return result.project, False, notice
        detail = (
            result.diagnostics[0].message if result.diagnostics else "unknown error"
        )
        notice = f"Could not open {path}: {detail}"
    recovered = session.read_autosave(repository)
    if recovered is not None:
        return recovered, True, "Recovered unsaved work from the last session"
    return starter_project(), False, notice


def build(
    page: ft.Page,
    *,
    path: str | Path | None = None,
    mode: str = "design",
) -> Workspace:
    page.title = "Flet Visual Builder"
    page.padding = 0
    page.spacing = 0
    page.bgcolor = T.bg
    page.theme = page_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    try:
        page.window.min_width = 1024
        page.window.min_height = 640
    except Exception:
        pass

    session = ProjectSession()
    project, dirty, notice = _boot_project(path, session)
    ws = Workspace(page, project, session=session)
    if dirty:
        session.mark_dirty()

    actions = FileActions(ws)
    shell = ShellImpl()
    panels = {
        "toolbar": Toolbar(ws, actions),
        "palette": Palette(ws),
        "tree": Outline(ws),
        "design": Canvas(ws),
        "inspector": Inspector(ws),
        "preview": Preview(ws),
        "code": CodeView(ws),
        "diagnostics": DiagnosticsView(ws),
        "status": StatusBar(ws),
    }
    tabs = {
        "design": EditorTab.DESIGN,
        "preview": EditorTab.PREVIEW,
        "code": EditorTab.CODE,
    }
    ws.editor.activate(tabs.get(mode, EditorTab.DESIGN))
    ws.add_panel(_ShellSync(ws, shell))
    for name, panel in panels.items():
        ws.add_panel(panel)
        shell.mount(name, panel.control)  # type: ignore[arg-type]

    _install_shortcuts(page, ws, actions)

    page.add(shell.root)
    ws.refresh(Refresh.ALL)
    if notice:
        ws.toast(notice, "error" if "Could not" in notice else "info")
    return ws


def _install_shortcuts(page: ft.Page, ws: Workspace, actions: FileActions) -> None:
    def on_key(event: ft.KeyboardEvent) -> None:
        key = (event.key or "").upper()
        if event.ctrl or event.meta:
            if key == "Z":
                ws.redo() if event.shift else ws.undo()
            elif key == "Y":
                ws.redo()
            elif key == "S":
                actions.save()
            elif key == "O":
                actions.open()
            elif key == "D":
                if ws.editor.selection:
                    ws.duplicate(ws.editor.selection)
            return
        if key in ("DELETE", "BACKSPACE"):
            if ws.editor.text_focus:
                return
            if ws.editor.selection and ws.editor.selection not in ws.project.root_ids:
                ws.delete(ws.editor.selection)
        elif key == "ESCAPE":
            ws.select(None)

    page.on_keyboard_event = on_key


def main(
    page: ft.Page,
    *,
    path: str | Path | None = None,
    mode: str = "design",
) -> Workspace:
    ws = build(page, path=path, mode=mode)
    page.on_close = lambda e: ws.close()
    return ws
