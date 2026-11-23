"""Supplementary validation rules (TDD v2 §2.4.3 lines 1637-1647)."""

from __future__ import annotations

from flet_visual_builder.catalogue import (
    CODE_BUTTON_CONTENT,
    CODE_CHECKBOX_TRISTATE,
    CODE_LAYOUT_CONSTRAINT,
    CODE_REMOTE_IMAGE,
    CODE_SCALAR_CONTROL_UNION,
    catalogue,
)
from flet_visual_builder.contracts import Node, Severity


def _node(
    type_id: str,
    props: dict | None = None,
    slots: dict | None = None,
    *,
    node_id: str = "n1",
) -> Node:
    return Node(
        id=node_id,
        type_id=type_id,
        props=props or {},
        slots=slots or {},
        events={},
    )


def _codes(node: Node, *, nodes=None) -> set[str]:
    return {d.code for d in catalogue.validate_node(node, nodes=nodes)}


def test_button_requires_meaningful_scalar_child_or_icon() -> None:
    empty = _node("Button", {"content": "", "visible": True, "disabled": False})
    assert CODE_BUTTON_CONTENT in _codes(empty)
    whitespace = _node("Button", {"content": "   "})
    assert CODE_BUTTON_CONTENT in _codes(whitespace)
    text = _node("Button", {"content": "Save"})
    assert CODE_BUTTON_CONTENT not in _codes(text)
    icon_only = _node("Button", {"icon": "SAVE"})
    assert CODE_BUTTON_CONTENT not in _codes(icon_only)
    child = _node(
        "Button",
        {},
        {"content": ("c1",)},
    )
    child_node = _node("Text", {"value": "OK", "visible": True}, node_id="c1")
    assert CODE_BUTTON_CONTENT not in _codes(child, nodes={"c1": child_node})
    hidden = _node("Text", {"value": "OK", "visible": False}, node_id="c1")
    assert CODE_BUTTON_CONTENT in _codes(child, nodes={"c1": hidden})


def test_textbutton_same_content_rule() -> None:
    empty = _node("TextButton", {"content": ""})
    assert CODE_BUTTON_CONTENT in _codes(empty)


def test_checkbox_null_requires_tristate() -> None:
    bad = _node("Checkbox", {"value": None, "tristate": False})
    assert CODE_CHECKBOX_TRISTATE in _codes(bad)
    omitted_tristate = _node("Checkbox", {"value": None})
    assert CODE_CHECKBOX_TRISTATE in _codes(omitted_tristate)
    ok = _node("Checkbox", {"value": None, "tristate": True})
    assert CODE_CHECKBOX_TRISTATE not in _codes(ok)


def test_scalar_control_union_cannot_be_both() -> None:
    both = _node(
        "Button",
        {"content": "Save"},
        {"content": ("c1",)},
    )
    assert CODE_SCALAR_CONTROL_UNION in _codes(both)
    scalar_only = _node("Button", {"content": "Save"})
    assert CODE_SCALAR_CONTROL_UNION not in _codes(scalar_only)


def test_incompatible_layout_column_tight_scroll() -> None:
    node = _node("Column", {"tight": True, "scroll": "AUTO"})
    assert CODE_LAYOUT_CONSTRAINT in _codes(node)
    ok = _node("Column", {"tight": False, "scroll": "AUTO"})
    assert CODE_LAYOUT_CONSTRAINT not in _codes(ok)


def test_incompatible_layout_row_wrap_scroll() -> None:
    node = _node("Row", {"wrap": True, "scroll": "ALWAYS"})
    assert CODE_LAYOUT_CONSTRAINT in _codes(node)


def test_incompatible_layout_listview_unbounded() -> None:
    node = _node("ListView", {"spacing": 0, "horizontal": False, "auto_scroll": False})
    assert CODE_LAYOUT_CONSTRAINT in _codes(node)
    bounded = _node("ListView", {"height": 240})
    assert CODE_LAYOUT_CONSTRAINT not in _codes(bounded)


def test_remote_image_url_policy_diagnostic() -> None:
    node = _node(
        "Image",
        {"src": {"kind": "url", "url": "https://example.com/a.png"}},
    )
    diags = catalogue.validate_node(node)
    remote = [d for d in diags if d.code == CODE_REMOTE_IMAGE]
    assert remote
    assert remote[0].severity is Severity.WARNING
    builtin = _node("Image", {"src": {"kind": "builtin"}})
    assert CODE_REMOTE_IMAGE not in _codes(builtin)
