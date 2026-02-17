from __future__ import annotations

from typing import Any

WIDGET_REGISTRY: dict[str, dict[str, Any]] = {
    # ── Basic ──────────────────────────────────────────────────
    "Text": {
        "category": "Basic",
        "icon": "text_fields",
        "props": {
            "value": {"type": "str", "default": "Text"},
            "size": {"type": "float", "default": 14.0},
            "weight": {
                "type": "enum",
                "default": "normal",
                "options": [
                    "normal", "bold", "w100", "w200", "w300",
                    "w400", "w500", "w600", "w700", "w800", "w900",
                ],
            },
            "color": {"type": "color", "default": None},
            "text_align": {
                "type": "enum", "default": "left",
                "options": ["left", "center", "right", "justify"],
            },
        },
        "children": [],
    },
    "Icon": {
        "category": "Basic",
        "icon": "star",
        "props": {
            "name": {"type": "str", "default": "home"},
            "size": {"type": "float", "default": 24.0},
            "color": {"type": "color", "default": None},
        },
        "children": [],
    },
    "Image": {
        "category": "Basic",
        "icon": "image",
        "props": {
            "src": {"type": "str", "default": "https://picsum.photos/200"},
            "width": {"type": "float", "default": None},
            "height": {"type": "float", "default": None},
            "fit": {
                "type": "enum", "default": "contain",
                "options": ["contain", "cover", "fill", "fitWidth", "fitHeight", "none"],
            },
        },
        "children": [],
    },
    "Divider": {
        "category": "Basic",
        "icon": "horizontal_rule",
        "props": {
            "height": {"type": "float", "default": 1.0},
            "thickness": {"type": "float", "default": 1.0},
            "color": {"type": "color", "default": None},
        },
        "children": [],
    },
    "ProgressBar": {
        "category": "Basic",
        "icon": "linear_scale",
        "props": {
            "value": {"type": "float", "default": None},
            "color": {"type": "color", "default": None},
            "bgcolor": {"type": "color", "default": None},
        },
        "children": [],
    },

    # ── Input ──────────────────────────────────────────────────
    "TextField": {
        "category": "Input",
        "icon": "edit",
        "props": {
            "label": {"type": "str", "default": ""},
            "hint_text": {"type": "str", "default": ""},
            "value": {"type": "str", "default": ""},
            "password": {"type": "bool", "default": False},
            "multiline": {"type": "bool", "default": False},
            "read_only": {"type": "bool", "default": False},
            "on_change": {"type": "event", "default": None},
        },
        "children": [],
    },
    "Checkbox": {
        "category": "Input",
        "icon": "check_box",
        "props": {
            "label": {"type": "str", "default": "Checkbox"},
            "value": {"type": "bool", "default": False},
            "on_change": {"type": "event", "default": None},
        },
        "children": [],
    },
    "Switch": {
        "category": "Input",
        "icon": "toggle_on",
        "props": {
            "label": {"type": "str", "default": "Switch"},
            "value": {"type": "bool", "default": False},
            "on_change": {"type": "event", "default": None},
        },
        "children": [],
    },

    # ── Buttons ────────────────────────────────────────────────
    "ElevatedButton": {
        "category": "Buttons",
        "icon": "smart_button",
        "props": {
            "text": {"type": "str", "default": "Button"},
            "icon": {"type": "str", "default": None},
            "color": {"type": "color", "default": None},
            "bgcolor": {"type": "color", "default": None},
            "on_click": {"type": "event", "default": None},
        },
        "children": [],
    },
    "IconButton": {
        "category": "Buttons",
        "icon": "touch_app",
        "props": {
            "icon": {"type": "str", "default": "add"},
            "icon_size": {"type": "float", "default": 24.0},
            "icon_color": {"type": "color", "default": None},
            "on_click": {"type": "event", "default": None},
        },
        "children": [],
    },

    # ── Layout ─────────────────────────────────────────────────
    "Container": {
        "category": "Layout",
        "icon": "crop_square",
        "props": {
            "width": {"type": "float", "default": None},
            "height": {"type": "float", "default": None},
            "padding": {"type": "padding", "default": 10},
            "bgcolor": {"type": "color", "default": None},
            "border_radius": {"type": "float", "default": 0.0},
            "alignment": {
                "type": "enum",
                "enum_key": "container_alignment",
                "default": "center",
                "options": [
                    "center", "topLeft", "topCenter", "topRight",
                    "centerLeft", "centerRight",
                    "bottomLeft", "bottomCenter", "bottomRight",
                ],
            },
        },
        "children": [{"slot": "content", "max": 1}],
    },
    "Column": {
        "category": "Layout",
        "icon": "view_agenda",
        "props": {
            "alignment": {
                "type": "enum", "default": "start",
                "options": ["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"],
            },
            "horizontal_alignment": {
                "type": "enum", "default": "start",
                "options": ["start", "center", "end", "stretch"],
            },
            "spacing": {"type": "float", "default": 10.0},
            "tight": {"type": "bool", "default": False},
            "scroll": {
                "type": "enum", "default": "none",
                "options": ["none", "auto", "always", "hidden"],
            },
        },
        "children": [{"slot": "controls", "max": None}],
    },
    "Row": {
        "category": "Layout",
        "icon": "view_week",
        "props": {
            "alignment": {
                "type": "enum", "default": "start",
                "options": ["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"],
            },
            "vertical_alignment": {
                "type": "enum", "default": "start",
                "options": ["start", "center", "end", "stretch"],
            },
            "spacing": {"type": "float", "default": 10.0},
            "wrap": {"type": "bool", "default": False},
        },
        "children": [{"slot": "controls", "max": None}],
    },
    "Card": {
        "category": "Layout",
        "icon": "crop_portrait",
        "props": {
            "color": {"type": "color", "default": None},
            "elevation": {"type": "float", "default": 1.0},
        },
        "children": [{"slot": "content", "max": 1}],
    },
    "ListView": {
        "category": "Layout",
        "icon": "view_list",
        "props": {
            "spacing": {"type": "float", "default": 0.0},
            "padding": {"type": "padding", "default": 0},
            "auto_scroll": {"type": "bool", "default": False},
        },
        "children": [{"slot": "controls", "max": None}],
    },
}


def defaults_for(widget_type: str) -> dict[str, Any]:
    return {k: v["default"] for k, v in WIDGET_REGISTRY[widget_type]["props"].items()}


def enum_key_for(widget_type: str, prop: str) -> str:
    pdef = WIDGET_REGISTRY[widget_type]["props"][prop]
    return pdef.get("enum_key", prop)


def accepts_children(widget_type: str) -> bool:
    return bool(WIDGET_REGISTRY.get(widget_type, {}).get("children"))


def default_slot(widget_type: str) -> str | None:
    slots = WIDGET_REGISTRY.get(widget_type, {}).get("children", [])
    if len(slots) == 1:
        return slots[0]["slot"]
    return None