"""A tiny stand-in for :class:`flet.Page` for headless composition tests."""

from __future__ import annotations


class FakePage:
    def __init__(self) -> None:
        self.title = ""
        self.padding = 0
        self.spacing = 0
        self.bgcolor = None
        self.theme = None
        self.theme_mode = None
        self.controls: list[object] = []
        self.services: list[object] = []
        self.overlay: list[object] = []
        self.dialogs: list[object] = []
        self.on_keyboard_event = None
        self.on_close = None
        self.updates = 0

    def add(self, *controls: object) -> None:
        self.controls.extend(controls)

    def update(self) -> None:
        self.updates += 1

    def show_dialog(self, control: object) -> None:
        self.dialogs.append(control)

    def pop_dialog(self) -> None:
        if self.dialogs:
            self.dialogs.pop()

    def run_task(self, handler, *args, **kwargs):
        return None
