"""In-app file dialogs.

Native file pickers on Linux depend on a desktop portal. When that is missing the
async picker call never returns, which would leave Save doing nothing. These
dialogs take a path directly, remember recent projects, and work everywhere.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import flet as ft

from flet_visual_builder.services.session import RecentEntry
from flet_visual_builder.ui.theme import (
    F_BODY,
    MD,
    R_MD,
    SM,
    T,
    button,
    faint,
    muted,
    text,
)

DEFAULT_DIR = Path.home() / "Documents"


def suggested_path(name: str, suffix: str = ".fvb.json") -> str:
    safe = (
        "".join(ch for ch in name if ch.isalnum() or ch in " -_").strip() or "Untitled"
    )
    return str(DEFAULT_DIR / f"{safe}{suffix}")


def _path_field(value: str, *, helper: str) -> ft.TextField:
    return ft.TextField(
        value=value,
        label="File path",
        dense=True,
        text_size=F_BODY,
        autofocus=True,
        helper=helper,
        border=ft.OutlineInputBorder(border_radius=R_MD),
    )


def _resolve(raw: str, fallback_suffix: str) -> Path:
    candidate = Path(raw.strip()).expanduser()
    if not candidate.suffix:
        candidate = candidate.with_suffix(fallback_suffix)
    return candidate


def save_dialog(
    *,
    title: str,
    initial_path: str,
    suffix: str,
    confirm_label: str,
    on_confirm: Callable[[Path], object],
    on_close: Callable[[], object],
    note: str | None = None,
) -> ft.AlertDialog:
    """Ask for a path and hand a resolved :class:`Path` to ``on_confirm``."""

    field = _path_field(
        initial_path, helper=note or "Relative paths resolve from your home folder."
    )
    error = text("", size=11, color=T.danger, visible=False)

    def confirm(event: ft.ControlEvent) -> None:
        path = _resolve(field.value or "", suffix)
        if not path.name:
            field.error = "Enter a file name"
            field.update()
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            error.value = f"Folder is not writable: {exc}"
            error.visible = True
            error.update()
            return
        on_confirm(path)

    return ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Column(
            controls=[
                field,
                error,
                faint(
                    "Saving writes one JSON document. Opening replaces the current editor "
                    "contents.",
                    size=11,
                ),
            ],
            spacing=SM,
            tight=True,
            width=440,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: on_close()),
            button(confirm_label, confirm, primary=True),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def open_dialog(
    *,
    initial_path: str,
    recents: list[RecentEntry],
    on_confirm: Callable[[Path], object],
    on_close: Callable[[], object],
) -> ft.AlertDialog:
    field = _path_field(
        initial_path, helper="Type a project path, or pick a recent project."
    )

    def confirm(event: ft.ControlEvent) -> None:
        path = _resolve(field.value or "", ".fvb.json")
        if path.suffix != ".json":
            path = path.with_suffix(".fvb.json")
        on_confirm(path)

    rows: list[ft.Control] = []
    if recents:
        rows.append(faint("Recent projects", size=11))
        for entry in recents:
            rows.append(
                ft.Container(
                    content=ft.Column(
                        controls=[
                            text(entry.name, size=F_BODY, weight=ft.FontWeight.W_500),
                            faint(
                                entry.path,
                                size=10,
                                max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS,
                            ),
                        ],
                        spacing=0,
                        tight=True,
                    ),
                    padding=ft.Padding(left=SM, top=6, right=SM, bottom=6),
                    border_radius=R_MD,
                    on_click=lambda e, path=entry.path: on_confirm(Path(path)),
                    tooltip=f"Open {entry.path}",
                )
            )
    else:
        rows.append(faint("No recent projects yet.", size=11))

    return ft.AlertDialog(
        modal=True,
        title=ft.Text("Open project"),
        content=ft.Column(
            controls=[field, ft.Container(height=MD), *rows],
            spacing=SM,
            tight=True,
            width=460,
            scroll=ft.ScrollMode.AUTO,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=lambda e: on_close()),
            button("Open", confirm, primary=True),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )


def confirm_export_dialog(
    *,
    initial_path: str,
    on_confirm: Callable[[Path], object],
    on_close: Callable[[], object],
) -> ft.AlertDialog:
    return save_dialog(
        title="Export Python",
        initial_path=initial_path,
        suffix=".py",
        confirm_label="Export",
        on_confirm=on_confirm,
        on_close=on_close,
        note="The exported file is a standalone Flet app with no dependency on this builder.",
    )
