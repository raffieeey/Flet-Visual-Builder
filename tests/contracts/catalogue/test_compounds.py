"""Compound codecs: padding/margin, border all-xor-sides, input-border kinds."""

from __future__ import annotations

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.catalogue.codecs import CODE_BORDER_SHAPE, CODE_INPUT_BORDER
from flet_visual_builder.contracts import CallValue, Severity, SymbolRef


def _errors(diags):
    return [d for d in diags if d.severity is Severity.ERROR]


def test_padding_uniform_scalar_and_record() -> None:
    padding = catalogue.codecs["padding"]
    assert padding.validate(10) == ()
    assert padding.validate({"left": 8, "top": 4, "right": 8, "bottom": 4}) == ()
    assert _errors(padding.validate(-1))
    assert _errors(padding.validate({"left": -2}))
    lowered = padding.lower(10)
    assert isinstance(lowered, CallValue)
    assert lowered.constructor == SymbolRef(("Padding", "all"))


def test_margin_uniform_scalar_and_record() -> None:
    margin = catalogue.codecs["margin"]
    assert margin.validate(0) == ()
    assert margin.validate({"left": 1, "right": 1}) == ()
    lowered = margin.lower({"top": 2, "bottom": 2})
    assert isinstance(lowered, CallValue)
    assert lowered.constructor == SymbolRef(("Margin",))


def test_border_all_xor_sides() -> None:
    border = catalogue.codecs["border"]
    all_ok = {"all": {"width": 1, "color": "BLACK_12"}}
    sides_ok = {
        "left": {"width": 1, "color": "INDIGO"},
        "right": {"width": 1, "color": "INDIGO"},
    }
    assert border.validate(all_ok) == ()
    assert border.validate(sides_ok) == ()
    both = {**all_ok, **sides_ok}
    diags = _errors(border.validate(both))
    assert diags
    assert any(d.code == CODE_BORDER_SHAPE for d in diags)
    lowered = border.lower(all_ok)
    assert isinstance(lowered, CallValue)
    assert lowered.constructor == SymbolRef(("Border", "all"))


def test_input_border_three_kinds_and_field_rules() -> None:
    codec = catalogue.codecs["input_border"]
    assert codec.validate({"kind": "outline"}) == ()
    assert (
        codec.validate(
            {
                "kind": "outline",
                "border_radius": 4,
                "gap_padding": 2,
                "side": {"width": 1, "color": "INDIGO"},
            }
        )
        == ()
    )
    assert codec.validate({"kind": "underline", "border_radius": 0}) == ()
    assert codec.validate({"kind": "none"}) == ()
    # none accepts no shape fields
    none_extra = _errors(codec.validate({"kind": "none", "side": {"width": 1}}))
    assert none_extra
    assert any(d.code == CODE_INPUT_BORDER for d in none_extra)
    # underline does not accept gap_padding
    underline_extra = _errors(codec.validate({"kind": "underline", "gap_padding": 1}))
    assert underline_extra
    # deprecated enum-style values are not accepted
    assert _errors(codec.validate("OUTLINE"))
    assert _errors(codec.validate("NONE"))
    assert _errors(codec.validate("underline"))
    lowered = codec.lower({"kind": "outline"})
    assert isinstance(lowered, CallValue)
    assert lowered.constructor == SymbolRef(("OutlineInputBorder",))
    none_lowered = codec.lower({"kind": "none"})
    assert isinstance(none_lowered, CallValue)
    assert none_lowered.constructor == SymbolRef(("NoInputBorder",))


def test_input_border_state_map() -> None:
    codec = catalogue.codecs["input_border"]
    value = {
        "DEFAULT": {"kind": "outline"},
        "FOCUSED": {"kind": "underline"},
    }
    assert codec.validate(value) == ()
    lowered = codec.lower(value)
    from flet_visual_builder.contracts import MappingValue

    assert isinstance(lowered, MappingValue)


def test_textfield_default_border_validates() -> None:
    prop = catalogue.widget("TextField").properties["border"]
    assert prop.new_default == {"kind": "outline"}
    assert catalogue.validate_value(prop, {"kind": "outline"}) == ()
