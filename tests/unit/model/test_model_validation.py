"""§2.3.4 invariant checks and structural validation."""

from __future__ import annotations

import hashlib

import pytest

from flet_visual_builder.contracts import (
    Asset,
    EventSymbol,
    SlotSpec,
)
from flet_visual_builder.model.validation import (
    MAX_DEPTH,
    MAX_NODES,
    event_symbol_name,
    is_identifier_safe_node_id,
    slot_accepts,
    validate_project,
)
from tests.unit.model.helpers import make_node, make_snapshot, nested_containers


def test_valid_column_has_no_diagnostics() -> None:
    child = make_node("t0", "Text")
    root = make_node("root", "Column", slots={"controls": ("t0",)})
    snap = make_snapshot(root, child)
    assert validate_project(snap.project) == ()


def test_duplicate_ownership_is_reported() -> None:
    child = make_node("t0", "Text")
    left = make_node("left", "Column", slots={"controls": ("t0",)})
    right = make_node("right", "Column", slots={"controls": ("t0",)})
    root = make_node("root", "Row", slots={"controls": ("left", "right")})
    project = make_snapshot(root, left, right, child).project
    codes = {d.code for d in validate_project(project)}
    assert "ownership.multiple" in codes


def test_dangling_child_reference() -> None:
    root = make_node("root", "Column", slots={"controls": ("ghost",)})
    codes = {d.code for d in validate_project(make_snapshot(root).project)}
    assert "ref.dangling" in codes


def test_orphan_node() -> None:
    root = make_node("root", "Column", slots={"controls": ()})
    stray = make_node("stray", "Text")
    codes = {d.code for d in validate_project(make_snapshot(root, stray).project)}
    assert "ref.orphan" in codes


def test_cycle_is_reported() -> None:
    a = make_node("a", "Container", slots={"content": ("b",)})
    b = make_node("b", "Container", slots={"content": ("a",)})
    project = make_snapshot(a, b, root_ids=("a",)).project
    codes = {d.code for d in validate_project(project)}
    assert "graph.cycle" in codes


def test_node_id_must_match_map_key() -> None:
    node = make_node("a", "Text")
    project = make_snapshot(node).project
    # Bypass constructor identity: copy-like mismatch via object.__setattr__ is
    # blocked on frozen nodes, so build a Project with a wrong key.
    from flet_visual_builder.contracts import Project

    mismatched = Project(
        name="t",
        page={},
        root_ids=("a",),
        nodes={"wrong": node},
        assets={},
    )
    codes = {d.code for d in validate_project(mismatched)}
    assert "id.mismatch" in codes
    assert "ref.dangling" in codes


@pytest.mark.parametrize(
    "node_id,ok",
    [
        ("root", True),
        ("t0", True),
        ("_x", True),
        ("node-1", False),
        ("class", False),
        ("1abc", False),
        ("", False),
        ("a" * 65, False),
        ("a" * 64, True),
    ],
)
def test_identifier_safe_node_ids(node_id: str, ok: bool) -> None:
    assert is_identifier_safe_node_id(node_id) is ok


def test_event_symbol_syntax_form() -> None:
    assert event_symbol_name("save", "on_click") == "handle_save_click"
    assert event_symbol_name("reset", "on_click") == "handle_reset_click"


def test_wrong_event_symbol_on_document() -> None:
    node = make_node(
        "save",
        "Button",
        events={"on_click": EventSymbol("handle_other_click")},
    )
    root = make_node("root", "Column", slots={"controls": ("save",)})
    codes = {d.code for d in validate_project(make_snapshot(root, node).project)}
    assert "event.symbol" in codes


def test_asset_hash_mismatch() -> None:
    data = b"hello"
    asset = Asset(
        id="a1",
        media_type="image/png",
        sha256="00" * 32,
        data=data,
    )
    root = make_node("root", "Column", slots={"controls": ()})
    project = make_snapshot(root, assets={"a1": asset}).project
    codes = {d.code for d in validate_project(project)}
    assert "asset.hash" in codes


def test_valid_asset_passes() -> None:
    data = b"hello"
    asset = Asset(
        id="a1",
        media_type="image/png",
        sha256=hashlib.sha256(data).hexdigest(),
        data=data,
    )
    root = make_node("root", "Column", slots={"controls": ()})
    assert validate_project(make_snapshot(root, assets={"a1": asset}).project) == ()


def test_single_child_cardinality() -> None:
    a = make_node("a", "Text")
    b = make_node("b", "Text")
    box = make_node("root", "Container", slots={"content": ("a", "b")})
    codes = {d.code for d in validate_project(make_snapshot(box, a, b).project)}
    assert "slot.cardinality" in codes


def test_unknown_slot_on_known_type() -> None:
    child = make_node("t0", "Text")
    root = make_node("root", "Column", slots={"content": ("t0",)})
    codes = {d.code for d in validate_project(make_snapshot(root, child).project)}
    assert "slot.unknown" in codes


def test_slot_accepts_none_means_any() -> None:
    spec = SlotSpec(name="controls", minimum=0, maximum=None, accepted_types=None)
    assert slot_accepts(spec, "Text") is True
    restricted = SlotSpec(
        name="content",
        minimum=0,
        maximum=1,
        accepted_types=frozenset({"Text"}),
    )
    assert slot_accepts(restricted, "Text") is True
    assert slot_accepts(restricted, "Column") is False


def test_nested_depth_within_limit() -> None:
    snap = nested_containers(8)
    assert validate_project(snap.project) == ()


def test_max_nodes_constant() -> None:
    assert MAX_NODES == 1000
    assert MAX_DEPTH == 64
