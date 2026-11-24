"""Sixteen-entry WidgetSpec catalogue (TDD v2 §2.4.2–§2.4.3)."""

from __future__ import annotations

from collections.abc import Mapping

from flet_visual_builder.catalogue.codecs import BUILTIN_IMAGE_PLACEHOLDER
from flet_visual_builder.contracts import (
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

_CONTENT_SLOT = SlotSpec(name="content", minimum=0, maximum=1, accepted_types=None)
_CONTROLS_SLOT = SlotSpec(name="controls", minimum=0, maximum=None, accepted_types=None)
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
    omit_shared: frozenset[str] = frozenset(),
) -> WidgetSpec:
    return WidgetSpec(
        type_id=type_id,
        constructor=SymbolRef((type_id,)),
        properties={k: v for k, v in _merge(*extras).items() if k not in omit_shared},
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
        # ft.Divider has no `width`; exposing it produced code the constructor rejects.
        omit_shared=frozenset({"width"}),
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
        # Flet's Container really does accept a click handler; clickable cards are common.
        events=frozenset({"on_click"}),
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

# Additional entries use only fields exposed by Flet 1.0.1.
_NO_SIZE = frozenset({"width", "height"})
_MULTI_DEST = SlotSpec("destinations", 0, None, frozenset({"NavigationBarDestination"}))
WIDGET_SPECS.update(
    {
        "Stack": _widget(
            "Stack",
            (_p("alignment", "enum.Alignment", "CENTER", nullable=False),),
            {"controls": _CONTROLS_SLOT},
        ),
        "GridView": _widget(
            "GridView",
            (
                _p("height", "nonneg_number", 240, nullable=True),
                _p("spacing", "nonneg_number", 10, nullable=False),
                _p("run_spacing", "nonneg_number", 10, nullable=False),
                _p("runs_count", "positive_integer", 2, nullable=False),
            ),
            {"controls": _CONTROLS_SLOT},
        ),
        "ResponsiveRow": _widget(
            "ResponsiveRow",
            (
                _p("spacing", "nonneg_number", 10, nullable=False),
                _p("run_spacing", "nonneg_number", 10, nullable=False),
            ),
            {"controls": _CONTROLS_SLOT},
        ),
        "VerticalDivider": _widget(
            "VerticalDivider",
            (
                _p("thickness", "nonneg_number", 1, nullable=True),
                _p("color", "color", U, nullable=True),
            ),
            omit_shared=frozenset({"height"}),
        ),
        "ProgressRing": _widget(
            "ProgressRing",
            (
                _p("value", "unit_interval", 0.5, nullable=True),
                _p("stroke_width", "nonneg_number", 4, nullable=False),
                _p("color", "color", U, nullable=True),
            ),
        ),
        "CircleAvatar": _widget(
            "CircleAvatar",
            (
                _p("radius", "nonneg_number", 20, nullable=True),
                _p("bgcolor", "color", U, nullable=True),
            ),
            {"content": _CONTENT_SLOT},
        ),
        "Chip": _widget(
            "Chip",
            (
                _p("label", "string", "Chip", nullable=False),
                _p("selected", "boolean", False, nullable=False),
            ),
            {
                "label": SlotSpec("label", 0, 1, None),
                "leading": SlotSpec("leading", 0, 1, None),
            },
            frozenset({"on_click", "on_select", "on_delete"}),
        ),
        "ListTile": _widget(
            "ListTile",
            (
                _p("title", "string", "List tile", nullable=True),
                _p("subtitle", "string", U, nullable=True),
                _p("selected", "boolean", False, nullable=False),
            ),
            {
                name: SlotSpec(name, 0, 1, None)
                for name in ("title", "subtitle", "leading", "trailing")
            },
            frozenset({"on_click", "on_long_press"}),
        ),
        "Markdown": _widget(
            "Markdown",
            (
                _p("value", "string", "Markdown", nullable=False),
                _p("selectable", "boolean", False, nullable=False),
            ),
            events=frozenset({"on_tap_link"}),
        ),
        "FilledButton": _widget(
            "FilledButton",
            (
                _p("content", "string", "Filled button", nullable=True),
                _p("icon", "icon", U, nullable=True),
            ),
            {"content": _CONTENT_SLOT},
            frozenset({"on_click"}),
        ),
        "OutlinedButton": _widget(
            "OutlinedButton",
            (
                _p("content", "string", "Outlined button", nullable=True),
                _p("icon", "icon", U, nullable=True),
            ),
            {"content": _CONTENT_SLOT},
            frozenset({"on_click"}),
        ),
        "FloatingActionButton": _widget(
            "FloatingActionButton",
            (
                _p("icon", "icon", "ADD", nullable=True),
                _p("mini", "boolean", False, nullable=False),
                _p("bgcolor", "color", U, nullable=True),
            ),
            {"content": _CONTENT_SLOT},
            frozenset({"on_click"}),
        ),
        "Radio": _widget(
            "Radio",
            (
                _p("value", "string", "option", nullable=True),
                _p("label", "string", "Radio", nullable=True),
            ),
        ),
        "Slider": _widget(
            "Slider",
            (
                _p("value", "unit_interval", 0.5, nullable=False),
                _p("label", "string", U, nullable=True),
            ),
            events=frozenset({"on_change", "on_change_start", "on_change_end"}),
        ),
        "Dropdown": _widget(
            "Dropdown",
            (
                _p("label", "string", "Choose", nullable=True),
                _p("options", "dropdown_options", (), nullable=False),
                _p("value", "string", U, nullable=True),
            ),
            events=frozenset({"on_select"}),
        ),
        "ExpansionTile": _widget(
            "ExpansionTile",
            (
                _p("title", "string", "Expand", nullable=False),
                _p("expanded", "boolean", False, nullable=False),
            ),
            {"controls": _CONTROLS_SLOT, "title": SlotSpec("title", 0, 1, None)},
            frozenset({"on_change"}),
        ),
        "NavigationBar": _widget(
            "NavigationBar",
            (
                _p(
                    "destinations",
                    "navigation_destinations",
                    (
                        {"icon": "HOME", "label": "Home"},
                        {"icon": "SEARCH", "label": "Search"},
                    ),
                    nullable=False,
                ),
                _p("selected_index", "nonneg_integer", 0, nullable=False),
            ),
            {"destinations": _MULTI_DEST},
            frozenset({"on_change"}),
        ),
        "NavigationBarDestination": _widget(
            "NavigationBarDestination",
            (
                _p("icon", "icon", "HOME", nullable=False, required=True),
                _p("label", "string", "Home", nullable=True),
            ),
            omit_shared=_NO_SIZE,
        ),
        "SegmentedButton": _widget(
            "SegmentedButton",
            (
                _p(
                    "segments",
                    "segments",
                    ({"value": "one", "label": "One"},),
                    nullable=False,
                    required=True,
                ),
                _p("allow_empty_selection", "boolean", True, nullable=False),
            ),
            events=frozenset({"on_change"}),
        ),
        "DropdownOption": _widget(
            "DropdownOption",
            (_p("text", "string", "Option", nullable=True),),
            omit_shared=_NO_SIZE,
        ),
        "Segment": _widget(
            "Segment",
            (
                _p("value", "string", "one", nullable=False, required=True),
                _p("label", "string", "One", nullable=True),
                _p("icon", "icon", U, nullable=True),
            ),
            omit_shared=_NO_SIZE,
        ),
        "Tab": _widget(
            "Tab",
            (
                _p("label", "string", "Tab", nullable=True),
                _p("icon", "icon", U, nullable=True),
            ),
            omit_shared=frozenset({"width"}),
        ),
    }
)
WIDGET_SPECS.update(
    {
        "SafeArea": _widget(
            "SafeArea",
            (
                _p("content", "empty_control", {"kind": "empty"}, nullable=False),
                _p("minimum_padding", "padding", 0, nullable=False),
            ),
            {"content": _CONTENT_SLOT},
        ),
        "RadioGroup": _widget(
            "RadioGroup",
            (
                _p("content", "empty_control", {"kind": "empty"}, nullable=False),
                _p("value", "string", U, nullable=True),
            ),
            {"content": _CONTENT_SLOT},
            frozenset({"on_change"}),
            omit_shared=_NO_SIZE,
        ),
    }
)
WIDGET_SPECS.update(
    {
        "TabBar": _widget(
            "TabBar",
            (
                _p("tabs", "tabs", ({"label": "Tab"},), nullable=False),
                _p("scrollable", "boolean", True, nullable=False),
            ),
            {"tabs": SlotSpec("tabs", 0, None, frozenset({"Tab"}))},
            frozenset({"on_click"}),
        ),
        "TabBarView": _widget(
            "TabBarView",
            (
                _p(
                    "controls", "tab_views", ({"value": "Tab content"},), nullable=False
                ),
                _p("height", "nonneg_number", 200, nullable=True),
            ),
            {"controls": _CONTROLS_SLOT},
        ),
        "Tabs": _widget(
            "Tabs",
            (
                _p("content", "tabs_content", {"kind": "empty"}, nullable=False),
                _p("length", "positive_integer", 1, nullable=False),
                _p("selected_index", "nonneg_integer", 0, nullable=False),
            ),
            {"content": _CONTENT_SLOT},
            frozenset({"on_change"}),
        ),
    }
)
WIDGET_ORDER += tuple(name for name in WIDGET_SPECS if name not in WIDGET_ORDER)
