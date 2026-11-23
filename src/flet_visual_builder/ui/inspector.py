"""Inspector: typed property editors for the selection or the page."""

from __future__ import annotations

from typing import Any

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.catalogue import CODECS
from flet_visual_builder.contracts import PropertySpec
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import (
    F_BODY,
    F_LABEL,
    MD,
    R_MD,
    SM,
    T,
    empty_state,
    faint,
    label,
    section,
    text,
)

SHARED = ("width", "height", "expand", "disabled", "visible")


class Inspector(BasePanel):
    interests = frozenset({Refresh.SELECTION, Refresh.PROJECT, Refresh.DOCUMENT})

    def build(self) -> ft.Control:
        node = self.ws.selected_node()
        if node is None:
            return empty_state(
                ft.Icons.TUNE,
                "Nothing selected",
                "Select a widget on the canvas or in the outline.",
            )
        spec = self.ws.spec(node.type_id)
        props = [
            (name, prop)
            for name, prop in spec.properties.items()
            if name not in SHARED
        ]
        return ft.Column(
            controls=[
                ft.Container(
                    content=ft.Column(
                        controls=[
                            ft.Row(
                                controls=[
                                    text(node.type_id, size=F_LABEL, weight=ft.FontWeight.W_600),
                                    ft.Container(expand=True),
                                    faint(node.id, size=10),
                                ],
                            ),
                            faint(f"{len(node.slots)} slots · {len(node.events)} events"),
                        ],
                        spacing=2,
                        tight=True,
                    ),
                    padding=ft.Padding(left=MD, top=MD, right=MD, bottom=SM),
                    border=ft.Border(bottom=ft.BorderSide(width=1, color=T.border_soft)),
                ),
                ft.Column(
                    controls=[
                        self._field(node, name, prop) for name, prop in props
                    ],
                    spacing=SM,
                    scroll=ft.ScrollMode.AUTO,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _field(self, node, name: str, prop: PropertySpec) -> ft.Control:
        value = node.props.get(name)
        codec = prop.codec_id
        if codec == "boolean":
            control = ft.Switch(value=bool(value), on_change=lambda e, n=name: self.ws.set_property(node.id, n, e.control.value))
        elif codec in ("nonneg_number", "unit_interval"):
            control = ft.TextField(
                value="" if value is None else str(value),
                dense=True,
                text_size=F_BODY,
                on_submit=lambda e, n=name: self._commit_number(node.id, n, e.control.value),
                on_blur=lambda e, n=name: self._commit_number(node.id, n, e.control.value),
            )
        elif codec.startswith("enum."):
            members = sorted(getattr(CODECS[codec], "members", frozenset()))
            control = ft.Dropdown(
                value=value,
                dense=True,
                text_size=F_BODY,
                options=[ft.DropdownOption(key=m, text=m) for m in members],
                on_select=lambda e, n=name: self.ws.set_property(node.id, n, e.control.value),
            )
        else:
            control = ft.TextField(
                value="" if value is None else str(value),
                dense=True,
                text_size=F_BODY,
                on_submit=lambda e, n=name: self.ws.set_property(node.id, n, e.control.value),
                on_blur=lambda e, n=name: self.ws.set_property(node.id, n, e.control.value),
            )
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        text(name, size=11, color=T.text_muted),
                        ft.Container(expand=True),
                        faint(codec, size=9),
                    ],
                ),
                control,
            ],
            spacing=2,
            tight=True,
        )

    def _commit_number(self, node_id: str, name: str, raw: str) -> None:
        raw = raw.strip()
        if not raw:
            self.ws.unset_property(node_id, name)
            return
        try:
            self.ws.set_property(node_id, name, float(raw))
        except ValueError:
            self.ws.toast(f"{name} expects a number", "error")
