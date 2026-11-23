"""Stateful CommandDispatcher: history, revisions, coalescing, stale guard.

Document transforms are delegated to T04's pure reducer. Undo/Redo are
intercepted here — the reducer rejects them with ``history.unsupported``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import replace
from typing import Final

from flet_visual_builder.contracts import (
    Asset,
    CommandADT,
    CommandReducer,
    CommandResult,
    CommandStatus,
    Diagnostic,
    DocumentSnapshot,
    Node,
    NodeId,
    Project,
    Redo,
    ReplaceProject,
    SetProperty,
    Severity,
    Undo,
    UnsetProperty,
)
from flet_visual_builder.model.reducer import Reducer

MAX_HISTORY_ENTRIES: Final[int] = 100
MAX_HISTORY_STRUCTURAL_BYTES: Final[int] = 64 * 1024 * 1024
COALESCE_IDLE_SECONDS: Final[float] = 0.75

_CoalesceKey = tuple[str, NodeId | None, str]


def _thaw(value: object) -> object:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, Mapping):
        return {str(key): _thaw(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_thaw(item) for item in value]
    raise TypeError(f"Unsupported structural value: {type(value)!r}")


def _node_struct(node: Node) -> dict[str, object]:
    return {
        "id": node.id,
        "type_id": node.type_id,
        "props": _thaw(dict(node.props)),
        "slots": {slot: list(ids) for slot, ids in node.slots.items()},
        "events": {name: symbol.name for name, symbol in node.events.items()},
    }


def structural_snapshot_dict(project: Project) -> dict[str, object]:
    """JSON-able structural document. Asset *bytes* are omitted (hash only)."""
    assets = {
        key: {
            "id": asset.id,
            "media_type": asset.media_type,
            "sha256": asset.sha256.lower(),
        }
        for key, asset in project.assets.items()
    }
    return {
        "name": project.name,
        "page": _thaw(dict(project.page)),
        "root_ids": list(project.root_ids),
        "nodes": {nid: _node_struct(node) for nid, node in project.nodes.items()},
        "assets": assets,
        "schema_version": project.schema_version,
        "catalogue_version": project.catalogue_version,
        "target_flet": project.target_flet,
    }


def structural_snapshot_bytes(project: Project) -> int:
    """UTF-8 size of serialized structural snapshot data (no asset payloads)."""
    raw = json.dumps(
        structural_snapshot_dict(project),
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )
    return len(raw.encode("utf-8"))


def _error(code: str, message: str) -> Diagnostic:
    return Diagnostic(code=code, message=message, severity=Severity.ERROR)


class HistoryDispatcher:
    """CommandDispatcher wrapping T04's reducer with a snapshot history stack."""

    def __init__(
        self,
        snapshot: DocumentSnapshot,
        *,
        reducer: CommandReducer | None = None,
        clock: Callable[[], float] | None = None,
        max_entries: int = MAX_HISTORY_ENTRIES,
        max_structural_bytes: int = MAX_HISTORY_STRUCTURAL_BYTES,
        coalesce_idle_seconds: float = COALESCE_IDLE_SECONDS,
    ) -> None:
        self._reducer: CommandReducer = reducer if reducer is not None else Reducer()
        self._clock = clock if clock is not None else time.monotonic
        self._max_entries = max_entries
        self._max_structural_bytes = max_structural_bytes
        self._coalesce_idle_s = coalesce_idle_seconds
        self._asset_store: dict[str, bytes] = {}
        self._undo: list[Project] = []
        self._redo: list[Project] = []
        self._committed_ids: set[str] = set()
        self._coalesce_key: _CoalesceKey | None = None
        self._coalesce_time: float | None = None
        self._snapshot = DocumentSnapshot(
            project=self._intern_project(snapshot.project),
            revision=snapshot.revision,
        )

    @property
    def snapshot(self) -> DocumentSnapshot:
        return self._snapshot

    @property
    def history_length(self) -> int:
        return len(self._undo) + len(self._redo)

    @property
    def undo_count(self) -> int:
        return len(self._undo)

    @property
    def redo_count(self) -> int:
        return len(self._redo)

    def history_structural_bytes(self) -> int:
        total = 0
        for project in self._undo:
            total += structural_snapshot_bytes(project)
        for project in self._redo:
            total += structural_snapshot_bytes(project)
        return total

    def execute(self, command: CommandADT, *, expected_revision: int) -> CommandResult:
        current = self._snapshot
        if expected_revision != current.revision:
            return self._reject(
                command.command_id,
                "revision.stale",
                (
                    f"expected_revision {expected_revision} does not match "
                    f"current revision {current.revision}"
                ),
            )
        if command.command_id in self._committed_ids:
            return self._reject(
                command.command_id,
                "command.duplicate",
                f"command_id {command.command_id!r} was already committed",
            )
        if isinstance(command, Undo):
            return self._execute_undo(command)
        if isinstance(command, Redo):
            return self._execute_redo(command)

        result = self._reducer.apply(current, command)
        if result.status is CommandStatus.COMMITTED:
            if result.before_revision != current.revision:
                return self._reject(
                    command.command_id,
                    "revision.stale",
                    "Result was computed against a stale revision and was discarded",
                )
            return self._install_committed(command, result)
        return result

    def apply_result(self, result: CommandResult) -> CommandResult:
        """Install a previously computed result only if its base revision is live.

        Out-of-order / background results whose ``before_revision`` is no longer
        current are discarded without mutation (TDD §2.6 line 1879).
        """
        if result.before_revision != self._snapshot.revision:
            return self._reject(
                result.command_id,
                "revision.stale",
                "Result was computed against a stale revision and was discarded",
            )
        if result.status is not CommandStatus.COMMITTED:
            return result
        if result.command_id in self._committed_ids:
            return self._reject(
                result.command_id,
                "command.duplicate",
                f"command_id {result.command_id!r} was already committed",
            )
        self._undo.append(self._intern_project(self._snapshot.project))
        self._redo.clear()
        self._clear_coalesce()
        interned = self._intern_project(result.snapshot.project)
        self._snapshot = DocumentSnapshot(
            project=interned, revision=result.snapshot.revision
        )
        self._committed_ids.add(result.command_id)
        self._trim()
        if interned is result.snapshot.project:
            return result
        return replace(result, snapshot=self._snapshot)

    def _install_committed(
        self, command: CommandADT, result: CommandResult
    ) -> CommandResult:
        now = self._clock()
        interned = self._intern_project(result.snapshot.project)
        live = DocumentSnapshot(project=interned, revision=result.snapshot.revision)

        if isinstance(command, ReplaceProject):
            self._undo.clear()
            self._redo.clear()
            self._committed_ids.clear()
            self._clear_coalesce()
        elif self._should_coalesce(command, now):
            pass
        else:
            self._undo.append(self._intern_project(self._snapshot.project))
            self._redo.clear()

        self._snapshot = live
        self._committed_ids.add(command.command_id)
        self._remember_coalesce(command, now)
        self._trim()
        if interned is result.snapshot.project:
            return result
        return replace(result, snapshot=live)

    def _execute_undo(self, command: Undo) -> CommandResult:
        current = self._snapshot
        if not self._undo:
            return self._noop(command.command_id)
        restored = self._undo.pop()
        self._redo.append(self._intern_project(current.project))
        new_project = self._intern_project(restored)
        live = DocumentSnapshot(project=new_project, revision=current.revision + 1)
        self._snapshot = live
        self._committed_ids.add(command.command_id)
        self._clear_coalesce()
        affected = frozenset(current.project.nodes) | frozenset(new_project.nodes)
        return CommandResult(
            command_id=command.command_id,
            status=CommandStatus.COMMITTED,
            before_revision=current.revision,
            snapshot=live,
            affected_ids=affected,
        )

    def _execute_redo(self, command: Redo) -> CommandResult:
        current = self._snapshot
        if not self._redo:
            return self._noop(command.command_id)
        restored = self._redo.pop()
        self._undo.append(self._intern_project(current.project))
        new_project = self._intern_project(restored)
        live = DocumentSnapshot(project=new_project, revision=current.revision + 1)
        self._snapshot = live
        self._committed_ids.add(command.command_id)
        self._clear_coalesce()
        affected = frozenset(current.project.nodes) | frozenset(new_project.nodes)
        return CommandResult(
            command_id=command.command_id,
            status=CommandStatus.COMMITTED,
            before_revision=current.revision,
            snapshot=live,
            affected_ids=affected,
        )

    def _should_coalesce(self, command: CommandADT, now: float) -> bool:
        if not isinstance(command, (SetProperty, UnsetProperty)):
            return False
        if command.gesture_id is None:
            return False
        if self._coalesce_key is None or self._coalesce_time is None:
            return False
        key: _CoalesceKey = (command.gesture_id, command.node_id, command.name)
        if key != self._coalesce_key:
            return False
        idle = now - self._coalesce_time
        return 0 <= idle <= self._coalesce_idle_s

    def _remember_coalesce(self, command: CommandADT, now: float) -> None:
        if (
            isinstance(command, (SetProperty, UnsetProperty))
            and command.gesture_id is not None
        ):
            self._coalesce_key = (command.gesture_id, command.node_id, command.name)
            self._coalesce_time = now
            return
        self._clear_coalesce()

    def _clear_coalesce(self) -> None:
        self._coalesce_key = None
        self._coalesce_time = None

    def _trim(self) -> None:
        while self._undo or self._redo:
            over_count = self.history_length > self._max_entries
            over_bytes = self.history_structural_bytes() > self._max_structural_bytes
            if not over_count and not over_bytes:
                break
            if self._undo:
                self._undo.pop(0)
            else:
                self._redo.pop(0)
        self._gc_assets()

    def _gc_assets(self) -> None:
        live: set[str] = set()
        for project in (self._snapshot.project, *self._undo, *self._redo):
            for asset in project.assets.values():
                live.add(asset.sha256.lower())
        for digest in list(self._asset_store):
            if digest not in live:
                del self._asset_store[digest]

    def _intern_project(self, project: Project) -> Project:
        if not project.assets:
            return project
        new_assets: dict[str, Asset] = {}
        changed = False
        for key, asset in project.assets.items():
            digest = asset.sha256.lower()
            stored = self._asset_store.get(digest)
            if stored is None:
                self._asset_store[digest] = asset.data
                stored = asset.data
            if stored is asset.data and asset.sha256 == digest:
                new_assets[key] = asset
            else:
                new_assets[key] = Asset(
                    id=asset.id,
                    media_type=asset.media_type,
                    sha256=digest,
                    data=stored,
                )
                changed = True
        if not changed:
            return project
        return replace(project, assets=new_assets)

    def _reject(self, command_id: str, code: str, message: str) -> CommandResult:
        current = self._snapshot
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.REJECTED,
            before_revision=current.revision,
            snapshot=current,
            affected_ids=frozenset(),
            diagnostics=(_error(code, message),),
        )

    def _noop(self, command_id: str) -> CommandResult:
        current = self._snapshot
        return CommandResult(
            command_id=command_id,
            status=CommandStatus.NOOP,
            before_revision=current.revision,
            snapshot=current,
            affected_ids=frozenset(),
        )
