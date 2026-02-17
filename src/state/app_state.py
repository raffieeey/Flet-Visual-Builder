from __future__ import annotations

from collections.abc import Callable

from src.state.project_state import ProjectState
from src.utils.serializer import project_to_dict, project_from_dict


class AppState:
    def __init__(self, project: ProjectState):
        self.project = project
        self._listeners: list[Callable[[ProjectState], None]] = []
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []

    def transact(self, fn: Callable[[ProjectState], None]) -> None:
        self._undo_stack.append(self._snapshot())
        if len(self._undo_stack) > 50:
            self._undo_stack.pop(0)
        fn(self.project)
        self._redo_stack.clear()
        self._notify()

    def undo(self) -> None:
        if not self._undo_stack:
            return
        self._redo_stack.append(self._snapshot())
        self._restore(self._undo_stack.pop())
        self._notify()

    def redo(self) -> None:
        if not self._redo_stack:
            return
        self._undo_stack.append(self._snapshot())
        self._restore(self._redo_stack.pop())
        self._notify()

    def subscribe(self, cb: Callable[[ProjectState], None]) -> None:
        self._listeners.append(cb)

    def _notify(self) -> None:
        for cb in self._listeners:
            cb(self.project)

    def _snapshot(self) -> dict:
        return project_to_dict(self.project)

    def _restore(self, snapshot: dict) -> None:
        self.project = project_from_dict(snapshot)
