"""T08 shell mount points. Headless structural checks; no GUI, no live page."""

from __future__ import annotations

import ast
from dataclasses import fields
from pathlib import Path
from typing import get_args

import flet as ft
import pytest

from flet_visual_builder.contracts import (
    EditorTab,
    RegionName,
    ShellMountPoints,
)
from flet_visual_builder.ui.shell import ShellImpl
from flet_visual_builder.ui import shell as shell_mod

REPO_ROOT = Path(__file__).resolve().parents[2]
SHELL_PATH = REPO_ROOT / "src" / "flet_visual_builder" / "ui" / "shell.py"

REGION_NAMES: tuple[str, ...] = get_args(RegionName)
EXPECTED_MOUNT_FIELDS: tuple[str, ...] = (*REGION_NAMES, "status")
EDITOR_REGIONS: dict[EditorTab, str] = {
    EditorTab.DESIGN: "design",
    EditorTab.PREVIEW: "preview",
    EditorTab.CODE: "code",
}

FORBIDDEN_IMPORT_SEGMENTS: frozenset[str] = frozenset(
    {
        "palette",
        "tree_view",
        "live_preview",
        "code_preview",
        "catalogue",
        "model",
        "persistence",
    }
)
FORBIDDEN_NAMESPACE_NAMES: frozenset[str] = frozenset(
    {
        "palette",
        "tree",
        "tree_view",
        "preview",
        "live_preview",
        "code_preview",
        "catalogue",
        "model",
        "persistence",
        "build_palette",
        "build_tree_view",
        "build_live_preview",
        "build_code_preview",
    }
)

# Representative mount orders: forward, reverse, and one interleaved permutation.
MOUNT_ORDERS: tuple[tuple[str, ...], ...] = (
    REGION_NAMES,
    tuple(reversed(REGION_NAMES)),
    (
        "diagnostics",
        "toolbar",
        "code",
        "palette",
        "inspector",
        "tree",
        "preview",
        "design",
    ),
)


def _walk_controls(node: object) -> list[ft.Control]:
    found: list[ft.Control] = []

    def visit(current: object) -> None:
        if not isinstance(current, ft.Control):
            return
        found.append(current)
        content = getattr(current, "content", None)
        if content is not None:
            visit(content)
        controls = getattr(current, "controls", None)
        if controls:
            for child in controls:
                visit(child)

    visit(node)
    return found


def _region_hosts(shell: ShellImpl) -> dict[str, ft.Container]:
    return {name: getattr(shell.mounts, name) for name in REGION_NAMES}


def _assert_root_contains_all_eight(shell: ShellImpl) -> None:
    descendants = _walk_controls(shell.root)
    descendant_ids = {id(control) for control in descendants}
    hosts = _region_hosts(shell)
    assert len(hosts) == 8
    missing = [name for name, host in hosts.items() if id(host) not in descendant_ids]
    assert missing == [], f"root is missing region containers: {missing}"
    assert id(shell.mounts.status) in descendant_ids


def test_all_nine_mount_point_fields_have_expected_types() -> None:
    declared = tuple(f.name for f in fields(ShellMountPoints))
    assert declared == EXPECTED_MOUNT_FIELDS
    assert declared == tuple(f.name for f in fields(ShellImpl().mounts))

    shell = ShellImpl()
    for name in REGION_NAMES:
        host = getattr(shell.mounts, name)
        assert isinstance(host, ft.Container), name
    assert isinstance(shell.mounts.status, ft.Text)
    assert isinstance(shell.mounts, ShellMountPoints)
    assert isinstance(shell.root, ft.Control)


@pytest.mark.parametrize("order", MOUNT_ORDERS)
def test_mounting_one_region_does_not_replace_others(order: tuple[str, ...]) -> None:
    shell = ShellImpl()
    hosts_before = _region_hosts(shell)
    contents = {name: ft.Text(value=f"content-{name}") for name in REGION_NAMES}

    for name in order:
        shell.mount(name, contents[name])  # type: ignore[arg-type]

    for name in REGION_NAMES:
        host = getattr(shell.mounts, name)
        assert host is hosts_before[name]
        assert host.content is contents[name]

    _assert_root_contains_all_eight(shell)

    replacement = ft.Text(value="replacement")
    target = order[0]
    shell.mount(target, replacement)  # type: ignore[arg-type]
    assert getattr(shell.mounts, target).content is replacement
    for name in REGION_NAMES:
        if name != target:
            assert getattr(shell.mounts, name).content is contents[name]
            assert getattr(shell.mounts, name) is hosts_before[name]

    shell.mount(target, None)  # type: ignore[arg-type]
    assert getattr(shell.mounts, target).content is None
    for name in REGION_NAMES:
        if name != target:
            assert getattr(shell.mounts, name).content is contents[name]

    _assert_root_contains_all_eight(shell)


def test_root_contains_all_eight_region_containers() -> None:
    shell = ShellImpl()
    _assert_root_contains_all_eight(shell)
    assert len(_region_hosts(shell)) == len(REGION_NAMES)


def test_activate_all_tabs_is_consistent_and_idempotent() -> None:
    shell = ShellImpl()
    hosts = {
        tab: getattr(shell.mounts, region) for tab, region in EDITOR_REGIONS.items()
    }
    assert tuple(EditorTab) == (EditorTab.DESIGN, EditorTab.PREVIEW, EditorTab.CODE)

    for tab in EditorTab:
        shell.activate(tab)
        for other, host in hosts.items():
            assert host.visible is (other == tab)
        shell.activate(tab)
        for other, host in hosts.items():
            assert host.visible is (other == tab)
        _assert_root_contains_all_eight(shell)


def test_set_status_writes_through_including_empty_string() -> None:
    shell = ShellImpl()
    status = shell.mounts.status
    assert isinstance(status, ft.Text)

    shell.set_status("Ready")
    assert status.value == "Ready"
    assert shell.mounts.status is status
    assert shell.mounts.status.value == "Ready"

    shell.set_status("")
    assert status.value == ""
    assert shell.mounts.status is status
    assert shell.mounts.status.value == ""


def test_shell_module_namespace_has_no_feature_logic() -> None:
    leaked = FORBIDDEN_NAMESPACE_NAMES & set(shell_mod.__dict__)
    assert leaked == set(), f"feature names in shell namespace: {sorted(leaked)}"

    tree = ast.parse(SHELL_PATH.read_text(encoding="utf-8"))
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imported.append(module)
            for alias in node.names:
                imported.append(f"{module}.{alias.name}" if module else alias.name)

    for item in imported:
        assert not item.startswith("src.ui"), item
        segments = set(item.split("."))
        overlap = segments & FORBIDDEN_IMPORT_SEGMENTS
        assert not overlap, f"shell imports {item!r} ({sorted(overlap)})"
