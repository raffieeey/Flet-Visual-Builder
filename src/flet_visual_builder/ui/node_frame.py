"""Selectable design-time frame and drag target for one rendered node."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.contracts import Point, Size
from flet_visual_builder.interaction import (
    DRAG_GROUP,
    decode_drag,
    encode_move,
    resolve_drop,
)
from flet_visual_builder.ui.theme import T


def _update(control: ft.Control) -> None:
    try:
        control.update()
    except RuntimeError:
        pass  # Headless or not mounted yet.


def _payload(event):
    # Flet resolves src_id to the Draggable; event.data is event metadata,
    # not normally the source payload. The fallback also supports synthetic events.
    src = getattr(event, "src", None)
    return decode_drag(getattr(src, "data", None)) or decode_drag(
        getattr(event, "data", None)
    )


class NodeFrame:
    def __init__(
        self, canvas, node_id: str, child: ft.Control, *, root: bool, empty_root: bool
    ):
        self.canvas = canvas
        self.ws = canvas.ws
        self.node_id = node_id
        self.root = root
        self.size: Size | None = None
        self.indicator = ft.Container(visible=False, ignore_interactions=True)
        # Suppress preview interactions on leaves so buttons and text fields do
        # not steal selection clicks. Containers with framed descendants must
        # remain interactive, otherwise their nested targets cannot receive drops.
        node = self.ws.project.nodes[node_id]
        visual = (
            child
            if any(node.slots.values())
            else ft.Container(content=child, padding=0, ignore_interactions=True)
        )
        self.box = ft.Container(
            content=ft.Stack(
                controls=[visual, self.indicator],
                # Pass the parent's constraints straight to the rendered control;
                # LOOSE would shrink-wrap every node in a stretching parent.
                fit=ft.StackFit.PASS_THROUGH,
            ),
            padding=0,
            border=ft.Border.all(2, ft.Colors.TRANSPARENT),
            on_click=lambda e: self.ws.select(node_id),
            on_hover=self._hover,
            on_size_change=self._measure,
            height=120 if empty_root else None,
            width=300 if empty_root else None,
            expand=getattr(child, "expand", None),
        )
        self.paint_border()
        draggable = ft.Draggable(
            content=self.box,
            group=DRAG_GROUP,
            data=encode_move(node_id),
            expand=getattr(child, "expand", None),
        )
        self.target = ft.DragTarget(
            content=draggable,
            group=DRAG_GROUP,
            on_will_accept=self._will_accept,
            on_move=self._move,
            on_accept=self._accept,
            on_leave=self._leave,
            expand=getattr(child, "expand", None),
        )
        self.control = self.target

    def paint_border(self):
        color = (
            T.selection
            if self.ws.editor.selection == self.node_id
            else (
                T.hover
                if self.ws.editor.hover == self.node_id
                else T.border_strong if self.root else ft.Colors.TRANSPARENT
            )
        )
        self.box.border = ft.Border.all(2, color)

    def _hover(self, e):
        entered = e.data is True or str(e.data).lower() == "true"
        previous = self.ws.editor.hover
        if entered:
            self.ws.editor.hover = self.node_id
        elif previous == self.node_id:
            self.ws.editor.hover = None
        self.canvas.update_frame_borders(previous, self.ws.editor.hover)

    def _measure(self, e):
        self.size = Size(e.width, e.height)

    def _resolve(self, event):
        payload = _payload(event)
        position = getattr(event, "local_position", None)
        if not payload or position is None or self.size is None:
            return None
        return resolve_drop(
            self.ws.project,
            self.ws.catalogue,
            self.node_id,
            Point(position.x, position.y),
            self.size,
            *payload,
        )

    def _will_accept(self, e):
        # Flet's callback is notification-only; actual acceptance is group-based.
        # Reject invalid payloads when handling movement/acceptance instead.
        if _payload(e) is None:
            self._clear()

    def _move(self, e):
        drop = self._resolve(e)
        self.canvas.show_drop(self, drop.zone if drop else None)

    def _accept(self, e):
        drop = self._resolve(e)
        payload = _payload(e)
        self.canvas.show_drop(self, None)
        if drop is None or payload is None:
            return
        kind, value = payload
        if kind == "create":
            self.ws.insert(value, drop.parent_id, drop.slot_name, drop.index)
        else:
            self.ws.move(value, drop.parent_id, drop.slot_name, drop.index)

    def _leave(self, e):
        self.canvas.show_drop(self, None)

    def _clear(self):
        self.indicator.visible = False
        _update(self.indicator)

    def show_indicator(self, zone):
        indicator = self.indicator
        indicator.visible = zone is not None
        indicator.left = 0 if zone != "inside" else 4
        indicator.right = 0 if zone != "inside" else 4
        indicator.top = 0 if zone == "before" else 4 if zone == "inside" else None
        indicator.bottom = 0 if zone == "after" else 4 if zone == "inside" else None
        indicator.height = 2 if zone in ("before", "after") else None
        indicator.bgcolor = T.drop if zone != "inside" else T.drop_soft
        indicator.opacity = 0.45 if zone == "inside" else 1
        _update(indicator)
