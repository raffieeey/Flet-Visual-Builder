"""Deterministic Python export from a validated ControlPlan (TDD v2 §2.6 / §6).

Ordering is defined here, never by incidental dict iteration:

* page attributes follow ``PAGE_PROPERTIES`` declaration order
* widget keyword arguments follow ``WidgetSpec.properties`` then slots then events
* nested constructor kwargs follow a per-constructor field order, then name
* children follow ``root_ids`` and each slot's child-id tuple
* event stubs follow a preorder tree walk with event names sorted per node
"""
from __future__ import annotations

import ast
import keyword
import math
from collections.abc import Mapping, Sequence

from src.flet_visual_builder.catalogue import catalogue
from src.flet_visual_builder.catalogue.enum_manifest import (
    COLORS,
    CONTROL_STATE,
    ENUM_FAMILIES,
    ICONS,
)
from src.flet_visual_builder.catalogue.page import PAGE_PROPERTIES
from src.flet_visual_builder.contracts import (
    AssetValue,
    CallValue,
    ControlPlan,
    Diagnostic,
    EventSymbol,
    ExportOptions,
    GeneratedArtifact,
    LiteralValue,
    MappingValue,
    NodeId,
    NodePlan,
    SequenceValue,
    Severity,
    SymbolRef,
    ValueExpr,
)
from src.flet_visual_builder.engine.formatting import FORMATTER_SPEC, format_python

FILENAME = "generated_app.py"

CODE_INVALID_OPTIONS = "CODEGEN_INVALID_OPTIONS"
CODE_TARGET = "CODEGEN_TARGET_MISMATCH"
CODE_CATALOGUE = "CODEGEN_CATALOGUE_VERSION"
CODE_UNKNOWN_WIDGET = "CODEGEN_UNKNOWN_WIDGET"
CODE_UNKNOWN_NODE = "CODEGEN_UNKNOWN_NODE"
CODE_UNKNOWN_PROPERTY = "CODEGEN_UNKNOWN_PROPERTY"
CODE_UNKNOWN_SLOT = "CODEGEN_UNKNOWN_SLOT"
CODE_UNKNOWN_EVENT = "CODEGEN_UNKNOWN_EVENT"
CODE_UNKNOWN_SYMBOL = "CODEGEN_UNKNOWN_SYMBOL"
CODE_UNKNOWN_ASSET = "CODEGEN_UNKNOWN_ASSET"
CODE_CYCLE = "CODEGEN_CYCLE"
CODE_DUPLICATE = "CODEGEN_DUPLICATE_NODE"
CODE_EVENT_SYMBOL = "CODEGEN_EVENT_SYMBOL"
CODE_CONSTRUCTOR = "CODEGEN_CONSTRUCTOR"
CODE_SLOT_OCCUPANCY = "CODEGEN_SLOT_OCCUPANCY"
CODE_UNION = "CODEGEN_SCALAR_CONTROL_UNION"
CODE_SYNTAX = "CODEGEN_SYNTAX"
CODE_IDENTIFIER = "CODEGEN_INVALID_IDENTIFIER"
CODE_UNSUPPORTED = "CODEGEN_UNSUPPORTED_EXPR"

_COMPOUND_PATHS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("Padding",),
        ("Padding", "all"),
        ("Margin",),
        ("Margin", "all"),
        ("BorderRadius",),
        ("BorderRadius", "all"),
        ("Border",),
        ("Border", "all"),
        ("Border", "only"),
        ("BorderSide",),
        ("OutlineInputBorder",),
        ("UnderlineInputBorder",),
        ("NoInputBorder",),
        ("Theme",),
        ("AppBar",),
    }
)

_CALL_KWARG_ORDER: dict[tuple[str, ...], tuple[str, ...]] = {
    ("Padding",): ("left", "top", "right", "bottom"),
    ("Margin",): ("left", "top", "right", "bottom"),
    ("BorderRadius",): ("top_left", "top_right", "bottom_left", "bottom_right"),
    ("Border", "all"): ("width", "color"),
    ("Border", "only"): ("left", "top", "right", "bottom"),
    ("BorderSide",): ("width", "color"),
    ("OutlineInputBorder",): ("side", "border_radius", "gap_padding"),
    ("UnderlineInputBorder",): ("side", "border_radius"),
    ("Theme",): ("color_scheme_seed",),
    ("AppBar",): ("title",),
}

_STUB_COMMENT = "# Add application behavior in the exported application."


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    node_id: NodeId | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
        node_id=node_id,
    )


def _is_identifier(name: str) -> bool:
    return name.isidentifier() and not keyword.iskeyword(name)


def _event_symbol_name(node_id: str, event_name: str) -> str:
    rest = event_name[3:] if event_name.startswith("on_") else event_name
    return f"handle_{node_id}_{rest}"


def _ordered_keys(
    mapping: Mapping[str, object], order: Sequence[str]
) -> tuple[str, ...]:
    present = set(mapping)
    extra = sorted(present.difference(order))
    return tuple(key for key in order if key in present) + tuple(extra)


def _ordered_kwargs(
    path: tuple[str, ...], kwargs: Mapping[str, ValueExpr]
) -> tuple[tuple[str, ValueExpr], ...]:
    order = _CALL_KWARG_ORDER.get(path, ())
    keys = _ordered_keys(kwargs, order)
    return tuple((key, kwargs[key]) for key in keys)


def _symbol_allowed(path: tuple[str, ...]) -> bool:
    if not path or not all(_is_identifier(part) for part in path):
        return False
    if path in _COMPOUND_PATHS:
        return True
    if len(path) == 1 and path[0] in catalogue.widgets:
        return True
    if len(path) != 2:
        return False
    family, member = path
    if family == "Colors":
        return member in COLORS
    if family == "Icons":
        return member in ICONS
    if family == "ControlState":
        return member in CONTROL_STATE
    allowed = ENUM_FAMILIES.get(family)
    return allowed is not None and member in allowed


def _ft_attr(path: tuple[str, ...]) -> str:
    return "ft." + ".".join(path)


def _render_literal(value: object) -> str:
    if value is None:
        return "None"
    if isinstance(value, bool):
        return "True" if value else "False"
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, str):
        return repr(value)
    raise TypeError(f"unsupported literal {type(value)!r}")


def _mapping_sort_key(expr: ValueExpr) -> tuple[object, ...]:
    if isinstance(expr, LiteralValue):
        return (0, repr(expr.value))
    if isinstance(expr, SymbolRef):
        return (1, expr.path)
    if isinstance(expr, CallValue):
        return (2, expr.constructor.path)
    if isinstance(expr, AssetValue):
        return (3, expr.asset_id)
    return (4, type(expr).__name__)


class Codegen:
    """``CodeGenerator`` implementation. Same plan ⇒ byte-identical source."""

    def generate_python(
        self, plan: ControlPlan, options: ExportOptions
    ) -> GeneratedArtifact:
        diagnostics = _validate_request(plan, options)
        errors = tuple(d for d in diagnostics if d.severity is Severity.ERROR)
        if errors:
            return _failed(plan, options, errors)
        source = _emit(plan)
        formatted = format_python(source, line_length=options.line_length)
        try:
            ast.parse(formatted)
            compile(formatted, FILENAME, "exec")
        except SyntaxError as exc:
            return _failed(
                plan,
                options,
                (_error(CODE_SYNTAX, f"generated source is not valid Python: {exc}"),),
            )
        return GeneratedArtifact(
            source=formatted,
            filename=FILENAME,
            target_flet=plan.target_flet,
            formatter=options.formatter,
            document_sha256=plan.document_sha256,
            diagnostics=(),
        )


def _failed(
    plan: ControlPlan,
    options: ExportOptions,
    diagnostics: tuple[Diagnostic, ...],
) -> GeneratedArtifact:
    return GeneratedArtifact(
        source="",
        filename=FILENAME,
        target_flet=options.target_flet,
        formatter=options.formatter,
        document_sha256=plan.document_sha256,
        diagnostics=diagnostics,
    )


def _validate_request(
    plan: ControlPlan, options: ExportOptions
) -> tuple[Diagnostic, ...]:
    diags: list[Diagnostic] = []
    if options.formatter != FORMATTER_SPEC:
        diags.append(
            _error(
                CODE_INVALID_OPTIONS,
                f"formatter must be {FORMATTER_SPEC!r}",
                path=("options", "formatter"),
            )
        )
    if options.target_flet != "1.0.1":
        diags.append(
            _error(
                CODE_INVALID_OPTIONS,
                "target_flet must be '1.0.1'",
                path=("options", "target_flet"),
            )
        )
    if options.python_target != "py312":
        diags.append(
            _error(
                CODE_INVALID_OPTIONS,
                "python_target must be 'py312'",
                path=("options", "python_target"),
            )
        )
    if options.line_length != 88:
        diags.append(
            _error(
                CODE_INVALID_OPTIONS,
                "line_length must be 88",
                path=("options", "line_length"),
            )
        )
    if options.include_event_stubs is not True:
        diags.append(
            _error(
                CODE_INVALID_OPTIONS,
                "include_event_stubs must be True",
                path=("options", "include_event_stubs"),
            )
        )
    if plan.target_flet != options.target_flet:
        diags.append(
            _error(
                CODE_TARGET,
                "plan target_flet does not match export options",
                path=("target_flet",),
            )
        )
    if plan.catalogue_version != catalogue.version:
        diags.append(
            _error(
                CODE_CATALOGUE,
                "plan catalogue_version is not the frozen catalogue",
                path=("catalogue_version",),
            )
        )
    diags.extend(_validate_page(plan))
    diags.extend(_validate_graph(plan))
    return tuple(diags)


def _validate_page(plan: ControlPlan) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    for name in _ordered_keys(plan.page_properties, tuple(PAGE_PROPERTIES)):
        if name not in PAGE_PROPERTIES:
            diags.append(
                _error(
                    CODE_UNKNOWN_PROPERTY,
                    f"unknown PageSpec property {name!r}",
                    path=("page", name),
                )
            )
            continue
        diags.extend(
            _validate_expr(
                plan.page_properties[name],
                plan,
                path=("page", name),
                node_id=None,
            )
        )
    return diags


def _validate_graph(plan: ControlPlan) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    visiting: set[NodeId] = set()
    seen: set[NodeId] = set()

    def walk(node_id: NodeId, path: tuple[str | int, ...]) -> None:
        if node_id not in plan.nodes:
            diags.append(
                _error(
                    CODE_UNKNOWN_NODE,
                    f"unknown node {node_id!r}",
                    path=path,
                    node_id=node_id,
                )
            )
            return
        if node_id in visiting:
            diags.append(
                _error(
                    CODE_CYCLE,
                    f"cycle at node {node_id!r}",
                    path=path,
                    node_id=node_id,
                )
            )
            return
        if node_id in seen:
            diags.append(
                _error(
                    CODE_DUPLICATE,
                    f"node {node_id!r} is referenced more than once",
                    path=path,
                    node_id=node_id,
                )
            )
            return
        visiting.add(node_id)
        diags.extend(_validate_node(plan, plan.nodes[node_id]))
        node = plan.nodes[node_id]
        spec = catalogue.widgets.get(node.type_id)
        slot_order = tuple(spec.slots) if spec is not None else tuple(node.slots)
        for slot_name in _ordered_keys(node.slots, slot_order):
            for index, child_id in enumerate(node.slots[slot_name]):
                walk(child_id, ("nodes", node_id, "slots", slot_name, index))
        visiting.remove(node_id)
        seen.add(node_id)

    for index, root_id in enumerate(plan.root_ids):
        walk(root_id, ("root_ids", index))
    return diags


def _validate_node(plan: ControlPlan, node: NodePlan) -> list[Diagnostic]:
    diags: list[Diagnostic] = []
    path_base: tuple[str | int, ...] = ("nodes", node.node_id)
    if node.type_id not in catalogue.widgets:
        diags.append(
            _error(
                CODE_UNKNOWN_WIDGET,
                f"unknown widget type {node.type_id!r}",
                path=path_base + ("type_id",),
                node_id=node.node_id,
            )
        )
        return diags
    spec = catalogue.widget(node.type_id)
    if node.constructor.path != spec.constructor.path:
        diags.append(
            _error(
                CODE_CONSTRUCTOR,
                "node constructor is not the catalogue constructor",
                path=path_base + ("constructor",),
                node_id=node.node_id,
            )
        )
    prop_order = tuple(spec.properties)
    for name in _ordered_keys(node.properties, prop_order):
        if name not in spec.properties:
            diags.append(
                _error(
                    CODE_UNKNOWN_PROPERTY,
                    f"unknown property {name!r} on {node.type_id}",
                    path=path_base + ("properties", name),
                    node_id=node.node_id,
                )
            )
            continue
        diags.extend(
            _validate_expr(
                node.properties[name],
                plan,
                path=path_base + ("properties", name),
                node_id=node.node_id,
            )
        )
    slot_order = tuple(spec.slots)
    for name in _ordered_keys(node.slots, slot_order):
        if name not in spec.slots:
            diags.append(
                _error(
                    CODE_UNKNOWN_SLOT,
                    f"unknown slot {name!r} on {node.type_id}",
                    path=path_base + ("slots", name),
                    node_id=node.node_id,
                )
            )
            continue
        children = node.slots[name]
        maximum = spec.slots[name].maximum
        if maximum is not None and len(children) > maximum:
            diags.append(
                _error(
                    CODE_SLOT_OCCUPANCY,
                    f"slot {name!r} exceeds maximum {maximum}",
                    path=path_base + ("slots", name),
                    node_id=node.node_id,
                )
            )
        if name in node.properties and children:
            diags.append(
                _error(
                    CODE_UNION,
                    f"slot {name!r} cannot be populated together with the "
                    f"same-named property",
                    path=path_base + ("slots", name),
                    node_id=node.node_id,
                )
            )
    for name in sorted(node.events):
        if name not in spec.events:
            diags.append(
                _error(
                    CODE_UNKNOWN_EVENT,
                    f"unknown event {name!r} on {node.type_id}",
                    path=path_base + ("events", name),
                    node_id=node.node_id,
                )
            )
            continue
        symbol = node.events[name]
        expected = _event_symbol_name(node.node_id, name)
        if symbol.name != expected:
            diags.append(
                _error(
                    CODE_EVENT_SYMBOL,
                    f"event symbol {symbol.name!r} does not match {expected!r}",
                    path=path_base + ("events", name),
                    node_id=node.node_id,
                )
            )
    return diags


def _validate_expr(
    expr: ValueExpr,
    plan: ControlPlan,
    *,
    path: tuple[str | int, ...],
    node_id: NodeId | None,
) -> list[Diagnostic]:
    if isinstance(expr, LiteralValue):
        value = expr.value
        if value is None or isinstance(value, (str, bool)):
            return []
        if isinstance(value, int) and not isinstance(value, bool):
            return []
        if isinstance(value, float) and math.isfinite(value):
            return []
        return [
            _error(
                CODE_UNSUPPORTED,
                "literal is not a JSON scalar",
                path=path,
                node_id=node_id,
            )
        ]
    if isinstance(expr, SymbolRef):
        if _symbol_allowed(expr.path):
            return []
        return [
            _error(
                CODE_UNKNOWN_SYMBOL,
                f"symbol {expr.path!r} is not allowlisted",
                path=path,
                node_id=node_id,
            )
        ]
    if isinstance(expr, CallValue):
        diags: list[Diagnostic] = []
        if not _symbol_allowed(expr.constructor.path):
            diags.append(
                _error(
                    CODE_UNKNOWN_SYMBOL,
                    f"constructor {expr.constructor.path!r} is not allowlisted",
                    path=path,
                    node_id=node_id,
                )
            )
        for index, arg in enumerate(expr.args):
            diags.extend(
                _validate_expr(
                    arg, plan, path=path + (index,), node_id=node_id
                )
            )
        for name, value in _ordered_kwargs(expr.constructor.path, expr.kwargs):
            if not _is_identifier(name):
                diags.append(
                    _error(
                        CODE_IDENTIFIER,
                        f"keyword {name!r} is not a valid identifier",
                        path=path + (name,),
                        node_id=node_id,
                    )
                )
                continue
            diags.extend(
                _validate_expr(
                    value, plan, path=path + (name,), node_id=node_id
                )
            )
        return diags
    if isinstance(expr, SequenceValue):
        diags = []
        for index, item in enumerate(expr.items):
            diags.extend(
                _validate_expr(
                    item, plan, path=path + (index,), node_id=node_id
                )
            )
        return diags
    if isinstance(expr, MappingValue):
        diags = []
        ordered = sorted(expr.items, key=lambda pair: _mapping_sort_key(pair[0]))
        for index, (key, value) in enumerate(ordered):
            diags.extend(
                _validate_expr(
                    key, plan, path=path + (index, 0), node_id=node_id
                )
            )
            diags.extend(
                _validate_expr(
                    value, plan, path=path + (index, 1), node_id=node_id
                )
            )
        return diags
    if isinstance(expr, AssetValue):
        if expr.asset_id not in plan.assets:
            return [
                _error(
                    CODE_UNKNOWN_ASSET,
                    f"unknown asset {expr.asset_id!r}",
                    path=path,
                    node_id=node_id,
                )
            ]
        return []
    return [
        _error(
            CODE_UNSUPPORTED,
            f"unsupported value expression {type(expr).__name__}",
            path=path,
            node_id=node_id,
        )
    ]


def _emit(plan: ControlPlan) -> str:
    events = _collect_events(plan)
    used_assets = _collect_assets(plan)
    lines: list[str] = [
        f'"""Flet Visual Builder export. Target: {plan.target_flet}."""',
        "",
    ]
    if events:
        lines.append("from collections.abc import Callable")
        lines.append("")
    lines.append("import flet as ft")
    lines.append("")
    if used_assets:
        lines.append("_ASSETS = {")
        for asset_id in used_assets:
            payload = plan.assets[asset_id].data.hex()
            lines.append(f"    {asset_id!r}: bytes.fromhex({payload!r}),")
        lines.append("}")
        lines.append("")
    lines.extend(_emit_build_ui(plan, events))
    lines.append("")
    lines.extend(_emit_main(plan, events))
    lines.append("")
    lines.append("if __name__ == \"__main__\":")
    lines.append("    ft.run(main)")
    lines.append("")
    return "\n".join(lines)


def _collect_events(plan: ControlPlan) -> tuple[tuple[EventSymbol, str], ...]:
    collected: list[tuple[EventSymbol, str]] = []
    seen: set[str] = set()

    def visit(node_id: NodeId) -> None:
        node = plan.nodes[node_id]
        spec = catalogue.widget(node.type_id)
        for event_name in sorted(node.events):
            symbol = node.events[event_name]
            if symbol.name in seen:
                continue
            seen.add(symbol.name)
            collected.append((symbol, node.type_id))
        for slot_name in _ordered_keys(node.slots, tuple(spec.slots)):
            for child_id in node.slots[slot_name]:
                visit(child_id)

    for root_id in plan.root_ids:
        visit(root_id)
    return tuple(collected)


def _collect_assets(plan: ControlPlan) -> tuple[str, ...]:
    found: set[str] = set()

    def walk_expr(expr: ValueExpr) -> None:
        if isinstance(expr, AssetValue):
            found.add(expr.asset_id)
        elif isinstance(expr, CallValue):
            for arg in expr.args:
                walk_expr(arg)
            for _, value in _ordered_kwargs(expr.constructor.path, expr.kwargs):
                walk_expr(value)
        elif isinstance(expr, SequenceValue):
            for item in expr.items:
                walk_expr(item)
        elif isinstance(expr, MappingValue):
            for key, value in expr.items:
                walk_expr(key)
                walk_expr(value)

    def visit(node_id: NodeId) -> None:
        node = plan.nodes[node_id]
        spec = catalogue.widget(node.type_id)
        for name in _ordered_keys(node.properties, tuple(spec.properties)):
            walk_expr(node.properties[name])
        for slot_name in _ordered_keys(node.slots, tuple(spec.slots)):
            for child_id in node.slots[slot_name]:
                visit(child_id)

    for name in _ordered_keys(plan.page_properties, tuple(PAGE_PROPERTIES)):
        walk_expr(plan.page_properties[name])
    for root_id in plan.root_ids:
        visit(root_id)
    return tuple(sorted(found))


def _emit_build_ui(
    plan: ControlPlan, events: tuple[tuple[EventSymbol, str], ...]
) -> list[str]:
    if events:
        params = ", ".join(
            f"{symbol.name}: Callable[[ft.Event[ft.{type_id}]], None]"
            for symbol, type_id in events
        )
        header = f"def build_ui({params}) -> ft.Control:"
    else:
        header = "def build_ui() -> ft.Control:"
    body = _render_tree(plan)
    return [header, f"    return {body}"]


def _emit_main(
    plan: ControlPlan, events: tuple[tuple[EventSymbol, str], ...]
) -> list[str]:
    lines = ["def main(page: ft.Page) -> None:"]
    assigned = False
    for name in _ordered_keys(plan.page_properties, tuple(PAGE_PROPERTIES)):
        expr = plan.page_properties[name]
        if isinstance(expr, LiteralValue) and expr.value is None:
            continue
        lines.append(f"    page.{name} = {_render_expr(expr)}")
        assigned = True
    if assigned:
        lines.append("")
    for symbol, type_id in events:
        lines.append(f"    def {symbol.name}(e: ft.Event[ft.{type_id}]) -> None:")
        lines.append(f"        {_STUB_COMMENT}")
        lines.append("        pass")
        lines.append("")
    if events:
        args = ", ".join(symbol.name for symbol, _ in events)
        lines.append(f"    page.add(build_ui({args}))")
    else:
        lines.append("    page.add(build_ui())")
    return lines


def _render_tree(plan: ControlPlan) -> str:
    if not plan.root_ids:
        return "ft.Column()"
    if len(plan.root_ids) == 1:
        return _render_node(plan, plan.root_ids[0])
    children = ", ".join(_render_node(plan, node_id) for node_id in plan.root_ids)
    return f"ft.Column(controls=[{children}])"


def _render_node(plan: ControlPlan, node_id: NodeId) -> str:
    node = plan.nodes[node_id]
    spec = catalogue.widget(node.type_id)
    pieces: list[str] = []
    emitted: set[str] = set()
    for name in _ordered_keys(node.properties, tuple(spec.properties)):
        pieces.append(f"{name}={_render_expr(node.properties[name])}")
        emitted.add(name)
    for slot_name in _ordered_keys(node.slots, tuple(spec.slots)):
        if slot_name in emitted:
            continue
        children = node.slots[slot_name]
        if not children:
            continue
        maximum = spec.slots[slot_name].maximum
        if maximum == 1:
            pieces.append(f"{slot_name}={_render_node(plan, children[0])}")
        else:
            rendered = ", ".join(_render_node(plan, child_id) for child_id in children)
            pieces.append(f"{slot_name}=[{rendered}]")
        emitted.add(slot_name)
    for event_name in sorted(node.events):
        symbol = node.events[event_name]
        pieces.append(f"{event_name}={symbol.name}")
    ctor = _ft_attr(spec.constructor.path)
    if not pieces:
        return f"{ctor}()"
    return f"{ctor}({', '.join(pieces)})"


def _render_expr(expr: ValueExpr) -> str:
    if isinstance(expr, LiteralValue):
        return _render_literal(expr.value)
    if isinstance(expr, SymbolRef):
        return _ft_attr(expr.path)
    if isinstance(expr, CallValue):
        args = [_render_expr(arg) for arg in expr.args]
        kwargs = [
            f"{name}={_render_expr(value)}"
            for name, value in _ordered_kwargs(expr.constructor.path, expr.kwargs)
        ]
        inner = ", ".join(args + kwargs)
        name = _ft_attr(expr.constructor.path)
        return f"{name}({inner})"
    if isinstance(expr, SequenceValue):
        inner = ", ".join(_render_expr(item) for item in expr.items)
        return f"[{inner}]"
    if isinstance(expr, MappingValue):
        ordered = sorted(expr.items, key=lambda pair: _mapping_sort_key(pair[0]))
        inner = ", ".join(
            f"{_render_expr(key)}: {_render_expr(value)}" for key, value in ordered
        )
        return f"{{{inner}}}"
    if isinstance(expr, AssetValue):
        return f"_ASSETS[{expr.asset_id!r}]"
    raise TypeError(f"unsupported expression {type(expr).__name__}")
