"""Compact screen switcher and screen-management commands."""

from __future__ import annotations

from dataclasses import replace

import flet as ft

from flet_visual_builder.ui.dialogs import delete_screen_dialog, screen_dialog
from flet_visual_builder.ui.theme import MD, R_MD, SM, T, XS, faint, icon_button, text


class ScreenStrip:
    def __init__(self, workspace):
        self.ws = workspace
        self.control = ft.Container()
        self.refresh()

    def refresh(self):
        entries = self.ws.screen_entries()
        active = self.ws.active_screen()
        tabs = []
        for screen_id, meta in entries:
            menu = ft.PopupMenuButton(
                icon=ft.Icons.MORE_VERT,
                icon_size=18,
                icon_color=T.text_muted,
                tooltip=f"Screen options for {meta.title}",
                padding=XS,
                items=[
                    ft.PopupMenuItem(
                        content="Rename",
                        on_click=lambda e, sid=screen_id: self._edit(sid),
                    ),
                    ft.PopupMenuItem(
                        content="Set as initial",
                        disabled=meta.route == self.ws.project.initial_route,
                        on_click=lambda e, sid=screen_id: self._set_initial(sid),
                    ),
                    ft.PopupMenuItem(
                        content="Delete",
                        disabled=len(entries) <= 1,
                        on_click=lambda e, sid=screen_id: self._delete(sid),
                    ),
                ],
            )
            tabs.append(
                ft.Row(
                    controls=[
                        ft.Container(
                            content=text(
                                meta.title,
                                size=12,
                                weight=(
                                    ft.FontWeight.W_600 if screen_id == active else None
                                ),
                                tooltip=f"{meta.title} · {meta.route}",
                            ),
                            padding=SM,
                            border_radius=R_MD,
                            bgcolor=T.accent_soft if screen_id == active else T.panel,
                            border=ft.Border.all(
                                1, T.accent_border if screen_id == active else T.border
                            ),
                            data=("screen", screen_id, screen_id == active),
                            on_click=lambda e, sid=screen_id: self.ws.select_screen(
                                sid
                            ),
                        ),
                        menu,
                    ],
                    spacing=0,
                    tight=True,
                )
            )
        add = icon_button(ft.Icons.ADD, "Add screen", lambda e: self._add())
        self.control.content = ft.Row(
            controls=[*tabs, add],
            spacing=SM,
            scroll=ft.ScrollMode.AUTO,
        )
        self.control.padding = ft.Padding(left=MD, top=6, right=MD, bottom=6)
        self.control.bgcolor = T.panel
        try:
            self.control.update()
        except RuntimeError:
            pass

    def _close(self):
        self.ws.page.pop_dialog()

    def _add(self):
        routes = self.ws.routes()
        index = len(routes) + 1
        while f"/screen-{index}" in routes:
            index += 1

        def save(title, route, initial):
            result = self.ws.add_screen(title, route)
            if initial and result.status.value == "committed":
                self.ws.update_screen(
                    self.ws.active_screen(), title=title, route=route, initial=True
                )
            return result

        self.ws.page.show_dialog(
            screen_dialog(
                title=f"Screen {index}",
                route=f"/screen-{index}",
                initial=False,
                on_save=save,
                on_close=self._close,
                existing_routes=tuple(routes),
                editing=False,
            )
        )

    def _edit(self, screen_id):
        meta = self.ws.screen_meta(screen_id)
        if meta is None:
            return
        self.ws.page.show_dialog(
            screen_dialog(
                title=meta.title,
                route=meta.route,
                initial=meta.route == self.ws.project.initial_route,
                on_save=lambda title, route, initial: self.ws.update_screen(
                    screen_id, title=title, route=route, initial=initial
                ),
                on_close=self._close,
                existing_routes=tuple(
                    route for route, sid in self.ws.routes().items() if sid != screen_id
                ),
            )
        )

    def _set_initial(self, screen_id):
        meta = self.ws.screen_meta(screen_id)
        if meta is not None:
            self.ws.update_screen(
                screen_id, title=meta.title, route=meta.route, initial=True
            )

    def _delete(self, screen_id):
        meta = self.ws.screen_meta(screen_id)
        if meta is not None and len(self.ws.screen_entries()) > 1:
            self.ws.page.show_dialog(
                delete_screen_dialog(
                    meta.title,
                    lambda: self.ws.delete_screen(screen_id),
                    self._close,
                )
            )


def active_screen_plan(plan, screen_id):
    """Project just the active tree: the renderer otherwise visits all nodes."""
    roots = tuple(root for root in plan.root_ids if root == screen_id)
    seen = set()
    pending = list(roots)
    while pending:
        node_id = pending.pop()
        if node_id in seen or node_id not in plan.nodes:
            continue
        seen.add(node_id)
        pending.extend(
            child for ids in plan.nodes[node_id].slots.values() for child in ids
        )
    return replace(
        plan,
        root_ids=roots,
        nodes={nid: node for nid, node in plan.nodes.items() if nid in seen},
    )
