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
    """A composed welcome screen: band, three steps, and a footer action row."""
    ink = "#0F172A"
    paper = "#FFFFFF"
    accent = "#4F46E5"
    accent_soft = "#EEF0FF"

    nodes: list[Node] = [
        _node(
            "Column",
            "root",
            {"spacing": 0, "alignment": "START", "horizontal_alignment": "STRETCH"},
            slots={"controls": ("header", "body")},
        ),
        # ── header band ────────────────────────────────────────────────
        _node(
            "Container",
            "header",
            {
                "bgcolor": ink,
                "padding": {"left": 40, "top": 36, "right": 40, "bottom": 36},
            },
            slots={"content": ("header_col",)},
        ),
        _node(
            "Column",
            "header_col",
            {"spacing": 8, "horizontal_alignment": "START", "alignment": "START"},
            slots={"controls": ("header_title", "header_tagline")},
        ),
        _node(
            "Text",
            "header_title",
            {
                "value": "Flet Visual Builder",
                "size": 28,
                "weight": "BOLD",
                "color": paper,
            },
        ),
        _node(
            "Text",
            "header_tagline",
            {
                "value": "Design a screen, then export clean, runnable Python.",
                "size": 14,
                "color": "#A5B4FC",
            },
        ),
        # ── body ───────────────────────────────────────────────────────
        _node(
            "Container",
            "body",
            {
                "bgcolor": paper,
                "padding": {"left": 40, "top": 32, "right": 40, "bottom": 32},
            },
            slots={"content": ("body_col",)},
        ),
        _node(
            "Column",
            "body_col",
            {"spacing": 16, "horizontal_alignment": "STRETCH"},
            slots={"controls": ("body_title", "steps", "rule", "actions")},
        ),
        _node(
            "Text", "body_title", {"value": "Start here", "size": 18, "weight": "W_600"}
        ),
        _node(
            "Column",
            "steps",
            {"spacing": 10, "horizontal_alignment": "STRETCH"},
            slots={"controls": ("step1", "step2", "step3")},
        ),
    ]

    step_copy = (
        ("step1", "1", "Drag widgets from the palette into the canvas."),
        ("step2", "2", "Edit text, color, spacing, and handlers in the inspector."),
        ("step3", "3", "Switch to Code and export a runnable Flet app."),
    )
    for row_id, number, copy in step_copy:
        nodes.extend(
            [
                _node(
                    "Row",
                    row_id,
                    {"spacing": 12, "vertical_alignment": "CENTER"},
                    slots={"controls": (f"{row_id}_badge", f"{row_id}_text")},
                ),
                _node(
                    "Container",
                    f"{row_id}_badge",
                    {
                        "width": 26,
                        "height": 26,
                        "bgcolor": accent_soft,
                        "border_radius": 13,
                        "alignment": "CENTER",
                    },
                    slots={"content": (f"{row_id}_num",)},
                ),
                _node(
                    "Text",
                    f"{row_id}_num",
                    {"value": number, "size": 12, "weight": "W_600", "color": accent},
                ),
                _node("Text", f"{row_id}_text", {"value": copy, "size": 13}),
            ]
        )

    nodes.extend(
        [
            _node("Divider", "rule", {"thickness": 1, "color": "#E3E6EA"}),
            _node(
                "Row",
                "actions",
                {"spacing": 10, "vertical_alignment": "CENTER"},
                slots={"controls": ("action_export", "action_save")},
            ),
            _node(
                "Button",
                "action_export",
                {
                    "content": "Export code",
                    "bgcolor": accent,
                    "color": paper,
                    "elevation": 0,
                },
            ),
            _node(
                "TextButton",
                "action_save",
                {"content": "Save project", "icon_color": accent},
            ),
        ]
    )

    return Project(
        name="Welcome",
        page=_page("Welcome to Flet Visual Builder"),
        root_ids=("root",),
        nodes={node.id: node for node in nodes},
        assets={},
    )
