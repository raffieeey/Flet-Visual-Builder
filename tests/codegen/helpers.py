"""Builders for codegen tests. Plans are constructed from catalogue codecs."""
from __future__ import annotations

from collections.abc import Mapping

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import (
    Asset,
    CallValue,
    ControlPlan,
    EventSymbol,
    JsonValue,
    MappingValue,
    NodeId,
    NodePlan,
    SequenceValue,
    ValueExpr,
)
from flet_visual_builder.catalogue.widgets import WIDGET_ORDER

SHA = "a" * 64


def lower_props(type_id: str, props: Mapping[str, JsonValue]) -> dict[str, ValueExpr]:
    spec = catalogue.widget(type_id)
    return {
        name: catalogue.lower_value(spec.properties[name], value)
        for name, value in props.items()
    }


def lower_page(page: Mapping[str, JsonValue]) -> dict[str, ValueExpr]:
    return {
        name: catalogue.lower_value(catalogue.page_properties[name], value)
        for name, value in page.items()
    }


def make_node_plan(
    node_id: str,
    type_id: str,
    *,
    props: Mapping[str, JsonValue] | None = None,
    slots: Mapping[str, tuple[NodeId, ...]] | None = None,
    events: Mapping[str, EventSymbol] | None = None,
) -> NodePlan:
    spec = catalogue.widget(type_id)
    return NodePlan(
        node_id=node_id,
        type_id=type_id,
        constructor=spec.constructor,
        properties=lower_props(type_id, props or {}),
        slots=dict(slots or {}),
        events=dict(events or {}),
    )


def make_plan(
    *nodes: NodePlan,
    root_ids: tuple[NodeId, ...] | None = None,
    page: Mapping[str, JsonValue] | None = None,
    assets: Mapping[str, Asset] | None = None,
    document_sha256: str = SHA,
    revision: int = 1,
    target_flet: str = "1.0.1",
    catalogue_version: int = 1,
) -> ControlPlan:
    mapping = {node.node_id: node for node in nodes}
    if root_ids is None:
        root_ids = (nodes[0].node_id,) if nodes else ()
    return ControlPlan(
        revision=revision,
        document_sha256=document_sha256,
        target_flet=target_flet,
        catalogue_version=catalogue_version,
        page_properties=lower_page(page or {}),
        root_ids=root_ids,
        nodes=mapping,
        assets=dict(assets or {}),
    )


def reverse_expr(expr: ValueExpr) -> ValueExpr:
    if isinstance(expr, CallValue):
        reversed_kwargs = {
            key: reverse_expr(value)
            for key, value in reversed(list(expr.kwargs.items()))
        }
        return CallValue(
            constructor=expr.constructor,
            args=tuple(reverse_expr(arg) for arg in expr.args),
            kwargs=reversed_kwargs,
        )
    if isinstance(expr, SequenceValue):
        return SequenceValue(items=tuple(reverse_expr(item) for item in expr.items))
    if isinstance(expr, MappingValue):
        return MappingValue(
            items=tuple(
                (reverse_expr(key), reverse_expr(value))
                for key, value in reversed(expr.items)
            )
        )
    return expr


def reverse_plan_mappings(plan: ControlPlan) -> ControlPlan:
    """Reverse dict iteration order without changing child-id tuples or roots."""
    page = {
        name: reverse_expr(expr)
        for name, expr in reversed(list(plan.page_properties.items()))
    }
    nodes: dict[str, NodePlan] = {}
    for node_id in reversed(list(plan.nodes)):
        node = plan.nodes[node_id]
        nodes[node_id] = NodePlan(
            node_id=node.node_id,
            type_id=node.type_id,
            constructor=node.constructor,
            properties={
                name: reverse_expr(expr)
                for name, expr in reversed(list(node.properties.items()))
            },
            slots={
                name: children
                for name, children in reversed(list(node.slots.items()))
            },
            events={
                name: symbol
                for name, symbol in reversed(list(node.events.items()))
            },
        )
    assets = {key: plan.assets[key] for key in reversed(list(plan.assets))}
    return ControlPlan(
        revision=plan.revision,
        document_sha256=plan.document_sha256,
        target_flet=plan.target_flet,
        catalogue_version=plan.catalogue_version,
        page_properties=page,
        root_ids=plan.root_ids,
        nodes=nodes,
        assets=assets,
    )


def leaf_from_defaults(type_id: str) -> NodePlan:
    return make_node_plan(type_id, type_id, props=catalogue.new_props(type_id))


def all_widgets_plan() -> ControlPlan:
    leaves = tuple(leaf_from_defaults(type_id) for type_id in WIDGET_ORDER)
    root = make_node_plan(
        "root",
        "Column",
        props={"spacing": 8, "alignment": "START", "horizontal_alignment": "START"},
        slots={"controls": tuple(WIDGET_ORDER)},
    )
    return make_plan(root, *leaves, page={"title": "Catalogue"})


def simple_text_plan(*, value: str = "Hello") -> ControlPlan:
    return make_plan(
        make_node_plan("label", "Text", props={"value": value}),
        page={"title": "Untitled", "padding": 24, "theme_mode": "LIGHT"},
    )


def reference_plan() -> ControlPlan:
    """ControlPlan matching the semantic reference export fixture."""
    person = make_node_plan(
        "person", "Icon", props={"icon": "PERSON", "color": "INDIGO"}
    )
    heading = make_node_plan(
        "heading",
        "Text",
        props={"value": "Profile settings", "size": 24, "weight": "W_600"},
    )
    header = make_node_plan(
        "header",
        "Row",
        props={"spacing": 12, "alignment": "START", "vertical_alignment": "START"},
        slots={"controls": ("person", "heading")},
    )
    name = make_node_plan(
        "name",
        "TextField",
        props={
            "label": "Display name",
            "value": "",
            "border": {"kind": "outline"},
        },
    )
    notify = make_node_plan(
        "notify",
        "Checkbox",
        props={"label": "Receive notifications", "value": True},
    )
    enabled = make_node_plan(
        "enabled",
        "Switch",
        props={"label": "Profile enabled", "value": True},
    )
    form = make_node_plan(
        "form",
        "Column",
        props={"spacing": 12, "alignment": "START", "horizontal_alignment": "START"},
        slots={"controls": ("name", "notify", "enabled")},
    )
    card_box = make_node_plan(
        "card_box", "Container", props={"padding": 16}, slots={"content": ("form",)}
    )
    card = make_node_plan("card", "Card", slots={"content": ("card_box",)})
    reset = make_node_plan(
        "reset",
        "TextButton",
        props={"content": "Reset"},
        events={"on_click": EventSymbol("handle_reset_click")},
    )
    save = make_node_plan(
        "save",
        "Button",
        props={"content": "Save", "icon": "SAVE"},
        events={"on_click": EventSymbol("handle_save_click")},
    )
    actions = make_node_plan(
        "actions",
        "Row",
        props={"alignment": "END", "vertical_alignment": "START"},
        slots={"controls": ("reset", "save")},
    )
    divider = make_node_plan("divider", "Divider")
    status = make_node_plan(
        "status", "Text", props={"value": "Ready", "color": "INDIGO"}
    )
    body = make_node_plan(
        "body",
        "Column",
        props={
            "spacing": 16,
            "horizontal_alignment": "STRETCH",
            "alignment": "START",
        },
        slots={"controls": ("header", "card", "actions", "divider", "status")},
    )
    root = make_node_plan(
        "root",
        "Container",
        props={
            "alignment": "TOP_LEFT",
            "border": {"all": {"width": 1, "color": "BLACK_12"}},
            "padding": 20,
            "width": 640,
        },
        slots={"content": ("body",)},
    )
    return make_plan(
        root,
        body,
        header,
        person,
        heading,
        card,
        card_box,
        form,
        name,
        notify,
        enabled,
        actions,
        reset,
        save,
        divider,
        status,
        page={
            "title": "Profile settings",
            "padding": 24,
            "scroll": "AUTO",
            "theme_mode": "LIGHT",
            "theme": {"color_scheme_seed": "INDIGO"},
            "appbar": {"title": "Generated Flet application"},
        },
        document_sha256="b" * 64,
    )
