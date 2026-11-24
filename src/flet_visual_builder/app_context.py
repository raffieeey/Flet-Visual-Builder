"""Workspace controller: the single integration point for every panel.

The controller owns the document (through the history dispatcher), the editor
chrome state, and the cached projections of the document. Panels never talk to
each other; they read from this object and call its command helpers.

Panel contract
--------------
A panel is any object with:

``control``   the root :class:`flet.Control` mounted in the shell
``refresh(reason)``  rebuild or update itself for one of the :class:`Refresh`
             reasons. Panels ignore reasons they do not care about.

Reasons exist so that editing a text property does not rebuild the inspector
(which would steal focus from the field being typed into) while still
refreshing the canvas, outline, and status bar.
"""

from __future__ import annotations

import asyncio
import re
from pathlib import Path
from typing import Callable, Iterable, Protocol, Sequence, runtime_checkable

import flet as ft

from flet_visual_builder.catalogue import (
    FrozenCatalogue,
    catalogue as default_catalogue,
)
from flet_visual_builder.contracts import (
    AddScreen,
    CommandADT,
    CommandResult,
    CommandStatus,
    DeleteNode,
    DeleteScreen,
    Diagnostic,
    DocumentSnapshot,
    DropIntent,
    EditorTab,
    EventSymbol,
    ExportOptions,
    GeneratedArtifact,
    InsertNode,
    LoweringResult,
    MoveNode,
    Navigate,
    Node,
    NodeId,
    PasteNodes,
    Project,
    Redo,
    RenameProject,
    ReplaceProject,
    ScreenMeta,
    SetAction,
    SetEvent,
    SetProperty,
    SetScreen,
    Undo,
    UnsetProperty,
    WrapNode,
)
from flet_visual_builder.engine.codegen import Codegen
from flet_visual_builder.engine.lowering import Lowering
from flet_visual_builder.engine.runtime import RuntimeRenderer
from flet_visual_builder.model.screens import (
    effective_routes,
    meta_for,
    screen_entries,
)
from flet_visual_builder.model.validation import event_symbol_name
from flet_visual_builder.persistence.json_repository import (
    JsonRepository,
    PersistenceResult,
)
from flet_visual_builder.services.session import ProjectSession
from flet_visual_builder.state.editor_state import EditorState
from flet_visual_builder.state.history_dispatcher import HistoryDispatcher
from flet_visual_builder.ui.theme import T


class Refresh:
    """Reasons passed to ``Panel.refresh``."""

    ALL = "all"
    DOCUMENT = "document"  # node tree or properties changed
    SELECTION = "selection"  # selection changed, document unchanged
    PROJECT = "project"  # a different document was adopted
    CHROME = "chrome"  # dirty/save/undo state only
    LAYOUT = "layout"  # canvas width or active tab changed
    STATUS = "status"


@runtime_checkable
class Panel(Protocol):
    control: ft.Control

    def refresh(self, reason: str) -> None: ...


DEVICE_WIDTHS: dict[str, int | None] = {
    "fill": None,
    "phone": 390,
    "tablet": 768,
    "laptop": 1180,
}

DEVICE_LABELS: dict[str, str] = {
    "fill": "Fill",
    "phone": "Phone",
    "tablet": "Tablet",
    "laptop": "Laptop",
}

_ID_SAFE = re.compile(r"[^a-z0-9]+")
_CAMEL = re.compile(r"(?<!^)(?=[A-Z])")


def slug_for(type_id: str) -> str:
    return _ID_SAFE.sub("_", _CAMEL.sub("_", type_id).lower()).strip("_")


class Workspace:
    """Owns one document and every derived projection of it."""

    def __init__(
        self,
        page: ft.Page,
        project: Project,
        *,
        catalogue: FrozenCatalogue | None = None,
        session: ProjectSession | None = None,
        path: str | Path | None = None,
    ) -> None:
        self.page = page
        self.catalogue = catalogue or default_catalogue
        self.repository = JsonRepository(self.catalogue)
        self.session = session or ProjectSession()
        if path is not None:
            self.session.set_path(path, saved=True)
        self.editor = EditorState()
        self.renderer = RuntimeRenderer()
        self.lowerer = Lowering()
        self.codegen = Codegen()
        self._panels: list[Panel] = []
        self._dispatcher = HistoryDispatcher(
            DocumentSnapshot(project=project, revision=0)
        )
        self._plan_revision = -1
        self._plan_result: LoweringResult | None = None
        self._artifact_revision = -1
        self._artifact: GeneratedArtifact | None = None
        self._id_counters: dict[str, int] = {}
        self.device = "fill"
        self._autosave_due = False
        self._autosave_running = False
        self._closed = False
        self.editor.selection = project.root_ids[0] if project.root_ids else None
        self.editor.active_screen = self.editor.selection

    # ── document access ───────────────────────────────────────────────
    @property
    def snapshot(self) -> DocumentSnapshot:
        return self._dispatcher.snapshot

    @property
    def project(self) -> Project:
        return self._dispatcher.snapshot.project

    @property
    def revision(self) -> int:
        return self._dispatcher.snapshot.revision

    @property
    def dispatcher(self) -> HistoryDispatcher:
        return self._dispatcher

    def node(self, node_id: NodeId | None) -> Node | None:
        if node_id is None:
            return None
        return self.project.nodes.get(node_id)

    def selected_node(self) -> Node | None:
        return self.node(self.editor.selection)

    def spec(self, type_id: str):
        return self.catalogue.widgets[type_id]

    def slots_of(self, node: Node) -> dict[str, Sequence[NodeId]]:
        return {
            name: node.slots.get(name, ()) for name in self.spec(node.type_id).slots
        }

    def default_slot(self, type_id: str) -> str | None:
        slots = self.catalogue.widgets[type_id].slots
        if "content" in slots:
            return "content"
        if "controls" in slots:
            return "controls"
        return next(iter(slots), None)

    def accepts_children(self, type_id: str) -> bool:
        return bool(self.catalogue.widgets[type_id].slots)

    def children(self, node_id: NodeId, slot: str | None = None) -> list[Node]:
        node = self.node(node_id)
        if node is None:
            return []
        names = [slot] if slot else list(self.slots_of(node))
        result: list[Node] = []
        for name in names:
            for child_id in node.slots.get(name, ()):
                child = self.node(child_id)
                if child is not None:
                    result.append(child)
        return result

    def parent_of(self, node_id: NodeId) -> tuple[NodeId, str, int] | None:
        for candidate in self.project.nodes.values():
            for slot_name, child_ids in candidate.slots.items():
                for index, child_id in enumerate(child_ids):
                    if child_id == node_id:
                        return candidate.id, slot_name, index
        return None

    def depth(self, node_id: NodeId) -> int:
        depth = 0
        cursor = node_id
        seen: set[str] = set()
        while cursor is not None:
            parent = self.parent_of(cursor)
            if parent is None or parent[0] in seen:
                break
            seen.add(parent[0])
            depth += 1
            cursor = parent[0]
        return depth

    # ── projections ───────────────────────────────────────────────────
    def plan_result(self) -> LoweringResult:
        if self._plan_result is None or self._plan_revision != self.revision:
            self._plan_result = self.lowerer.lower_project(
                self.snapshot, self.catalogue
            )
            self._plan_revision = self.revision
        return self._plan_result

    def plan(self):
        return self.plan_result().plan

    def diagnostics(self) -> tuple[Diagnostic, ...]:
        """Lowering plus generation diagnostics, de-duplicated by code/message/node."""
        diagnostics = list(self.plan_result().diagnostics)
        artifact = self._artifact
        if artifact is not None and self._artifact_revision == self.revision:
            diagnostics.extend(artifact.diagnostics)
        seen: set[tuple[str, str, str]] = set()
        unique: list[Diagnostic] = []
        for item in diagnostics:
            key = (item.code, item.message, item.node_id or "")
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return tuple(unique)

    def artifact(self) -> GeneratedArtifact | None:
        if self._artifact is None or self._artifact_revision != self.revision:
            plan = self.plan()
            if plan is None:
                self._artifact = None
            else:
                self._artifact = self.codegen.generate_python(plan, ExportOptions())
            self._artifact_revision = self.revision
        return self._artifact

    def invalidate(self) -> None:
        self._plan_result = None
        self._artifact = None
        self._plan_revision = -1
        self._artifact_revision = -1

    # ── panels ────────────────────────────────────────────────────────
    def add_panel(self, panel: Panel) -> Panel:
        self._panels.append(panel)
        return panel

    def refresh(self, reason: str = Refresh.ALL) -> None:
        if self._closed:
            return
        for panel in list(self._panels):
            try:
                panel.refresh(reason)
            except Exception as exc:  # a broken panel must not kill the workspace
                print(f"[fvb] panel refresh failed ({type(panel).__name__}): {exc!r}")
        try:
            self.page.update()
        except Exception:
            pass

    def close(self) -> None:
        self._closed = True
        try:
            self.session.write_autosave(self.repository, self.project, self.revision)
        except Exception:
            pass

    # ── commands ──────────────────────────────────────────────────────
    def _command_id(self, prefix: str) -> str:
        self._id_counters[prefix] = self._id_counters.get(prefix, 0) + 1
        return f"{prefix}-{self._id_counters[prefix]}"

    def dispatch(
        self, command: CommandADT, *, reason: str = Refresh.DOCUMENT
    ) -> CommandResult:
        result = self._dispatcher.execute(command, expected_revision=self.revision)
        if result.status is CommandStatus.REJECTED:
            self.report(result.diagnostics)
            self.refresh(Refresh.STATUS)
            return result
        if result.status is CommandStatus.COMMITTED:
            self.invalidate()
            self.session.mark_dirty()
            self._drop_stale_selection()
            self._schedule_autosave()
            self.refresh(reason)
        return result

    def _drop_stale_selection(self) -> None:
        roots = self.project.root_ids
        if self.editor.selection and self.editor.selection not in self.project.nodes:
            self.editor.selection = roots[0] if roots else None
        if self.editor.active_screen not in roots:
            self.editor.active_screen = roots[0] if roots else None

    def new_node(self, type_id: str) -> Node:
        spec = self.catalogue.widgets[type_id]
        prefix = slug_for(type_id)
        self._id_counters[prefix] = self._id_counters.get(prefix, 0) + 1
        candidate = f"{prefix}_{self._id_counters[prefix]}"
        while candidate in self.project.nodes:
            self._id_counters[prefix] += 1
            candidate = f"{prefix}_{self._id_counters[prefix]}"
        return Node(
            id=candidate,
            type_id=type_id,
            props=self.catalogue.new_props(type_id),
            slots={name: () for name in spec.slots},
            events={},
        )

    def insert(
        self, type_id: str, parent_id: NodeId, slot_name: str, index: int
    ) -> CommandResult:
        node = self.new_node(type_id)
        result = self.dispatch(
            InsertNode(
                command_id=self._command_id("insert"),
                node=node,
                destination=DropIntent(
                    parent_id=parent_id, slot_name=slot_name, index=index
                ),
            )
        )
        if result.status is CommandStatus.COMMITTED:
            self.editor.selection = node.id
            self.refresh(Refresh.SELECTION)
        return result

    def insert_relative(
        self, type_id: str, anchor: NodeId, *, inside: bool, after: bool = False
    ) -> CommandResult:
        """Insert next to an existing node, following the reducer's slot rules."""
        anchor_node = self.node(anchor)
        if anchor_node is None:
            return self._noop("insert")
        if inside and self.accepts_children(anchor_node.type_id):
            slot = self.default_slot(anchor_node.type_id) or "controls"
            index = len(anchor_node.slots.get(slot, ()))
            return self.insert(type_id, anchor_node.id, slot, index)
        parent = self.parent_of(anchor_node.id)
        if parent is None:
            return self.insert(
                type_id,
                anchor_node.id,
                self.default_slot(anchor_node.type_id) or "controls",
                0,
            )
        parent_id, slot_name, index = parent
        return self.insert(type_id, parent_id, slot_name, index + (1 if after else 0))

    def delete(self, node_id: NodeId) -> CommandResult:
        parent = self.parent_of(node_id)
        result = self.dispatch(
            DeleteNode(command_id=self._command_id("delete"), node_id=node_id)
        )
        if result.status is CommandStatus.COMMITTED:
            self.editor.selection = (
                parent[0]
                if parent
                else (self.project.root_ids[0] if self.project.root_ids else None)
            )
            self.refresh(Refresh.SELECTION)
        return result

    def move(
        self, node_id: NodeId, parent_id: NodeId, slot_name: str, index: int
    ) -> CommandResult:
        """Move a node. ``index`` is the raw position in the target list before removal."""
        source = self.parent_of(node_id)
        destination_index = index
        if (
            source is not None
            and source[0] == parent_id
            and source[1] == slot_name
            and source[2] < index
        ):
            destination_index -= 1
        result = self.dispatch(
            MoveNode(
                command_id=self._command_id("move"),
                node_id=node_id,
                destination=DropIntent(
                    parent_id=parent_id, slot_name=slot_name, index=destination_index
                ),
            )
        )
        if result.status is CommandStatus.COMMITTED:
            self.editor.selection = node_id
            self.refresh(Refresh.SELECTION)
        return result

    def wrap(self, node_id: NodeId, wrapper_type: str) -> CommandResult:
        wrapper = self.new_node(wrapper_type)
        slot = self.default_slot(wrapper_type) or "content"
        result = self.dispatch(
            WrapNode(
                command_id=self._command_id("wrap"),
                node_id=node_id,
                wrapper=wrapper,
                wrapper_slot=slot,
            )
        )
        if result.status is CommandStatus.COMMITTED:
            self.editor.selection = wrapper.id
            self.refresh(Refresh.SELECTION)
        return result

    def duplicate(self, node_id: NodeId) -> CommandResult:
        source = self.node(node_id)
        parent = self.parent_of(node_id)
        if source is None or parent is None:
            return self._noop("duplicate")
        clones = self._clone_subtree(source)
        parent_id, slot_name, index = parent
        result = self.dispatch(
            PasteNodes(
                command_id=self._command_id("duplicate"),
                nodes=clones,
                destination=DropIntent(
                    parent_id=parent_id, slot_name=slot_name, index=index + 1
                ),
            )
        )
        if result.status is CommandStatus.COMMITTED:
            self.editor.selection = clones[-1].id
            self.refresh(Refresh.SELECTION)
        return result

    def _clone_subtree(self, source: Node) -> tuple[Node, ...]:
        """Deep copy with fresh ids; the returned root is last in the tuple."""
        import copy as _copy
        from dataclasses import replace as _replace

        collected: list[Node] = []

        def walk(node: Node) -> Node:
            fresh = self.new_node(node.type_id)
            slots: dict[str, tuple[str, ...]] = {}
            for slot_name, child_ids in node.slots.items():
                cloned_children: list[str] = []
                for child_id in child_ids:
                    child = self.node(child_id)
                    if child is None:
                        continue
                    cloned_children.append(walk(child).id)
                slots[slot_name] = tuple(cloned_children)
            events = {
                name: EventSymbol(event_symbol_name(fresh.id, name))
                for name in node.events
            }
            clone = _replace(
                fresh,
                props=_copy.deepcopy(dict(node.props)),
                slots=slots,
                events=events,
            )
            collected.append(clone)
            return clone

        root = walk(source)
        collected.remove(root)
        return (*collected, root)

    def set_property(self, node_id: NodeId | None, name: str, value) -> CommandResult:
        return self.dispatch(
            SetProperty(
                command_id=self._command_id("prop"),
                node_id=node_id,
                name=name,
                value=value,
            )
        )

    def unset_property(self, node_id: NodeId | None, name: str) -> CommandResult:
        return self.dispatch(
            UnsetProperty(
                command_id=self._command_id("unset"), node_id=node_id, name=name
            )
        )

    def set_event(
        self, node_id: NodeId, event_name: str, enabled: bool = True
    ) -> CommandResult:
        symbol = (
            EventSymbol(event_symbol_name(node_id, event_name)) if enabled else None
        )
        return self.dispatch(
            SetEvent(
                command_id=self._command_id("event"),
                node_id=node_id,
                event_name=event_name,
                symbol=symbol,
            )
        )

    def rename_project(self, name: str) -> CommandResult:
        return self.dispatch(
            RenameProject(command_id=self._command_id("rename"), name=name)
        )

    def undo(self) -> CommandResult:
        return self.dispatch(Undo(command_id=self._command_id("undo")))

    def redo(self) -> CommandResult:
        return self.dispatch(Redo(command_id=self._command_id("redo")))

    def _noop(self, prefix: str) -> CommandResult:
        return CommandResult(
            command_id=self._command_id(prefix),
            status=CommandStatus.NOOP,
            before_revision=self.revision,
            snapshot=self.snapshot,
            affected_ids=frozenset(),
        )

    # ── selection and chrome ──────────────────────────────────────────
    def select(self, node_id: NodeId | None) -> None:
        if node_id == self.editor.selection:
            return
        self.editor.selection = node_id
        self.refresh(Refresh.SELECTION)

    def set_tab(self, tab: EditorTab) -> None:
        if self.editor.active_tab is tab:
            return
        self.editor.activate(tab)
        self.refresh(Refresh.LAYOUT)

    def set_device(self, device: str) -> None:
        if device not in DEVICE_WIDTHS or device == self.device:
            return
        self.device = device
        self.refresh(Refresh.LAYOUT)

    def device_width(self) -> int | None:
        return DEVICE_WIDTHS.get(self.device)

    # ── screens ───────────────────────────────────────────────────────
    def screen_entries(self) -> tuple[tuple[NodeId, "ScreenMeta"], ...]:
        return screen_entries(self.project)

    def screen_meta(self, screen_id: NodeId):
        return meta_for(self.project, screen_id)

    def screen_route(self, screen_id: NodeId) -> str | None:
        meta = meta_for(self.project, screen_id)
        return meta.route if meta is not None else None

    def routes(self) -> dict[str, NodeId]:
        return effective_routes(self.project)

    def active_screen(self) -> NodeId | None:
        if self.editor.active_screen in self.project.root_ids:
            return self.editor.active_screen
        return self.project.root_ids[0] if self.project.root_ids else None

    def select_screen(self, screen_id: NodeId) -> None:
        if screen_id not in self.project.root_ids:
            return
        self.editor.active_screen = screen_id
        self.editor.selection = screen_id
        self.refresh(Refresh.ALL)

    def add_screen(
        self, title: str | None = None, route: str | None = None
    ) -> CommandResult:
        index = len(self.project.root_ids)
        node = self.new_node("Column")
        result = self.dispatch(
            AddScreen(
                command_id=self._command_id("screen"),
                node=node,
                title=title or f"Screen {index + 1}",
                route=route or f"/screen-{index + 1}",
            )
        )
        if result.status is CommandStatus.COMMITTED:
            self.editor.active_screen = node.id
            self.editor.selection = node.id
            self.refresh(Refresh.ALL)
        return result

    def update_screen(
        self,
        screen_id: NodeId,
        *,
        title: str,
        route: str,
        initial: bool = False,
    ) -> CommandResult:
        return self.dispatch(
            SetScreen(
                command_id=self._command_id("screen"),
                screen_id=screen_id,
                title=title,
                route=route,
                initial=initial,
            )
        )

    def delete_screen(self, screen_id: NodeId) -> CommandResult:
        result = self.dispatch(
            DeleteScreen(command_id=self._command_id("screen"), screen_id=screen_id)
        )
        if result.status is CommandStatus.COMMITTED:
            screens = self.project.root_ids
            self.editor.active_screen = screens[0] if screens else None
            self.editor.selection = self.editor.active_screen
            self.refresh(Refresh.ALL)
        return result

    def set_action(
        self, node_id: NodeId, event_name: str, route: str | None
    ) -> CommandResult:
        return self.dispatch(
            SetAction(
                command_id=self._command_id("action"),
                node_id=node_id,
                event_name=event_name,
                action=Navigate(route) if route else None,
            )
        )

    def set_text_focus(self, focused: bool) -> None:
        """Track text-input focus so destructive shortcuts stay inert while typing."""
        self.editor.text_focus = focused

    def set_status(self, message: str) -> None:
        self.editor.set_status(message)
        self.refresh(Refresh.STATUS)

    # ── feedback ──────────────────────────────────────────────────────
    def toast(self, message: str, kind: str = "info") -> None:
        colors = {
            "info": T.text,
            "success": T.success,
            "warning": T.warning,
            "error": T.danger,
        }
        try:
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(message, color="#FFFFFF", size=13),
                    bgcolor=colors.get(kind, T.text),
                    duration=2600,
                )
            )
        except Exception:
            pass

    def report(self, diagnostics: Iterable[Diagnostic]) -> None:
        messages = [f"{d.code}: {d.message}" for d in diagnostics]
        if not messages:
            self.toast("Command rejected", "error")
            return
        head = messages[0]
        extra = f" (+{len(messages) - 1} more)" if len(messages) > 1 else ""
        self.toast(f"{head}{extra}", "error")

    # ── persistence ───────────────────────────────────────────────────
    def save_to(self, path: str | Path) -> PersistenceResult:
        target = Path(path)
        if target.suffix != ".json":
            target = target.with_suffix(".fvb.json")
        result = self.repository.save(self.project, target)
        if result.ok:
            self.session.set_path(target, saved=True)
            self.session.remember(target, self.project.name)
            self.session.clear_autosave()
            self.toast(f"Saved {target.name}", "success")
            self.refresh(Refresh.CHROME)
        else:
            self.report(result.diagnostics)
        return result

    def open_path(self, path: str | Path) -> PersistenceResult:
        result = self.repository.load(path)
        if result.ok and result.project is not None:
            self.adopt(result.project, path=path, dirty=False)
            self.session.remember(path, result.project.name)
            self.toast(f"Opened {Path(path).name}", "success")
        else:
            self.report(result.diagnostics)
        return result

    def adopt(
        self, project: Project, *, path: str | Path | None = None, dirty: bool = False
    ) -> None:
        self._dispatcher = HistoryDispatcher(
            DocumentSnapshot(project=project, revision=0)
        )
        self._id_counters.clear()
        self.invalidate()
        self.session.set_path(path, saved=not dirty)
        if dirty:
            self.session.mark_dirty()
        self.editor.selection = project.root_ids[0] if project.root_ids else None
        self.editor.active_screen = self.editor.selection
        self.editor.hover = None
        self.refresh(Refresh.PROJECT)

    def new_document(self, project: Project) -> None:
        self.adopt(project, path=None, dirty=False)
        self.session.clear_autosave()

    # ── autosave ──────────────────────────────────────────────────────
    def _schedule_autosave(self) -> None:
        self._autosave_due = True
        if self._autosave_running or self._closed:
            return
        try:
            self.page.run_task(self._autosave_worker)
        except Exception:
            self._autosave_due = False

    async def _autosave_worker(self) -> None:
        self._autosave_running = True
        try:
            while self._autosave_due:
                self._autosave_due = False
                await asyncio.sleep(0.9)
            self.session.write_autosave(self.repository, self.project, self.revision)
        except Exception:
            pass
        finally:
            self._autosave_running = False
