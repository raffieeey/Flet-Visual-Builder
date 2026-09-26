"""Committed enum / Colors / Icons allowlists for catalogue version 1.

Colors and Icons are loaded from allowlist_manifest.json, which is generated
from the pinned Flet 1.0.1 package by tools/gen_manifest.py. Runtime catalogue
code must not import Flet.
"""
from __future__ import annotations

import json
from pathlib import Path

_MANIFEST_PATH = Path(__file__).with_name("allowlist_manifest.json")
_MANIFEST = json.loads(_MANIFEST_PATH.read_text(encoding="utf-8"))

TARGET_FLET: str = _MANIFEST["target_flet"]
COLORS: frozenset[str] = frozenset(_MANIFEST["colors"])
ICONS: frozenset[str] = frozenset(_MANIFEST["icons"])

# Normative subsets from TDD v2 §2.4.4. Not generated: the table is the allowlist.
MAIN_AXIS_ALIGNMENT: frozenset[str] = frozenset(
    {
        "START",
        "CENTER",
        "END",
        "SPACE_BETWEEN",
        "SPACE_AROUND",
        "SPACE_EVENLY",
    }
)
CROSS_AXIS_ALIGNMENT: frozenset[str] = frozenset({"START", "CENTER", "END", "STRETCH"})
TEXT_ALIGN: frozenset[str] = frozenset(
    {"LEFT", "CENTER", "RIGHT", "JUSTIFY", "START", "END"}
)
FONT_WEIGHT: frozenset[str] = frozenset(
    {
        "NORMAL",
        "BOLD",
        "W_100",
        "W_200",
        "W_300",
        "W_400",
        "W_500",
        "W_600",
        "W_700",
        "W_800",
        "W_900",
    }
)
ALIGNMENT: frozenset[str] = frozenset(
    {
        "TOP_LEFT",
        "TOP_CENTER",
        "TOP_RIGHT",
        "CENTER_LEFT",
        "CENTER",
        "CENTER_RIGHT",
        "BOTTOM_LEFT",
        "BOTTOM_CENTER",
        "BOTTOM_RIGHT",
    }
)
BOX_FIT: frozenset[str] = frozenset(
    {"FILL", "CONTAIN", "COVER", "FIT_WIDTH", "FIT_HEIGHT", "NONE", "SCALE_DOWN"}
)
SCROLL_MODE: frozenset[str] = frozenset({"AUTO", "ALWAYS", "HIDDEN", "ADAPTIVE"})
THEME_MODE: frozenset[str] = frozenset({"SYSTEM", "LIGHT", "DARK"})

# ControlState keys used by input-border state maps (TDD §2.4.4).
CONTROL_STATE: frozenset[str] = frozenset(
    {
        "DEFAULT",
        "DISABLED",
        "DRAGGED",
        "ERROR",
        "FOCUSED",
        "HOVERED",
        "PRESSED",
        "SCROLLED_UNDER",
        "SELECTED",
    }
)

ENUM_FAMILIES: dict[str, frozenset[str]] = {
    "MainAxisAlignment": MAIN_AXIS_ALIGNMENT,
    "CrossAxisAlignment": CROSS_AXIS_ALIGNMENT,
    "TextAlign": TEXT_ALIGN,
    "FontWeight": FONT_WEIGHT,
    "Alignment": ALIGNMENT,
    "BoxFit": BOX_FIT,
    "ScrollMode": SCROLL_MODE,
    "ThemeMode": THEME_MODE,
}
