"""Document actions: template adoption, export writing, and dialog plumbing."""

from __future__ import annotations

from pathlib import Path

import flet as ft

from flet_visual_builder.app_context import Workspace
from flet_visual_builder.services.session import ProjectSession
from flet_visual_builder.services.starter import starter_project
from flet_visual_builder.services.templates import TEMPLATES
from flet_visual_builder.ui.actions import FileActions
from tests.support.fake_page import FakePage


def make(tmp_path: Path) -> tuple[Workspace, FileActions, FakePage]:
    page = FakePage()
    ws = Workspace(page, starter_project(), session=ProjectSession(base=tmp_path))
    return ws, FileActions(ws), page


def test_export_writes_generated_python(tmp_path: Path) -> None:
    ws, actions, _ = make(tmp_path)
    target = tmp_path / "exported"
    actions._write_export(str(target))
    written = target.with_suffix(".py")
    assert written.exists()
    source = written.read_text(encoding="utf-8")
    assert "def main(page: ft.Page)" in source
    assert "ft.run(main)" in source


def test_apply_new_replaces_a_clean_document(tmp_path: Path) -> None:
    ws, actions, page = make(tmp_path)
    template = next(t for t in TEMPLATES if t.id == "dashboard").builder()
    actions._apply_new(template)
    assert ws.project.name == template.name
    assert len(ws.project.nodes) == len(template.nodes)
    assert not any(isinstance(d, ft.AlertDialog) for d in page.dialogs)


def test_apply_new_asks_before_discarding_changes(tmp_path: Path) -> None:
    ws, actions, page = make(tmp_path)
    ws.insert("Text", ws.project.root_ids[0], "controls", 0)  # marks the session dirty
    assert ws.session.dirty is True
    before = set(ws.project.nodes)
    template = next(t for t in TEMPLATES if t.id == "login").builder()

    actions._apply_new(template)

    assert len(page.dialogs) == 1, "a confirmation dialog should be shown"
    assert (
        set(ws.project.nodes) == before
    ), "document must not change before confirmation"


def test_new_document_opens_the_gallery(tmp_path: Path) -> None:
    _, actions, page = make(tmp_path)
    actions.new_document()
    assert len(page.dialogs) == 1
    assert page.dialogs[0].title.value == "New document"


def test_about_and_shortcuts_build(tmp_path: Path) -> None:
    _, actions, page = make(tmp_path)
    actions.about()
    actions.shortcuts()
    titles = [dialog.title.value for dialog in page.dialogs]
    assert titles == ["About Flet Visual Builder", "Keyboard shortcuts"]
