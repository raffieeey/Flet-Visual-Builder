from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WidgetNode:
    id: str
    type: str
    props: dict[str, Any] = field(default_factory=dict)
    children: list["WidgetNode"] = field(default_factory=list)
    parent_id: str | None = None
    order: int = 0
    slot: str | None = None

    def clone(self) -> "WidgetNode":
        copied = WidgetNode(
            id=self.id,
            type=self.type,
            props=dict(self.props),
            parent_id=self.parent_id,
            order=self.order,
            slot=self.slot,
        )
        copied.children = [child.clone() for child in self.children]
        return copied
