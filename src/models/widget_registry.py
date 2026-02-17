from __future__ import annotations

from typing import Any

WIDGET_REGISTRY: dict[str, dict[str, Any]] = {
    "Text": {
        "category": "Basic",
        "props": {
            "value": {"type": "str", "default": "Text"},
            "size": {"type": "float", "default": 14.0},
            "weight": {
                "type": "enum",
                "default": "normal",
                "options": ["normal", "bold", "w100", "w200", "w300", "w400", "w500", "w600", "w700", "w800", "w900"],
            },
            "color": {"type": "color", "default": None},
            "text_align": {"type": "enum", "default": "left", "options": ["left", "center", "right", "justify"]},
        },
        "children": [],
    },
    "Container": {
        "category": "Layout",
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
                "options": ["center", "topLeft", "topCenter", "topRight", "centerLeft", "centerRight", "bottomLeft", "bottomCenter", "bottomRight"],
            },
        },
        "children": [{"slot": "content", "max": 1}],
    },
    "Column": {
        "category": "Layout",
        "props": {
            "alignment": {
                "type": "enum",
                "default": "start",
                "options": ["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"],
            },
            "horizontal_alignment": {"type": "enum", "default": "start", "options": ["start", "center", "end", "stretch"]},
            "spacing": {"type": "float", "default": 10.0},
            "tight": {"type": "bool", "default": False},
        },
        "children": [{"slot": "controls", "max": None}],
    },
    "Row": {
        "category": "Layout",
        "props": {
            "alignment": {
                "type": "enum",
                "default": "start",
                "options": ["start", "center", "end", "spaceBetween", "spaceAround", "spaceEvenly"],
            },
            "vertical_alignment": {"type": "enum", "default": "start", "options": ["start", "center", "end", "stretch"]},
            "spacing": {"type": "float", "default": 10.0},
            "wrap": {"type": "bool", "default": False},
        },
        "children": [{"slot": "controls", "max": None}],
    },
    "ElevatedButton": {
        "category": "Buttons",
        "props": {
            "text": {"type": "str", "default": "Button"},
            "icon": {"type": "str", "default": None},
            "color": {"type": "color", "default": None},
            "bgcolor": {"type": "color", "default": None},
            "on_click": {"type": "event", "default": None},
        },
        "children": [],
    },
    "TextField": {
        "category": "Input",
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
}


def defaults_for(widget_type: str) -> dict[str, Any]:
    return {k: v["default"] for k, v in WIDGET_REGISTRY[widget_type]["props"].items()}



def enum_key_for(widget_type: str, prop: str) -> str:
    pdef = WIDGET_REGISTRY[widget_type]["props"][prop]
    return pdef.get("enum_key", prop)
