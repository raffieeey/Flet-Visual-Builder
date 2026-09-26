"""TDD v2 §2.4 transcribed as the expected catalogue table."""
from __future__ import annotations

from src.flet_visual_builder.contracts import Unset

U = Unset.VALUE

# name -> (codec_id, new_default, nullable)
SHARED_PROPS: dict[str, tuple[str, object, bool]] = {
    "width": ("nonneg_number", U, True),
    "height": ("nonneg_number", U, True),
    "expand": ("expand", U, True),
    "disabled": ("boolean", False, False),
    "visible": ("boolean", True, False),
}

# Widget extras that supplement or override SHARED_PROPS.
WIDGET_PROPS: dict[str, dict[str, tuple[str, object, bool]]] = {
    "Text": {
        "value": ("string", "Text", False),
        "size": ("nonneg_number", 14, True),
        "weight": ("enum.FontWeight", "NORMAL", True),
        "color": ("color", U, True),
        "text_align": ("enum.TextAlign", "LEFT", True),
    },
    "Icon": {
        "icon": ("icon", "HOME", False),
        "size": ("nonneg_number", 24, True),
        "color": ("color", U, True),
    },
    "Image": {
        "src": ("image_source", {"kind": "builtin"}, False),
        "fit": ("enum.BoxFit", "CONTAIN", True),
        "width": ("nonneg_number", 200, True),
        "height": ("nonneg_number", 120, True),
    },
    "Divider": {
        "height": ("nonneg_number", 1, True),
        "thickness": ("nonneg_number", 1, True),
        "color": ("color", U, True),
    },
    "ProgressBar": {
        "value": ("unit_interval", 0.5, True),
        "color": ("color", U, True),
        "bgcolor": ("color", U, True),
    },
    "TextField": {
        "label": ("string", "", True),
        "hint_text": ("string", "", True),
        "value": ("string", "", True),
        "password": ("boolean", False, False),
        "multiline": ("boolean", False, False),
        "read_only": ("boolean", False, False),
        "error": ("string", U, True),
        "border": ("input_border", {"kind": "outline"}, True),
    },
    "Checkbox": {
        "label": ("string", "Checkbox", True),
        "value": ("boolean", False, True),
        "tristate": ("boolean", False, False),
        "error": ("boolean", False, False),
    },
    "Switch": {
        "label": ("string", "Switch", True),
        "value": ("boolean", False, False),
    },
    "Button": {
        "content": ("string", "Button", True),
        "icon": ("icon", U, True),
        "color": ("color", U, True),
        "bgcolor": ("color", U, True),
        "elevation": ("nonneg_number", 1, False),
    },
    "IconButton": {
        "icon": ("icon", "ADD", False),
        "icon_size": ("nonneg_number", 24, True),
        "icon_color": ("color", U, True),
    },
    "Container": {
        "padding": ("padding", 10, True),
        "margin": ("margin", U, True),
        "bgcolor": ("color", U, True),
        "border_radius": ("radius", 0, True),
        "alignment": ("enum.Alignment", "CENTER", True),
        "border": ("border", U, True),
    },
    "Column": {
        "alignment": ("enum.MainAxisAlignment", "START", False),
        "horizontal_alignment": ("enum.CrossAxisAlignment", "START", False),
        "spacing": ("nonneg_number", 10, False),
        "tight": ("boolean", False, False),
        "scroll": ("enum.ScrollMode", U, True),
    },
    "Row": {
        "alignment": ("enum.MainAxisAlignment", "START", False),
        "vertical_alignment": ("enum.CrossAxisAlignment", "START", False),
        "spacing": ("nonneg_number", 10, False),
        "wrap": ("boolean", False, False),
        "scroll": ("enum.ScrollMode", U, True),
    },
    "Card": {
        "bgcolor": ("color", U, True),
        "elevation": ("nonneg_number", 1, True),
    },
    "ListView": {
        "spacing": ("nonneg_number", 0, False),
        "padding": ("padding", 0, True),
        "horizontal": ("boolean", False, False),
        "auto_scroll": ("boolean", False, False),
        "height": ("nonneg_number", 240, True),
    },
    "TextButton": {
        "content": ("string", "Text button", True),
        "icon": ("icon", U, True),
        "icon_color": ("color", U, True),
    },
}

# slot name -> (minimum, maximum)  maximum None means 0..N
WIDGET_SLOTS: dict[str, dict[str, tuple[int, int | None]]] = {
    "Text": {},
    "Icon": {},
    "Image": {"error_content": (0, 1)},
    "Divider": {},
    "ProgressBar": {},
    "TextField": {},
    "Checkbox": {},
    "Switch": {},
    "Button": {"content": (0, 1)},
    "IconButton": {},
    "Container": {"content": (0, 1)},
    "Column": {"controls": (0, None)},
    "Row": {"controls": (0, None)},
    "Card": {"content": (0, 1)},
    "ListView": {"controls": (0, None)},
    "TextButton": {"content": (0, 1)},
}

WIDGET_EVENTS: dict[str, frozenset[str]] = {
    "Text": frozenset(),
    "Icon": frozenset(),
    "Image": frozenset(),
    "Divider": frozenset(),
    "ProgressBar": frozenset(),
    "TextField": frozenset({"on_change"}),
    "Checkbox": frozenset({"on_change"}),
    "Switch": frozenset({"on_change"}),
    "Button": frozenset({"on_click"}),
    "IconButton": frozenset({"on_click"}),
    "Container": frozenset(),
    "Column": frozenset(),
    "Row": frozenset(),
    "Card": frozenset(),
    "ListView": frozenset(),
    "TextButton": frozenset({"on_click"}),
}

WIDGET_ORDER: tuple[str, ...] = (
    "Text",
    "Icon",
    "Image",
    "Divider",
    "ProgressBar",
    "TextField",
    "Checkbox",
    "Switch",
    "Button",
    "IconButton",
    "Container",
    "Column",
    "Row",
    "Card",
    "ListView",
    "TextButton",
)


def expected_props(type_id: str) -> dict[str, tuple[str, object, bool]]:
    merged = dict(SHARED_PROPS)
    merged.update(WIDGET_PROPS[type_id])
    return merged
