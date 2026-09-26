"""Clean preview rendering: ControlPlan -> real Flet controls.

Constructor/enum resolution uses the frozen catalogue allowlist only.
Project strings never reach eval, exec, dynamic import, or getattr.
Design chrome (frames, drag handles, drop targets) is not constructed here.
"""
from __future__ import annotations

import inspect
from collections.abc import Callable, Mapping
from typing import Any

import flet as ft

from src.flet_visual_builder.catalogue.enum_manifest import (
    COLORS,
    CONTROL_STATE,
    ENUM_FAMILIES,
    ICONS,
)
from src.flet_visual_builder.catalogue.widgets import WIDGET_ORDER
from src.flet_visual_builder.contracts import (
    AssetValue,
    CallValue,
    ControlPlan,
    Diagnostic,
    LiteralValue,
    MappingValue,
    NodeId,
    NodePlan,
    RenderMode,
    RenderResult,
    SequenceValue,
    Severity,
    SymbolRef,
    ValueExpr,
)
from src.flet_visual_builder.engine.lowering import (
    ALLOWED_SYMBOL_PATHS,
    CODE_ASSET_MISSING,
    CODE_SYMBOL_NOT_ALLOWLISTED,
    VALUE_CONSTRUCTOR_PATHS,
    is_allowlisted,
)

CODE_OCCUPIED_SLOT = "ENGINE_OCCUPIED_SLOT"
CODE_UNKNOWN_NODE = "ENGINE_UNKNOWN_NODE"
CODE_CONSTRUCT = "ENGINE_CONSTRUCT"
CODE_MISSING_CHILD = "ENGINE_MISSING_CHILD"


class _RenderRefuse(Exception):
    def __init__(self, diagnostic: Diagnostic) -> None:
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


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


def _trusted_getattr(owner: object, name: str) -> object:
    """getattr used only for catalogue-trusted names while building the table."""
    return getattr(owner, name)


def _build_ft_symbol_table() -> dict[tuple[str, ...], object]:
    table: dict[tuple[str, ...], object] = {}
    for type_id in WIDGET_ORDER:
        table[(type_id,)] = _trusted_getattr(ft, type_id)
    table[("Padding",)] = ft.Padding
    table[("Padding", "all")] = ft.Padding.all
    table[("Margin",)] = ft.Margin
    table[("Margin", "all")] = ft.Margin.all
    table[("BorderRadius",)] = ft.BorderRadius
    table[("BorderRadius", "all")] = ft.BorderRadius.all
    table[("Border",)] = ft.Border
    table[("Border", "all")] = ft.Border.all
    table[("Border", "only")] = ft.Border.only
    table[("BorderSide",)] = ft.BorderSide
    table[("OutlineInputBorder",)] = ft.OutlineInputBorder
    table[("UnderlineInputBorder",)] = ft.UnderlineInputBorder
    table[("NoInputBorder",)] = ft.NoInputBorder
    table[("Theme",)] = ft.Theme
    table[("AppBar",)] = ft.AppBar
    for family, members in ENUM_FAMILIES.items():
        enum_cls = _trusted_getattr(ft, family)
        for member in members:
            table[(family, member)] = _trusted_getattr(enum_cls, member)
    for name in COLORS:
        table[("Colors", name)] = _trusted_getattr(ft.Colors, name)
    for name in ICONS:
        table[("Icons", name)] = _trusted_getattr(ft.Icons, name)
    for name in CONTROL_STATE:
        table[("ControlState", name)] = _trusted_getattr(ft.ControlState, name)
    extra = VALUE_CONSTRUCTOR_PATHS - set(table)
    if extra:
        raise RuntimeError(f"missing Flet mappings for {sorted(extra)}")
    missing = ALLOWED_SYMBOL_PATHS - set(table)
    if missing:
        raise RuntimeError(
            f"allowlist/Flet table mismatch ({len(missing)} paths)"
        )
    return table


_FT_SYMBOLS: dict[tuple[str, ...], object] = _build_ft_symbol_table()


def resolve_symbol(path: tuple[str, ...]) -> object | None:
    """Look up a catalogue-allowlisted ft symbol. Never getattr on ``path``."""
    if not is_allowlisted(path):
        return None
    return _FT_SYMBOLS.get(path)


def _constructor_params(ctor: Callable[..., Any]) -> set[str] | None:
    try:
        signature = inspect.signature(ctor)
    except (TypeError, ValueError):
        return None
    if any(
        param.kind is inspect.Parameter.VAR_KEYWORD
        for param in signature.parameters.values()
    ):
        return None
    names: set[str] = set()
    for name, param in signature.parameters.items():
        if name == "self":
            continue
        if param.kind in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.KEYWORD_ONLY,
        ):
            names.add(name)
    return names


class RuntimeRenderer:
    """PreviewRenderer: clean PageSpec projection, fresh instances, no chrome."""

    def render_plan(self, plan: ControlPlan) -> RenderResult:
        try:
            by_node, diagnostics = self._build_tree(plan, include_children=True)
            if any(d.severity is Severity.ERROR for d in diagnostics):
                return RenderResult(
                    revision=plan.revision,
                    mode=RenderMode.PREVIEW,
                    root=None,
                    by_node={},
                    diagnostics=tuple(diagnostics),
                )
            roots = [by_node[nid] for nid in plan.root_ids]
            root = self._project_page(plan, roots)
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.PREVIEW,
                root=root,
                by_node=by_node,
                diagnostics=tuple(diagnostics),
            )
        except _RenderRefuse as refused:
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.PREVIEW,
                root=None,
                by_node={},
                diagnostics=(refused.diagnostic,),
            )
        except Exception as exc:
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.PREVIEW,
                root=None,
                by_node={},
                diagnostics=(
                    _error(CODE_CONSTRUCT, f"preview construction failed: {exc}"),
                ),
            )

    def render_leaf_sample(self, plan: ControlPlan, node_id: NodeId) -> RenderResult:
        node = plan.nodes.get(node_id)
        if node is None:
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.DESIGN_SAMPLE,
                root=None,
                by_node={},
                diagnostics=(
                    _error(
                        CODE_UNKNOWN_NODE,
                        f"unknown node {node_id!r}",
                        node_id=node_id,
                    ),
                ),
            )
        occupied = [
            slot for slot, ids in node.slots.items() if len(ids) > 0
        ]
        if occupied:
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.DESIGN_SAMPLE,
                root=None,
                by_node={},
                diagnostics=(
                    _error(
                        CODE_OCCUPIED_SLOT,
                        "render_leaf_sample rejects nodes with occupied child slots",
                        path=("slots", occupied[0]),
                        node_id=node_id,
                    ),
                ),
            )
        try:
            control = self._construct_node(plan, node, children_by_slot={})
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.DESIGN_SAMPLE,
                root=control,
                by_node={node_id: control},
                diagnostics=(),
            )
        except _RenderRefuse as refused:
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.DESIGN_SAMPLE,
                root=None,
                by_node={},
                diagnostics=(refused.diagnostic,),
            )
        except Exception as exc:
            return RenderResult(
                revision=plan.revision,
                mode=RenderMode.DESIGN_SAMPLE,
                root=None,
                by_node={},
                diagnostics=(
                    _error(
                        CODE_CONSTRUCT,
                        f"leaf sample construction failed: {exc}",
                        node_id=node_id,
                    ),
                ),
            )

    def _build_tree(
        self, plan: ControlPlan, *, include_children: bool
    ) -> tuple[dict[NodeId, ft.Control], list[Diagnostic]]:
        by_node: dict[NodeId, ft.Control] = {}
        diagnostics: list[Diagnostic] = []
        for node_id in _postorder(plan):
            node = plan.nodes.get(node_id)
            if node is None:
                raise _RenderRefuse(
                    _error(
                        CODE_UNKNOWN_NODE,
                        f"unknown node {node_id!r}",
                        node_id=node_id,
                    )
                )
            children_by_slot: dict[str, list[ft.Control]] = {}
            if include_children:
                for slot, ids in node.slots.items():
                    slot_controls: list[ft.Control] = []
                    for child_id in ids:
                        child = by_node.get(child_id)
                        if child is None:
                            raise _RenderRefuse(
                                _error(
                                    CODE_MISSING_CHILD,
                                    f"missing child {child_id!r} for slot {slot!r}",
                                    path=("slots", slot),
                                    node_id=node_id,
                                )
                            )
                        slot_controls.append(child)
                    children_by_slot[slot] = slot_controls
            by_node[node_id] = self._construct_node(
                plan, node, children_by_slot=children_by_slot
            )
        return by_node, diagnostics

    def _construct_node(
        self,
        plan: ControlPlan,
        node: NodePlan,
        *,
        children_by_slot: Mapping[str, list[ft.Control]],
    ) -> ft.Control:
        ctor = resolve_symbol(node.constructor.path)
        if ctor is None or not callable(ctor):
            raise _RenderRefuse(
                _error(
                    CODE_SYMBOL_NOT_ALLOWLISTED,
                    "constructor is not in the catalogue allowlist: "
                    + ".".join(node.constructor.path),
                    node_id=node.node_id,
                )
            )
        kwargs: dict[str, Any] = {}
        for name, expr in node.properties.items():
            kwargs[name] = self._eval_expr(
                expr, plan, node_id=node.node_id, path=("props", name)
            )
        for slot, children in children_by_slot.items():
            if not children:
                if slot == "controls" and slot not in kwargs:
                    kwargs[slot] = []
                continue
            if slot in kwargs:
                raise _RenderRefuse(
                    _error(
                        CODE_CONSTRUCT,
                        f"slot {slot!r} cannot combine a property value with children",
                        path=("slots", slot),
                        node_id=node.node_id,
                    )
                )
            if slot == "controls":
                kwargs[slot] = list(children)
            else:
                kwargs[slot] = children[0] if len(children) == 1 else list(children)
        allowed = _constructor_params(ctor)
        if allowed is not None:
            unknown = [key for key in kwargs if key not in allowed]
            if unknown:
                raise _RenderRefuse(
                    _error(
                        CODE_CONSTRUCT,
                        f"unsupported constructor argument {unknown[0]!r}",
                        path=("props", unknown[0]),
                        node_id=node.node_id,
                    )
                )
        try:
            control = ctor(**kwargs)
        except _RenderRefuse:
            raise
        except Exception as exc:
            raise _RenderRefuse(
                _error(
                    CODE_CONSTRUCT,
                    f"{node.type_id} construction failed: {exc}",
                    node_id=node.node_id,
                )
            ) from exc
        if not isinstance(control, ft.Control):
            raise _RenderRefuse(
                _error(
                    CODE_CONSTRUCT,
                    f"{node.type_id} did not produce a Flet control",
                    node_id=node.node_id,
                )
            )
        return control

    def _eval_expr(
        self,
        expr: ValueExpr,
        plan: ControlPlan,
        *,
        node_id: NodeId | None,
        path: tuple[str | int, ...],
    ) -> Any:
        if isinstance(expr, LiteralValue):
            return expr.value
        if isinstance(expr, SymbolRef):
            resolved = resolve_symbol(expr.path)
            if resolved is None:
                raise _RenderRefuse(
                    _error(
                        CODE_SYMBOL_NOT_ALLOWLISTED,
                        "constructor/enum symbol is not in the catalogue allowlist: "
                        + ".".join(expr.path),
                        path=path,
                        node_id=node_id,
                    )
                )
            return resolved
        if isinstance(expr, CallValue):
            ctor = resolve_symbol(expr.constructor.path)
            if ctor is None or not callable(ctor):
                raise _RenderRefuse(
                    _error(
                        CODE_SYMBOL_NOT_ALLOWLISTED,
                        "constructor is not in the catalogue allowlist: "
                        + ".".join(expr.constructor.path),
                        path=path,
                        node_id=node_id,
                    )
                )
            args = [
                self._eval_expr(
                    arg, plan, node_id=node_id, path=path + (index,)
                )
                for index, arg in enumerate(expr.args)
            ]
            kwargs = {
                key: self._eval_expr(
                    value, plan, node_id=node_id, path=path + (key,)
                )
                for key, value in expr.kwargs.items()
            }
            try:
                return ctor(*args, **kwargs)
            except _RenderRefuse:
                raise
            except Exception as exc:
                raise _RenderRefuse(
                    _error(
                        CODE_CONSTRUCT,
                        f"value construction failed: {exc}",
                        path=path,
                        node_id=node_id,
                    )
                ) from exc
        if isinstance(expr, SequenceValue):
            return [
                self._eval_expr(item, plan, node_id=node_id, path=path + (index,))
                for index, item in enumerate(expr.items)
            ]
        if isinstance(expr, MappingValue):
            mapping: dict[Any, Any] = {}
            for index, (key_expr, value_expr) in enumerate(expr.items):
                key = self._eval_expr(
                    key_expr, plan, node_id=node_id, path=path + (index, "key")
                )
                value = self._eval_expr(
                    value_expr, plan, node_id=node_id, path=path + (index, "value")
                )
                mapping[key] = value
            return mapping
        if isinstance(expr, AssetValue):
            asset = plan.assets.get(expr.asset_id)
            if asset is None:
                raise _RenderRefuse(
                    _error(
                        CODE_ASSET_MISSING,
                        f"asset {expr.asset_id!r} is not in the plan",
                        path=path,
                        node_id=node_id,
                    )
                )
            return asset.data
        raise _RenderRefuse(
            _error(
                CODE_CONSTRUCT,
                f"unsupported value expression {type(expr).__name__}",
                path=path,
                node_id=node_id,
            )
        )

    def _project_page(
        self, plan: ControlPlan, roots: list[ft.Control]
    ) -> ft.Pagelet:
        """Supported PageSpec adapter: themed Container inside a Pagelet."""
        page_values: dict[str, Any] = {}
        for name, expr in plan.page_properties.items():
            page_values[name] = self._eval_expr(
                expr, plan, node_id=None, path=("page", name)
            )
        scroll = page_values.get("scroll")
        column = ft.Column(controls=list(roots), scroll=scroll)
        host_kwargs: dict[str, Any] = {"content": column}
        if "padding" in page_values:
            host_kwargs["padding"] = page_values["padding"]
        if "theme" in page_values:
            host_kwargs["theme"] = page_values["theme"]
        if "theme_mode" in page_values:
            host_kwargs["theme_mode"] = page_values["theme_mode"]
        host = ft.Container(**host_kwargs)
        pagelet_kwargs: dict[str, Any] = {"content": host}
        if "appbar" in page_values:
            pagelet_kwargs["appbar"] = page_values["appbar"]
        title = page_values.get("title")
        if title is not None:
            pagelet_kwargs["data"] = {"page_title": title}
        return ft.Pagelet(**pagelet_kwargs)


def _postorder(plan: ControlPlan) -> list[NodeId]:
    seen: set[NodeId] = set()
    order: list[NodeId] = []

    def visit(node_id: NodeId) -> None:
        if node_id in seen:
            return
        seen.add(node_id)
        node = plan.nodes.get(node_id)
        if node is None:
            return
        for ids in node.slots.values():
            for child_id in ids:
                visit(child_id)
        order.append(node_id)

    for root_id in plan.root_ids:
        visit(root_id)
    for node_id in plan.nodes:
        visit(node_id)
    return order


def iter_controls(root: ft.Control | None) -> list[ft.Control]:
    """Depth-first walk of Flet controls (tests and chrome assertions)."""
    if root is None:
        return []
    found: list[ft.Control] = []
    stack: list[ft.Control] = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        marker = id(control)
        if marker in seen:
            continue
        seen.add(marker)
        found.append(control)
        content = getattr(control, "content", None)
        if isinstance(content, ft.Control):
            stack.append(content)
        controls = getattr(control, "controls", None)
        if isinstance(controls, list):
            for child in reversed(controls):
                if isinstance(child, ft.Control):
                    stack.append(child)
        for attr in (
            "appbar",
            "error_content",
            "leading",
            "title",
            "navigation_bar",
            "bottom_appbar",
            "bottom_sheet",
            "drawer",
            "end_drawer",
            "floating_action_button",
        ):
            child = getattr(control, attr, None)
            if isinstance(child, ft.Control):
                stack.append(child)
        actions = getattr(control, "actions", None)
        if isinstance(actions, list):
            for child in reversed(actions):
                if isinstance(child, ft.Control):
                    stack.append(child)
    return found


__all__ = [
    "CODE_CONSTRUCT",
    "CODE_MISSING_CHILD",
    "CODE_OCCUPIED_SLOT",
    "CODE_UNKNOWN_NODE",
    "RuntimeRenderer",
    "iter_controls",
    "resolve_symbol",
]
