"""UI-adjacent editor state. Selection/hover/tab/status never touch history."""

from __future__ import annotations

from src.flet_visual_builder.contracts import EditorTab, NodeId


class EditorState:
    """Mutable chrome state. Pure Python; no Flet import, no document history."""

    __slots__ = (
        "selection",
        "hover",
        "active_tab",
        "status",
        "last_successful_projection_revision",
        "visible_stale_revision",
    )

    def __init__(
        self,
        *,
        selection: NodeId | None = None,
        hover: NodeId | None = None,
        active_tab: EditorTab = EditorTab.DESIGN,
        status: str = "",
    ) -> None:
        self.selection = selection
        self.hover = hover
        self.active_tab = active_tab
        self.status = status
        self.last_successful_projection_revision: int | None = None
        self.visible_stale_revision: int | None = None

    def select_node(self, node_id: NodeId | None) -> None:
        self.selection = node_id

    def set_hover(self, node_id: NodeId | None) -> None:
        self.hover = node_id

    def activate(self, tab: EditorTab) -> None:
        self.active_tab = tab

    def set_status(self, text: str) -> None:
        self.status = text

    def note_preview_error(self, last_successful_revision: int) -> None:
        """Keep the last successful projection visible, marked stale."""
        self.visible_stale_revision = last_successful_revision

    def apply_background_result(
        self, result_revision: int, current_revision: int
    ) -> bool:
        """Apply a background projection only if its revision is still current.

        Returns True if applied; False if discarded as stale/out-of-order.
        """
        if result_revision != current_revision:
            return False
        self.last_successful_projection_revision = result_revision
        self.visible_stale_revision = None
        return True
