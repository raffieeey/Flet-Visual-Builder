from __future__ import annotations

from dataclasses import dataclass

from src.models.widget_node import WidgetNode


@dataclass
class ProjectState:
    name: str
    tree: WidgetNode
    schema_version: str = "0.1"
    theme: str = "light"
    device_frame: str = "desktop"
    selected_node_id: str | None = None
