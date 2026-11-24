from __future__ import annotations

import ast
import py_compile
from dataclasses import replace

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import (
    DocumentSnapshot,
    EventSymbol,
    ExportOptions,
    Navigate,
    Node,
    PlannedScreen,
    Project,
    ScreenMeta,
)
from flet_visual_builder.engine.codegen import Codegen
from flet_visual_builder.engine.lowering import Lowering, document_sha256
from flet_visual_builder.engine.runtime import RuntimeRenderer, iter_controls


def project() -> Project:
    return Project(
        name="App",
        page={"title": "App"},
        root_ids=("home", "settings"),
        nodes={
            "home": Node("home", "Column", {}, {"controls": ("next",)}, {}),
            "next": Node(
                "next",
                "Button",
                {"content": "Next"},
                {},
                {"on_click": EventSymbol("handle_next_click")},
                {"on_click": Navigate("/settings")},
            ),
            "settings": Node("settings", "Text", {"value": "Settings"}, {}, {}),
        },
        assets={},
        screens={
            "home": ScreenMeta("Home", "/"),
            "settings": ScreenMeta("Settings", "/settings"),
        },
        initial_route="/settings",
    )


def lower(p: Project):
    result = Lowering().lower_project(DocumentSnapshot(p, 1), catalogue)
    assert result.plan is not None, result.diagnostics
    return result.plan


def test_lowering_screens_and_hash_cover_navigation():
    p = project()
    plan = lower(p)
    assert plan.screens == (
        PlannedScreen("home", "Home", "/"),
        PlannedScreen("settings", "Settings", "/settings"),
    )
    assert plan.initial_route == "/settings"
    assert document_sha256(p) != document_sha256(replace(p, initial_route="/"))
    screens = dict(p.screens)
    screens["home"] = ScreenMeta("New name", "/")
    assert document_sha256(p) != document_sha256(replace(p, screens=screens))
    nodes = dict(p.nodes)
    nodes["next"] = replace(nodes["next"], actions={})
    assert document_sha256(p) != document_sha256(replace(p, nodes=nodes))


def test_render_only_requested_root_but_indexes_all_nodes():
    plan = lower(project())
    rendered = RuntimeRenderer().render_plan(plan, "settings")
    assert not rendered.diagnostics
    assert set(rendered.by_node) == set(plan.nodes)
    controls = iter_controls(rendered.root)
    assert rendered.by_node["settings"] in controls
    assert rendered.by_node["home"] not in controls
    assert rendered.by_node["next"] not in controls
    assert RuntimeRenderer().render_plan(plan, "next").root is None
    all_controls = iter_controls(RuntimeRenderer().render_plan(plan).root)
    assert sum(control.__class__.__name__ == "Column" for control in all_controls) == 2


def test_router_and_navigation_compile(tmp_path):
    artifact = Codegen().generate_python(lower(project()), ExportOptions())
    assert not artifact.diagnostics
    source = artifact.source
    tree = ast.parse(source)
    defs = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"build_home", "build_settings", "main"} <= defs
    assert "SCREENS" in source and '"/settings"' in source
    assert "push_route" in source and "on_route_change" in source
    assert "handle_next_click" not in source
    assert 'route = requested if requested in SCREENS else "/settings"' in source
    assert 'page.run_task(page.push_route, "/settings")' in source
    assert "route_change()" in source
    path = tmp_path / "generated.py"
    path.write_text(source)
    py_compile.compile(str(path), doraise=True)


def test_slug_collision_and_module_handler():
    p = project()
    nodes = dict(p.nodes)
    nodes["next"] = replace(nodes["next"], actions={})
    p = replace(
        p,
        nodes=nodes,
        screens={
            "home": ScreenMeta("123", "/"),
            "settings": ScreenMeta("Screen 1", "/settings"),
        },
    )
    source = Codegen().generate_python(lower(p), ExportOptions()).source
    tree = ast.parse(source)
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert {"build_screen_1", "build_screen_1_2", "handle_next_click"} <= functions
    assert "on_click=handle_next_click" in source


def test_missing_screen_root_rejected():
    p = project()
    nodes = dict(p.nodes)
    del nodes["settings"]
    result = Lowering().lower_project(
        DocumentSnapshot(replace(p, nodes=nodes), 1), catalogue
    )
    assert result.plan is None
    assert any(d.severity.value == "error" for d in result.diagnostics)


def test_single_screen_export_compiles(tmp_path):
    p = project()
    p = replace(
        p,
        root_ids=("settings",),
        nodes={"settings": p.nodes["settings"]},
        screens={"settings": p.screens["settings"]},
    )
    artifact = Codegen().generate_python(lower(p), ExportOptions())
    assert not artifact.diagnostics
    assert "SCREENS" in artifact.source
    path = tmp_path / "single.py"
    path.write_text(artifact.source)
    py_compile.compile(str(path), doraise=True)
