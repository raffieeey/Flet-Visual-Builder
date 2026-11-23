"""Every key/default/slot/event in TDD v2 §2.4 is implemented exactly."""

from __future__ import annotations

import pytest

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import Unset

from tests.contracts.catalogue.expected import (
    WIDGET_EVENTS,
    WIDGET_ORDER,
    WIDGET_SLOTS,
    expected_props,
)


def test_sixteen_widgets_in_normative_order() -> None:
    assert tuple(catalogue.widgets)[: len(WIDGET_ORDER)] == WIDGET_ORDER
    assert len(catalogue.widgets) >= len(WIDGET_ORDER)
    assert catalogue.version == 1
    assert catalogue.target_flet == "1.0.1"


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_widget_properties_match_tdd_table(type_id: str) -> None:
    spec = catalogue.widget(type_id)
    expected = expected_props(type_id)
    assert set(spec.properties) == set(expected)
    for name, (codec_id, default, nullable) in expected.items():
        prop = spec.properties[name]
        assert prop.name == name
        assert prop.codec_id == codec_id, name
        assert prop.nullable is nullable, name
        assert prop.new_default == default, name
        if default is Unset.VALUE:
            assert name not in catalogue.new_props(type_id)


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_widget_slots_match_tdd_table(type_id: str) -> None:
    spec = catalogue.widget(type_id)
    expected = WIDGET_SLOTS[type_id]
    assert set(spec.slots) == set(expected)
    for name, (minimum, maximum) in expected.items():
        slot = spec.slots[name]
        assert slot.name == name
        assert slot.minimum == minimum
        assert slot.maximum == maximum


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_widget_events_match_tdd_table(type_id: str) -> None:
    spec = catalogue.widget(type_id)
    assert spec.events == WIDGET_EVENTS[type_id]


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_constructor_is_ft_symbol(type_id: str) -> None:
    spec = catalogue.widget(type_id)
    assert spec.constructor.path == (type_id,)
    assert spec.type_id == type_id


#: Widgets whose Flet constructor rejects a shared property.
SHARED_EXCEPTIONS: dict[str, frozenset[str]] = {"Divider": frozenset({"width"})}


def test_shared_properties_present_on_every_widget() -> None:
    for type_id in WIDGET_ORDER:
        props = catalogue.widget(type_id).properties
        omitted = SHARED_EXCEPTIONS.get(type_id, frozenset())
        for name in ("width", "height", "expand", "disabled", "visible"):
            if name in omitted:
                assert name not in props, f"{type_id} still exposes unsupported {name}"
                continue
            assert name in props, f"{type_id} missing shared {name}"
