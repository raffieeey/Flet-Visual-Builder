"""Current enum forms only; legacy scroll none; Colors/Icons traps."""
from __future__ import annotations

from src.flet_visual_builder.catalogue import catalogue
from src.flet_visual_builder.catalogue.enum_manifest import (
    ALIGNMENT,
    BOX_FIT,
    COLORS,
    FONT_WEIGHT,
    ICONS,
    SCROLL_MODE,
)
from src.flet_visual_builder.contracts import LiteralValue, Severity, SymbolRef


def _errors(diags) -> list:
    return [d for d in diags if d.severity is Severity.ERROR]


def test_font_weight_uses_underscored_w_forms() -> None:
    assert "W_500" in FONT_WEIGHT
    assert "W500" not in FONT_WEIGHT
    weight = catalogue.widget("Text").properties["weight"]
    assert catalogue.validate_value(weight, "W_500") == ()
    assert _errors(catalogue.validate_value(weight, "W500"))


def test_scroll_mode_has_no_none_member() -> None:
    assert "NONE" not in SCROLL_MODE
    assert "none" not in SCROLL_MODE
    scroll = catalogue.widget("Column").properties["scroll"]
    assert catalogue.validate_value(scroll, "AUTO") == ()
    assert catalogue.validate_value(scroll, "none") == ()
    assert catalogue.lower_value(scroll, "none") == LiteralValue(None)
    assert catalogue.validate_value(scroll, None) == ()
    assert _errors(catalogue.validate_value(scroll, "NONE"))


def test_alignment_nine_constants() -> None:
    assert ALIGNMENT == frozenset(
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
    alignment = catalogue.widget("Container").properties["alignment"]
    assert catalogue.lower_value(alignment, "CENTER") == SymbolRef(
        ("Alignment", "CENTER")
    )


def test_box_fit_members() -> None:
    assert BOX_FIT == frozenset(
        {"FILL", "CONTAIN", "COVER", "FIT_WIDTH", "FIT_HEIGHT", "NONE", "SCALE_DOWN"}
    )


def test_colors_naming_traps() -> None:
    assert "BLACK_12" in COLORS
    assert "BLACK12" not in COLORS
    assert "SURFACE_CONTAINER_HIGHEST" in COLORS
    assert "SURFACE_VARIANT" not in COLORS
    color = catalogue.widget("Text").properties["color"]
    assert catalogue.validate_value(color, "BLACK_12") == ()
    assert _errors(catalogue.validate_value(color, "BLACK12"))
    assert _errors(catalogue.validate_value(color, "SURFACE_VARIANT"))
    assert catalogue.lower_value(color, "INDIGO") == SymbolRef(("Colors", "INDIGO"))


def test_hex_color_literal_accepted() -> None:
    color = catalogue.widget("Text").properties["color"]
    assert catalogue.validate_value(color, "#112233") == ()
    lowered = catalogue.lower_value(color, "#112233")
    from src.flet_visual_builder.contracts import LiteralValue as LV

    assert lowered == LV("#112233")


def test_icons_allowlist() -> None:
    assert "HOME" in ICONS
    assert "ADD" in ICONS
    icon = catalogue.widget("Icon").properties["icon"]
    assert catalogue.validate_value(icon, "HOME") == ()
    assert _errors(catalogue.validate_value(icon, "home"))
    assert catalogue.lower_value(icon, "HOME") == SymbolRef(("Icons", "HOME"))


def test_cross_axis_excludes_baseline() -> None:
    prop = catalogue.widget("Column").properties["horizontal_alignment"]
    assert catalogue.validate_value(prop, "STRETCH") == ()
    assert _errors(catalogue.validate_value(prop, "BASELINE"))
