"""Searchable, draggable widget catalogue."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.contracts import CommandStatus
from flet_visual_builder.interaction.protocol import DRAG_GROUP, encode_create
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import F_BODY, MD, R_MD, T, label, text

CATEGORIES = {
    "Layout": (
        "Column",
        "Row",
        "Container",
        "Stack",
        "GridView",
        "ResponsiveRow",
        "ListView",
        "Card",
        "SafeArea",
        "ExpansionTile",
    ),
    "Text": ("Text", "Markdown", "TextButton"),
    "Input": (
        "TextField",
        "Checkbox",
        "Switch",
        "RadioGroup",
        "Slider",
        "Dropdown",
    ),
    "Display": (
        "Icon",
        "Image",
        "CircleAvatar",
        "ProgressBar",
        "ProgressRing",
        "Divider",
        "VerticalDivider",
        "Chip",
        "ListTile",
    ),
    "Buttons": (
        "Button",
        "FilledButton",
        "OutlinedButton",
        "IconButton",
        "FloatingActionButton",
    ),
    "Navigation": ("Tabs", "TabBar", "TabBarView", "NavigationBar", "SegmentedButton"),
    "Parts": (
        "DropdownOption",
        "Segment",
        "Tab",
        "NavigationBarDestination",
        "Radio",
    ),
}

ICONS = {
    "Column": ft.Icons.VIEW_AGENDA,
    "Row": ft.Icons.VIEW_WEEK,
    "Container": ft.Icons.CROP_SQUARE,
    "Stack": ft.Icons.LAYERS,
    "GridView": ft.Icons.GRID_VIEW,
    "ResponsiveRow": ft.Icons.DASHBOARD,
    "ListView": ft.Icons.LIST_ALT,
    "Card": ft.Icons.RECTANGLE,
    "SafeArea": ft.Icons.PHONE_IPHONE,
    "ExpansionTile": ft.Icons.EXPAND_MORE,
    "Text": ft.Icons.TITLE,
    "Markdown": ft.Icons.ARTICLE,
    "TextButton": ft.Icons.LINK,
    "TextField": ft.Icons.INPUT,
    "Checkbox": ft.Icons.CHECK_BOX_OUTLINED,
    "Switch": ft.Icons.TOGGLE_ON_OUTLINED,
    "RadioGroup": ft.Icons.RADIO_BUTTON_CHECKED,
    "Radio": ft.Icons.RADIO_BUTTON_CHECKED,
    "Slider": ft.Icons.TUNE,
    "Dropdown": ft.Icons.ARROW_DROP_DOWN,
    "DropdownOption": ft.Icons.FORMAT_LIST_BULLETED,
    "Icon": ft.Icons.EMOJI_SYMBOLS,
    "Image": ft.Icons.IMAGE_OUTLINED,
    "CircleAvatar": ft.Icons.ACCOUNT_CIRCLE,
    "ProgressBar": ft.Icons.LINEAR_SCALE,
    "ProgressRing": ft.Icons.DONUT_LARGE,
    "Divider": ft.Icons.HORIZONTAL_RULE,
    "VerticalDivider": ft.Icons.MORE_VERT,
    "Chip": ft.Icons.LABEL,
    "ListTile": ft.Icons.VIEW_LIST,
    "Button": ft.Icons.SMART_BUTTON,
    "FilledButton": ft.Icons.SMART_BUTTON,
    "OutlinedButton": ft.Icons.CROP_SQUARE,
    "IconButton": ft.Icons.TOUCH_APP,
    "FloatingActionButton": ft.Icons.ADD_CIRCLE,
    "Tabs": ft.Icons.TAB,
    "Tab": ft.Icons.TAB,
    "TabBar": ft.Icons.TAB_UNSELECTED,
    "TabBarView": ft.Icons.VIEW_CAROUSEL,
    "NavigationBar": ft.Icons.NAVIGATION,
    "NavigationBarDestination": ft.Icons.PLACE,
    "SegmentedButton": ft.Icons.VIEW_MODULE,
    "Segment": ft.Icons.VIEW_MODULE,
}


class Palette(BasePanel):
    interests = frozenset({Refresh.PROJECT})

    def __init__(self, workspace):
        self._recent: list[str] = []
        super().__init__(workspace)

    def build(self) -> ft.Control:
        self.search = ft.TextField(
            hint_text="Search widgets",
            prefix_icon=ft.Icons.SEARCH,
            dense=True,
            text_size=F_BODY,
            border=ft.OutlineInputBorder(),
            on_change=self._search,
            on_focus=lambda e: self.ws.set_text_focus(True),
            on_blur=lambda e: self.ws.set_text_focus(False),
        )
        self.items = ft.ListView(expand=True, spacing=0)
        self._populate()
        return ft.Column(
            controls=[
                ft.Container(
                    content=label("Widgets"),
                    padding=ft.Padding(left=MD, top=10, right=MD, bottom=4),
                ),
                ft.Container(
                    content=self.search,
                    padding=ft.Padding(left=MD, top=4, right=MD, bottom=4),
                ),
                self.items,
            ],
            spacing=0,
            expand=True,
        )

    def refresh(self, reason: str) -> None:
        # Do not replace the focused search control on *any* workspace refresh.
        if reason in (Refresh.PROJECT, Refresh.ALL):
            self._populate()
            self._update_items()

    def _hover_row(self, event) -> None:
        entered = event.data is True or str(event.data).lower() == "true"
        event.control.bgcolor = T.hover_fill if entered else None
        try:
            event.control.update()
        except RuntimeError:
            pass

    def _search(self, event) -> None:
        self._populate()
        self._update_items()

    def _update_items(self) -> None:
        try:
            self.items.update()
        except RuntimeError:
            pass

    def _populate(self) -> None:
        query = (self.search.value or "").strip().casefold()
        available = self.ws.catalogue.widgets
        matches = [name for name in available if query in name.casefold()]
        rows: list[ft.Control] = []

        def section(title: str, members: list[str]) -> None:
            if members:
                rows.append(
                    ft.Container(
                        content=label(title),
                        padding=ft.Padding(left=MD, top=10, right=MD, bottom=2),
                    )
                )
                rows.extend(self._item(name) for name in members)

        section("Recently used", [name for name in self._recent if name in matches])
        classified = {name for members in CATEGORIES.values() for name in members}
        for category, members in CATEGORIES.items():
            section(category, [name for name in members if name in matches])
        section("Other", sorted(name for name in matches if name not in classified))
        if not matches:
            rows.append(
                ft.Container(
                    content=text(
                        "No widgets match your search", size=F_BODY, color=T.text_muted
                    ),
                    padding=MD,
                )
            )
        self.items.controls = rows

    def _item(self, type_id: str) -> ft.Draggable:
        row = ft.Container(
            content=ft.Row(
                controls=[
                    ft.Icon(
                        ICONS.get(type_id, ft.Icons.WIDGETS),
                        size=15,
                        color=T.text_muted,
                    ),
                    text(
                        type_id,
                        size=F_BODY,
                        expand=True,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=ft.Padding(left=MD, top=5, right=MD, bottom=5),
            border_radius=R_MD,
            on_click=lambda e, name=type_id: self._add(name),
            on_hover=lambda e, control=None: self._hover_row(e),
            tooltip=f"Add {type_id} beside the current selection, or drag to the canvas",
        )
        return ft.Draggable(
            content=row,
            group=DRAG_GROUP,
            data=encode_create(type_id),
            on_drag_complete=lambda e, name=type_id: self._remember(name),
        )

    def _remember(self, type_id: str) -> None:
        self._recent = [type_id] + [name for name in self._recent if name != type_id]
        self._recent = self._recent[:6]
        self._populate()
        self._update_items()

    def _add(self, type_id: str) -> None:
        anchor = self.ws.editor.selection or next(iter(self.ws.project.root_ids), None)
        if anchor is None:
            self.ws.toast("Select a destination before adding a widget", "warning")
            return
        result = self.ws.insert_relative(type_id, anchor, inside=False, after=True)
        if result.status is CommandStatus.COMMITTED:
            self._remember(type_id)
