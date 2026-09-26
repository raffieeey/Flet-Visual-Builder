"""Legacy v0.0/v0.1 migration and refusal of ambiguous ownership."""

from __future__ import annotations

import json
from pathlib import Path

from src.flet_visual_builder.catalogue import catalogue
from src.flet_visual_builder.contracts import Severity
from src.flet_visual_builder.model.validation import event_symbol_name, validate_project
from src.flet_visual_builder.persistence.json_repository import JsonRepository, load
from tests.unit.persistence.helpers import diagnostic_blob

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CONTRACTS_LEGACY = (
    Path(__file__).resolve().parents[2]
    / "contracts"
    / "fixtures"
    / "legacy-0.1-minimal.json"
)

# TDD §2.3.4: handle_ + node_id + _ + event_name without on_
SAVE_CLICK_SYMBOL = event_symbol_name("save", "on_click")


def _assert_migrated_legacy(result) -> None:
    assert result.project is not None, diagnostic_blob(result.diagnostics)
    project = result.project
    assert validate_project(project) == ()
    page_errors = [
        d for d in catalogue.validate_page(project.page) if d.severity == Severity.ERROR
    ]
    assert page_errors == []
    for node in project.nodes.values():
        node_errors = [
            d
            for d in catalogue.validate_node(node, nodes=project.nodes)
            if d.severity == Severity.ERROR
        ]
        assert node_errors == [], node_errors

    assert project.nodes["root"].type_id == "Column"
    assert project.nodes["root"].props["alignment"] == "START"
    assert project.nodes["root"].props["spacing"] == 10.0
    assert project.nodes["root"].slots["controls"] == ("label", "save")
    assert project.root_ids == ("root",)

    label = project.nodes["label"]
    assert label.type_id == "Text"
    assert label.props["value"] == "Hello"
    assert label.props["weight"] == "BOLD"

    save = project.nodes["save"]
    assert save.type_id == "Button"
    assert save.props.get("content") == "Save"
    assert "text" not in save.props
    assert "on_click" not in save.props
    assert save.events["on_click"].name == SAVE_CLICK_SYMBOL
    assert SAVE_CLICK_SYMBOL == "handle_save_click"
    assert project.page.get("theme_mode") == "LIGHT"


def test_legacy_0_1_fixture_migrates_events_to_typed_bindings() -> None:
    path = FIXTURES / "legacy-0.1-minimal.json"
    result = load(path)
    _assert_migrated_legacy(result)
    assert result.migrated_from == "0.1"
    assert result.editor_hints is not None
    assert result.editor_hints.selected_node_id == "save"
    assert result.editor_hints.device_frame == "desktop"


def test_committed_contracts_legacy_fixture_matches_unit_copy() -> None:
    unit = (FIXTURES / "legacy-0.1-minimal.json").read_bytes()
    committed = CONTRACTS_LEGACY.read_bytes()
    assert json.loads(unit) == json.loads(committed)


def test_legacy_0_0_fixture_chains_to_v2() -> None:
    result = load(FIXTURES / "legacy-0.0-minimal.json")
    _assert_migrated_legacy(result)
    assert result.migrated_from == "0.0"


def test_absent_schema_version_is_treated_as_0_0() -> None:
    data = json.loads(
        (FIXTURES / "legacy-0.0-minimal.json").read_text(encoding="utf-8")
    )
    data.pop("schema_version")
    result = JsonRepository().loads(data)
    _assert_migrated_legacy(result)
    assert result.migrated_from == "0.0"


def test_executable_event_text_refuses_migration() -> None:
    data = json.loads(
        (FIXTURES / "legacy-0.1-minimal.json").read_text(encoding="utf-8")
    )
    data["tree"]["children"][1]["props"]["on_click"] = "on_save()"
    result = JsonRepository().loads(data)
    assert result.project is None
    blob = diagnostic_blob(result.diagnostics)
    assert "event" in blob
    assert "on_save()" not in str(result.project)


def test_ambiguous_parent_id_refuses() -> None:
    data = json.loads(
        (FIXTURES / "legacy-0.1-minimal.json").read_text(encoding="utf-8")
    )
    data["tree"]["children"][0]["parent_id"] = "other"
    result = JsonRepository().loads(data)
    assert result.project is None
    assert "ambiguous" in diagnostic_blob(result.diagnostics)


def test_conflicting_order_refuses() -> None:
    data = json.loads(
        (FIXTURES / "legacy-0.1-minimal.json").read_text(encoding="utf-8")
    )
    data["tree"]["children"][0]["order"] = 1
    data["tree"]["children"][1]["order"] = 0
    result = JsonRepository().loads(data)
    assert result.project is None
    assert "ambiguous" in diagnostic_blob(result.diagnostics)


def test_duplicate_order_refuses() -> None:
    data = json.loads(
        (FIXTURES / "legacy-0.1-minimal.json").read_text(encoding="utf-8")
    )
    data["tree"]["children"][0]["order"] = 0
    data["tree"]["children"][1]["order"] = 0
    result = JsonRepository().loads(data)
    assert result.project is None
    assert "ambiguous" in diagnostic_blob(result.diagnostics)


def test_missing_slot_on_leaf_parent_refuses() -> None:
    data = json.loads(
        (FIXTURES / "legacy-0.1-minimal.json").read_text(encoding="utf-8")
    )
    data["tree"]["type"] = "Text"
    data["tree"]["children"][0]["slot"] = None
    data["tree"]["children"][1]["slot"] = None
    result = JsonRepository().loads(data)
    assert result.project is None
    assert "ambiguous" in diagnostic_blob(result.diagnostics)
