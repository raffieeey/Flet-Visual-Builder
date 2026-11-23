"""Starter documents.

A builder that opens on a blank grey rectangle teaches nothing. These documents
are small, valid projects that show the vocabulary of the tool: bands, cards,
titles, actions. They are written against the frozen catalogue and validated in
``tests/test_starter.py``.
"""

from __future__ import annotations

from flet_visual_builder.contracts import EventSymbol, Node, Project


def _node(
    type_id: str,
    node_id: str,
    props: dict[str, object] | None = None,
    *,
    slots: dict[str, tuple[str, ...]] | None = None,
    events: dict[str, str] | None = None,
) -> Node:
    return Node(
        id=node_id,
        type_id=type_id,
        props=dict(props or {}),
        slots=dict(slots or {}),
        events={name: EventSymbol(symbol) for name, symbol in (events or {}).items()},
    )


def _page(title: str) -> dict[str, object]:
    return {
        "title": title,
        "padding": 0,
        "scroll": "AUTO",
        "theme_mode": "LIGHT",
        "theme": {"color_scheme_seed": "INDIGO"},
    }


def empty_project(name: str = "Untitled") -> Project:
    root = _node(
        "Column", "root", {"spacing": 0, "alignment": "START"}, slots={"controls": ()}
    )
    return Project(
        name=name, page=_page(name), root_ids=("root",), nodes={"root": root}, assets={}
    )


def starter_project() -> Project:
    """A welcoming, editable introduction to the visual builder."""
    ink, paper, accent = "#0B1220", "#FFFFFF", "#4F46E5"
    muted, canvas, border = "#475569", "#F6F7F9", "#E2E8F0"
    nodes: list[Node] = [
        _node(
            "Column",
            "root",
            {
                "spacing": 0,
                "horizontal_alignment": "STRETCH",
                "alignment": "CENTER",
                "expand": True,
            },
            slots={"controls": ("header", "body")},
        ),
        _node(
            "Container",
            "header",
            {"bgcolor": ink, "padding": 40},
            slots={"content": ("header_center",)},
        ),
        _node(
            "Row",
            "header_center",
            {"alignment": "CENTER"},
            slots={"controls": ("header_width",)},
        ),
        _node(
            "Container",
            "header_width",
            {"width": 840},
            slots={"content": ("header_col",)},
        ),
        # Keep the first title a direct child for editor selection/drop semantics.
        _node(
            "Column",
            "header_col",
            {"spacing": 14, "horizontal_alignment": "START"},
            slots={"controls": ("header_title", "header_detail")},
        ),
        _node(
            "Text",
            "header_title",
            {
                "value": "YOUR CREATIVE WORKSPACE",
                "size": 12,
                "weight": "W_600",
                "color": "#A5B4FC",
            },
        ),
        _node(
            "Column",
            "header_detail",
            {"spacing": 8},
            slots={"controls": ("headline", "header_tagline")},
        ),
        _node(
            "Text",
            "headline",
            {
                "value": "From idea to interface.",
                "size": 34,
                "weight": "BOLD",
                "color": paper,
            },
        ),
        _node(
            "Text",
            "header_tagline",
            {
                "value": "Flet Visual Builder: design visually and export real Python.",
                "size": 15,
                "color": "#C7D2FE",
            },
        ),
        _node(
            "Container",
            "body",
            {"bgcolor": canvas, "padding": 32},
            slots={"content": ("body_center",)},
        ),
        _node(
            "Row",
            "body_center",
            {"alignment": "CENTER"},
            slots={"controls": ("body_width",)},
        ),
        _node(
            "Container", "body_width", {"width": 840}, slots={"content": ("body_col",)}
        ),
        _node(
            "Column",
            "body_col",
            {"spacing": 16, "horizontal_alignment": "STRETCH"},
            slots={"controls": ("body_title", "intro", "steps", "rule", "actions")},
        ),
        _node(
            "Text",
            "body_title",
            {"value": "Start here", "size": 23, "weight": "BOLD", "color": ink},
        ),
        _node(
            "Text",
            "intro",
            {
                "value": "Your first screen is just three small steps away.",
                "size": 14,
                "color": muted,
            },
        ),
        _node(
            "Column",
            "steps",
            {"spacing": 10, "horizontal_alignment": "STRETCH"},
            slots={"controls": ("step1", "step2", "step3")},
        ),
    ]
    step_copy = (
        (
            "step1",
            "01",
            "Build your layout",
            "Drag widgets from the palette onto the canvas.",
        ),
        (
            "step2",
            "02",
            "Make it yours",
            "Fine-tune content, color and spacing in the inspector.",
        ),
        ("step3", "03", "Ship your app", "Open Code to export a runnable Flet app."),
    )
    for row_id, number, title, copy in step_copy:
        nodes.extend(
            [
                _node(
                    "Container",
                    row_id,
                    {"bgcolor": paper, "padding": 14, "border_radius": 12},
                    slots={"content": (f"{row_id}_row",)},
                ),
                _node(
                    "Row",
                    f"{row_id}_row",
                    {"spacing": 16, "vertical_alignment": "CENTER"},
                    slots={"controls": (f"{row_id}_badge", f"{row_id}_col")},
                ),
                _node(
                    "CircleAvatar",
                    f"{row_id}_badge",
                    {"radius": 21, "bgcolor": "#EEF2FF"},
                    slots={"content": (f"{row_id}_num",)},
                ),
                _node(
                    "Text",
                    f"{row_id}_num",
                    {"value": number, "size": 12, "weight": "BOLD", "color": accent},
                ),
                _node(
                    "Column",
                    f"{row_id}_col",
                    {"spacing": 3, "expand": True},
                    slots={"controls": (f"{row_id}_title", f"{row_id}_text")},
                ),
                _node(
                    "Text",
                    f"{row_id}_title",
                    {"value": title, "size": 15, "weight": "W_600", "color": ink},
                ),
                _node(
                    "Text",
                    f"{row_id}_text",
                    {"value": copy, "size": 13, "color": muted},
                ),
            ]
        )
    nodes.extend(
        [
            _node("Divider", "rule", {"thickness": 1, "color": border}),
            _node(
                "Row",
                "actions",
                {"spacing": 14, "vertical_alignment": "CENTER", "wrap": True},
                slots={"controls": ("action_export", "action_hint")},
            ),
            _node(
                "Button",
                "action_export",
                {
                    "content": "Start designing  →",
                    "bgcolor": accent,
                    "color": paper,
                    "elevation": 0,
                },
            ),
            _node(
                "Text",
                "action_hint",
                {
                    "value": "Tip: select any element to make it your own.",
                    "size": 13,
                    "color": muted,
                },
            ),
        ]
    )
    return Project(
        name="Welcome",
        page={
            **_page("Welcome to Flet Visual Builder"),
            "bgcolor": canvas,
            "scroll": "none",
        },
        root_ids=("root",),
        nodes={node.id: node for node in nodes},
        assets={},
    )
