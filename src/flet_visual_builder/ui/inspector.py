"""Selection and page property inspector, with focus-safe document refreshes."""

from __future__ import annotations

import flet as ft

from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.editors import create_editor
from flet_visual_builder.ui.panel import BasePanel
from flet_visual_builder.ui.theme import (
    F_LABEL,
    MD,
    SM,
    T,
    faint,
    icon_button,
    section,
    text,
)

_LAYOUT = frozenset(
    {
        "width",
        "height",
        "expand",
        "padding",
        "margin",
        "alignment",
        "horizontal_alignment",
        "vertical_alignment",
        "spacing",
        "tight",
        "wrap",
        "scroll",
        "horizontal",
        "auto_scroll",
    }
)
_STYLE = frozenset(
    {
        "size",
        "weight",
        "color",
        "bgcolor",
        "icon_color",
        "icon_size",
        "text_align",
        "border",
        "border_radius",
        "elevation",
        "thickness",
        "theme",
        "theme_mode",
    }
)


CODEC_LABELS = {
    "string": "Text",
    "boolean": "Toggle",
    "nonneg_number": "Number",
    "unit_interval": "0 to 1",
    "expand": "Flex",
    "color": "Color",
    "icon": "Icon",
    "image_source": "Image",
    "padding": "Padding",
    "margin": "Margin",
    "border": "Border",
    "radius": "Radius",
    "input_border": "Input border",
    "appbar": "App bar",
    "theme": "Theme",
}


ENUM_LABELS = {
    "MainAxisAlignment": "Alignment",
    "CrossAxisAlignment": "Cross align",
    "FontWeight": "Weight",
    "ScrollMode": "Scroll",
    "TextAlign": "Text align",
    "ThemeMode": "Theme mode",
    "BoxFit": "Fit",
    "Alignment": "Alignment",
}


def codec_label(codec_id: str) -> str:
    """Human wording for a codec id; enum families read as their own name."""
    if codec_id.startswith("enum."):
        family = codec_id.split(".", 1)[1]
        return ENUM_LABELS.get(family, family.replace("_", " "))
    return CODEC_LABELS.get(codec_id, codec_id.replace("_", " ").title())


def _group(name):
    if name in _LAYOUT:
        return "Layout"
    if name in _STYLE:
        return "Style"
    return "Content"


class Inspector(BasePanel):
    interests = frozenset({Refresh.SELECTION, Refresh.PROJECT})

    def refresh(self, reason):
        if reason == Refresh.DOCUMENT:
            self._refresh_labels()
            return
        super().refresh(reason)

    def _refresh_labels(self):
        # Mutate only derived labels: never replace the input under the cursor.
        props = (
            self.ws.project.page
            if self._node_id is None
            else (
                self.ws.node(self._node_id).props if self.ws.node(self._node_id) else {}
            )
        )
        diagnostics = self.ws.diagnostics()
        for name, (status, reset, error) in self._rows.items():
            is_set = name in props
            status.value = "Set" if is_set else "Default"
            reset.disabled = not is_set
            prefix = ("page", name) if self._node_id is None else ("props", name)
            matches = [
                d.message
                for d in diagnostics
                if d.node_id == self._node_id
                and (
                    tuple(d.path[:2]) == prefix
                    or (
                        self._node_id is not None
                        and tuple(d.path[:4]) == ("nodes", self._node_id, "props", name)
                    )
                )
            ]
            error.value = " · ".join(matches)
            error.visible = bool(matches)
        if self._node_id is not None:
            node = self.ws.node(self._node_id)
            for name, label in self._event_labels.items():
                symbol = node.events.get(name) if node else None
                action = node.actions.get(name) if node else None
                label.value = (
                    f"Navigation: {action.route}"
                    if action
                    else (symbol.name if symbol else "Not bound")
                )
                switch, dropdown = self._event_controls[name]
                switch.value = bool(symbol) and not bool(action)
                dropdown.options = [ft.DropdownOption(key="", text="None")] + [
                    ft.DropdownOption(key=route, text=route)
                    for route in self.ws.routes()
                ]
                dropdown.value = action.route if action else ""

    def build(self) -> ft.Control:
        node = self.ws.selected_node()
        self._node_id = node.id if node else None
        self._rows = {}
        self._event_labels = {}
        self._event_controls = {}
        if node:
            specs = self.ws.spec(node.type_id).properties
            props = node.props
            parent = self.ws.parent_of(node.id)
            subtitle = f"ID: {node.id} · Parent: {parent[0] if parent else 'Page'}"
            header = ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            text(
                                node.type_id,
                                size=F_LABEL,
                                weight=ft.FontWeight.W_600,
                                expand=True,
                            ),
                            ft.TextButton(
                                content="Page settings",
                                on_click=lambda e: self.ws.select(None),
                            ),
                        ]
                    ),
                    faint(subtitle),
                ],
                tight=True,
                spacing=2,
            )
        else:
            specs, props = self.ws.catalogue.page_properties, self.ws.project.page
            header = ft.Column(
                controls=[
                    text("Page", size=F_LABEL, weight=ft.FontWeight.W_600),
                    faint("Page settings"),
                ],
                tight=True,
                spacing=2,
            )
        groups = {name: [] for name in ("Content", "Layout", "Style")}
        for name, spec in specs.items():
            groups[_group(name)].append(self._property_row(name, spec, props))
        sections = [
            section(name, ft.Column(controls=rows, spacing=SM, tight=True))
            for name, rows in groups.items()
            if rows
        ]
        if node:
            events = []
            for event_name in sorted(self.ws.spec(node.type_id).events):
                symbol = node.events.get(event_name)
                action = node.actions.get(event_name)
                symbol_label = faint(
                    f"Navigation: {action.route}"
                    if action
                    else (symbol.name if symbol else "Not bound")
                )
                self._event_labels[event_name] = symbol_label

                def toggle(e, event_name=event_name, node_id=node.id):
                    enabled = e.control.value
                    result = self.ws.set_event(node_id, event_name, enabled)
                    current = self.ws.node(node_id)
                    if (
                        result.status.value != "rejected"
                        and enabled
                        and current.actions.get(event_name)
                    ):
                        self.ws.set_action(node_id, event_name, None)
                    self._refresh_labels()

                def navigate(e, event_name=event_name, node_id=node.id):
                    route = e.control.value or None
                    result = self.ws.set_action(node_id, event_name, route)
                    current = self.ws.node(node_id)
                    if (
                        result.status.value != "rejected"
                        and route
                        and current.events.get(event_name)
                    ):
                        self.ws.set_event(node_id, event_name, False)
                    self._refresh_labels()

                switch = ft.Switch(
                    label=event_name,
                    value=bool(symbol) and not bool(action),
                    data=("event", event_name),
                    on_change=toggle,
                )
                dropdown = ft.Dropdown(
                    label="Navigation",
                    value=action.route if action else "",
                    data=("navigation", event_name),
                    on_select=navigate,
                    dense=True,
                )
                self._event_controls[event_name] = (switch, dropdown)
                events.append(
                    ft.Column(
                        controls=[switch, dropdown, symbol_label],
                        tight=True,
                        spacing=SM,
                    )
                )
            sections.append(
                section(
                    "Events",
                    ft.Column(
                        controls=events or [faint("No events")], spacing=SM, tight=True
                    ),
                )
            )
        self._refresh_labels()
        spaced: list[ft.Control] = []
        for index, block in enumerate(sections):
            if index:
                spaced.append(ft.Container(height=1, bgcolor=T.border_soft))
            spaced.append(block)
        return ft.Column(
            controls=[
                ft.Container(
                    content=header,
                    padding=ft.Padding(left=MD, top=10, right=MD, bottom=10),
                    bgcolor=T.panel_alt,
                    border=ft.Border(
                        bottom=ft.BorderSide(width=1, color=T.border_soft)
                    ),
                ),
                ft.Container(
                    content=ft.Column(
                        controls=spaced,
                        spacing=MD,
                        scroll=ft.ScrollMode.AUTO,
                        expand=True,
                    ),
                    padding=MD,
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )

    def _property_row(self, name, spec, props):
        status = ft.Container(
            width=5,
            height=5,
            border_radius=3,
            bgcolor=T.accent if name in props else T.border_strong,
            tooltip="Customised" if name in props else "Using the default",
        )
        error = text("", size=11, color=T.danger, visible=False)
        host = ft.Container()

        def changed():
            self._refresh_labels()

        editor = create_editor(self.ws, self._node_id, spec, props.get(name), changed)
        host.content = editor.control

        def reset(e):
            result = self.ws.unset_property(self._node_id, name)
            if result.status.value != "rejected":
                # Reset is an explicit action: replace just this editor, not the panel.
                host.content = create_editor(
                    self.ws, self._node_id, spec, None, changed
                ).control
                self._refresh_labels()

        reset_button = icon_button(
            ft.Icons.RESTART_ALT, f"Reset {name}", reset, disabled=name not in props
        )
        reset_button.data = ("reset", name)
        self._rows[name] = (status, reset_button, error)
        return ft.Column(
            data=("property", name),
            controls=[
                ft.Row(
                    controls=[
                        text(name, size=11, color=T.text_muted, expand=True),
                        faint(codec_label(spec.codec_id), size=10),
                        status,
                        reset_button,
                    ],
                    spacing=2,
                ),
                host,
                error,
            ],
            spacing=2,
            tight=True,
        )
