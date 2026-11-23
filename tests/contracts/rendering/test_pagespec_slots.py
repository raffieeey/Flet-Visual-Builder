"""PageSpec projection, child order, slots, and assets."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import AssetValue, LiteralValue, RenderMode
from flet_visual_builder.engine.runtime import iter_controls

from tests.contracts.rendering.helpers import (
    RENDERER,
    TINY_PNG,
    lower_ok,
    make_asset,
    make_node,
    make_snapshot,
    widget_node,
    widget_snapshot,
)


def test_pagespec_projection_uses_pagelet_and_themed_container() -> None:
    snapshot = widget_snapshot(
        "Text",
        page={
            "title": "Profile settings",
            "padding": 24,
            "scroll": "AUTO",
            "theme_mode": "LIGHT",
            "theme": {"color_scheme_seed": "INDIGO"},
            "appbar": {"title": "Generated Flet application"},
        },
    )
    result = RENDERER.render_plan(lower_ok(snapshot))
    assert result.root is not None
    assert isinstance(result.root, ft.Pagelet)
    assert result.root.data == {"page_title": "Profile settings"}
    assert isinstance(result.root.appbar, ft.AppBar)
    assert isinstance(result.root.appbar.title, ft.Text)
    assert result.root.appbar.title.value == "Generated Flet application"
    host = result.root.content
    assert isinstance(host, ft.Container)
    assert host.theme_mode is ft.ThemeMode.LIGHT
    assert host.theme is not None
    assert host.theme.color_scheme_seed is ft.Colors.INDIGO
    assert host.padding == ft.Padding.all(24)
    inner = host.content
    assert isinstance(inner, ft.Column)
    assert inner.scroll is ft.ScrollMode.AUTO
    assert inner.controls[0] is result.by_node["root"]


def test_pagespec_null_appbar_and_theme() -> None:
    snapshot = widget_snapshot(
        "Text",
        page={
            "title": "Untitled",
            "padding": 24,
            "scroll": None,
            "theme_mode": "DARK",
            "theme": None,
            "appbar": None,
        },
    )
    result = RENDERER.render_plan(lower_ok(snapshot))
    assert isinstance(result.root, ft.Pagelet)
    assert result.root.appbar is None
    host = result.root.content
    assert isinstance(host, ft.Container)
    assert host.theme is None
    assert host.theme_mode is ft.ThemeMode.DARK


def test_children_order_and_slots_agree() -> None:
    texts = [
        widget_node("Text", node_id="a", props={"value": "a"}),
        widget_node("Text", node_id="b", props={"value": "b"}),
        widget_node("Text", node_id="c", props={"value": "c"}),
    ]
    column = widget_node(
        "Column",
        slots={"controls": ("a", "b", "c")},
    )
    snapshot = make_snapshot(column, *texts)
    plan = lower_ok(snapshot)
    assert plan.nodes["root"].slots["controls"] == ("a", "b", "c")
    result = RENDERER.render_plan(plan)
    rendered = result.by_node["root"]
    assert isinstance(rendered, ft.Column)
    assert [child.value for child in rendered.controls] == ["a", "b", "c"]
    assert rendered.controls[0] is result.by_node["a"]
    assert rendered.controls[1] is result.by_node["b"]
    assert rendered.controls[2] is result.by_node["c"]


def test_single_child_content_slot() -> None:
    child = widget_node("Text", node_id="inner", props={"value": "hello"})
    box = widget_node("Container", slots={"content": ("inner",)})
    plan = lower_ok(make_snapshot(box, child))
    assert plan.nodes["root"].slots["content"] == ("inner",)
    result = RENDERER.render_plan(plan)
    container = result.by_node["root"]
    assert isinstance(container, ft.Container)
    assert container.content is result.by_node["inner"]
    assert container.content.value == "hello"


def test_asset_image_src_is_asset_bytes() -> None:
    asset = make_asset("pic", TINY_PNG)
    snapshot = widget_snapshot(
        "Image",
        props={"src": {"kind": "asset", "asset_id": "pic"}},
        assets={"pic": asset},
    )
    plan = lower_ok(snapshot)
    src_expr = plan.nodes["root"].properties["src"]
    assert isinstance(src_expr, AssetValue)
    assert src_expr.asset_id == "pic"
    result = RENDERER.render_plan(plan)
    image = result.by_node["root"]
    assert isinstance(image, ft.Image)
    assert image.src == TINY_PNG


def test_builtin_image_lowers_to_literal_and_constructs() -> None:
    snapshot = widget_snapshot("Image")
    plan = lower_ok(snapshot)
    assert isinstance(plan.nodes["root"].properties["src"], LiteralValue)
    assert plan.nodes["root"].properties["src"].value == "builtin"
    result = RENDERER.render_plan(plan)
    assert isinstance(result.by_node["root"], ft.Image)
    assert result.mode is RenderMode.PREVIEW
