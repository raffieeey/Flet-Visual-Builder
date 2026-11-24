"""Small composition DSL for template documents.

Templates are ordinary :class:`Node` graphs; this helper keeps them readable and
keeps ids deterministic so a template renders identically every time it is used.
Slot names are explicit per widget because the catalogue no longer has a single
"default slot" convention (chips label, list tiles title, navigation bars
destinations).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from flet_visual_builder.contracts import (
    JsonValue,
    Navigate,
    Node,
    Project,
    ScreenMeta,
)

#: Which slot receives children for a given widget type.
DEFAULT_SLOT: dict[str, str] = {
    "Container": "content",
    "Card": "content",
    "CircleAvatar": "content",
    "SafeArea": "content",
    "Tabs": "content",
    "Stack": "controls",
    "Row": "controls",
    "Column": "controls",
    "ListView": "controls",
    "GridView": "controls",
    "ResponsiveRow": "controls",
    "TabBarView": "controls",
    "ExpansionTile": "controls",
    "NavigationBar": "destinations",
    "TabBar": "tabs",
}


class Screen:
    """Collect literal nodes while retaining deterministic, unique ids."""

    def __init__(self) -> None:
        self.nodes: dict[str, Node] = {}

    # ── primitives ────────────────────────────────────────────────────
    def add(
        self,
        type_id: str,
        node_id: str,
        props: Mapping[str, JsonValue] | None = None,
        children: Iterable[str] = (),
        *,
        slot: str | None = None,
        slots: Mapping[str, Iterable[str]] | None = None,
    ) -> str:
        if node_id in self.nodes:
            raise ValueError(f"duplicate template node: {node_id}")
        built: dict[str, tuple[str, ...]] = {}
        if slots:
            for name, ids in slots.items():
                built[name] = tuple(ids)
        child_tuple = tuple(children)
        if child_tuple:
            channel = slot or DEFAULT_SLOT.get(type_id)
            if channel is None:
                raise ValueError(f"{type_id} has no default child slot; pass slot=")
            built[channel] = child_tuple
        self.nodes[node_id] = Node(
            id=node_id,
            type_id=type_id,
            props=dict(props or {}),
            slots=built,
            events={},
        )
        return node_id

    # ── text ──────────────────────────────────────────────────────────
    def text(
        self,
        node_id: str,
        value: str,
        size: float = 14,
        color: str = "#172033",
        weight: str = "NORMAL",
        *,
        align: str | None = None,
    ) -> str:
        props: dict[str, JsonValue] = {
            "value": value,
            "size": size,
            "color": color,
            "weight": weight,
        }
        if align:
            props["text_align"] = align
        return self.add("Text", node_id, props)

    def eyebrow(self, node_id: str, value: str, color: str) -> str:
        return self.text(node_id, value.upper(), 11, color, "W_600")

    def headline(
        self, node_id: str, value: str, size: float = 30, color: str = "#0B1220"
    ) -> str:
        return self.text(node_id, value, size, color, "BOLD")

    def body(self, node_id: str, value: str, color: str = "#475569") -> str:
        return self.text(node_id, value, 14, color)

    # ── layout ────────────────────────────────────────────────────────
    def column(
        self,
        node_id: str,
        *children: str,
        spacing: float = 12,
        align: str = "STRETCH",
        main: str = "START",
    ) -> str:
        return self.add(
            "Column",
            node_id,
            {
                "spacing": spacing,
                "horizontal_alignment": align,
                "alignment": main,
            },
            children,
        )

    def row(
        self,
        node_id: str,
        *children: str,
        spacing: float = 12,
        wrap: bool = False,
        align: str = "CENTER",
    ) -> str:
        return self.add(
            "Row",
            node_id,
            {"spacing": spacing, "vertical_alignment": align, "wrap": wrap},
            children,
        )

    def stack(self, node_id: str, *children: str) -> str:
        return self.add("Stack", node_id, {}, children)

    def box(
        self,
        node_id: str,
        child: str | None,
        color: str,
        padding: float = 24,
        radius: float = 10,
    ) -> str:
        props: dict[str, JsonValue] = {
            "bgcolor": color,
            "padding": padding,
            "border_radius": radius,
        }
        return self.add("Container", node_id, props, (child,) if child else ())

    def surface(
        self,
        node_id: str,
        child: str,
        *,
        color: str = "#FFFFFF",
        padding: float = 24,
        radius: float = 14,
        border: str | None = None,
    ) -> str:
        props: dict[str, JsonValue] = {
            "bgcolor": color,
            "padding": padding,
            "border_radius": radius,
        }
        if border:
            props["border"] = {
                "top": {"width": 1, "color": border},
                "right": {"width": 1, "color": border},
                "bottom": {"width": 1, "color": border},
                "left": {"width": 1, "color": border},
            }
        return self.add("Container", node_id, props, (child,))

    def card(
        self,
        node_id: str,
        child: str,
        *,
        color: str = "#FFFFFF",
        elevation: float = 1,
    ) -> str:
        return self.add(
            "Card", node_id, {"bgcolor": color, "elevation": elevation}, (child,)
        )

    def divider(
        self, node_id: str, color: str = "#E2E8F0", thickness: float = 1
    ) -> str:
        return self.add("Divider", node_id, {"color": color, "thickness": thickness})

    # ── components ────────────────────────────────────────────────────
    def button(self, node_id: str, label: str, color: str = "#4F46E5") -> str:
        return self.add(
            "Button",
            node_id,
            {
                "content": label,
                "bgcolor": color,
                "color": "#FFFFFF",
                "elevation": 0,
            },
        )

    def filled(self, node_id: str, label: str, *, icon: str | None = None) -> str:
        props: dict[str, JsonValue] = {"content": label}
        if icon:
            props["icon"] = icon
        return self.add("FilledButton", node_id, props)

    def text_button(self, node_id: str, label: str, color: str = "#4F46E5") -> str:
        return self.add("TextButton", node_id, {"content": label, "icon_color": color})

    def chip(self, node_id: str, label: str, *, selected: bool = False) -> str:
        return self.add("Chip", node_id, {"label": label, "selected": selected})

    def avatar(
        self,
        node_id: str,
        initials: str,
        *,
        size: float = 52,
        bgcolor: str = "#E0E7FF",
        color: str = "#4338CA",
    ) -> str:
        label = self.text(
            f"{node_id}_initials", initials, round(size / 2.6), color, "BOLD"
        )
        return self.add(
            "CircleAvatar",
            node_id,
            {"radius": size / 2, "bgcolor": bgcolor},
            (label,),
        )

    def list_tile(
        self, node_id: str, title: str, subtitle: str, *, title_color: str = "#0B1220"
    ) -> str:
        title_id = self.text(f"{node_id}_title", title, 14, title_color, "W_500")
        subtitle_id = self.text(f"{node_id}_subtitle", subtitle, 12, "#64748B")
        return self.add(
            "ListTile",
            node_id,
            {},
            slots={"title": (title_id,), "subtitle": (subtitle_id,)},
        )

    def centered(self, node_id: str, child: str, *, width: float = 1040) -> str:
        """Bound a content column and centre it: the desktop composition rule."""
        inner = self.add("Container", f"{node_id}_inner", {"width": width}, (child,))
        return self.add("Row", node_id, {"alignment": "CENTER"}, (inner,))

    def progress(self, node_id: str, value: float, *, color: str, bgcolor: str) -> str:
        return self.add(
            "ProgressBar",
            node_id,
            {"value": value, "color": color, "bgcolor": bgcolor},
        )

    # ── navigation ────────────────────────────────────────────────────
    def navigate(self, node_id: str, event_name: str, route: str) -> str:
        """Bind a click on ``node_id`` to a route in the finished app."""
        from dataclasses import replace as _replace

        node = self.nodes.get(node_id)
        if node is None:
            raise ValueError(f"navigate() on unknown node {node_id!r}")
        actions = dict(node.actions)
        actions[event_name] = Navigate(route)
        self.nodes[node_id] = _replace(node, actions=actions)
        return node_id

    def finish_flow(
        self,
        name: str,
        screens: list[tuple[str, str, str]],
        *,
        seed: str = "INDIGO",
        bgcolor: str | None = None,
    ) -> Project:
        """Finish a multi-screen document.

        ``screens`` is an ordered list of ``(root_node_id, title, route)``; the
        first entry is the initial route unless ``initial_route`` is given.
        """
        if not screens:
            raise ValueError("a flow needs at least one screen")
        roots = tuple(root for root, _, _ in screens)
        for root, title, route in screens:
            if root not in self.nodes:
                raise ValueError(f"screen root {root!r} is not part of this document")
            if not title.strip():
                raise ValueError(f"screen {root!r} needs a title")
            if not route.startswith("/") or " " in route:
                raise ValueError(f"screen {root!r} has an invalid route {route!r}")
        if len({route for _, _, route in screens}) != len(screens):
            raise ValueError("screen routes must be unique")
        page: dict[str, JsonValue] = {
            "title": name,
            "padding": 0,
            "scroll": "none",
            "theme_mode": "LIGHT",
            "theme": {"color_scheme_seed": seed},
        }
        if bgcolor:
            page["bgcolor"] = bgcolor
        return Project(
            name=name,
            page=page,
            root_ids=roots,
            nodes=self.nodes,
            assets={},
            screens={
                root: ScreenMeta(title=title.strip(), route=route)
                for root, title, route in screens
            },
            initial_route=screens[0][2],
        )

    # ── document ──────────────────────────────────────────────────────
    def finish(
        self,
        name: str,
        root: str,
        *,
        seed: str = "INDIGO",
        bgcolor: str | None = None,
        scroll: str = "AUTO",
    ) -> Project:
        page: dict[str, JsonValue] = {
            "title": name,
            "padding": 0,
            "scroll": scroll,
            "theme_mode": "LIGHT",
            "theme": {"color_scheme_seed": seed},
        }
        if bgcolor:
            page["bgcolor"] = bgcolor
        return Project(
            name=name,
            page=page,
            root_ids=(root,),
            nodes=self.nodes,
            assets={},
        )


# Backwards-compatible alias used by older template bodies.
_Screen = Screen
