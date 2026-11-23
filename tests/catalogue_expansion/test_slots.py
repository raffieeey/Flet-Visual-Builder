import pytest

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.engine.runtime import RuntimeRenderer
from tests.contracts.rendering.helpers import lower_ok, make_node, make_snapshot


@pytest.mark.parametrize(
    ("parent_type", "slot", "child_type", "prop"),
    [
        ("Chip", "label", "Text", "label"),
        ("ExpansionTile", "title", "Text", "title"),
        ("TabBar", "tabs", "Tab", "tabs"),
        ("TabBarView", "controls", "Text", "controls"),
        ("SafeArea", "content", "Text", "content"),
        ("RadioGroup", "content", "Radio", "content"),
    ],
)
def test_property_can_be_replaced_by_a_child_slot(parent_type, slot, child_type, prop):
    props = catalogue.new_props(parent_type)
    props.pop(prop)
    parent = make_node("parent", parent_type, props=props, slots={slot: ("child",)})
    child = make_node("child", child_type, props=catalogue.new_props(child_type))
    plan = lower_ok(make_snapshot(parent, child))
    rendered = RuntimeRenderer().render_plan(plan)
    assert rendered.root is not None, rendered.diagnostics
    actual = getattr(rendered.by_node["parent"], slot)
    if catalogue.widget(parent_type).slots[slot].maximum is None:
        assert actual == [rendered.by_node["child"]]
    else:
        assert actual is rendered.by_node["child"]
