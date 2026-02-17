from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.utils.id_generator import new_id


@dataclass
class WidgetNode:
    id: str
    type: str
    props: dict[str, Any] = field(default_factory=dict)
    children: list["WidgetNode"] = field(default_factory=list)
    parent_id: str | None = None
    order: int = 0
    slot: str | None = None

    def clone(self, *, deep_new_ids: bool = True) -> "WidgetNode":
        """Create a deep copy of this node.

        Args:
            deep_new_ids: If True (default), every node in the cloned subtree
                gets a fresh unique id.  Set to False only when you need an
                exact structural copy (e.g. for undo snapshots).
        """
        copied = WidgetNode(
            id=new_id(self.type.lower()) if deep_new_ids else self.id,
            type=self.type,
            props=dict(self.props),
            parent_id=self.parent_id,
            order=self.order,
            slot=self.slot,
        )
        copied.children = [
            child.clone(deep_new_ids=deep_new_ids) for child in self.children
        ]
        return copied