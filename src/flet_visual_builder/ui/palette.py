"""Widget palette: grouped, searchable, and insertable."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.catalogue.widgets import WIDGET_ORDER
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import (
    F_BODY,
    F_SMALL,
    MD,
    R_MD,
    SM,
    T,
    empty_state,
    label,
    text,
)

CATEGORIES: dict[str, tuple[str, ...]] = {
    "Layout": ("Column", "Row", "Container", "Card", "ListView"),
    "Text": ("Text", "TextButton"),
    "Input": ("TextField", "Checkbox", "Switch"),
    "Media": ("Image", "Icon"),
    "Feedback": ("ProgressBar", "Divider"),
    "Actions": ("Button", "IconButton"),
}

ICONS: dict[str, str] = {
    "Column": ft.Icons.VIEW_AGENDA,
    "Row": ft.Icons.VIEW_WEEK,
    "Container": ft.Icons.CROP_SQUARE,
    "Card": ft.Icons.RECTANGLE,
    "ListView": ft.Icons.LIST_ALT,
    "Text": ft.Icons.TITLE,
    "TextButton": ft.Icons.LINK,
    "TextField": ft.Icons.INPUT,
    "Checkbox": ft.Icons.CHECK_BOX_OUTLINED,
    "Switch": ft.Icons.TOGGLE_ON_OUTLINED,
    "Image": ft.Icons.IMAGE_OUTLINED,
    "Icon": ft.Icons.EMOJI_SYMBOLS,
    "ProgressBar": ft.Icons.LINEAR_SCALE,
    "Divider": ft.Icons.HORIZONTAL_RULE,
    "Button": ft.Icons.SMART_BUTTON,
    "IconButton": ft.Icons.TOUCH_APP,
}


class Palette(BasePanel):
    interests = frozenset({Refresh.PROJECT, Refresh.SELECTION, Refresh.DOCUMENT})

    def build(self) -> ft.Control:
        self._query = getattr(self, "_query", "")
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Row(
                        controls=[
                            label("Widgets"),
                            ft.Container(expand=True),
                            ft.Icon(ft.Icons.SEARCH, size=13, color=T.text_faint),
                        ],
                        spacing=4,
                    ),
                    padding=ft.Padding(left=MD, top=10, right=MD, bottom=4),
                ),
                self._list(),
            ],
            spacing=0,
            expand=True,
        )

    def _list(self) -> ft.Control:
        rows: list[ft.Control] = []
        known = set(WIDGET_ORDER)
        for category, members in CATEGORIES.items():
            present = [member for member in members if member in known]
            if not present:
                continue
            rows.append(
                ft.Container(
                    content=label(category),
                    padding=ft.Padding(left=MD, top=10, right=MD, bottom=2),
                )
            )
            for type_id in present:
                rows.append(self._item(type_id))
        if not rows:
            return empty_state(ft.Icons.SEARCH_OFF, "No widgets", "Try another category.")
        return ft.Column(controls=rows, spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    def _item(self, type_id: str) -> ft.Control:
        return ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(ICONS.get(type_id, ft.Icons.WIDGETS), size=15, color=T.text_muted),
                    text(type_id, size=F_BODY),
                    ft.Container(expand=True),
                    ft.Icon(ft.Icons.ADD, size=13, color=T.text_faint),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=MD, top=6, right=MD, bottom=6),
            border_radius=R_MD,
            on_click=lambda e, value=type_id: self._add(value),
            tooltip=f"Add {type_id} beside the current selection",
        )

    def _add(self, type_id: str) -> None:
        anchor = self.ws.editor.selection
        if anchor is None:
            roots = self.ws.project.root_ids
            if roots:
                self.ws.insert(type_id, roots[0], "controls", 0)
            return
        self.ws.insert_relative(type_id, anchor, inside=True)
