"""JSON persistence and legacy migration. Runtime Flet imports are forbidden."""

from flet_visual_builder.persistence.assets import (
    MAX_ASSET_BYTES,
    MAX_TOTAL_ASSET_BYTES,
    deduplicate_assets,
    sha256_hex,
)
from flet_visual_builder.persistence.json_repository import (
    MAX_PROJECT_FILE_BYTES,
    MAX_STRUCTURAL_JSON_BYTES,
    JsonRepository,
    PersistenceResult,
    dump,
    load,
    loads,
    save,
)
from flet_visual_builder.persistence.migrations import EditorHints, migrate_to_v2

__all__ = [
    "MAX_ASSET_BYTES",
    "MAX_PROJECT_FILE_BYTES",
    "MAX_STRUCTURAL_JSON_BYTES",
    "MAX_TOTAL_ASSET_BYTES",
    "EditorHints",
    "JsonRepository",
    "PersistenceResult",
    "deduplicate_assets",
    "dump",
    "load",
    "loads",
    "migrate_to_v2",
    "save",
    "sha256_hex",
]
