"""Composition and command tests for the workspace controller."""

from __future__ import annotations

import py_compile
import tempfile
from pathlib import Path

import pytest

from flet_visual_builder.app_context import Refresh, Workspace
from flet_visual_builder.contracts import CommandStatus, EditorTab
from flet_visual_builder.services.session import ProjectSession
from flet_visual_builder.services.starter import empty_project, starter_project
from tests.support.fake_page import FakePage


def make_workspace(tmp_path: Path) -> Workspace:
    session = ProjectSession(base=tmp_path)
    return Workspace(FakePage(), starter_project(), session=session)


def test_starter_project_is_valid(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    result = ws.plan_result()
    assert result.plan is not None, [d.message for d in result.diagnostics]
    assert result.diagnostics == ()


def test_artifact_compiles(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    artifact = ws.artifact()
    assert artifact is not None
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False) as handle:
        handle.write(artifact.source)
        path = handle.name
    py_compile.compile(path, doraise=True)
    Path(path).unlink()


def test_insert_select_delete_undo_redo(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    before = within = None
    root = ws.project.root_ids[0]
    result = ws.insert("Text", root, "controls", 0)
    assert result.status is CommandStatus.COMMITTED
    new_id = ws.editor.selection
    assert new_id in ws.project.nodes
    assert ws.project.nodes[new_id].props["value"] == "Text"

    ws.delete(new_id)
    assert new_id not in ws.project.nodes
    ws.undo()
    assert new_id in ws.project.nodes
    ws.redo()
    assert new_id not in ws.project.nodes


def test_move_and_wrap(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    root = ws.project.root_ids[0]
    first = ws.project.nodes[root].slots["controls"][0]
    result = ws.wrap(first, "Card")
    assert result.status is CommandStatus.COMMITTED
    wrapper = ws.editor.selection
    assert ws.project.nodes[wrapper].type_id == "Card"
    assert ws.project.nodes[wrapper].slots["content"] == (first,)


def test_save_and_open_roundtrip(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    target = tmp_path / "demo.fvb.json"
    saved = ws.save_to(target)
    assert saved.ok, [d.message for d in saved.diagnostics]
    assert ws.session.dirty is False

    fresh = make_workspace(tmp_path / "fresh")
    opened = fresh.open_path(target)
    assert opened.ok
    assert fresh.project.name == ws.project.name
    assert set(fresh.project.nodes) == set(ws.project.nodes)


def test_rejected_command_reports_without_mutating(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    revision = ws.revision
    result = ws.set_property("missing-node", "value", "x")
    assert result.status is CommandStatus.REJECTED
    assert ws.revision == revision


def test_autosave_writes_recovery_copy(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    ws.insert("Text", ws.project.root_ids[0], "controls", 0)
    assert ws.session.write_autosave(ws.repository, ws.project, ws.revision) is True
    assert ws.session.autosave_path.exists()
    recovered = ws.session.read_autosave(ws.repository)
    assert recovered is not None
    assert set(recovered.nodes) == set(ws.project.nodes)


def test_empty_project_and_tabs(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    ws.new_document(empty_project("Blank"))
    assert ws.editor.selection == "root"
    ws.set_tab(EditorTab.CODE)
    assert ws.editor.active_tab is EditorTab.CODE
    assert ws.device_width() is None
    ws.set_device("phone")
    assert ws.device_width() == 390


def test_app_build_mounts_every_panel(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("FLET_VISUAL_BUILDER_HOME", str(tmp_path))
    from flet_visual_builder.ui.app import build
    from tests.support.fake_page import FakePage

    page = FakePage()
    ws = build(page)
    assert page.controls, "shell root was not added to the page"
    assert len(ws._panels) >= 10
    shell_root = page.controls[0]
    assert shell_root is not None
    # Every region host received a control.
    for name in (
        "toolbar",
        "palette",
        "tree",
        "inspector",
        "design",
        "preview",
        "code",
        "diagnostics",
    ):
        host = getattr(ws._panels[0].shell.mounts, name)
        assert host.content is not None, name


def test_rename_preserves_undo_history(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    ws.insert("Text", ws.project.root_ids[0], "controls", 0)
    depth_before = ws.dispatcher.undo_count
    ws.rename_project("Renamed")
    assert ws.project.name == "Renamed"
    assert ws.dispatcher.undo_count == depth_before + 1
    ws.undo()
    assert ws.project.name == "Welcome"


def test_duplicate_container_is_atomic(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    before = set(ws.project.nodes)
    result = ws.duplicate("header")
    assert result.status is CommandStatus.COMMITTED, [
        d.message for d in result.diagnostics
    ]
    added = set(ws.project.nodes) - before
    assert len(added) >= 2, added
    clone_root = ws.project.nodes[ws.editor.selection]
    assert clone_root.type_id == "Container"
    assert clone_root.slots["content"], "cloned container lost its children"
    ws.undo()
    assert set(ws.project.nodes) == before


def test_diagnostics_are_deduplicated(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    diagnostics = ws.diagnostics()
    assert diagnostics == ()
    keys = [(d.code, d.message, d.node_id or "") for d in ws.diagnostics()]
    assert len(keys) == len(set(keys))


def test_duplicate_rewrites_event_handler_names(tmp_path: Path) -> None:
    ws = make_workspace(tmp_path)
    root = ws.project.root_ids[0]
    result = ws.insert("Button", root, "controls", 0)
    button_id = ws.editor.selection
    ws.set_event(button_id, "on_click", True)
    original = ws.project.nodes[button_id].events["on_click"].name

    ws.duplicate(button_id)
    clone_id = ws.editor.selection
    clone_symbol = ws.project.nodes[clone_id].events["on_click"].name
    assert clone_id != button_id
    assert clone_symbol != original
    assert clone_id in clone_symbol


def test_boot_recovers_autosaved_work(tmp_path: Path) -> None:
    from dataclasses import replace

    from flet_visual_builder.persistence.json_repository import JsonRepository
    from flet_visual_builder.ui.app import _boot_project

    session = ProjectSession(base=tmp_path)
    recovered = replace(starter_project(), name="Recovered draft")
    assert session.write_autosave(JsonRepository(), recovered, 5) is True

    project, dirty, notice = _boot_project(None, session)
    assert project.name == "Recovered draft"
    assert dirty is True
    assert "Recovered" in notice


def test_boot_reports_a_missing_project_file(tmp_path: Path) -> None:
    from flet_visual_builder.ui.app import _boot_project

    session = ProjectSession(base=tmp_path / "empty")
    project, dirty, notice = _boot_project(tmp_path / "nope.fvb.json", session)
    assert project.name == "Welcome"
    assert dirty is False
    assert "Could not open" in notice
