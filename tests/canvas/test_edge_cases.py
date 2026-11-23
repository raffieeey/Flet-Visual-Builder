from dataclasses import replace
from types import SimpleNamespace

from flet_visual_builder.app_context import Workspace
from flet_visual_builder.contracts import Severity
from flet_visual_builder.engine.runtime import iter_controls
from flet_visual_builder.services.starter import empty_project
from flet_visual_builder.ui.canvas import Canvas
from tests.support.fake_page import FakePage


def test_invalid_plan_shows_first_blocking_diagnostic():
    project = empty_project()
    root = project.nodes["root"]
    broken = replace(
        project, nodes={"root": replace(root, props={"not_a_property": 3})}
    )
    ws = Workspace(FakePage(), broken)
    diagnostic = next(d for d in ws.diagnostics() if d.severity == Severity.ERROR)
    canvas = Canvas(ws)
    values = [
        getattr(control, "value", None) for control in iter_controls(canvas.control)
    ]
    assert f"{diagnostic.code}: {diagnostic.message}" in values
    assert not canvas.frames


def test_interactive_leaf_is_inert_and_empty_root_has_drop_area():
    ws = Workspace(FakePage(), empty_project())
    canvas = Canvas(ws)
    root = canvas.frames["root"]
    assert root.box.width == 300 and root.box.height == 120
    # Root with no measured size cannot silently accept a drop.
    root.target.on_accept(
        SimpleNamespace(
            src=SimpleNamespace(data="create:Text"),
            local_position=SimpleNamespace(x=0, y=0),
        )
    )
    assert len(ws.project.nodes) == 1
    ws.insert("Button", "root", "controls", 0)
    canvas.rebuild()
    button = canvas.frames[ws.editor.selection]
    assert button.box.content.controls[0].ignore_interactions is True
