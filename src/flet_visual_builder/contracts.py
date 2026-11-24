"""Frozen design contracts for Flet Visual Builder, targeting Flet 1.0.1.

This module defines data and interfaces, not the builder implementation.
Flet is deliberately imported only for type checking.
"""

from __future__ import annotations

import keyword
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Literal, Protocol, TypeAlias

if TYPE_CHECKING:
    import flet as ft

JsonScalar: TypeAlias = None | bool | int | float | str
JsonValue: TypeAlias = JsonScalar | tuple["JsonValue", ...] | Mapping[str, "JsonValue"]
JsonObject: TypeAlias = Mapping[str, JsonValue]
NodeId: TypeAlias = str


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True, slots=True)
class Diagnostic:
    code: str
    message: str
    severity: Severity
    path: tuple[str | int, ...] = ()
    node_id: NodeId | None = None


@dataclass(frozen=True, slots=True)
class EventSymbol:
    name: str

    def __post_init__(self) -> None:
        if (
            re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", self.name) is None
            or keyword.iskeyword(self.name)
            or not self.name.startswith("handle_")
        ):
            raise ValueError("Invalid event symbol")


@dataclass(frozen=True, slots=True)
class Navigate:
    """A click action that moves the running app to another screen."""

    route: str

    def __post_init__(self) -> None:
        if not self.route.startswith("/") or " " in self.route:
            raise ValueError("route must start with '/' and contain no spaces")


ActionADT: TypeAlias = Navigate


@dataclass(frozen=True, slots=True)
class Node:
    id: NodeId
    type_id: str
    props: JsonObject
    slots: Mapping[str, tuple[NodeId, ...]]
    events: Mapping[str, EventSymbol]
    actions: Mapping[str, ActionADT] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class Asset:
    id: str
    media_type: str
    sha256: str
    data: bytes


@dataclass(frozen=True, slots=True)
class ScreenMeta:
    """Title and route for one screen (a root node in ``root_ids``)."""

    title: str
    route: str


@dataclass(frozen=True, slots=True)
class Project:
    name: str
    page: JsonObject
    root_ids: tuple[NodeId, ...]
    nodes: Mapping[NodeId, Node]
    assets: Mapping[str, Asset]
    screens: Mapping[NodeId, ScreenMeta] = field(default_factory=dict)
    initial_route: str = "/"
    schema_version: Literal[3] = 3
    catalogue_version: Literal[1] = 1
    target_flet: Literal["1.0.1"] = "1.0.1"


@dataclass(frozen=True, slots=True)
class DocumentSnapshot:
    project: Project
    revision: int


@dataclass(frozen=True, slots=True)
class DropIntent:
    parent_id: NodeId | None
    slot_name: str
    index: int  # Index AFTER removal of a moved source node.


@dataclass(frozen=True, slots=True, kw_only=True)
class Command:
    command_id: str
    gesture_id: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class InsertNode(Command):
    node: Node  # New node with empty child slots.
    destination: DropIntent


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteNode(Command):
    node_id: NodeId


@dataclass(frozen=True, slots=True, kw_only=True)
class MoveNode(Command):
    node_id: NodeId
    destination: DropIntent


@dataclass(frozen=True, slots=True, kw_only=True)
class WrapNode(Command):
    node_id: NodeId
    wrapper: Node  # Fresh node with empty child slots.
    wrapper_slot: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SetProperty(Command):
    node_id: NodeId | None  # None means the PageSpec.
    name: str
    value: JsonValue


@dataclass(frozen=True, slots=True, kw_only=True)
class UnsetProperty(Command):
    node_id: NodeId | None
    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SetEvent(Command):
    node_id: NodeId
    event_name: str
    symbol: EventSymbol | None  # None removes the binding.


@dataclass(frozen=True, slots=True, kw_only=True)
class ReplaceProject(Command):
    project: Project


@dataclass(frozen=True, slots=True, kw_only=True)
class RenameProject(Command):
    """Rename the document without discarding undo history."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SetScreen(Command):
    """Rename a screen, change its route, or make it the initial screen."""

    screen_id: NodeId
    title: str
    route: str
    initial: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class AddScreen(Command):
    """Append a new screen whose root is ``node`` (a fresh, empty root)."""

    node: Node
    title: str
    route: str
    initial: bool = False


@dataclass(frozen=True, slots=True, kw_only=True)
class DeleteScreen(Command):
    screen_id: NodeId


@dataclass(frozen=True, slots=True, kw_only=True)
class SetAction(Command):
    """Bind (or clear) a click action such as navigation on one event."""

    node_id: NodeId
    event_name: str
    action: ActionADT | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class PasteNodes(Command):
    """Insert a complete subtree atomically (used by duplicate and paste).

    ``nodes`` carries the new nodes; exactly one must be a root that is not
    referenced by another payload node. ``destination`` places that root.
    """

    nodes: tuple[Node, ...]
    destination: DropIntent


@dataclass(frozen=True, slots=True, kw_only=True)
class Undo(Command):
    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class Redo(Command):
    pass


CommandADT: TypeAlias = (
    InsertNode
    | DeleteNode
    | MoveNode
    | WrapNode
    | SetProperty
    | UnsetProperty
    | SetEvent
    | ReplaceProject
    | RenameProject
    | PasteNodes
    | SetScreen
    | AddScreen
    | DeleteScreen
    | SetAction
    | Undo
    | Redo
)


class CommandStatus(str, Enum):
    COMMITTED = "committed"
    NOOP = "noop"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CommandResult:
    command_id: str
    status: CommandStatus
    before_revision: int
    snapshot: DocumentSnapshot
    affected_ids: frozenset[NodeId]
    diagnostics: tuple[Diagnostic, ...] = ()


class CommandReducer(Protocol):
    def apply(
        self, snapshot: DocumentSnapshot, command: CommandADT
    ) -> CommandResult: ...


class CommandDispatcher(Protocol):
    @property
    def snapshot(self) -> DocumentSnapshot: ...

    def execute(
        self, command: CommandADT, *, expected_revision: int
    ) -> CommandResult: ...


class Unset(Enum):
    VALUE = "unset"


@dataclass(frozen=True, slots=True)
class SymbolRef:
    path: tuple[str, ...]  # Relative to ft; constructed ONLY by trusted catalogue.


@dataclass(frozen=True, slots=True)
class LiteralValue:
    value: JsonScalar


@dataclass(frozen=True, slots=True)
class CallValue:
    constructor: SymbolRef
    args: tuple[ValueExpr, ...]
    kwargs: Mapping[str, ValueExpr]


@dataclass(frozen=True, slots=True)
class SequenceValue:
    items: tuple[ValueExpr, ...]


@dataclass(frozen=True, slots=True)
class MappingValue:
    items: tuple[tuple[ValueExpr, ValueExpr], ...]


@dataclass(frozen=True, slots=True)
class AssetValue:
    asset_id: str


ValueExpr: TypeAlias = (
    LiteralValue | SymbolRef | CallValue | SequenceValue | MappingValue | AssetValue
)


class ValueCodec(Protocol):
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]: ...
    def lower(self, value: JsonValue) -> ValueExpr: ...


@dataclass(frozen=True, slots=True)
class PropertySpec:
    name: str
    codec_id: str
    new_default: JsonValue | Unset
    nullable: bool
    required: bool = False


@dataclass(frozen=True, slots=True)
class SlotSpec:
    name: str
    minimum: int
    maximum: int | None
    accepted_types: frozenset[str] | None  # None means any catalogue visual type.


@dataclass(frozen=True, slots=True)
class WidgetSpec:
    type_id: str
    constructor: SymbolRef
    properties: Mapping[str, PropertySpec]
    slots: Mapping[str, SlotSpec]
    events: frozenset[str]


class Catalogue(Protocol):
    version: int
    target_flet: str
    widgets: Mapping[str, WidgetSpec]
    page_properties: Mapping[str, PropertySpec]
    codecs: Mapping[str, ValueCodec]

    def widget(self, type_id: str) -> WidgetSpec: ...


@dataclass(frozen=True, slots=True)
class NodePlan:
    node_id: NodeId
    type_id: str
    constructor: SymbolRef
    properties: Mapping[str, ValueExpr]
    slots: Mapping[str, tuple[NodeId, ...]]
    events: Mapping[str, EventSymbol]
    actions: Mapping[str, ActionADT] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PlannedScreen:
    """One exported screen: its root node, title and route."""

    root_id: NodeId
    title: str
    route: str


@dataclass(frozen=True, slots=True)
class ControlPlan:
    revision: int
    document_sha256: str
    target_flet: str
    catalogue_version: int
    page_properties: Mapping[str, ValueExpr]
    root_ids: tuple[NodeId, ...]
    nodes: Mapping[NodeId, NodePlan]
    assets: Mapping[str, Asset]
    screens: tuple[PlannedScreen, ...] = ()
    initial_route: str = "/"


@dataclass(frozen=True, slots=True)
class LoweringResult:
    plan: ControlPlan | None
    diagnostics: tuple[Diagnostic, ...]


class Lowerer(Protocol):
    def lower_project(
        self, snapshot: DocumentSnapshot, catalogue: Catalogue
    ) -> LoweringResult: ...


class RenderMode(str, Enum):
    PREVIEW = "preview"
    DESIGN_SAMPLE = "design_sample"


@dataclass(frozen=True, slots=True)
class RenderResult:
    revision: int
    mode: RenderMode
    root: ft.Control | None
    by_node: Mapping[NodeId, ft.Control]
    diagnostics: tuple[Diagnostic, ...]


class PreviewRenderer(Protocol):
    def render_plan(self, plan: ControlPlan) -> RenderResult: ...
    def render_leaf_sample(
        self, plan: ControlPlan, node_id: NodeId
    ) -> RenderResult: ...


@dataclass(frozen=True, slots=True)
class ExportOptions:
    target_flet: Literal["1.0.1"] = "1.0.1"
    python_target: Literal["py312"] = "py312"
    formatter: Literal["black==25.1.0"] = "black==25.1.0"
    line_length: Literal[88] = 88
    include_event_stubs: Literal[True] = True


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    source: str
    filename: str
    target_flet: str
    formatter: str
    document_sha256: str
    diagnostics: tuple[Diagnostic, ...]


class CodeGenerator(Protocol):
    def generate_python(
        self, plan: ControlPlan, options: ExportOptions
    ) -> GeneratedArtifact: ...


@dataclass(frozen=True, slots=True)
class CreateDrag:
    widget_type: str


@dataclass(frozen=True, slots=True)
class MoveDrag:
    node_id: NodeId


DragPayload: TypeAlias = CreateDrag | MoveDrag


class DragStatus(str, Enum):
    ACTIVE = "active"
    CONSUMED = "consumed"
    CANCELLED = "cancelled"


@dataclass(frozen=True, slots=True)
class DragSession:
    session_id: str
    source_key: str
    source_object_id: int  # Python id(draggable), never a persisted Flet ID.
    payload: DragPayload
    revision: int
    started_monotonic: float
    status: DragStatus = DragStatus.ACTIVE
    client_complete: bool = False


@dataclass(frozen=True, slots=True)
class Point:
    x: float
    y: float


@dataclass(frozen=True, slots=True)
class Size:
    width: float
    height: float


@dataclass(frozen=True, slots=True)
class TargetKey:
    parent_id: NodeId | None
    slot_name: str
    index: int  # BEFORE source removal; normalized by the resolver exactly once.
    kind: Literal["rail", "empty_slot", "zone"]


@dataclass(frozen=True, slots=True)
class TargetDescriptor:
    key: TargetKey
    revision: int
    axis: Literal["horizontal", "vertical"]
    anchor_node_id: NodeId | None = None
    inside_slot_name: str | None = None


@dataclass(frozen=True, slots=True)
class DropFeedback:
    target: TargetKey
    intent: DropIntent | None
    valid: bool
    message: str


class DesignActions(Protocol):
    def select_node(self, node_id: NodeId) -> None: ...
    def begin_drag(
        self, source_key: str, source_object_id: int, payload: DragPayload
    ) -> DragSession | None: ...
    def propose_drop(
        self, target: TargetDescriptor, point: Point | None, size: Size | None
    ) -> DropFeedback: ...
    def commit_drop(
        self,
        target: TargetDescriptor,
        source_object_id: int,
        point: Point | None,
        size: Size | None,
    ) -> CommandResult: ...
    def leave_target(self, target: TargetKey) -> None: ...
    def client_drag_complete(self, source_object_id: int) -> None: ...


@dataclass(slots=True)
class TargetMount:
    descriptor: TargetDescriptor
    target: ft.DragTarget
    aperture: ft.Container  # Direct content of target; the ONLY geometry box.
    label: ft.Text
    measured_size: Size | None = None


@dataclass(slots=True)
class DesignProjection:
    revision: int
    root: ft.Control
    frames: Mapping[NodeId, ft.Control]
    targets: Mapping[TargetKey, TargetMount]


class DesignChrome(Protocol):
    def build(
        self, plan: ControlPlan, actions: DesignActions, samples: PreviewRenderer
    ) -> DesignProjection: ...
    def set_feedback(
        self, projection: DesignProjection, feedback: DropFeedback | None
    ) -> None: ...


class EditorTab(str, Enum):
    DESIGN = "design"
    PREVIEW = "preview"
    CODE = "code"


@dataclass(frozen=True, slots=True)
class ShellMountPoints:
    toolbar: ft.Container
    palette: ft.Container
    tree: ft.Container
    inspector: ft.Container
    design: ft.Container
    preview: ft.Container
    code: ft.Container
    diagnostics: ft.Container
    status: ft.Container


RegionName: TypeAlias = Literal[
    "toolbar",
    "palette",
    "tree",
    "inspector",
    "design",
    "preview",
    "code",
    "diagnostics",
]


class Shell(Protocol):
    mounts: ShellMountPoints
    root: ft.Control

    def mount(self, region: RegionName, content: ft.Control | None) -> None: ...
    def activate(self, tab: EditorTab) -> None: ...
    def set_status(self, text: str) -> None: ...
