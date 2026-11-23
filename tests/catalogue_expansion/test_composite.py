import pytest
import flet as ft

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import ExportOptions
from flet_visual_builder.engine.codegen import Codegen
from flet_visual_builder.engine.runtime import RuntimeRenderer
from tests.contracts.rendering.helpers import lower_ok, widget_snapshot


@pytest.mark.parametrize(
    ("widget", "prop", "value", "expected"),
    [
        (
            "Dropdown",
            "options",
            ({"key": "a", "text": "A", "leading_icon": "HOME"},),
            ft.DropdownOption,
        ),
        (
            "NavigationBar",
            "destinations",
            ({"icon": "HOME", "label": "Home"},),
            ft.NavigationBarDestination,
        ),
        (
            "SegmentedButton",
            "segments",
            ({"value": "one", "label": "One", "icon": "HOME"},),
            ft.Segment,
        ),
    ],
)
def test_composite_sequences_lower_export_and_render(widget, prop, value, expected):
    plan = lower_ok(widget_snapshot(widget, props={prop: value}))
    artifact = Codegen().generate_python(plan, ExportOptions())
    assert artifact.diagnostics == ()
    assert f"ft.{expected.__name__}(" in artifact.source
    rendered = RuntimeRenderer().render_plan(plan)
    assert rendered.diagnostics == ()
    actual = getattr(rendered.by_node["root"], prop)
    assert len(actual) == 1 and isinstance(actual[0], expected)


@pytest.mark.parametrize(
    ("codec", "value"),
    [
        ("dropdown_options", ({"text": 42},)),
        ("navigation_destinations", ({"icon": "NOT_AN_ICON"},)),
        ("navigation_destinations", ({"label": "no icon"},)),
        ("segments", ({"value": "x", "bogus": "y"},)),
        ("segments", ()),
        ("tabs", "not a list"),
    ],
)
def test_composite_rejects_invalid_input(codec, value):
    assert catalogue.codecs[codec].validate(value)


def test_required_content_controls_have_constructible_defaults():
    for widget in ("SafeArea", "RadioGroup"):
        assert widget in catalogue.widgets
        plan = lower_ok(widget_snapshot(widget))
        assert RuntimeRenderer().render_plan(plan).root is not None
