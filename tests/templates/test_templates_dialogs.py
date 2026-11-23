import py_compile
import warnings

import flet as ft
import pytest

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import DocumentSnapshot, ExportOptions, Severity
from flet_visual_builder.engine.codegen import Codegen
from flet_visual_builder.engine.lowering import Lowering
from flet_visual_builder.engine.runtime import RuntimeRenderer
from flet_visual_builder.persistence.json_repository import JsonRepository
from flet_visual_builder.services.templates import TEMPLATES
from flet_visual_builder.ui.dialogs import (
    REPOSITORY_URL,
    SHORTCUTS,
    about_dialog,
    new_document_dialog,
    shortcuts_dialog,
    template_gallery_dialog,
)


def test_unique_template_ids():
    ids = [template.id for template in TEMPLATES]
    assert len(ids) >= 5
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("template", TEMPLATES, ids=lambda t: t.id)
def test_template_round_trip_and_engine(template, tmp_path):
    project = template.builder()
    assert len(project.nodes) >= 12
    ids = [node.id for node in project.nodes.values()]
    assert len(ids) == len(set(ids))
    assert set(ids) == set(project.nodes)
    assert len({node.type_id for node in project.nodes.values()}) >= 3
    assert template.builder() == project
    assert template.builder() is not project

    repo = JsonRepository()
    loaded = repo.loads(repo.dump(project))
    assert loaded.ok, loaded.diagnostics
    assert loaded.project == project
    lowered = Lowering().lower_project(DocumentSnapshot(loaded.project, 0), catalogue)
    assert not [d for d in lowered.diagnostics if d.severity == Severity.ERROR]
    assert lowered.plan is not None
    artifact = Codegen().generate_python(lowered.plan, ExportOptions())
    assert not artifact.diagnostics
    output = tmp_path / "generated.py"
    output.write_text(artifact.source, encoding="utf-8")
    py_compile.compile(str(output), doraise=True)
    result = RuntimeRenderer().render_plan(lowered.plan)
    assert result.root is not None
    assert not result.diagnostics
    assert set(result.by_node) == set(project.nodes)


@pytest.mark.parametrize(
    "builder,title",
    [
        (template_gallery_dialog, "Template gallery"),
        (new_document_dialog, "New document"),
    ],
)
def test_gallery_choices_and_callbacks(builder, title):
    selected = []
    closed = []
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        dialog = builder(selected.append, lambda: closed.append(True))
    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.title.value == title
    assert dialog.actions
    assert isinstance(dialog.content, ft.ListView)
    cards = dialog.content.controls
    assert len(cards) == len(TEMPLATES)
    for card, template in zip(cards, TEMPLATES, strict=True):
        contents = card.content.controls
        assert contents[0].controls[0].value == template.name
        assert contents[0].controls[1].content.value == template.category
        assert contents[1].value == template.description
        assert contents[2].controls[0].value == f"{len(template.builder().nodes)} nodes"
        action = contents[2].controls[1]
        assert (
            action.content.value == "Use template"
            if isinstance(action.content, ft.Text)
            else action.content == "Use template"
        )
        action.on_click(None)
        assert selected[-1] == template.builder()
        assert selected[-1] is not template.builder()
    dialog.actions[0].on_click(None)
    assert closed == [True]


@pytest.mark.parametrize(
    "builder,title",
    [
        (about_dialog, "About Flet Visual Builder"),
        (shortcuts_dialog, "Keyboard shortcuts"),
    ],
)
def test_information_dialogs(builder, title):
    closed = []
    with warnings.catch_warnings():
        warnings.simplefilter("error", DeprecationWarning)
        dialog = builder(lambda: closed.append(True))
    assert isinstance(dialog, ft.AlertDialog)
    assert dialog.title.value == title
    assert dialog.actions
    dialog.actions[0].on_click(None)
    assert closed == [True]


def test_about_and_shortcut_content():
    about = about_dialog(lambda: None)
    controls = about.content.controls
    assert "0.2.0" in controls[0].value
    assert "1.0.1" in controls[1].value
    assert controls[2].url == REPOSITORY_URL
    shortcuts = shortcuts_dialog(lambda: None)
    assert [
        (row.controls[0].value, row.controls[1].value)
        for row in shortcuts.content.controls
    ] == list(SHORTCUTS)
    assert {binding for binding, _ in SHORTCUTS} == {
        "Ctrl/Cmd + Z",
        "Ctrl/Cmd + Shift + Z",
        "Ctrl/Cmd + Y",
        "Ctrl/Cmd + S",
        "Ctrl/Cmd + O",
        "Ctrl/Cmd + D",
        "Delete / Backspace",
        "Escape",
    }
