"""Panel base class shared by every region in the workspace."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh, Workspace


class BasePanel:
    """A mountable region that rebuilds itself when its data changes.

    Subclasses set ``interests`` to the refresh reasons they care about and
    implement :meth:`build`. An empty ``interests`` means every reason.
    """

    interests: frozenset[str] = frozenset()

    def __init__(self, workspace: Workspace) -> None:
        self.ws = workspace
        self.control = ft.Container(expand=True)
        self.rebuild()

    def refresh(self, reason: str) -> None:
        if self.interests and reason not in self.interests and reason != Refresh.ALL:
            return
        self.rebuild()
        try:
            self.control.update()
        except RuntimeError:
            # The panel is not mounted yet (first build, or headless composition).
            pass

    def rebuild(self) -> None:
        self.control.content = self.build()

    def build(self) -> ft.Control:  # pragma: no cover - interface
        raise NotImplementedError
