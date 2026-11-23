"""Unknown persisted keys reject with Severity.ERROR naming the key."""
from __future__ import annotations

import pytest

from flet_visual_builder.catalogue import CODE_UNKNOWN_PROPERTY, catalogue
from flet_visual_builder.contracts import Severity

from tests.contracts.catalogue.expected import WIDGET_ORDER


@pytest.mark.parametrize("type_id", WIDGET_ORDER)
def test_undeclared_property_is_error_naming_the_key(type_id: str) -> None:
    key = "not_a_catalogue_key"
    diags = catalogue.validate_props(type_id, {key: 1})
    errors = [d for d in diags if d.severity is Severity.ERROR]
    assert errors, f"{type_id} accepted unknown key"
    assert any(key in d.message for d in errors)
    assert any(d.code == CODE_UNKNOWN_PROPERTY for d in errors)
    assert any(key in d.path for d in errors)


def test_unknown_page_property_is_error_naming_the_key() -> None:
    key = "clipboard"
    diags = catalogue.validate_page({key: "x"})
    assert any(
        d.severity is Severity.ERROR and key in d.message for d in diags
    )
