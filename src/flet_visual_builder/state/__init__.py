"""History-aware dispatch and editor UI state. No Flet import."""

from src.flet_visual_builder.state.editor_state import EditorState
from src.flet_visual_builder.state.history_dispatcher import (
    COALESCE_IDLE_SECONDS,
    HistoryDispatcher,
    MAX_HISTORY_ENTRIES,
    MAX_HISTORY_STRUCTURAL_BYTES,
    structural_snapshot_bytes,
)

__all__ = [
    "COALESCE_IDLE_SECONDS",
    "EditorState",
    "HistoryDispatcher",
    "MAX_HISTORY_ENTRIES",
    "MAX_HISTORY_STRUCTURAL_BYTES",
    "structural_snapshot_bytes",
]
