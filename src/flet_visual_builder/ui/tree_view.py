"""Outline tree mirroring the document structure."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.contracts import Node
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, F_SMALL, MD, R_MD, T, label, text

TYPE_ICONS: dict[str, str] = {
    "Column": ft.Icons.VIEW_AGENDA,
    "Row": ft.Icons.VIEW_WEEK,
    "Container": ft.Icons.CROP_SQUARE,
    "Card": ft.Icons.RECTANGLE,
    "ListView": ft.Icons.LIST_ALT,
    "Text": ft.Icons.TITLE,
    "Button": ft.Icons.SMART_BUTTON,
}


class Outline(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.DOCUMENT, Refresh.SELECTION})

    def build(self) -> ft.Control:
        self._expanded = getattr(self, "_expanded", set())
        rows: list[ft.Control] = []
        for root_id in self.ws.project.root_ids:
            root = self.ws.node(root_id)
            if root is not None:
                self._walk(root, 0, rows)
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            label("Outline"),
                            ft.Container(expand=True),
                            ft.Icon(ft.Icons.ACCOUNT_TREE, size=13, color=T.text_faint),
                        ],
                    ),
                    padding=ft.Padding(left=MD, top=10, right=MD, bottom=4),
                ),
                ft.Column(controls=rows, spacing=0, scroll=ft.ScrollMode.AUTO, expand=True),
            ],
            spacing=0,
            expand=True,
        )

    def _walk(self, node: Node, depth: int, rows: list[ft.Control]) -> None:
        selected = node.id == self.ws.editor.selection
        children = self.ws.children(node.id)
        chevron = (
            ft.Icon(
                ft.Icons.KEYBOARD_ARROW_DOWN if node.id in self._expanded else ft.Icons.KEYBOARD_ARROW_RIGHT,
                size=12,
                color=T.text_faint,
            )
            if children
            else ft.Container(width=12)
        )
        rows.append(
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.Container(width=depth * 12),
                        ft.Container(content=chevron, on_click=lambda e, n=node.id: self._toggle(n)) if children else chevron,
                        ft.Icon(TYPE_ICONS.get(node.type_id, ft.Icons.WIDGETS), size=13,
                                color=T.accent if selected else T.text_muted),
                        text(node.type_id, size=F_BODY, color=T.accent if selected else T.text),
                    ],
                    spacing=5,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=T.accent_soft if selected else None,
                padding=ft.Padding(left=8, top=4, right=MD, bottom=4),
                border_radius=R_MD,
                on_click=lambda e, n=node.id: self.ws.select(n),
            )
        )
        if children and node.id in self._expanded:
            for child in children:
                self._walk(child, depth + 1, rows)

    def _toggle(self, node_id: str) -> None:
        self._expanded ^= {node_id}
        self.rebuild()
        self.control.update()
