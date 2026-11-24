"""Screens and click actions: model, validation and persistence."""

from __future__ import annotations

import pytest

from flet_visual_builder.contracts import (
    AddScreen,
    CommandStatus,
    DeleteScreen,
    DocumentSnapshot,
    Navigate,
    Node,
    Project,
    ScreenMeta,
    SetAction,
    SetScreen,
)
from flet_visual_builder.model.reducer import Reducer
from flet_visual_builder.model.screens import (
    effective_routes,
    meta_for,
    screen_entries,
)
from flet_visual_builder.model.validation import validate_project
from flet_visual_builder.persistence.json_repository import JsonRepository


def node(node_id: str, type_id: str = "Column", children=(), slot="controls") -> Node:
    slots = {slot: tuple(children)} if children else {}
    return Node(
        id=node_id,
        type_id=type_id,
        props={},
        slots=slots,
        events={},
    )


def two_screen_project() -> Project:
    return Project(
        name="App",
        page={},
        root_ids=("home", "settings"),
        nodes={
            "home": node("home", children=("home_text",)),
            "home_text": node("home_text", "Text"),
            "settings": node("settings"),
        },
        assets={},
    )


def apply(project: Project, command):
    return Reducer().apply(DocumentSnapshot(project=project, revision=0), command)


# ── defaults and derivation ───────────────────────────────────────────
def test_legacy_project_derives_stable_screen_metadata() -> None:
    project = two_screen_project()
    entries = screen_entries(project)
    assert entries[0][1] == ScreenMeta("Home", "/")
    assert entries[1][1] == ScreenMeta("Screen 2", "/screen-2")
    assert effective_routes(project) == {"/": "home", "/screen-2": "settings"}


def test_validation_rejects_duplicate_routes() -> None:
    project = Project(
        name="App",
        page={},
        root_ids=("a", "b"),
        nodes={"a": node("a"), "b": node("b")},
        assets={},
        screens={
            "a": ScreenMeta("A", "/"),
            "b": ScreenMeta("B", "/"),
        },
        initial_route="/",
    )
    codes = {d.code for d in validate_project(project)}
    assert "screen.route.duplicate" in codes


def test_validation_rejects_initial_route_that_matches_nothing() -> None:
    project = Project(
        name="App",
        page={},
        root_ids=("a",),
        nodes={"a": node("a")},
        assets={},
        initial_route="/missing",
    )
    assert "screen.initial" in {d.code for d in validate_project(project)}


# ── commands ──────────────────────────────────────────────────────────
def test_set_screen_renames_and_changes_route() -> None:
    result = apply(
        two_screen_project(),
        SetScreen(command_id="c1", screen_id="settings", title="Settings", route="/prefs"),
    )
    assert result.status is CommandStatus.COMMITTED
    assert meta_for(result.snapshot.project, "settings") == ScreenMeta("Settings", "/prefs")


def test_set_screen_cannot_steal_another_route() -> None:
    result = apply(
        two_screen_project(),
        SetScreen(command_id="c1", screen_id="settings", title="Settings", route="/"),
    )
    assert result.status is CommandStatus.REJECTED
    assert {d.code for d in result.diagnostics} == {"screen.route.duplicate"}


def test_set_screen_can_make_a_screen_initial_and_follows_route_changes() -> None:
    project = two_screen_project()
    made_initial = apply(
        project,
        SetScreen(
            command_id="c1",
            screen_id="settings",
            title="Settings",
            route="/settings",
            initial=True,
        ),
    )
    assert made_initial.snapshot.project.initial_route == "/settings"

    renamed = apply(
        made_initial.snapshot.project,
        SetScreen(
            command_id="c2",
            screen_id="settings",
            title="Settings",
            route="/preferences",
        ),
    )
    assert renamed.snapshot.project.initial_route == "/preferences"


def test_add_screen_appends_root_and_metadata() -> None:
    result = apply(
        two_screen_project(),
        AddScreen(
            command_id="c1",
            node=node("profile"),
            title="Profile",
            route="/profile",
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    project = result.snapshot.project
    assert project.root_ids[-1] == "profile"
    assert meta_for(project, "profile") == ScreenMeta("Profile", "/profile")


def test_add_screen_rejects_a_route_already_in_use() -> None:
    result = apply(
        two_screen_project(),
        AddScreen(command_id="c1", node=node("profile"), title="Profile", route="/"),
    )
    assert result.status is CommandStatus.REJECTED


def test_delete_screen_removes_the_subtree_and_keeps_the_rest() -> None:
    result = apply(two_screen_project(), DeleteScreen(command_id="c1", screen_id="home"))
    assert result.status is CommandStatus.COMMITTED
    project = result.snapshot.project
    assert project.root_ids == ("settings",)
    assert "home" not in project.nodes and "home_text" not in project.nodes


def test_delete_screen_refuses_the_last_screen() -> None:
    project = Project(
        name="One",
        page={},
        root_ids=("only",),
        nodes={"only": node("only")},
        assets={},
    )
    result = apply(project, DeleteScreen(command_id="c1", screen_id="only"))
    assert result.status is CommandStatus.REJECTED
    assert {d.code for d in result.diagnostics} == {"screen.last"}


def test_deleting_the_initial_screen_moves_the_initial_route() -> None:
    project = two_screen_project()
    project = apply(
        project,
        SetScreen(
            command_id="c0", screen_id="home", title="Home", route="/", initial=True
        ),
    ).snapshot.project
    result = apply(project, DeleteScreen(command_id="c1", screen_id="home"))
    assert result.snapshot.project.initial_route == "/screen-2"


# ── actions ───────────────────────────────────────────────────────────
def test_set_action_binds_navigation_to_an_existing_route() -> None:
    result = apply(
        two_screen_project(),
        SetAction(
            command_id="c1",
            node_id="home_text",
            event_name="on_click",
            action=Navigate("/screen-2"),
        ),
    )
    assert result.status is CommandStatus.COMMITTED
    stored = result.snapshot.project.nodes["home_text"].actions["on_click"]
    assert stored == Navigate("/screen-2")


def test_set_action_rejects_an_unknown_route() -> None:
    result = apply(
        two_screen_project(),
        SetAction(
            command_id="c1",
            node_id="home_text",
            event_name="on_click",
            action=Navigate("/nowhere"),
        ),
    )
    assert result.status is CommandStatus.REJECTED
    assert {d.code for d in result.diagnostics} == {"action.route"}


def test_set_action_can_be_cleared() -> None:
    project = two_screen_project()
    with_action = apply(
        project,
        SetAction(
            command_id="c1",
            node_id="home_text",
            event_name="on_click",
            action=Navigate("/screen-2"),
        ),
    ).snapshot.project
    cleared = apply(
        with_action,
        SetAction(command_id="c2", node_id="home_text", event_name="on_click"),
    )
    assert cleared.snapshot.project.nodes["home_text"].actions == {}


def test_delete_screen_strips_actions_that_pointed_at_it() -> None:
    project = two_screen_project()
    project = apply(
        project,
        SetAction(
            command_id="c1",
            node_id="home_text",
            event_name="on_click",
            action=Navigate("/screen-2"),
        ),
    ).snapshot.project
    result = apply(project, DeleteScreen(command_id="c2", screen_id="settings"))
    assert result.snapshot.project.nodes["home_text"].actions == {}


# ── persistence ───────────────────────────────────────────────────────
def test_screens_and_actions_round_trip() -> None:
    project = two_screen_project()
    project = apply(
        project,
        SetScreen(
            command_id="c1",
            screen_id="home",
            title="Welcome",
            route="/",
            initial=True,
        ),
    ).snapshot.project
    project = apply(
        project,
        SetAction(
            command_id="c2",
            node_id="home_text",
            event_name="on_click",
            action=Navigate("/screen-2"),
        ),
    ).snapshot.project

    repo = JsonRepository()
    payload = repo.dump(project)
    assert payload["schema_version"] == 3
    assert payload["screens"]["home"] == {"title": "Welcome", "route": "/"}

    loaded = repo.loads(payload)
    assert loaded.ok, loaded.diagnostics
    assert loaded.project.screens["home"] == ScreenMeta("Welcome", "/")
    assert loaded.project.nodes["home_text"].actions["on_click"] == Navigate("/screen-2")


def test_schema_v2_document_without_screens_still_loads() -> None:
    payload = JsonRepository().dump(two_screen_project())
    payload["schema_version"] = 2
    payload.pop("screens")
    payload.pop("initial_route")
    loaded = JsonRepository().loads(payload)
    assert loaded.ok, loaded.diagnostics
    assert effective_routes(loaded.project) == {"/": "home", "/screen-2": "settings"}


def test_route_must_start_with_a_slash() -> None:
    with pytest.raises(ValueError):
        Navigate("settings")
