import py_compile

import flet as ft
import pytest

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.catalogue.codecs import CODECS
from flet_visual_builder.contracts import ExportOptions, Severity
from flet_visual_builder.engine.codegen import Codegen
from flet_visual_builder.engine.lowering import Lowering
from flet_visual_builder.engine.runtime import RuntimeRenderer
from tests.contracts.rendering.helpers import make_node, make_snapshot, widget_snapshot


def errors(items):
    return [item for item in items if item.severity is Severity.ERROR]


def test_catalogue_structure():
    assert len(catalogue.widgets) >= 36
    for spec in catalogue.widgets.values():
        assert all(prop.codec_id in CODECS for prop in spec.properties.values())
        assert len({slot.name for slot in spec.slots.values()}) == len(spec.slots)


@pytest.mark.parametrize("type_id", tuple(catalogue.widgets))
def test_widget_end_to_end(type_id, tmp_path):
    props = catalogue.new_props(type_id)
    assert not errors(catalogue.validate_props(type_id, props))
    result = Lowering().lower_project(widget_snapshot(type_id), catalogue)
    assert not errors(result.diagnostics)
    assert result.plan is not None
    artifact = Codegen().generate_python(result.plan, ExportOptions())
    assert not errors(artifact.diagnostics)
    source = tmp_path / "generated.py"
    source.write_text(artifact.source)
    py_compile.compile(str(source), doraise=True)
    rendered = RuntimeRenderer().render_plan(result.plan)
    assert not errors(rendered.diagnostics)
    assert rendered.root is not None
    assert isinstance(rendered.by_node["root"], getattr(ft, type_id))


def test_page_projection_and_export():
    page = {
        "bgcolor": "INDIGO",
        "adaptive": True,
        "rtl": True,
        "horizontal_alignment": "CENTER",
    }
    assert not errors(catalogue.validate_page(page))
    plan_result = Lowering().lower_project(
        widget_snapshot("Text", page=page), catalogue
    )
    assert plan_result.plan is not None, plan_result.diagnostics
    result = RuntimeRenderer().render_plan(plan_result.plan)
    assert not errors(result.diagnostics)
    assert result.root.bgcolor == ft.Colors.INDIGO
    assert result.root.rtl is True
    assert result.root.adaptive is True
    assert (
        result.root.content.content.horizontal_alignment == ft.CrossAxisAlignment.CENTER
    )
    source = Codegen().generate_python(plan_result.plan, ExportOptions()).source
    for name in page:
        assert f"page.{name} =" in source


def test_single_child_non_controls_list_slot():
    parent = make_node(
        "parent", "NavigationBar", props={}, slots={"destinations": ("child",)}
    )
    child = make_node(
        "child",
        "NavigationBarDestination",
        props=catalogue.new_props("NavigationBarDestination"),
    )
    lowered = Lowering().lower_project(make_snapshot(parent, child), catalogue)
    assert lowered.plan is not None, lowered.diagnostics
    result = RuntimeRenderer().render_plan(lowered.plan)
    assert not errors(result.diagnostics)
    assert isinstance(result.by_node["parent"].destinations, list)
    assert len(result.by_node["parent"].destinations) == 1
