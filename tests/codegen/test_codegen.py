"""Deterministic generation: AST, import, construction, PageSpec, events."""
from __future__ import annotations

import ast
import importlib.util
import inspect
import sys
from pathlib import Path
from types import ModuleType

import flet as ft
import pytest

from src.flet_visual_builder.catalogue import catalogue
from src.flet_visual_builder.catalogue.page import PAGE_PROPERTIES
from src.flet_visual_builder.catalogue.widgets import WIDGET_ORDER
from src.flet_visual_builder.contracts import (
    Asset,
    AssetValue,
    ControlPlan,
    EventSymbol,
    ExportOptions,
    LiteralValue,
    NodePlan,
    Severity,
    SymbolRef,
)
from src.flet_visual_builder.engine.codegen import FILENAME, Codegen
from src.flet_visual_builder.engine.formatting import format_python
from tests.codegen.helpers import (
    all_widgets_plan,
    make_node_plan,
    make_plan,
    reference_plan,
    reverse_plan_mappings,
    simple_text_plan,
)

PAGE_KEYS = frozenset(PAGE_PROPERTIES)
GENERATOR = Codegen()
OPTIONS = ExportOptions()
GOLDEN = Path(__file__).resolve().parent / "golden" / "reference.py.golden"


def generate(plan: ControlPlan, options: ExportOptions = OPTIONS) -> str:
    artifact = GENERATOR.generate_python(plan, options)
    assert artifact.diagnostics == ()
    assert artifact.source
    return artifact.source


def parse(source: str) -> ast.Module:
    tree = ast.parse(source)
    compile(source, FILENAME, "exec")
    return tree


def load_generated(source: str, tmp_path: Path, name: str) -> ModuleType:
    path = tmp_path / f"{name}.py"
    path.write_text(source, encoding="utf-8", newline="\n")
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def construct(module: ModuleType) -> ft.Control:
    def noop(e: object | None = None) -> None:
        return None

    params = inspect.signature(module.build_ui).parameters
    root = module.build_ui(**{name: noop for name in params})
    assert isinstance(root, ft.Control)
    return root


def page_assignments(source: str) -> list[str]:
    tree = parse(source)
    names: list[str] = []
    for node in tree.body:
        if not (isinstance(node, ast.FunctionDef) and node.name == "main"):
            continue
        for stmt in node.body:
            if not isinstance(stmt, ast.Assign) or len(stmt.targets) != 1:
                continue
            target = stmt.targets[0]
            if (
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "page"
            ):
                names.append(target.attr)
    return names


def test_artifact_metadata() -> None:
    plan = simple_text_plan()
    artifact = GENERATOR.generate_python(plan, OPTIONS)
    assert artifact.filename == "generated_app.py"
    assert artifact.target_flet == "1.0.1"
    assert artifact.formatter == "black==25.1.0"
    assert artifact.document_sha256 == plan.document_sha256
    assert artifact.diagnostics == ()


def test_source_parses_and_compiles() -> None:
    source = generate(reference_plan())
    tree = parse(source)
    assert isinstance(tree, ast.Module)
    assert "ft.run(main)" in source
    assert "ft.app" not in source
    assert 'if __name__ == "__main__":' in source


def test_black_output_is_stable() -> None:
    source = generate(reference_plan())
    assert source == format_python(source, line_length=88)
    assert source == generate(reference_plan())
    assert max(len(line) for line in source.splitlines()) <= 88


def test_repeated_generation_is_byte_identical() -> None:
    plan = reference_plan()
    first = GENERATOR.generate_python(plan, OPTIONS).source
    second = GENERATOR.generate_python(plan, OPTIONS).source
    assert first == second
    assert first.encode("utf-8") == second.encode("utf-8")


def test_generation_independent_of_mapping_order() -> None:
    plan = reference_plan()
    reversed_plan = reverse_plan_mappings(plan)
    assert generate(plan) == generate(reversed_plan)


def test_property_order_follows_spec_not_dict() -> None:
    spec_order = tuple(catalogue.widget("Text").properties)
    props = {
        "color": "INDIGO",
        "weight": "W_600",
        "value": "Profile settings",
        "size": 24,
    }
    source = generate(make_plan(make_node_plan("label", "Text", props=props)))
    positions = [source.index(f"{name}=") for name in ("value", "size", "weight", "color")]
    assert positions == sorted(positions)
    assert spec_order.index("value") < spec_order.index("size")
    assert spec_order.index("size") < spec_order.index("weight")


def test_pagespec_projection() -> None:
    source = generate(reference_plan())
    assigned = page_assignments(source)
    assert set(assigned) <= PAGE_KEYS
    assert assigned == [
        "title",
        "padding",
        "scroll",
        "theme_mode",
        "theme",
        "appbar",
    ]
    assert "bgcolor" not in assigned
    assert "window" not in assigned
    assert "page.bgcolor" not in source
    assert "page.title = " in source
    assert "ft.ScrollMode.AUTO" in source
    assert "ft.ThemeMode.LIGHT" in source
    assert "ft.Theme(" in source
    assert "ft.AppBar(" in source


def test_null_appbar_is_not_emitted() -> None:
    source = generate(
        make_plan(
            make_node_plan("label", "Text", props={"value": "Hi"}),
            page={"title": "T", "appbar": None},
        )
    )
    assert page_assignments(source) == ["title"]
    assert "page.appbar" not in source


def test_event_stubs_use_handle_form_and_empty_bodies() -> None:
    source = generate(reference_plan())
    assert "handle_reset_click" in source
    assert "handle_save_click" in source
    tree = parse(source)
    main = next(
        node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == "main"
    )
    stubs = [node for node in main.body if isinstance(node, ast.FunctionDef)]
    assert [stub.name for stub in stubs] == ["handle_reset_click", "handle_save_click"]
    for stub in stubs:
        assert len(stub.body) == 1
        assert isinstance(stub.body[0], ast.Pass)
    assert "# Add application behavior in the exported application." in source
    assert "page.update" not in source
    assert "e.control" not in source


def test_import_does_not_call_ft_run(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("ft.run must not be called")

    monkeypatch.setattr(ft, "run", boom)
    source = generate(reference_plan())
    module = load_generated(source, tmp_path, "generated_app_import")
    assert callable(module.build_ui)
    assert callable(module.main)
    construct(module)


def test_build_ui_constructs_on_flet_1_0_1(tmp_path: Path) -> None:
    source = generate(reference_plan())
    module = load_generated(source, tmp_path, "generated_app_construct")
    root = construct(module)
    assert isinstance(root, ft.Container)
    assert root.width == 640


def test_all_catalogue_entries_generate() -> None:
    plan = all_widgets_plan()
    source = generate(plan)
    parse(source)
    for type_id in WIDGET_ORDER:
        assert f"ft.{type_id}(" in source
    assert len(WIDGET_ORDER) == 16
    assert len(catalogue.widgets) == 16


def test_all_catalogue_entries_construct(tmp_path: Path) -> None:
    source = generate(all_widgets_plan())
    module = load_generated(source, tmp_path, "generated_app_catalogue")
    root = construct(module)
    assert isinstance(root, ft.Column)
    assert root.controls is not None
    assert len(root.controls) == 16


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_each_widget_generates_alone(type_id: str) -> None:
    source = generate(
        make_plan(make_node_plan(type_id, type_id, props=catalogue.new_props(type_id)))
    )
    parse(source)
    assert f"ft.{type_id}(" in source


def test_invalid_unknown_widget_returns_empty_source() -> None:
    plan = ControlPlan(
        revision=1,
        document_sha256="c" * 64,
        target_flet="1.0.1",
        catalogue_version=1,
        page_properties={},
        root_ids=("x",),
        nodes={
            "x": NodePlan(
                node_id="x",
                type_id="Nope",
                constructor=SymbolRef(("Nope",)),
                properties={},
                slots={},
                events={},
            )
        },
        assets={},
    )
    artifact = GENERATOR.generate_python(plan, OPTIONS)
    assert artifact.source == ""
    assert artifact.diagnostics
    assert all(d.severity is Severity.ERROR for d in artifact.diagnostics)


def test_invalid_missing_child_returns_empty_source() -> None:
    plan = make_plan(
        make_node_plan("root", "Container", slots={"content": ("missing",)})
    )
    artifact = GENERATOR.generate_python(plan, OPTIONS)
    assert artifact.source == ""
    assert any(d.code == "CODEGEN_UNKNOWN_NODE" for d in artifact.diagnostics)


def test_invalid_cycle_returns_empty_source() -> None:
    plan = make_plan(
        make_node_plan("root", "Container", slots={"content": ("root",)})
    )
    artifact = GENERATOR.generate_python(plan, OPTIONS)
    assert artifact.source == ""
    assert any(d.code == "CODEGEN_CYCLE" for d in artifact.diagnostics)


def test_invalid_unknown_page_property_returns_empty_source() -> None:
    plan = make_plan(
        make_node_plan("label", "Text", props={"value": "Hi"}),
    )
    bad = ControlPlan(
        revision=plan.revision,
        document_sha256=plan.document_sha256,
        target_flet=plan.target_flet,
        catalogue_version=plan.catalogue_version,
        page_properties={"bgcolor": LiteralValue("INDIGO")},
        root_ids=plan.root_ids,
        nodes=plan.nodes,
        assets=plan.assets,
    )
    artifact = GENERATOR.generate_python(bad, OPTIONS)
    assert artifact.source == ""
    assert any(d.code == "CODEGEN_UNKNOWN_PROPERTY" for d in artifact.diagnostics)


def test_invalid_target_mismatch_returns_empty_source() -> None:
    plan = simple_text_plan()
    mismatched = ControlPlan(
        revision=plan.revision,
        document_sha256=plan.document_sha256,
        target_flet="0.24.1",
        catalogue_version=plan.catalogue_version,
        page_properties=plan.page_properties,
        root_ids=plan.root_ids,
        nodes=plan.nodes,
        assets=plan.assets,
    )
    artifact = GENERATOR.generate_python(mismatched, OPTIONS)
    assert artifact.source == ""
    assert any(d.severity is Severity.ERROR for d in artifact.diagnostics)


def test_invalid_missing_asset_returns_empty_source() -> None:
    plan = ControlPlan(
        revision=1,
        document_sha256="d" * 64,
        target_flet="1.0.1",
        catalogue_version=1,
        page_properties={},
        root_ids=("img",),
        nodes={
            "img": NodePlan(
                node_id="img",
                type_id="Image",
                constructor=SymbolRef(("Image",)),
                properties={"src": AssetValue("missing")},
                slots={},
                events={},
            )
        },
        assets={},
    )
    artifact = GENERATOR.generate_python(plan, OPTIONS)
    assert artifact.source == ""
    assert any(d.code == "CODEGEN_UNKNOWN_ASSET" for d in artifact.diagnostics)


def test_invalid_event_symbol_returns_empty_source() -> None:
    plan = make_plan(
        make_node_plan(
            "save",
            "Button",
            props={"content": "Save"},
            events={"on_click": EventSymbol("handle_wrong_click")},
        )
    )
    artifact = GENERATOR.generate_python(plan, OPTIONS)
    assert artifact.source == ""
    assert any(d.code == "CODEGEN_EVENT_SYMBOL" for d in artifact.diagnostics)


def test_generated_source_has_no_eval_exec() -> None:
    source = generate(reference_plan())
    tree = parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            assert node.func.id not in {"eval", "exec", "__import__", "getattr"}


def test_asset_bytes_are_embedded(tmp_path: Path) -> None:
    payload = bytes.fromhex("89504e470d0a1a0a")
    plan = ControlPlan(
        revision=1,
        document_sha256="e" * 64,
        target_flet="1.0.1",
        catalogue_version=1,
        page_properties={},
        root_ids=("img",),
        nodes={
            "img": NodePlan(
                node_id="img",
                type_id="Image",
                constructor=SymbolRef(("Image",)),
                properties={"src": AssetValue("logo")},
                slots={},
                events={},
            )
        },
        assets={
            "logo": Asset(
                id="logo", media_type="image/png", sha256="f" * 64, data=payload
            )
        },
    )
    source = generate(plan)
    assert "_ASSETS" in source
    assert "bytes.fromhex" in source
    module = load_generated(source, tmp_path, "generated_app_asset")
    root = construct(module)
    assert isinstance(root, ft.Image)


def test_golden_reference_export() -> None:
    source = generate(reference_plan())
    assert GOLDEN.is_file(), "missing tests/codegen/golden/reference.py.golden"
    expected = GOLDEN.read_text(encoding="utf-8")
    assert source == expected
