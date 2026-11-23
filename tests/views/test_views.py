import asyncio
from dataclasses import replace

import flet as ft

from flet_visual_builder.app_context import Refresh, Workspace
from flet_visual_builder.contracts import Diagnostic, Node, Project, Severity
from flet_visual_builder.engine.runtime import iter_controls
from flet_visual_builder.services.starter import starter_project
from flet_visual_builder.ui.code_view import CodeView
from flet_visual_builder.ui.diagnostics import DiagnosticsView
from flet_visual_builder.ui.preview import Preview
from tests.support.fake_page import FakePage


def workspace(project=None):
    return Workspace(FakePage(), project or starter_project())


def values(control):
    return [c.value for c in iter_controls(control) if isinstance(c, ft.Text)]


def buttons(control, caption):
    return [
        c
        for c in iter_controls(control)
        if isinstance(c, (ft.TextButton, ft.OutlinedButton)) and c.content == caption
    ]


def invalid_workspace():
    node = Node(
        id="bad", type_id="Text", props={"not_a_property": "oops"}, slots={}, events={}
    )
    return workspace(
        Project(
            name="Broken", page={}, root_ids=("bad",), nodes={"bad": node}, assets={}
        )
    )


def test_preview_uses_renderer_and_device_width(monkeypatch):
    ws = workspace()
    ws.device = "phone"
    called = []
    original = ws.renderer.render_plan
    monkeypatch.setattr(
        ws.renderer,
        "render_plan",
        lambda plan: (called.append(plan), original(plan))[1],
    )
    monkeypatch.setattr(
        ws,
        "artifact",
        lambda: (_ for _ in ()).throw(AssertionError("no artifact needed")),
    )
    view = Preview(ws)
    assert called
    assert any(
        isinstance(c, ft.Container) and c.width == ws.device_width()
        for c in iter_controls(view.control)
    )
    assert "Welcome to Flet Visual Builder" in values(view.control)
    assert "Phone" in values(view.control)


def test_invalid_document_surfaces_code_in_preview_and_code_view():
    ws = invalid_workspace()
    assert ws.plan() is None and ws.artifact() is None
    code = ws.diagnostics()[0].code
    assert any(code in s for s in values(Preview(ws).control))
    assert any(code in s for s in values(CodeView(ws).control))


def test_code_lines_metadata_and_copy(monkeypatch):
    ws = workspace()
    artifact = ws.artifact()
    view = CodeView(ws)
    source_controls = [
        c
        for c in iter_controls(view.control)
        if isinstance(c, ft.Text) and c.value == artifact.source
    ]
    assert len(source_controls) == 1 and source_controls[0].selectable
    assert "def main(page" in source_controls[0].value
    count = len(artifact.source.splitlines())
    assert any(
        f"{count} lines" in s and f"{len(artifact.source.encode('utf-8'))} bytes" in s
        for s in values(view.control)
    )
    assert any(
        s == "\n".join(map(str, range(1, count + 1))) for s in values(view.control)
    )
    assert any(
        artifact.target_flet in s and artifact.formatter in s
        for s in values(view.control)
    )
    copied = []

    async def copy(self, text):
        copied.append(text)

    monkeypatch.setattr(ft.Clipboard, "set", copy)
    monkeypatch.setattr(ws.page, "run_task", lambda handler: asyncio.run(handler()))
    buttons(view.control, "Copy")[0].on_click(None)
    assert copied == [artifact.source]


def test_diagnostics_hidden_and_node_link():
    assert not DiagnosticsView(workspace()).control.visible
    ws = invalid_workspace()
    ws.editor.selection = None
    view = DiagnosticsView(ws)
    assert view.control.visible
    diag = ws.diagnostics()[0]
    assert any(diag.code in s for s in values(view.control))
    assert any("not_a_property" in s for s in values(view.control))
    buttons(view.control, "Go to node")[0].on_click(None)
    assert ws.editor.selection == "bad"


def test_diagnostics_expand_and_collapse(monkeypatch):
    ws = workspace()
    diagnostics = tuple(
        Diagnostic(f"E{i}", f"Problem {i}", Severity.ERROR, ("props", "value"), "root")
        for i in range(8)
    )
    monkeypatch.setattr(ws, "diagnostics", lambda: diagnostics)
    view = DiagnosticsView(ws)
    assert "E5" in values(view.control) and "E6" not in values(view.control)
    buttons(view.control, "Show all (8)")[0].on_click(None)
    assert "E7" in values(view.control)
    buttons(view.control, "Show less")[0].on_click(None)
    assert "E6" not in values(view.control)


def test_render_failure_is_stale_and_names_renderer_diagnostic(monkeypatch):
    ws = workspace()
    view = Preview(ws)
    result = ws.renderer.render_plan(ws.plan())
    error = Diagnostic("ENGINE_TEST", "Render broke", Severity.ERROR)
    monkeypatch.setattr(
        ws.renderer,
        "render_plan",
        lambda plan: replace(result, root=None, diagnostics=(error,)),
    )
    view.refresh(Refresh.DOCUMENT)
    assert any("stale" in s.lower() for s in values(view.control))
    assert any("ENGINE_TEST" in s for s in values(view.control))


def test_large_code_reuses_number_string_and_handles_replacement_at_same_revision(
    monkeypatch,
):
    ws = workspace()
    original = ws.artifact()
    source = "\n".join(f"line_{i} = {i}" for i in range(1500)) + "\n"
    artifact = replace(original, source=source)
    monkeypatch.setattr(ws, "artifact", lambda: artifact)
    view = CodeView(ws)
    numbers = view._numbers
    assert len(numbers.splitlines()) == 1500
    view.refresh(Refresh.LAYOUT)
    assert view._numbers is numbers
    artifact = replace(artifact, source="print('new')\n")
    view.refresh(Refresh.PROJECT)
    assert view._numbers == "1"
    assert "print('new')\n" in values(view.control)


def test_failed_codegen_artifact_displays_its_diagnostics(monkeypatch):
    ws = workspace()
    artifact = ws.artifact()
    diagnostic = Diagnostic("CODEGEN_TEST", "Cannot export", Severity.ERROR)
    monkeypatch.setattr(
        ws, "artifact", lambda: replace(artifact, source="", diagnostics=(diagnostic,))
    )
    view = CodeView(ws)
    assert any(
        "CODEGEN_TEST" in s and "Cannot export" in s for s in values(view.control)
    )
    assert not buttons(view.control, "Copy")


def test_preview_none_root_without_diagnostics_and_clipboard_failure(monkeypatch):
    ws = workspace()
    result = ws.renderer.render_plan(ws.plan())
    monkeypatch.setattr(
        ws.renderer,
        "render_plan",
        lambda plan: replace(result, root=None, diagnostics=()),
    )
    assert any("no diagnostic" in s.lower() for s in values(Preview(ws).control))
    messages = []

    async def fail(self, source):
        raise RuntimeError("denied")

    monkeypatch.setattr(ft.Clipboard, "set", fail)
    monkeypatch.setattr(ws.page, "run_task", lambda handler: asyncio.run(handler()))
    monkeypatch.setattr(
        ws, "toast", lambda message, kind: messages.append((message, kind))
    )
    view = CodeView(ws)
    buttons(view.control, "Copy")[0].on_click(None)
    assert messages == [("Clipboard failed: denied", "error")]
