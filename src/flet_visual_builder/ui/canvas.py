"""Design canvas: real rendered controls with selectable/drop-target frames."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import DEVICE_LABELS, Refresh
from flet_visual_builder.contracts import Severity
from flet_visual_builder.ui.node_frame import NodeFrame, _update
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import LG, T, empty_state, faint


class Canvas(BasePanel):
    interests = frozenset(
        {Refresh.PROJECT, Refresh.DOCUMENT, Refresh.SELECTION, Refresh.LAYOUT}
    )

    def __init__(self, workspace):
        self.frames: dict[str, NodeFrame] = {}
        self._selection = None
        self._drop_frame: NodeFrame | None = None
        super().__init__(workspace)

    def refresh(self, reason: str) -> None:
        if reason == Refresh.SELECTION:
            selected = self.ws.editor.selection
            self.update_frame_borders(self._selection, selected)
            self._selection = selected
            return
        super().refresh(reason)

    def update_frame_borders(self, *node_ids):
        for node_id in set(node_ids):
            frame = self.frames.get(node_id)
            if frame is not None:
                frame.paint_border()
                _update(frame.box)

    def show_drop(self, frame: NodeFrame, zone: str | None):
        if self._drop_frame is not None and self._drop_frame is not frame:
            self._drop_frame.show_indicator(None)
        if zone is None:
            frame.show_indicator(None)
            if self._drop_frame is frame:
                self._drop_frame = None
        else:
            frame.show_indicator(zone)
            self._drop_frame = frame

    @staticmethod
    def _diagnostic(diagnostics, fallback):
        first = next((d for d in diagnostics if d.severity == Severity.ERROR), None)
        return f"{first.code}: {first.message}" if first else fallback

    def build(self) -> ft.Control:
        self.frames = {}
        self._drop_frame = None
        self._selection = self.ws.editor.selection
        ws = self.ws
        plan = ws.plan()
        if plan is None:
            return empty_state(
                ft.Icons.ERROR_OUTLINE,
                "This document cannot be rendered",
                self._diagnostic(ws.diagnostics(), "The document is empty or invalid."),
            )
        if not plan.root_ids:
            return empty_state(
                ft.Icons.ERROR_OUTLINE,
                "No root control",
                self._diagnostic(ws.diagnostics(), "Add a root control to begin."),
            )
        rendered = ws.renderer.render_plan(plan)
        if rendered.root is None:
            return empty_state(
                ft.Icons.ERROR_OUTLINE,
                "Preview unavailable",
                self._diagnostic(
                    rendered.diagnostics, "The document could not be rendered."
                ),
            )

        def frame_node(node_id: str) -> ft.Control:
            node = plan.nodes[node_id]
            child = rendered.by_node[node_id]
            for slot, ids in node.slots.items():
                children = [frame_node(child_id) for child_id in ids]
                if slot == "controls":
                    child.controls = children
                elif children:
                    setattr(
                        child, slot, children[0] if len(children) == 1 else children
                    )
            is_root = node_id in plan.root_ids
            empty_root = is_root and not any(node.slots.values())
            frame = NodeFrame(self, node_id, child, root=is_root, empty_root=empty_root)
            self.frames[node_id] = frame
            return frame.control

        # The renderer's Pagelet preserves PageSpec styling and wraps the roots in
        # a Column. Replace just that column's children, preserving the projection.
        rendered.root.content.content.controls = [
            frame_node(nid) for nid in plan.root_ids
        ]
        width = ws.device_width()
        device = ft.Container(
            content=rendered.root,
            width=width,
            expand=width is None,
            bgcolor=T.panel,
            border_radius=10,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            shadow=ft.BoxShadow(
                blur_radius=24, spread_radius=0, color=T.shadow, offset=ft.Offset(0, 6)
            ),
        )
        return ft.Column(
            controls=[
                ft.Row(
                    controls=[
                        faint("Design", size=11),
                        ft.Container(expand=True),
                        faint(DEVICE_LABELS.get(ws.device, "Fill"), size=11),
                    ]
                ),
                ft.Container(
                    content=device,
                    alignment=ft.Alignment.TOP_CENTER,
                    expand=True,
                    bgcolor=T.canvas_bg,
                    padding=LG,
                    on_click=lambda e: ws.select(None),
                ),
            ],
            spacing=0,
            expand=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
