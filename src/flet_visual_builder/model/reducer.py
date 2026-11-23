"""Pure CommandReducer. No Flet import. No history stack (T09)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import Final

from flet_visual_builder.contracts import (
    CommandADT,
    CommandResult,
    CommandStatus,
    DeleteNode,
    Diagnostic,
    DocumentSnapshot,
    DropIntent,
    InsertNode,
    JsonValue,
    MoveNode,
    Node,
    NodeId,
    Project,
    Redo,
    ReplaceProject,
    SetEvent,
    SetProperty,
    Severity,
    Undo,
    UnsetProperty,
    WrapNode,
)
from flet_visual_builder.model.validation import (
    MAX_DEPTH,
    MAX_NODES,
    ROOT_SLOT,
    descendants_of,
    destination_depth,
    event_symbol_name,
    is_identifier_safe_node_id,
    node_depth,
    owner_of,
    slot_children,
    slots_are_empty,
    subtree_height,
    subtree_ids,
    type_slot_table,
    validate_index,
    validate_occupancy,
    validate_project,
)

_MISSING: Final[object] = object()


def _error(
    code: str,
    message: str,
    *,
    node_id: NodeId | None = None,
    path: tuple[str | int, ...] = (),
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
        node_id=node_id,
    )


def _json_equal(left: object, right: object) -> bool:
    """Distinguish unset/null/false/0: bool is not a number."""
    if type(left) is bool or type(right) is bool:
        return type(left) is type(right) and left == right
    if left is None or right is None:
        return left is right
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        if set(left.keys()) != set(right.keys()):
            return False
        return all(_json_equal(left[k], right[k]) for k in left)
    if isinstance(left, tuple) and isinstance(right, tuple):
        return len(left) == len(right) and all(
            _json_equal(a, b) for a, b in zip(left, right)
        )
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return type(left) is type(right) and left == right
    return left == right


def _result(
    command_id: str,
    status: CommandStatus,
    before: DocumentSnapshot,
    snapshot: DocumentSnapshot,
    *,
    affected_ids: frozenset[NodeId] = frozenset(),
    diagnostics: tuple[Diagnostic, ...] = (),
) -> CommandResult:
    return CommandResult(
        command_id=command_id,
        status=status,
        before_revision=before.revision,
        snapshot=snapshot,
        affected_ids=affected_ids,
        diagnostics=diagnostics,
    )


def _reject(
    snapshot: DocumentSnapshot,
    command_id: str,
    *diagnostics: Diagnostic,
) -> CommandResult:
    return _result(
        command_id,
        CommandStatus.REJECTED,
        snapshot,
        snapshot,
        diagnostics=diagnostics,
    )


def _noop(snapshot: DocumentSnapshot, command_id: str) -> CommandResult:
    return _result(command_id, CommandStatus.NOOP, snapshot, snapshot)


def _commit(
    before: DocumentSnapshot,
    project: Project,
    command_id: str,
    affected_ids: frozenset[NodeId],
) -> CommandResult:
    errors = validate_project(project)
    if errors:
        return _reject(before, command_id, *errors)
    return _result(
        command_id,
        CommandStatus.COMMITTED,
        before,
        DocumentSnapshot(project=project, revision=before.revision + 1),
        affected_ids=affected_ids,
    )


def _replace_slot(
    project: Project,
    parent_id: NodeId | None,
    slot_name: str,
    children: tuple[NodeId, ...],
    nodes: dict[NodeId, Node] | None = None,
) -> tuple[Project, dict[NodeId, Node]]:
    working = dict(project.nodes if nodes is None else nodes)
    if parent_id is None:
        return replace(project, root_ids=children, nodes=working), working
    parent = working[parent_id]
    new_slots = dict(parent.slots)
    new_slots[slot_name] = children
    working[parent_id] = replace(parent, slots=new_slots)
    return replace(project, nodes=working), working


def _parent_type(project: Project, parent_id: NodeId | None) -> str | None:
    if parent_id is None:
        return None
    parent = project.nodes.get(parent_id)
    return None if parent is None else parent.type_id


def _destination_errors(
    project: Project,
    destination: DropIntent,
    *,
    child_type: str,
    count_after: int,
    node_id: NodeId | None = None,
) -> tuple[Diagnostic, ...]:
    if destination.parent_id is None and destination.slot_name != ROOT_SLOT:
        return (
            _error(
                "slot.unknown",
                f"Root list slot must be {ROOT_SLOT!r}",
                node_id=node_id,
            ),
        )
    if destination.parent_id is not None:
        if destination.parent_id not in project.nodes:
            return (
                _error(
                    "node.missing",
                    f"Parent {destination.parent_id!r} does not exist",
                    node_id=destination.parent_id,
                ),
            )
    errors = validate_occupancy(
        parent_type=_parent_type(project, destination.parent_id),
        slot_name=destination.slot_name,
        count=count_after,
        child_type=child_type,
        node_id=destination.parent_id,
    )
    return errors


def _limit_errors(
    *,
    node_count: int,
    depth: int | None,
    node_id: NodeId | None = None,
) -> tuple[Diagnostic, ...]:
    errors: list[Diagnostic] = []
    if node_count > MAX_NODES:
        errors.append(
            _error(
                "node.limit",
                f"Document would have {node_count} nodes; maximum is {MAX_NODES}",
                node_id=node_id,
            )
        )
    if depth is not None and depth > MAX_DEPTH:
        errors.append(
            _error(
                "node.depth",
                f"Operation would exceed maximum depth {MAX_DEPTH}",
                node_id=node_id,
            )
        )
    return tuple(errors)


def _fresh_node_errors(node: Node, *, existing: Mapping[NodeId, Node]) -> tuple[Diagnostic, ...]:
    errors: list[Diagnostic] = []
    if not is_identifier_safe_node_id(node.id):
        errors.append(
            _error(
                "id.invalid",
                f"Node id {node.id!r} is not a bounded identifier-safe name",
                node_id=node.id,
            )
        )
    if node.id in existing:
        errors.append(
            _error(
                "id.duplicate",
                f"Node id {node.id!r} already exists",
                node_id=node.id,
            )
        )
    if not slots_are_empty(node):
        errors.append(
            _error(
                "node.slots_not_empty",
                f"Inserted node {node.id!r} must have empty child slots",
                node_id=node.id,
            )
        )
    if not node.type_id:
        errors.append(
            _error("node.type", "Node type_id must be non-empty", node_id=node.id)
        )
    table = type_slot_table(node.type_id)
    if table is not None:
        for slot_name in node.slots:
            if slot_name not in table:
                errors.append(
                    _error(
                        "slot.unknown",
                        f"{node.type_id} does not declare slot {slot_name!r}",
                        node_id=node.id,
                    )
                )
    for event_name, symbol in node.events.items():
        expected = event_symbol_name(node.id, event_name)
        if symbol.name != expected:
            errors.append(
                _error(
                    "event.symbol",
                    f"Event {event_name!r} requires symbol {expected!r}",
                    node_id=node.id,
                )
            )
    return tuple(errors)


def _apply_insert(snapshot: DocumentSnapshot, command: InsertNode) -> CommandResult:
    project = snapshot.project
    node = command.node
    dest = command.destination
    fresh = _fresh_node_errors(node, existing=project.nodes)
    if fresh:
        return _reject(snapshot, command.command_id, *fresh)

    current = slot_children(project, dest.parent_id, dest.slot_name)
    if current is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "node.missing" if dest.parent_id is not None else "slot.unknown",
                "Insert destination does not exist",
                node_id=dest.parent_id,
            ),
        )
    index_error = validate_index(dest.index, len(current))
    if index_error is not None:
        return _reject(snapshot, command.command_id, index_error)

    dest_errors = _destination_errors(
        project,
        dest,
        child_type=node.type_id,
        count_after=len(current) + 1,
        node_id=node.id,
    )
    if dest_errors:
        return _reject(snapshot, command.command_id, *dest_errors)

    child_depth = destination_depth(project, dest.parent_id)
    limit = _limit_errors(
        node_count=len(project.nodes) + 1,
        depth=child_depth,
        node_id=node.id,
    )
    if limit:
        return _reject(snapshot, command.command_id, *limit)

    new_children = current[: dest.index] + (node.id,) + current[dest.index :]
    nodes = dict(project.nodes)
    nodes[node.id] = node
    new_project, _ = _replace_slot(
        replace(project, nodes=nodes), dest.parent_id, dest.slot_name, new_children, nodes
    )
    affected = {node.id}
    if dest.parent_id is not None:
        affected.add(dest.parent_id)
    return _commit(snapshot, new_project, command.command_id, frozenset(affected))


def _apply_delete(snapshot: DocumentSnapshot, command: DeleteNode) -> CommandResult:
    project = snapshot.project
    node_id = command.node_id
    if node_id not in project.nodes:
        return _reject(
            snapshot,
            command.command_id,
            _error("node.missing", f"Node {node_id!r} does not exist", node_id=node_id),
        )
    owner = owner_of(project, node_id)
    if owner is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "ref.orphan",
                f"Node {node_id!r} is not in the document forest",
                node_id=node_id,
            ),
        )
    parent_id, slot_name, _index = owner
    current = slot_children(project, parent_id, slot_name)
    if current is None:
        return _reject(
            snapshot,
            command.command_id,
            _error("node.missing", "Delete owner slot is missing", node_id=parent_id),
        )
    remaining = tuple(cid for cid in current if cid != node_id)
    dest_errors = validate_occupancy(
        parent_type=_parent_type(project, parent_id),
        slot_name=slot_name,
        count=len(remaining),
        node_id=parent_id,
    )
    if dest_errors:
        return _reject(snapshot, command.command_id, *dest_errors)

    removed = subtree_ids(project, node_id)
    nodes = {nid: node for nid, node in project.nodes.items() if nid not in removed}
    new_project, _ = _replace_slot(
        replace(project, nodes=nodes), parent_id, slot_name, remaining, nodes
    )
    affected = set(removed)
    if parent_id is not None:
        affected.add(parent_id)
    return _commit(snapshot, new_project, command.command_id, frozenset(affected))


def _apply_move(snapshot: DocumentSnapshot, command: MoveNode) -> CommandResult:
    project = snapshot.project
    node_id = command.node_id
    dest = command.destination
    node = project.nodes.get(node_id)
    if node is None:
        return _reject(
            snapshot,
            command.command_id,
            _error("node.missing", f"Node {node_id!r} does not exist", node_id=node_id),
        )
    owner = owner_of(project, node_id)
    if owner is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "ref.orphan",
                f"Node {node_id!r} is not in the document forest",
                node_id=node_id,
            ),
        )
    src_parent, src_slot, _src_index = owner

    # DropIntent.index is already post-removal (TDD §2.5.5). The resolver
    # subtracts 1 when source index < boundary in the same slot. This reducer
    # must NOT repeat that correction.
    if dest.parent_id is not None and dest.parent_id not in project.nodes:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "node.missing",
                f"Parent {dest.parent_id!r} does not exist",
                node_id=dest.parent_id,
            ),
        )
    if dest.parent_id == node_id or dest.parent_id in descendants_of(project, node_id):
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "graph.cycle",
                "Cannot move a node into its descendant.",
                node_id=node_id,
            ),
        )

    same_slot = src_parent == dest.parent_id and src_slot == dest.slot_name
    src_children = slot_children(project, src_parent, src_slot)
    if src_children is None:
        return _reject(
            snapshot,
            command.command_id,
            _error("node.missing", "Move source slot is missing", node_id=src_parent),
        )
    without_source = tuple(cid for cid in src_children if cid != node_id)

    if same_slot:
        dest_list = without_source
    else:
        dest_list = slot_children(project, dest.parent_id, dest.slot_name)
        if dest_list is None:
            return _reject(
                snapshot,
                command.command_id,
                _error(
                    "slot.unknown",
                    "Move destination does not exist",
                    node_id=dest.parent_id,
                ),
            )

    index_error = validate_index(dest.index, len(dest_list))
    if index_error is not None:
        return _reject(snapshot, command.command_id, index_error)

    if same_slot and dest.index < len(src_children) and src_children[dest.index] == node_id:
        # Same list, already at the post-removal index that restores position.
        restored = (
            without_source[: dest.index] + (node_id,) + without_source[dest.index :]
        )
        if restored == src_children:
            return _noop(snapshot, command.command_id)

    dest_errors = _destination_errors(
        project,
        dest,
        child_type=node.type_id,
        count_after=len(dest_list) + 1,
        node_id=node_id,
    )
    if dest_errors:
        return _reject(snapshot, command.command_id, *dest_errors)

    if not same_slot:
        src_occ = validate_occupancy(
            parent_type=_parent_type(project, src_parent),
            slot_name=src_slot,
            count=len(without_source),
            node_id=src_parent,
        )
        if src_occ:
            return _reject(snapshot, command.command_id, *src_occ)

    new_depth = destination_depth(project, dest.parent_id)
    if new_depth is not None:
        deepest = new_depth + subtree_height(project, node_id) - 1
    else:
        deepest = None
    limit = _limit_errors(
        node_count=len(project.nodes),
        depth=deepest,
        node_id=node_id,
    )
    if limit:
        return _reject(snapshot, command.command_id, *limit)

    placed = dest_list[: dest.index] + (node_id,) + dest_list[dest.index :]
    nodes = dict(project.nodes)
    new_project = replace(project, nodes=nodes)
    if same_slot:
        new_project, nodes = _replace_slot(
            new_project, dest.parent_id, dest.slot_name, placed, nodes
        )
    else:
        new_project, nodes = _replace_slot(
            new_project, src_parent, src_slot, without_source, nodes
        )
        new_project, nodes = _replace_slot(
            new_project, dest.parent_id, dest.slot_name, placed, nodes
        )

    if (
        new_project.root_ids == project.root_ids
        and new_project.nodes == project.nodes
    ):
        return _noop(snapshot, command.command_id)

    affected = {node_id}
    if src_parent is not None:
        affected.add(src_parent)
    if dest.parent_id is not None:
        affected.add(dest.parent_id)
    return _commit(snapshot, new_project, command.command_id, frozenset(affected))


def _apply_wrap(snapshot: DocumentSnapshot, command: WrapNode) -> CommandResult:
    project = snapshot.project
    node_id = command.node_id
    wrapper = command.wrapper
    node = project.nodes.get(node_id)
    if node is None:
        return _reject(
            snapshot,
            command.command_id,
            _error("node.missing", f"Node {node_id!r} does not exist", node_id=node_id),
        )
    owner = owner_of(project, node_id)
    if owner is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "ref.orphan",
                f"Node {node_id!r} is not in the document forest",
                node_id=node_id,
            ),
        )
    parent_id, slot_name, index = owner
    fresh = _fresh_node_errors(wrapper, existing=project.nodes)
    if fresh:
        return _reject(snapshot, command.command_id, *fresh)
    if wrapper.id == node_id:
        return _reject(
            snapshot,
            command.command_id,
            _error("id.duplicate", "Wrapper id collides with wrapped node", node_id=wrapper.id),
        )

    # Owner slot keeps the same occupancy (replace node with wrapper).
    owner_errors = validate_occupancy(
        parent_type=_parent_type(project, parent_id),
        slot_name=slot_name,
        count=len(slot_children(project, parent_id, slot_name) or ()),
        child_type=wrapper.type_id,
        node_id=parent_id,
    )
    wrapper_slot_children = tuple(wrapper.slots.get(command.wrapper_slot, ()))
    inner_errors = validate_occupancy(
        parent_type=wrapper.type_id,
        slot_name=command.wrapper_slot,
        count=len(wrapper_slot_children) + 1,
        child_type=node.type_id,
        node_id=wrapper.id,
    )
    if owner_errors or inner_errors:
        return _reject(snapshot, command.command_id, *(owner_errors + inner_errors))

    parent_depth = 1 if parent_id is None else node_depth(project, parent_id)
    if parent_depth is None:
        deepest = None
    else:
        # Wrapper occupies the wrapped node's depth; the subtree grows by 1.
        old_depth = node_depth(project, node_id) or (
            parent_depth if parent_id is None else parent_depth + 1
        )
        deepest = old_depth + subtree_height(project, node_id)
    limit = _limit_errors(
        node_count=len(project.nodes) + 1,
        depth=deepest,
        node_id=wrapper.id,
    )
    if limit:
        return _reject(snapshot, command.command_id, *limit)

    owner_children = slot_children(project, parent_id, slot_name)
    if owner_children is None:
        return _reject(
            snapshot,
            command.command_id,
            _error("node.missing", "Wrap owner slot is missing", node_id=parent_id),
        )
    replaced = (
        owner_children[:index] + (wrapper.id,) + owner_children[index + 1 :]
    )
    new_slots = dict(wrapper.slots)
    new_slots[command.wrapper_slot] = (node_id,)
    placed_wrapper = replace(wrapper, slots=new_slots)
    nodes = dict(project.nodes)
    nodes[placed_wrapper.id] = placed_wrapper
    new_project, _ = _replace_slot(
        replace(project, nodes=nodes), parent_id, slot_name, replaced, nodes
    )
    affected = {node_id, wrapper.id}
    if parent_id is not None:
        affected.add(parent_id)
    return _commit(snapshot, new_project, command.command_id, frozenset(affected))


def _props_of(
    project: Project, node_id: NodeId | None
) -> Mapping[str, JsonValue] | None:
    if node_id is None:
        return project.page
    node = project.nodes.get(node_id)
    if node is None:
        return None
    return node.props


def _with_props(
    project: Project, node_id: NodeId | None, props: Mapping[str, JsonValue]
) -> Project:
    if node_id is None:
        return replace(project, page=dict(props))
    node = project.nodes[node_id]
    nodes = dict(project.nodes)
    nodes[node_id] = replace(node, props=dict(props))
    return replace(project, nodes=nodes)


def _apply_set_property(
    snapshot: DocumentSnapshot, command: SetProperty
) -> CommandResult:
    project = snapshot.project
    props = _props_of(project, command.node_id)
    if props is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "node.missing",
                f"Node {command.node_id!r} does not exist",
                node_id=command.node_id,
            ),
        )
    if not command.name:
        return _reject(
            snapshot,
            command.command_id,
            _error("property.name", "Property name must be non-empty", node_id=command.node_id),
        )
    current = props.get(command.name, _MISSING)
    if current is not _MISSING and _json_equal(current, command.value):
        return _noop(snapshot, command.command_id)
    new_props = dict(props)
    new_props[command.name] = command.value
    new_project = _with_props(project, command.node_id, new_props)
    affected = frozenset() if command.node_id is None else frozenset({command.node_id})
    return _commit(snapshot, new_project, command.command_id, affected)


def _apply_unset_property(
    snapshot: DocumentSnapshot, command: UnsetProperty
) -> CommandResult:
    project = snapshot.project
    props = _props_of(project, command.node_id)
    if props is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "node.missing",
                f"Node {command.node_id!r} does not exist",
                node_id=command.node_id,
            ),
        )
    if command.name not in props:
        return _noop(snapshot, command.command_id)
    new_props = dict(props)
    del new_props[command.name]
    new_project = _with_props(project, command.node_id, new_props)
    affected = frozenset() if command.node_id is None else frozenset({command.node_id})
    return _commit(snapshot, new_project, command.command_id, affected)


def _apply_set_event(snapshot: DocumentSnapshot, command: SetEvent) -> CommandResult:
    project = snapshot.project
    node = project.nodes.get(command.node_id)
    if node is None:
        return _reject(
            snapshot,
            command.command_id,
            _error(
                "node.missing",
                f"Node {command.node_id!r} does not exist",
                node_id=command.node_id,
            ),
        )
    if not command.event_name:
        return _reject(
            snapshot,
            command.command_id,
            _error("event.name", "Event name must be non-empty", node_id=command.node_id),
        )
    if command.symbol is None:
        if command.event_name not in node.events:
            return _noop(snapshot, command.command_id)
        new_events = dict(node.events)
        del new_events[command.event_name]
    else:
        expected = event_symbol_name(command.node_id, command.event_name)
        if command.symbol.name != expected:
            return _reject(
                snapshot,
                command.command_id,
                _error(
                    "event.symbol",
                    f"Event {command.event_name!r} requires symbol {expected!r}, "
                    f"got {command.symbol.name!r}",
                    node_id=command.node_id,
                ),
            )
        current = node.events.get(command.event_name)
        if current is not None and current.name == command.symbol.name:
            return _noop(snapshot, command.command_id)
        new_events = dict(node.events)
        new_events[command.event_name] = command.symbol
    nodes = dict(project.nodes)
    nodes[command.node_id] = replace(node, events=new_events)
    new_project = replace(project, nodes=nodes)
    return _commit(
        snapshot, new_project, command.command_id, frozenset({command.node_id})
    )


def _apply_replace(snapshot: DocumentSnapshot, command: ReplaceProject) -> CommandResult:
    errors = validate_project(command.project)
    if errors:
        return _reject(snapshot, command.command_id, *errors)
    if command.project == snapshot.project:
        return _noop(snapshot, command.command_id)
    return _commit(
        snapshot,
        command.project,
        command.command_id,
        frozenset(command.project.nodes),
    )


def _history_unsupported(
    snapshot: DocumentSnapshot, command: Undo | Redo
) -> CommandResult:
    kind = "Undo" if isinstance(command, Undo) else "Redo"
    return _reject(
        snapshot,
        command.command_id,
        _error(
            "history.unsupported",
            f"{kind} is owned by T09 history_dispatcher; the pure reducer "
            "has no stack and rejects undo/redo.",
        ),
    )


class Reducer:
    """CommandReducer: atomic, pure document transformations."""

    def apply(
        self, snapshot: DocumentSnapshot, command: CommandADT
    ) -> CommandResult:
        if isinstance(command, InsertNode):
            return _apply_insert(snapshot, command)
        if isinstance(command, DeleteNode):
            return _apply_delete(snapshot, command)
        if isinstance(command, MoveNode):
            return _apply_move(snapshot, command)
        if isinstance(command, WrapNode):
            return _apply_wrap(snapshot, command)
        if isinstance(command, SetProperty):
            return _apply_set_property(snapshot, command)
        if isinstance(command, UnsetProperty):
            return _apply_unset_property(snapshot, command)
        if isinstance(command, SetEvent):
            return _apply_set_event(snapshot, command)
        if isinstance(command, ReplaceProject):
            return _apply_replace(snapshot, command)
        if isinstance(command, (Undo, Redo)):
            return _history_unsupported(snapshot, command)
        return _reject(
            snapshot,
            getattr(command, "command_id", ""),
            _error("command.unknown", f"Unknown command type {type(command)!r}"),
        )


_REDUCER = Reducer()
apply = _REDUCER.apply
