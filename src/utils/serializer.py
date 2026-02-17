from __future__ import annotations

import json
import shutil
from dataclasses import asdict
from pathlib import Path

from src.models.widget_node import WidgetNode
from src.state.project_state import ProjectState
from src.utils.constants import SCHEMA_VERSION


def node_to_dict(node: WidgetNode) -> dict:
    data = asdict(node)
    data["children"] = [node_to_dict(child) for child in node.children]
    return data


def node_from_dict(data: dict) -> WidgetNode:
    node = WidgetNode(
        id=data["id"],
        type=data["type"],
        props=data.get("props", {}),
        parent_id=data.get("parent_id"),
        order=data.get("order", 0),
        slot=data.get("slot"),
    )
    node.children = [node_from_dict(child) for child in data.get("children", [])]
    return node


def project_to_dict(project: ProjectState) -> dict:
    return {
        "name": project.name,
        "schema_version": project.schema_version,
        "theme": project.theme,
        "device_frame": project.device_frame,
        "selected_node_id": project.selected_node_id,
        "tree": node_to_dict(project.tree),
    }


def project_from_dict(data: dict) -> ProjectState:
    migrated = migrate_project_dict(data)
    return ProjectState(
        name=migrated["name"],
        schema_version=migrated["schema_version"],
        theme=migrated.get("theme", "light"),
        device_frame=migrated.get("device_frame", "desktop"),
        selected_node_id=migrated.get("selected_node_id"),
        tree=node_from_dict(migrated["tree"]),
    )


def save_project(project: ProjectState, path: str | Path) -> None:
    path = Path(path)
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + ".bak"))
    path.write_text(json.dumps(project_to_dict(project), indent=2), encoding="utf-8")


def load_project(path: str | Path) -> ProjectState:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return project_from_dict(data)


def migrate_0_0_to_0_1(data: dict) -> dict:
    data["schema_version"] = "0.1"
    data.setdefault("theme", "light")
    data.setdefault("device_frame", "desktop")
    return data


MIGRATIONS = {"0.0": migrate_0_0_to_0_1}


def migrate_project_dict(data: dict) -> dict:
    version = data.get("schema_version", "0.0")
    while version in MIGRATIONS:
        data = MIGRATIONS[version](data)
        version = data.get("schema_version", SCHEMA_VERSION)
    return data
