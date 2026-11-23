"""Document actions that need the platform: open, save, export, new."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from flet_visual_builder.app_context import Workspace
from flet_visual_builder.services.starter import starter_project
from flet_visual_builder.ui import dialogs


class FileActions:
    """Thin command layer shared by the toolbar, menus, and shortcuts."""

    def __init__(self, ws: Workspace) -> None:
        self.ws = ws
        self._picker: ft.FilePicker | None = None
        self._mode = ""

    # ── pickers ───────────────────────────────────────────────────────
    def _ensure_picker(self) -> ft.FilePicker:
        if self._picker is None:
            self._picker = ft.FilePicker(on_result=self._on_result)
            try:
                self.ws.page.services.append(self._picker)
            except Exception:
                pass
        return self._picker

    def _on_result(self, event: ft.FilePickerResultEvent) -> None:
        mode = self._mode
        if mode == "open":
            if event.files and event.files[0].path:
                self.ws.open_path(event.files[0].path)
        elif mode == "save":
            if event.path:
                self.ws.save_to(event.path)
        elif mode == "export":
            if event.path:
                self._write_export(event.path)

    def open(self) -> None:
        self._mode = "open"
        self._ensure_picker().pick_files(
            dialog_title="Open a Flet Visual Builder project",
            allowed_extensions=["json"],
        )

    def save(self) -> None:
        if self.ws.session.path is None:
            self.save_as()
            return
        self.ws.save_to(self.ws.session.path)

    def save_as(self) -> None:
        self._mode = "save"
        self._ensure_picker().save_file(
            dialog_title="Save project",
            file_name=f"{self.ws.project.name}.fvb.json",
            allowed_extensions=["json"],
        )

    def export_code(self) -> None:
        artifact = self.ws.artifact()
        if artifact is None:
            self.ws.toast("Nothing to export: fix the diagnostics first", "error")
            return
        self._mode = "export"
        self._ensure_picker().save_file(
            dialog_title="Export runnable Python",
            file_name="app.py",
            allowed_extensions=["py"],
        )

    def _write_export(self, raw_path: str) -> None:
        artifact = self.ws.artifact()
        if artifact is None:
            return
        path = Path(raw_path)
        if path.suffix != ".py":
            path = path.with_suffix(".py")
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
