"""Sixteen-entry WidgetSpec catalogue (TDD v2 §2.4.2–§2.4.3)."""
from __future__ import annotations

from collections.abc import Mapping

from src.flet_visual_builder.catalogue.codecs import BUILTIN_IMAGE_PLACEHOLDER
from src.flet_visual_builder.contracts import (
    JsonValue,
    PropertySpec,
    SlotSpec,
    SymbolRef,
    Unset,
    WidgetSpec,
)

U = Unset.VALUE


def _p(
    name: str,
    codec_id: str,
    new_default: JsonValue | Unset,
    *,
    nullable: bool,
    required: bool = False,
) -> PropertySpec:
    return PropertySpec(
        name=name,
        codec_id=codec_id,
        new_default=new_default,
        nullable=nullable,
        required=required,
    )


SHARED: tuple[PropertySpec, ...] = (
    _p("width", "nonneg_number", U, nullable=True),
    _p("height", "nonneg_number", U, nullable=True),
    _p("expand", "expand", U, nullable=True),
    _p("disabled", "boolean", False, nullable=False),
    _p("visible", "boolean", True, nullable=False),
)

_CONTENT_SLOT = SlotSpec(
    name="content", minimum=0, maximum=1, accepted_types=None
)
_CONTROLS_SLOT = SlotSpec(
    name="controls", minimum=0, maximum=None, accepted_types=None
)
_ERROR_CONTENT_SLOT = SlotSpec(
    name="error_content", minimum=0, maximum=1, accepted_types=None
)


def _merge(*extras: PropertySpec) -> dict[str, PropertySpec]:
    props = {spec.name: spec for spec in SHARED}
    for spec in extras:
        props[spec.name] = spec
    return props


def _widget(
    type_id: str,
    extras: tuple[PropertySpec, ...],
    slots: Mapping[str, SlotSpec] | None = None,
    events: frozenset[str] = frozenset(),
) -> WidgetSpec:
    return WidgetSpec(
        type_id=type_id,
        constructor=SymbolRef((type_id,)),
        properties=_merge(*extras),
        slots=dict(slots) if slots else {},
        events=events,
    )


WIDGET_SPECS: dict[str, WidgetSpec] = {
    "Text": _widget(
        "Text",
        (
            _p("value", "string", "Text", nullable=False),
            _p("size", "nonneg_number", 14, nullable=True),
            _p("weight", "enum.FontWeight", "NORMAL", nullable=True),
            _p("color", "color", U, nullable=True),
            _p("text_align", "enum.TextAlign", "LEFT", nullable=True),
        ),
    ),
    "Icon": _widget(
        "Icon",
        (
            _p("icon", "icon", "HOME", nullable=False, required=True),
            _p("size", "nonneg_number", 24, nullable=True),
            _p("color", "color", U, nullable=True),
        ),
    ),
    "Image": _widget(
        "Image",
        (
            _p(
                "src",
                "image_source",
                dict(BUILTIN_IMAGE_PLACEHOLDER),
                nullable=False,
                required=True,
            ),
            _p("fit", "enum.BoxFit", "CONTAIN", nullable=True),
            _p("width", "nonneg_number", 200, nullable=True),
            _p("height", "nonneg_number", 120, nullable=True),
        ),
        slots={"error_content": _ERROR_CONTENT_SLOT},
    ),
    "Divider": _widget(
        "Divider",
        (
            _p("height", "nonneg_number", 1, nullable=True),
            _p("thickness", "nonneg_number", 1, nullable=True),
            _p("color", "color", U, nullable=True),
        ),
    ),
    "ProgressBar": _widget(
        "ProgressBar",
        (
            _p("value", "unit_interval", 0.5, nullable=True),
            _p("color", "color", U, nullable=True),
            _p("bgcolor", "color", U, nullable=True),
        ),
    ),
    "TextField": _widget(
        "TextField",
        (
            _p("label", "string", "", nullable=True),
            _p("hint_text", "string", "", nullable=True),
            _p("value", "string", "", nullable=True),
            _p("password", "boolean", False, nullable=False),
            _p("multiline", "boolean", False, nullable=False),
            _p("read_only", "boolean", False, nullable=False),
            _p("error", "string", U, nullable=True),
            _p("border", "input_border", {"kind": "outline"}, nullable=True),
        ),
        events=frozenset({"on_change"}),
    ),
    "Checkbox": _widget(
        "Checkbox",
        (
            _p("label", "string", "Checkbox", nullable=True),
            _p("value", "boolean", False, nullable=True),
            _p("tristate", "boolean", False, nullable=False),
            _p("error", "boolean", False, nullable=False),
        ),
        events=frozenset({"on_change"}),
    ),
    "Switch": _widget(
        "Switch",
        (
            _p("label", "string", "Switch", nullable=True),
            _p("value", "boolean", False, nullable=False),
        ),
        events=frozenset({"on_change"}),
    ),
    "Button": _widget(
        "Button",
        (
            _p("content", "string", "Button", nullable=True),
            _p("icon", "icon", U, nullable=True),
            _p("color", "color", U, nullable=True),
            _p("bgcolor", "color", U, nullable=True),
            _p("elevation", "nonneg_number", 1, nullable=False),
        ),
        slots={"content": _CONTENT_SLOT},
        events=frozenset({"on_click"}),
    ),
    "IconButton": _widget(
        "IconButton",
        (
            _p("icon", "icon", "ADD", nullable=False, required=True),
            _p("icon_size", "nonneg_number", 24, nullable=True),
            _p("icon_color", "color", U, nullable=True),
        ),
        events=frozenset({"on_click"}),
    ),
    "Container": _widget(
        "Container",
        (
            _p("padding", "padding", 10, nullable=True),
            _p("margin", "margin", U, nullable=True),
            _p("bgcolor", "color", U, nullable=True),
            _p("border_radius", "radius", 0, nullable=True),
            _p("alignment", "enum.Alignment", "CENTER", nullable=True),
            _p("border", "border", U, nullable=True),
        ),
        slots={"content": _CONTENT_SLOT},
    ),
    "Column": _widget(
        "Column",
        (
            _p("alignment", "enum.MainAxisAlignment", "START", nullable=False),
            _p(
                "horizontal_alignment",
                "enum.CrossAxisAlignment",
                "START",
                nullable=False,
            ),
            _p("spacing", "nonneg_number", 10, nullable=False),
            _p("tight", "boolean", False, nullable=False),
            _p("scroll", "enum.ScrollMode", U, nullable=True),
        ),
        slots={"controls": _CONTROLS_SLOT},
    ),
    "Row": _widget(
        "Row",
        (
            _p("alignment", "enum.MainAxisAlignment", "START", nullable=False),
            _p(
                "vertical_alignment",
                "enum.CrossAxisAlignment",
                "START",
                nullable=False,
            ),
            _p("spacing", "nonneg_number", 10, nullable=False),
            _p("wrap", "boolean", False, nullable=False),
            _p("scroll", "enum.ScrollMode", U, nullable=True),
        ),
        slots={"controls": _CONTROLS_SLOT},
    ),
    "Card": _widget(
        "Card",
        (
            _p("bgcolor", "color", U, nullable=True),
            _p("elevation", "nonneg_number", 1, nullable=True),
        ),
        slots={"content": _CONTENT_SLOT},
    ),
    "ListView": _widget(
        "ListView",
        (
            _p("spacing", "nonneg_number", 0, nullable=False),
            _p("padding", "padding", 0, nullable=True),
            _p("horizontal", "boolean", False, nullable=False),
            _p("auto_scroll", "boolean", False, nullable=False),
            _p("height", "nonneg_number", 240, nullable=True),
        ),
        slots={"controls": _CONTROLS_SLOT},
    ),
    "TextButton": _widget(
        "TextButton",
        (
            _p("content", "string", "Text button", nullable=True),
            _p("icon", "icon", U, nullable=True),
            _p("icon_color", "color", U, nullable=True),
        ),
        slots={"content": _CONTENT_SLOT},
        events=frozenset({"on_click"}),
    ),
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
