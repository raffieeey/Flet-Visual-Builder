from __future__ import annotations

import flet as ft

from src.models.widget_node import WidgetNode
from src.state.app_state import AppState
from src.state.project_state import ProjectState


def _initial_project() -> ProjectState:
    root = WidgetNode(id="root", type="Column", props={"alignment": "start"})
    return ProjectState(name="New Project", tree=root)


def main(page: ft.Page) -> None:
    page.title = "Flet Visual Builder"
    state = AppState(project=_initial_project())
    page.add(
        ft.Column(
            controls=[
                ft.Text("Flet Visual Builder", size=24, weight=ft.FontWeight.BOLD),
                ft.Text(f"Project: {state.project.name}"),
                ft.Text("MVP foundation is ready."),
            ]
        )
    )


def run() -> None:
    ft.app(target=main)
