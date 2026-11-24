"""Screen metadata helpers.

Screens are the document's root nodes. Their titles and routes are stored in
``Project.screens``; documents written before multi-screen support have no
metadata, so stable defaults are derived from the root order instead.
"""

from __future__ import annotations

from flet_visual_builder.contracts import NodeId, Project, ScreenMeta


def default_screen_meta(index: int) -> ScreenMeta:
    if index == 0:
        return ScreenMeta(title="Home", route="/")
    return ScreenMeta(title=f"Screen {index + 1}", route=f"/screen-{index + 1}")


def screen_entries(project: Project) -> tuple[tuple[NodeId, ScreenMeta], ...]:
    """Root id and effective metadata for every screen, in document order."""
    entries: list[tuple[NodeId, ScreenMeta]] = []
    for index, root_id in enumerate(project.root_ids):
        meta = project.screens.get(root_id)
        entries.append(
            (root_id, meta if meta is not None else default_screen_meta(index))
        )
    return tuple(entries)


def effective_routes(project: Project) -> dict[str, NodeId]:
    """route -> screen root id."""
    return {meta.route: root_id for root_id, meta in screen_entries(project)}


def meta_for(project: Project, root_id: NodeId) -> ScreenMeta | None:
    for candidate, meta in screen_entries(project):
        if candidate == root_id:
            return meta
    return None


def route_for(project: Project, root_id: NodeId) -> str | None:
    meta = meta_for(project, root_id)
    return meta.route if meta is not None else None


def screen_for_route(project: Project, route: str) -> NodeId | None:
    return effective_routes(project).get(route)
