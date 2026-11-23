"""File-backed project session: dirty tracking, recents, and crash-safe autosave.

The session owns *where* a project lives and whether it has unsaved changes.
It never owns the document itself; the history dispatcher does.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from flet_visual_builder.contracts import Project
from flet_visual_builder.persistence.json_repository import JsonRepository

AUTOSAVE_NAME = "autosave.fvb.json"
RECENTS_NAME = "recents.json"
MAX_RECENTS = 8


def app_dir() -> Path:
    override = os.environ.get("FLET_VISUAL_BUILDER_HOME")
    if override:
        return Path(override).expanduser()
    xdg = os.environ.get("XDG_DATA_HOME")
    base = Path(xdg).expanduser() if xdg else Path.home() / ".local" / "share"
    return base / "flet-visual-builder"


def _atomic_write(path: Path, payload: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


@dataclass(frozen=True)
class RecentEntry:
    path: str
    name: str
    opened_at: str

    def as_dict(self) -> dict[str, str]:
        return {"path": self.path, "name": self.name, "opened_at": self.opened_at}


class ProjectSession:
    """Session metadata for the currently open document."""

    def __init__(self, base: Path | None = None) -> None:
        self.base = base or app_dir()
        self.path: Path | None = None
        self.dirty = False
        self._autosaved_revision = -1

    # ── identity ──────────────────────────────────────────────────────
    def label(self, fallback: str = "Untitled") -> str:
        if self.path is None:
            return fallback
        return self.path.name.removesuffix(".fvb.json").removesuffix(".json")

    def location(self) -> str:
        if self.path is None:
            return "Not saved yet"
        return str(self.path)

    def set_path(self, path: str | Path | None, *, saved: bool = False) -> None:
        self.path = Path(path).expanduser().resolve() if path else None
        if saved:
            self.dirty = False
            self._autosaved_revision = -1

    def mark_dirty(self) -> None:
        self.dirty = True

    def mark_saved(self) -> None:
        self.dirty = False
        self._autosaved_revision = -1

    # ── autosave ──────────────────────────────────────────────────────
    @property
    def autosave_path(self) -> Path:
        return self.base / AUTOSAVE_NAME

    def should_autosave(
        self, project: Project, revision: int, *, min_interval: int = 40
    ) -> bool:
        return revision != self._autosaved_revision

    def write_autosave(
        self, repository: JsonRepository, project: Project, revision: int
    ) -> bool:
        """Persist a recovery copy. Returns False when the document is not serialisable."""
        result = repository.save(project, self.autosave_path)
        if not result.ok:
            return False
        self._autosaved_revision = revision
        _atomic_write(
            self.base / "autosave.meta.json",
            json.dumps(
                {
                    "path": str(self.path) if self.path else None,
                    "name": project.name,
                    "revision": revision,
                    "saved_at": datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                },
                indent=2,
            ),
        )
        return True

    def autosave_metadata(self) -> dict[str, object] | None:
        meta = self.base / "autosave.meta.json"
        if not meta.exists():
            return None
        try:
            return json.loads(meta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None

    def read_autosave(self, repository: JsonRepository) -> Project | None:
        if not self.autosave_path.exists():
            return None
        result = repository.load(self.autosave_path)
        return result.project if result.ok else None

    def clear_autosave(self) -> None:
        for path in (self.autosave_path, self.base / "autosave.meta.json"):
            try:
                path.unlink()
            except FileNotFoundError:
                pass
            except OSError:
                pass

    # ── recents ───────────────────────────────────────────────────────
    def _recents_path(self) -> Path:
        return self.base / RECENTS_NAME

    def recents(self) -> list[RecentEntry]:
        path = self._recents_path()
        if not path.exists():
            return []
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return []
        entries: list[RecentEntry] = []
        if not isinstance(raw, list):
            return entries
        for item in raw:
            if not isinstance(item, dict):
                continue
            file_path = item.get("path")
            if not isinstance(file_path, str):
                continue
            entries.append(
                RecentEntry(
                    path=file_path,
                    name=str(item.get("name") or Path(file_path).name),
                    opened_at=str(item.get("opened_at") or ""),
                )
            )
        return [entry for entry in entries if Path(entry.path).exists()][:MAX_RECENTS]

    def remember(self, path: str | Path, name: str | None = None) -> None:
        resolved = str(Path(path).expanduser().resolve())
        entries = [entry for entry in self.recents() if entry.path != resolved]
        entries.insert(
            0,
            RecentEntry(
                path=resolved,
                name=name or Path(resolved).name.removesuffix(".fvb.json"),
                opened_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
        payload = [entry.as_dict() for entry in entries[:MAX_RECENTS]]
        _atomic_write(self._recents_path(), json.dumps(payload, indent=2))
