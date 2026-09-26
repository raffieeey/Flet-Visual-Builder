"""U / ? / null / unset / false / 0 remain distinct (TDD v2 §2.4.1)."""
from __future__ import annotations

from src.flet_visual_builder.catalogue import catalogue
from src.flet_visual_builder.contracts import LiteralValue, Severity, Unset, WidgetSpec


def _text() -> WidgetSpec:
    return catalogue.widget("Text")


def test_u_means_absent_from_new_node() -> None:
    props = catalogue.new_props("Text")
    assert "width" not in props
    assert "height" not in props
    assert "expand" not in props
    assert "color" not in props
    assert catalogue.widget("Text").properties["width"].new_default is Unset.VALUE


def test_creation_defaults_are_materialized() -> None:
    props = catalogue.new_props("Text")
    assert props["value"] == "Text"
    assert props["size"] == 14
    assert props["disabled"] is False
    assert props["visible"] is True


def test_explicit_null_allowed_only_where_question_mark() -> None:
    size = catalogue.widget("Text").properties["size"]
    value = catalogue.widget("Text").properties["value"]
    assert size.nullable is True
    assert value.nullable is False
    assert catalogue.validate_value(size, None) == ()
    null_value = catalogue.validate_value(value, None)
    assert any(d.severity is Severity.ERROR for d in null_value)


def test_zero_false_empty_text_are_retained() -> None:
    disabled = catalogue.widget("Text").properties["disabled"]
    size = catalogue.widget("Text").properties["size"]
    label = catalogue.widget("TextField").properties["label"]
    assert catalogue.validate_value(disabled, False) == ()
    assert catalogue.validate_value(size, 0) == ()
    assert catalogue.validate_value(label, "") == ()
    assert catalogue.lower_value(disabled, False) == LiteralValue(False)
    assert catalogue.lower_value(size, 0) == LiteralValue(0)
    assert catalogue.lower_value(label, "") == LiteralValue("")


def test_false_is_not_a_number() -> None:
    size = catalogue.widget("Text").properties["size"]
    diags = catalogue.validate_value(size, False)
    assert any(d.severity is Severity.ERROR for d in diags)


def test_null_is_not_false_or_zero() -> None:
    checkbox_value = catalogue.widget("Checkbox").properties["value"]
    assert checkbox_value.nullable is True
    assert catalogue.validate_value(checkbox_value, None) == ()
    assert catalogue.validate_value(checkbox_value, False) == ()
    assert catalogue.lower_value(checkbox_value, None) == LiteralValue(None)
    assert catalogue.lower_value(checkbox_value, False) == LiteralValue(False)


def test_switch_value_does_not_allow_null() -> None:
    prop = catalogue.widget("Switch").properties["value"]
    assert prop.nullable is False
    diags = catalogue.validate_value(prop, None)
    assert any(d.severity is Severity.ERROR for d in diags)
