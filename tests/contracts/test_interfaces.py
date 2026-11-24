"""T03 contract ratification. Headless: no GUI, no flet runtime import of contracts."""

from __future__ import annotations

import ast
import inspect
import json
import re
from dataclasses import fields
from pathlib import Path
from typing import Any, get_args

import pytest

from flet_visual_builder import contracts as c

REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACTS_PATH = REPO_ROOT / "src" / "flet_visual_builder" / "contracts.py"
SCHEMA_PATH = (
    REPO_ROOT / "src" / "flet_visual_builder" / "schema" / "project.schema.json"
)
FIXTURES = Path(__file__).resolve().parent / "fixtures"
LEGACY_FIXTURE = FIXTURES / "legacy-0.1-minimal.json"
REFERENCE_EXPORT = FIXTURES / "reference_export.py"

# Every named shared interface in TDD v2 §2.3.3. A future deletion fails loudly.
REQUIRED_INTERFACE_NAMES: tuple[str, ...] = (
    "JsonScalar",
    "JsonValue",
    "JsonObject",
    "NodeId",
    "Severity",
    "Diagnostic",
    "EventSymbol",
    "Node",
    "Asset",
    "Project",
    "DocumentSnapshot",
    "DropIntent",
    "Command",
    "InsertNode",
    "DeleteNode",
    "MoveNode",
    "WrapNode",
    "SetProperty",
    "UnsetProperty",
    "SetEvent",
    "ReplaceProject",
    "Undo",
    "Redo",
    "CommandADT",
    "CommandStatus",
    "CommandResult",
    "CommandReducer",
    "CommandDispatcher",
    "Unset",
    "SymbolRef",
    "LiteralValue",
    "CallValue",
    "SequenceValue",
    "MappingValue",
    "AssetValue",
    "ValueExpr",
    "ValueCodec",
    "PropertySpec",
    "SlotSpec",
    "WidgetSpec",
    "Catalogue",
    "NodePlan",
    "ControlPlan",
    "LoweringResult",
    "Lowerer",
    "RenderMode",
    "RenderResult",
    "PreviewRenderer",
    "ExportOptions",
    "GeneratedArtifact",
    "CodeGenerator",
    "CreateDrag",
    "MoveDrag",
    "DragPayload",
    "DragStatus",
    "DragSession",
    "Point",
    "Size",
    "TargetKey",
    "TargetDescriptor",
    "DropFeedback",
    "DesignActions",
    "TargetMount",
    "DesignProjection",
    "DesignChrome",
    "EditorTab",
    "ShellMountPoints",
    "RegionName",
    "Shell",
)

VALID_V2_PROJECT: dict[str, Any] = {
    "name": "Example",
    "page": {},
    "root_ids": ["root"],
    "nodes": {
        "root": {
            "id": "root",
            "type_id": "Column",
            "props": {},
            "slots": {"controls": []},
            "events": {"on_click": {"name": "handle_root_click"}},
        }
    },
    "assets": {},
    "schema_version": 2,
    "catalogue_version": 1,
    "target_flet": "1.0.1",
}

_JSON_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


def _resolve_ref(schema: dict[str, Any], root: dict[str, Any]) -> dict[str, Any]:
    ref = schema.get("$ref")
    if not ref:
        return schema
    prefix = "#/$defs/"
    if not isinstance(ref, str) or not ref.startswith(prefix):
        raise ValueError(f"unsupported $ref: {ref!r}")
    name = ref[len(prefix) :]
    return root["$defs"][name]


def validate_against_schema(
    instance: Any,
    schema: dict[str, Any],
    *,
    root: dict[str, Any] | None = None,
    path: str = "$",
) -> list[str]:
    """Hand-written structural JSON Schema check (jsonschema is not installed)."""
    root = root if root is not None else schema
    schema = _resolve_ref(schema, root)
    errors: list[str] = []
    expected = schema.get("type")
    if expected is not None:
        py = _JSON_TYPES[expected]
        if expected == "integer" and isinstance(instance, bool):
            errors.append(f"{path}: expected integer, got bool")
            return errors
        if expected == "number" and isinstance(instance, bool):
            errors.append(f"{path}: expected number, got bool")
            return errors
        if not isinstance(instance, py):
            errors.append(f"{path}: expected {expected}, got {type(instance).__name__}")
            return errors
    if "const" in schema and instance != schema["const"]:
        errors.append(f"{path}: expected const {schema['const']!r}, got {instance!r}")
    pattern = schema.get("pattern")
    if pattern is not None and isinstance(instance, str):
        if re.fullmatch(pattern, instance) is None:
            errors.append(f"{path}: {instance!r} does not match {pattern}")
    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append(f"{path}: missing required property {key!r}")
        props = schema.get("properties", {})
        additional = schema.get("additionalProperties", True)
        for key, value in instance.items():
            child = f"{path}.{key}"
            if key in props:
                errors.extend(
                    validate_against_schema(value, props[key], root=root, path=child)
                )
            elif additional is False:
                errors.append(f"{path}: unexpected property {key!r}")
            elif isinstance(additional, dict):
                errors.extend(
                    validate_against_schema(value, additional, root=root, path=child)
                )
    if isinstance(instance, list) and "items" in schema:
        item_schema = schema["items"]
        for i, item in enumerate(instance):
            errors.extend(
                validate_against_schema(
                    item, item_schema, root=root, path=f"{path}[{i}]"
                )
            )
    return errors


def test_contracts_module_imports() -> None:
    assert c.Project is not None
    assert CONTRACTS_PATH.is_file()


def test_every_section_2_3_3_name_exists() -> None:
    missing = [name for name in REQUIRED_INTERFACE_NAMES if not hasattr(c, name)]
    found = len(REQUIRED_INTERFACE_NAMES) - len(missing)
    assert not missing, (
        f"asserted {len(REQUIRED_INTERFACE_NAMES)} §2.3.3 names, "
        f"found {found}, missing {missing}"
    )
    assert found == len(REQUIRED_INTERFACE_NAMES)


def test_public_definitions_are_importable_by_name() -> None:
    for name in REQUIRED_INTERFACE_NAMES:
        assert getattr(c, name) is not None


def test_contracts_does_not_import_flet_at_runtime() -> None:
    tree = ast.parse(CONTRACTS_PATH.read_text(encoding="utf-8"))

    class RuntimeImportVisitor(ast.NodeVisitor):
        def visit_If(self, node: ast.If) -> None:
            if isinstance(node.test, ast.Name) and node.test.id == "TYPE_CHECKING":
                for child in node.orelse:
                    self.visit(child)
                return
            self.generic_visit(node)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                assert alias.name != "flet" and not alias.name.startswith("flet.")

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            assert node.module != "flet" and not (node.module or "").startswith("flet.")

    RuntimeImportVisitor().visit(tree)


def test_event_symbol_accepts_handle_prefixed_identifiers() -> None:
    assert c.EventSymbol("handle_save").name == "handle_save"
    assert c.EventSymbol("handle_reset_click").name == "handle_reset_click"


@pytest.mark.parametrize(
    "name",
    [
        "on_save",
        "class",
        "1abc",
        "handle_x; import os",
        "handle_x\nimport os",
    ],
)
def test_event_symbol_rejects_invalid_names(name: str) -> None:
    with pytest.raises(ValueError, match="Invalid event symbol"):
        c.EventSymbol(name)


def test_index_semantics_are_documented() -> None:
    drop_src = inspect.getsource(c.DropIntent)
    target_src = inspect.getsource(c.TargetKey)
    assert "Index AFTER removal" in drop_src
    assert (
        "BEFORE source removal; normalized by the resolver exactly once." in target_src
    )


def test_project_literal_defaults() -> None:
    schema = c.Project.__dataclass_fields__["schema_version"]
    catalogue = c.Project.__dataclass_fields__["catalogue_version"]
    target = c.Project.__dataclass_fields__["target_flet"]
    assert schema.default == 3
    assert catalogue.default == 1
    assert target.default == "1.0.1"
    empty_nodes: dict[str, c.Node] = {}
    empty_assets: dict[str, c.Asset] = {}
    project = c.Project(
        name="n",
        page={},
        root_ids=(),
        nodes=empty_nodes,
        assets=empty_assets,
    )
    assert project.schema_version == 3
    assert project.catalogue_version == 1
    assert project.target_flet == "1.0.1"


def test_export_options_pins() -> None:
    opts = c.ExportOptions()
    assert opts.formatter == "black==25.1.0"
    assert opts.line_length == 88
    assert opts.python_target == "py312"
    by_name = {f.name: f.default for f in fields(c.ExportOptions)}
    assert by_name["formatter"] == "black==25.1.0"
    assert by_name["line_length"] == 88
    assert by_name["python_target"] == "py312"


def test_legacy_fixture_is_schema_0_1() -> None:
    data = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    assert data["schema_version"] == "0.1"


def test_reference_export_compiles_and_calls_ft_run_main() -> None:
    source = REFERENCE_EXPORT.read_text(encoding="utf-8")
    tree = ast.parse(source)
    assert isinstance(tree, ast.Module)
    text = ast.dump(tree)
    assert "ft.run(main)" in source
    assert "run" in text


def test_command_adt_members() -> None:
    members = get_args(c.CommandADT)
    assert members == (
        c.InsertNode,
        c.DeleteNode,
        c.MoveNode,
        c.WrapNode,
        c.SetProperty,
        c.UnsetProperty,
        c.SetEvent,
        c.ReplaceProject,
        c.RenameProject,
        c.PasteNodes,
        c.SetScreen,
        c.AddScreen,
        c.DeleteScreen,
        c.SetAction,
        c.Undo,
        c.Redo,
    )


def test_enum_values() -> None:
    assert {m.value for m in c.CommandStatus} == {"committed", "noop", "rejected"}
    assert {m.value for m in c.RenderMode} == {"preview", "design_sample"}
    assert {m.value for m in c.DragStatus} == {"active", "consumed", "cancelled"}
    assert {m.value for m in c.Severity} == {"error", "warning", "info"}


def test_target_key_kind_literal() -> None:
    annotation = str(c.TargetKey.__dataclass_fields__["kind"].type)
    for kind in ("rail", "empty_slot", "zone"):
        assert kind in annotation


def test_pagespec_is_set_property_none_node() -> None:
    src = inspect.getsource(c.SetProperty)
    assert "PageSpec" in src
    assert "NodeId | None" in str(c.SetProperty.__dataclass_fields__["node_id"].type)


def test_shell_region_names() -> None:
    assert get_args(c.RegionName) == (
        "toolbar",
        "palette",
        "tree",
        "inspector",
        "design",
        "preview",
        "code",
        "diagnostics",
    )


def test_v2_schema_file_exists_and_names_project_shape() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["type"] == "object"
    assert schema["properties"]["schema_version"]["const"] == 2
    required = set(schema["required"])
    assert {
        "name",
        "page",
        "root_ids",
        "nodes",
        "assets",
        "schema_version",
        "catalogue_version",
        "target_flet",
    } <= required
    assert "node" in schema["$defs"]
    assert "asset" in schema["$defs"]
    assert "event_symbol" in schema["$defs"]


def test_valid_v2_project_passes_handwritten_schema_check() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors = validate_against_schema(VALID_V2_PROJECT, schema)
    assert errors == []


def test_legacy_fixture_fails_v2_schema_negative_control() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    legacy = json.loads(LEGACY_FIXTURE.read_text(encoding="utf-8"))
    errors = validate_against_schema(legacy, schema)
    assert errors, "legacy v0.1 fixture must fail v2 schema (negative control)"
    joined = " ".join(errors)
    assert "schema_version" in joined or "missing required" in joined
