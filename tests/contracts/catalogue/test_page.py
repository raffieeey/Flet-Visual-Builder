"""PageSpec matches TDD v2 §2.4.5."""

from __future__ import annotations

from flet_visual_builder.catalogue import catalogue
from flet_visual_builder.contracts import Unset


def test_page_keys_and_defaults() -> None:
    expected = {
        "title": ("string", "Untitled", False),
        "padding": ("padding", 24, False),
        "scroll": ("enum.ScrollMode", "AUTO", True),
        "theme_mode": ("enum.ThemeMode", "LIGHT", False),
        "theme": ("theme", {"color_scheme_seed": "INDIGO"}, True),
        "appbar": ("appbar", None, True),
    }
    # Additive page properties are permitted; the original contract stays fixed.
    assert set(expected) <= set(catalogue.page_properties)
    assert set(catalogue.page_properties) - set(expected) <= {
        "bgcolor",
        "adaptive",
        "rtl",
        "horizontal_alignment",
    }
    for name, (codec_id, default, nullable) in expected.items():
        prop = catalogue.page_properties[name]
        assert prop.codec_id == codec_id
        assert prop.new_default == default
        assert prop.nullable is nullable
        assert prop.new_default is not Unset.VALUE


def test_new_page_materializes_null_appbar() -> None:
    page = catalogue.new_page()
    assert page["title"] == "Untitled"
    assert page["padding"] == 24
    assert page["scroll"] == "AUTO"
    assert page["theme_mode"] == "LIGHT"
    assert page["theme"] == {"color_scheme_seed": "INDIGO"}
    assert page["appbar"] is None


def test_page_theme_and_appbar_shapes() -> None:
    assert catalogue.validate_page({"theme": None}) == ()
    assert catalogue.validate_page({"theme": {"color_scheme_seed": "INDIGO"}}) == ()
    bad = catalogue.validate_page({"theme": {"color_scheme_seed": "not-a-color"}})
    assert bad
    assert catalogue.validate_page({"appbar": None}) == ()
    assert catalogue.validate_page({"appbar": {"title": "Hello"}}) == ()
    extra = catalogue.validate_page({"appbar": {"title": "Hello", "color": "INDIGO"}})
    assert extra
