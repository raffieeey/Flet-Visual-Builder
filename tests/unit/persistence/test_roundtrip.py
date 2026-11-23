"""v2 project JSON round-trip. Headless; no Flet."""

from __future__ import annotations

import ast
from pathlib import Path

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import Severity
from flet_visual_builder.model.validation import validate_project
from flet_visual_builder.persistence.json_repository import (
    JsonRepository,
    dump,
    load,
)
from tests.unit.persistence.helpers import sample_project

PERSISTENCE_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "flet_visual_builder" / "persistence"
)


def test_round_trip_preserves_unset_null_false_zero(tmp_path: Path) -> None:
    original = sample_project()
    path = tmp_path / "project.json"
    written = JsonRepository().save(original, path)
    assert written.project is not None
    assert path.is_file()

    loaded = load(path)
    assert loaded.project is not None
    project = loaded.project

    assert project.name == original.name
    assert project.page["title"] == "T"
    assert project.page["padding"] == 0
    assert project.page["appbar"] is None
    assert "theme_mode" not in project.page

    root = project.nodes["root"]
    assert root.props["spacing"] == 0
    assert root.props["tight"] is False
    assert root.props["scroll"] is None
    assert "alignment" not in root.props
    assert "disabled" not in root.props

    label = project.nodes["label"]
    assert label.props["value"] == ""
    assert label.props["size"] is None
    assert label.props["visible"] is False
    assert "weight" not in label.props

    save_node = project.nodes["save"]
    assert save_node.events["on_click"].name == "handle_save_click"
    assert "on_click" not in save_node.props

    payload = dump(project)
    assert payload["nodes"]["root"]["props"]["spacing"] == 0
    assert payload["nodes"]["root"]["props"]["tight"] is False
    assert payload["nodes"]["root"]["props"]["scroll"] is None
    assert "alignment" not in payload["nodes"]["root"]["props"]
    assert payload["nodes"]["label"]["props"]["size"] is None
    assert "weight" not in payload["nodes"]["label"]["props"]
    assert payload["page"]["padding"] == 0
    assert payload["page"]["appbar"] is None

    assert original.page == project.page
    assert original.nodes["root"].props == project.nodes["root"].props
    assert original.nodes["label"].props == project.nodes["label"].props
    assert original.nodes["save"].events == project.nodes["save"].events
    assert original.root_ids == project.root_ids


def test_round_trip_passes_invariants() -> None:
    project = sample_project()
    result = JsonRepository().loads(dump(project))
    assert result.project is not None
    assert validate_project(result.project) == ()
    page_diags = [
        d
        for d in catalogue.validate_page(result.project.page)
        if d.severity == Severity.ERROR
    ]
    assert page_diags == []
    for node in result.project.nodes.values():
        node_diags = [
            d
            for d in catalogue.validate_node(node, nodes=result.project.nodes)
            if d.severity == Severity.ERROR
        ]
        assert node_diags == []


def test_save_refuses_invalid_project_without_writing(tmp_path: Path) -> None:
    from tests.unit.persistence.helpers import make_node, make_project

    project = make_project(make_node("root", "NotAWidget"))
    path = tmp_path / "nope.json"
    result = JsonRepository().save(project, path)
    assert result.project is None
    assert result.diagnostics
    assert not path.exists()


def test_persistence_modules_do_not_import_flet() -> None:
    for path in PERSISTENCE_DIR.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name.split(".")[0] != "flet", path
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] != "flet", path
