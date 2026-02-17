from __future__ import annotations

from src.models.widget_node import WidgetNode


def walk(root: WidgetNode):
    yield root
    for child in root.children:
        yield from walk(child)


def find_node(root: WidgetNode, node_id: str) -> WidgetNode | None:
    for node in walk(root):
        if node.id == node_id:
            return node
    return None


def find_parent(root: WidgetNode, node_id: str) -> WidgetNode | None:
    for node in walk(root):
        if any(child.id == node_id for child in node.children):
            return node
    return None


def insert_child(parent: WidgetNode, child: WidgetNode, index: int | None = None, slot: str | None = None) -> None:
    child.parent_id = parent.id
    child.slot = slot
    if index is None:
        parent.children.append(child)
    else:
        parent.children.insert(index, child)
    _reindex(parent)


def delete_node(root: WidgetNode, node_id: str) -> bool:
    parent = find_parent(root, node_id)
    if not parent:
        return False
    parent.children = [c for c in parent.children if c.id != node_id]
    _reindex(parent)
    return True


def move_node(root: WidgetNode, node_id: str, target_parent_id: str, index: int | None = None, slot: str | None = None) -> bool:
    node = find_node(root, node_id)
    source_parent = find_parent(root, node_id)
    target_parent = find_node(root, target_parent_id)
    if not node or not source_parent or not target_parent:
        return False
    source_parent.children = [c for c in source_parent.children if c.id != node_id]
    _reindex(source_parent)
    insert_child(target_parent, node, index=index, slot=slot)
    return True


def reorder_sibling(root: WidgetNode, node_id: str, delta: int) -> bool:
    parent = find_parent(root, node_id)
    if not parent:
        return False
    idx = next((i for i, c in enumerate(parent.children) if c.id == node_id), None)
    if idx is None:
        return False
    new_idx = idx + delta
    if new_idx < 0 or new_idx >= len(parent.children):
        return False
    node = parent.children.pop(idx)
    parent.children.insert(new_idx, node)
    _reindex(parent)
    return True


def wrap_node(root: WidgetNode, node_id: str, wrapper: WidgetNode, wrapper_slot: str = "content") -> bool:
    parent = find_parent(root, node_id)
    node = find_node(root, node_id)
    if not parent or not node:
        return False
    idx = next(i for i, c in enumerate(parent.children) if c.id == node_id)
    parent.children[idx] = wrapper
    wrapper.parent_id = parent.id
    wrapper.slot = node.slot
    wrapper.children = []
    node.parent_id = wrapper.id
    node.slot = wrapper_slot
    wrapper.children.append(node)
    _reindex(parent)
    _reindex(wrapper)
    return True


def _reindex(parent: WidgetNode) -> None:
    for i, child in enumerate(parent.children):
        child.order = i
