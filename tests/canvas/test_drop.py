from dataclasses import replace

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import Point, Size
from flet_visual_builder.interaction import resolve_drop
from flet_visual_builder.services.starter import starter_project, empty_project


def drop(project, node, y, kind="create", value="Text"):
    return resolve_drop(
        project, catalogue, node, Point(10, y), Size(100, 100), kind, value
    )


def test_three_zones_and_leaf_fallback():
    project = starter_project()
    before = drop(project, "header", 24)
    inside = drop(project, "header_col", 25)
    after = drop(project, "header", 75)
    leaf = drop(project, "header_title", 50)
    assert (before.zone, before.parent_id, before.slot_name, before.index) == (
        "before",
        "root",
        "controls",
        0,
    )
    assert (inside.zone, inside.parent_id, inside.slot_name, inside.index) == (
        "inside",
        "header_col",
        "controls",
        2,
    )
    assert (after.zone, after.index) == ("after", 1)
    assert (leaf.zone, leaf.parent_id, leaf.index) == ("after", "header_col", 1)


def test_same_parent_raw_indices_and_descendant_refusal():
    project = starter_project()
    result = drop(project, "body", 90, "move", "header")
    assert (result.parent_id, result.index) == ("root", 2)  # Workspace normalizes to 1.
    assert drop(project, "header_col", 50, "move", "header") is None
    assert drop(project, "header", 50, "move", "header") is None
    assert drop(project, "body", 50, "move", "root") is None


def test_empty_root_and_occupied_slot():
    project = empty_project()
    result = drop(project, "root", 0)
    assert (result.zone, result.parent_id, result.slot_name, result.index) == (
        "inside",
        "root",
        "controls",
        0,
    )
    assert drop(starter_project(), "header", 50) is None
    assert (
        resolve_drop(
            project, catalogue, "root", Point(0, 0), Size(0, 1), "create", "Text"
        )
        is None
    )
    assert drop(project, "root", 50, "create", "Unknown") is None
