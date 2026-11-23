"""Structural outline with persistent expansion and node actions."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.palette import ICONS
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, MD, R_MD, T, label, pill, text


class Outline(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.DOCUMENT, Refresh.SELECTION})

    def __init__(self, workspace):
        self._expanded: set[str] = set(workspace.project.root_ids)
        self._last_selection = object()
        super().__init__(workspace)

    def refresh(self, reason: str) -> None:
        if reason == Refresh.PROJECT:
            self._expanded = set(self.ws.project.root_ids)
            self._last_selection = object()
        super().refresh(reason)

    def build(self) -> ft.Control:
        selected = self.ws.editor.selection
        if selected != self._last_selection:
            self._last_selection = selected
            seen = set()
            cursor = selected
            while cursor is not None and cursor not in seen:
                seen.add(cursor)
                parent = self.ws.parent_of(cursor)
                if parent is None:
                    break
                self._expanded.add(parent[0])
                cursor = parent[0]
        rows: list[ft.Control] = []
        for root_id in self.ws.project.root_ids:
            root = self.ws.node(root_id)
            if root is not None:
                self._walk(root, 0, rows, set())
        if not rows:
            rows.append(
                ft.Container(
                    content=text("No document structure", color=T.text_muted),
                    padding=MD,
                )
            )
        self.rows = ft.ListView(controls=rows, spacing=0, expand=True)
        return ft.Column(
            controls=[
                ft.Container(
                    content=label("Outline"),
                    padding=ft.Padding(left=MD, top=10, right=MD, bottom=4),
                ),
                self.rows,
            ],
            spacing=0,
            expand=True,
        )

    def _walk(
        self, node, depth: int, rows: list[ft.Control], ancestors: set[str]
    ) -> None:
        if node.id in ancestors:
            return
        children = self.ws.children(node.id)
        selected = node.id == self.ws.editor.selection
        if children:
            arrow = ft.Container(
                content=ft.Icon(
                    (
                        ft.Icons.KEYBOARD_ARROW_DOWN
                        if node.id in self._expanded
                        else ft.Icons.KEYBOARD_ARROW_RIGHT
                    ),
                    size=16,
                    color=T.text_muted,
                ),
                on_click=lambda e, n=node.id: self._toggle(n),
                tooltip="Collapse" if node.id in self._expanded else "Expand",
            )
        else:
            arrow = ft.Container(width=16)
        badges = [
            pill(slot, color=T.text_muted, bgcolor=T.border_soft)
            for slot in self.ws.spec(node.type_id).slots
        ]
        root = node.id in self.ws.project.root_ids
        menu = ft.PopupMenuButton(
            icon=ft.Icons.MORE_VERT,
            icon_size=15,
            padding=0,
            tooltip=f"Actions for {node.type_id}",
            items=[
                ft.PopupMenuItem(
                    content="Duplicate",
                    disabled=root,
                    on_click=lambda e, n=node.id: self.ws.duplicate(n),
                ),
                *[
                    ft.PopupMenuItem(
                        content=f"Wrap in {wrapper}",
                        on_click=lambda e, n=node.id, w=wrapper: self.ws.wrap(n, w),
                    )
                    for wrapper in ("Container", "Row", "Column", "Card")
                ],
                ft.PopupMenuItem(
                    content="Delete",
                    disabled=root,
                    on_click=lambda e, n=node.id: self.ws.delete(n),
                ),
            ],
        )
        rows.append(
            ft.Container(
                data=node.id,
                content=ft.Row(
                    controls=[
                        ft.Container(width=depth * 12),
                        arrow,
                        ft.Icon(
                            ICONS.get(node.type_id, ft.Icons.WIDGETS),
                            size=14,
                            color=T.accent if selected else T.text_muted,
                        ),
                        text(
                            node.type_id,
                            size=F_BODY,
                            color=T.accent if selected else T.text,
                            expand=True,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                        *badges,
                        menu,
                    ],
                    spacing=4,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                bgcolor=T.accent_soft if selected else None,
                border_radius=R_MD,
                padding=ft.Padding(left=8, top=2, right=4, bottom=2),
                on_click=lambda e, n=node.id: self.ws.select(n),
            )
        )
        if node.id in self._expanded:
            for child in children:
                self._walk(child, depth + 1, rows, ancestors | {node.id})

    def _toggle(self, node_id: str) -> None:
        self._expanded.symmetric_difference_update({node_id})
        self.rebuild()
        try:
            self.control.update()
        except RuntimeError:
            pass
