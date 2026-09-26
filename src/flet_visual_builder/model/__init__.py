"""Pure document model: validation and command reduction.

No Flet import at runtime. History policy lives in T09.
"""

from src.flet_visual_builder.model.reducer import Reducer, apply
from src.flet_visual_builder.model.validation import (
    MAX_DEPTH,
    MAX_NODES,
    ROOT_SLOT,
    validate_project,
)

__all__ = [
    "MAX_DEPTH",
    "MAX_NODES",
    "ROOT_SLOT",
    "Reducer",
    "apply",
    "validate_project",
]
