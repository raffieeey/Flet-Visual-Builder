"""Invalid snapshots/plans and the constructor allowlist guard."""
from __future__ import annotations

import ast
from pathlib import Path

import flet as ft

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import (
    CallValue,
    ControlPlan,
    LiteralValue,
    NodePlan,
    RenderMode,
    Severity,
    SymbolRef,
)
from flet_visual_builder.engine.lowering import (
    CODE_SYMBOL_NOT_ALLOWLISTED,
    Lowering,
    is_allowlisted,
)
from flet_visual_builder.engine.runtime import (
    CODE_CONSTRUCT,
    RuntimeRenderer,
    resolve_symbol,
)

from tests.contracts.rendering.helpers import (
    LOWERER,
    RENDERER,
    make_node,
    make_snapshot,
    widget_snapshot,
)

ENGINE = Path(__file__).resolve().parents[3] / "src" / "flet_visual_builder" / "engine"


def test_invalid_snapshot_yields_no_plan() -> None:
    snapshot = make_snapshot(make_node("root", "NotAWidget", props={"value": "x"}))
    result = LOWERER.lower_project(snapshot, catalogue)
    assert result.plan is None
    errors = [d for d in result.diagnostics if d.severity is Severity.ERROR]
    assert errors
    assert CODE_SYMBOL_NOT_ALLOWLISTED in {d.code for d in errors} or any(
        "Unknown widget" in d.message or "allowlist" in d.message for d in errors
    )


def test_invalid_property_yields_no_plan() -> None:
    snapshot = widget_snapshot("Text", props={"size": "huge"})
    result = LOWERER.lower_project(snapshot, catalogue)
    assert result.plan is None
    assert any(d.severity is Severity.ERROR for d in result.diagnostics)


def test_unknown_page_key_yields_no_plan() -> None:
    snapshot = widget_snapshot("Text", page={"title": "T", "mystery": 1})
    result = LOWERER.lower_project(snapshot, catalogue)
    assert result.plan is None
    assert any(d.severity is Severity.ERROR for d in result.diagnostics)


def test_render_plan_does_not_raise_on_invalid_plan() -> None:
    plan = ControlPlan(
        revision=9,
        document_sha256="00",
        target_flet="1.0.1",
        catalogue_version=1,
        page_properties={},
        root_ids=("missing",),
        nodes={},
        assets={},
    )
    result = RENDERER.render_plan(plan)
    assert result.root is None
    assert result.by_node == {}
    assert result.mode is RenderMode.PREVIEW
    assert result.revision == 9
    assert any(d.severity is Severity.ERROR for d in result.diagnostics)


def test_smuggled_constructor_symbol_is_refused() -> None:
    plan = ControlPlan(
        revision=1,
        document_sha256="00",
        target_flet="1.0.1",
        catalogue_version=1,
        page_properties={},
        root_ids=("root",),
        nodes={
            "root": NodePlan(
                node_id="root",
                type_id="Text",
                constructor=SymbolRef(("eval",)),
                properties={"value": LiteralValue("x")},
                slots={},
                events={},
            )
        },
        assets={},
    )
    result = RENDERER.render_plan(plan)
    assert result.root is None
    errors = [d for d in result.diagnostics if d.severity is Severity.ERROR]
    assert errors
    assert any(d.code == CODE_SYMBOL_NOT_ALLOWLISTED for d in errors)
    assert resolve_symbol(("eval",)) is None
    assert not is_allowlisted(("eval",))
    assert not is_allowlisted(("os", "system"))
    assert not is_allowlisted(("Colors", "__class__"))


def test_smuggled_callvalue_is_refused() -> None:
    plan = ControlPlan(
        revision=1,
        document_sha256="00",
        target_flet="1.0.1",
        catalogue_version=1,
        page_properties={},
        root_ids=("root",),
        nodes={
            "root": NodePlan(
                node_id="root",
                type_id="Text",
                constructor=SymbolRef(("Text",)),
                properties={
                    "value": CallValue(
                        constructor=SymbolRef(("os", "system")),
                        args=(LiteralValue("echo hi"),),
                        kwargs={},
                    )
                },
                slots={},
                events={},
            )
        },
        assets={},
    )
    result = RENDERER.render_plan(plan)
    assert result.root is None
    assert any(d.code == CODE_SYMBOL_NOT_ALLOWLISTED for d in result.diagnostics)


def test_allowlisted_symbols_resolve_without_project_getattr() -> None:
    assert resolve_symbol(("Text",)) is ft.Text
    assert resolve_symbol(("Button",)) is ft.Button
    assert resolve_symbol(("Colors", "INDIGO")) is ft.Colors.INDIGO
    assert resolve_symbol(("Icons", "HOME")) is ft.Icons.HOME
    assert resolve_symbol(("FontWeight", "W_500")) is ft.FontWeight.W_500
    padding_all = resolve_symbol(("Padding", "all"))
    assert callable(padding_all)
    assert padding_all(24) == ft.Padding.all(24)
    assert is_allowlisted(("Text",))
    assert is_allowlisted(("Colors", "INDIGO"))
    assert not is_allowlisted(("__builtins__", "eval"))


def test_engine_source_has_no_eval_exec_or_dynamic_import() -> None:
    for path in (ENGINE / "lowering.py", ENGINE / "runtime.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"eval", "exec"}
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert alias.name != "importlib"
            if isinstance(node, ast.ImportFrom):
                assert node.module != "importlib" and not (node.module or "").startswith(
                    "importlib."
                )


def test_resolve_symbol_never_getattr_on_path_segments() -> None:
    """A project-supplied path is a dict key, not a getattr chain."""
    source = (ENGINE / "runtime.py").read_text(encoding="utf-8")
    assert "getattr(ft, expr" not in source
    assert "getattr(ft, path" not in source
    assert "getattr(ft, name)" not in source or "_trusted_getattr(ft, type_id)" in source
    # Lookup function uses the prebuilt table only.
    assert "return _FT_SYMBOLS.get(path)" in source
    assert resolve_symbol(("Colors", "__dict__")) is None
    assert resolve_symbol(("ft", "Page")) is None
