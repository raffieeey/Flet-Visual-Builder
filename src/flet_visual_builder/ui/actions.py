"""Document actions that need the platform: open, save, export, new."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from flet_visual_builder.app_context import Workspace
from flet_visual_builder.ui import dialogs, file_dialogs


class FileActions:
    """Thin command layer shared by the toolbar, menus, and shortcuts.

    File choice goes through in-app dialogs rather than a native picker: the
    native picker needs a desktop portal and hangs without one.
    """

    def __init__(self, ws: Workspace) -> None:
        self.ws = ws

    # ── files ─────────────────────────────────────────────────────────
    def open(self) -> None:
        session = self.ws.session
        self._show(
            file_dialogs.open_dialog(
                initial_path=str(
                    session.path or file_dialogs.suggested_path(self.ws.project.name)
                ),
                recents=session.recents(),
                on_confirm=self._open_path,
                on_close=self._close_dialog,
            )
        )

    def _open_path(self, path: Path) -> None:
        self._close_dialog()
        self.ws.open_path(path)

    def save(self) -> None:
        if self.ws.session.path is None:
            self.save_as()
            return
        self.ws.save_to(self.ws.session.path)

    def save_as(self) -> None:
        self._show(
            file_dialogs.save_dialog(
                title="Save project",
                initial_path=str(
                    self.ws.session.path
                    or file_dialogs.suggested_path(self.ws.project.name)
                ),
                suffix=".fvb.json",
                confirm_label="Save",
                on_confirm=self._save_path,
                on_close=self._close_dialog,
            )
        )

    def _save_path(self, path: Path) -> None:
        self._close_dialog()
        self.ws.save_to(path)

    def export_code(self) -> None:
        if self.ws.artifact() is None:
            self.ws.toast("Nothing to export: fix the diagnostics first", "error")
            return
        self._show(
            file_dialogs.confirm_export_dialog(
                initial_path=file_dialogs.suggested_path(self.ws.project.name, ".py"),
                on_confirm=self._export_path,
                on_close=self._close_dialog,
            )
        )

    def _export_path(self, path: Path) -> None:
        self._close_dialog()
        self._write_export(path)

    def _write_export(self, raw_path: str | Path) -> None:
        artifact = self.ws.artifact()
        if artifact is None:
            return
        path = Path(raw_path).expanduser()
        if path.suffix != ".py":
            path = path.with_suffix(".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(artifact.source, encoding="utf-8")
        self.ws.toast(f"Exported {path.name}", "success")

    # ── dialogs ───────────────────────────────────────────────────────
    def new_document(self) -> None:
        """Open the template gallery; the current document is only replaced on choice."""
        self._show(dialogs.new_document_dialog(self._apply_new, self._close_dialog))

    def templates(self) -> None:
        self._show(dialogs.template_gallery_dialog(self._apply_new, self._close_dialog))

    def about(self) -> None:
        self._show(dialogs.about_dialog(self._close_dialog))

    def shortcuts(self) -> None:
        self._show(dialogs.shortcuts_dialog(self._close_dialog))

    def _show(self, dialog: ft.AlertDialog) -> None:
        try:
            self.ws.page.show_dialog(dialog)
        except Exception as exc:  # a dialog must never take the workspace down
            self.ws.toast(f"Could not open dialog: {exc}", "error")

    def _close_dialog(self) -> None:
        try:
            self.ws.page.pop_dialog()
        except Exception:
            pass

    def _apply_new(self, project) -> None:
        self._close_dialog()

        def replace_document() -> None:
            self.ws.new_document(project)
            self.ws.toast(f"Started from {project.name}", "success")

        if not self.ws.session.dirty:
            replace_document()
            return

        def discard(event: ft.ControlEvent) -> None:
            self._close_dialog()
            replace_document()

        self._show(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Discard unsaved changes?"),
                content=ft.Text(
                    "The current document has changes that are not on disk."
                ),
                actions=[
                    ft.TextButton(
                        "Keep editing", on_click=lambda e: self._close_dialog()
                    ),
                    ft.TextButton("Discard", on_click=discard),
                ],
                actions_alignment=ft.MainAxisAlignment.END,
            )
        )
