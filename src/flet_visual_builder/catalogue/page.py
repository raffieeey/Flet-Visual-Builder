"""PageSpec for catalogue version 1 (TDD v2 §2.4.5)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from flet_visual_builder.contracts import PropertySpec, Unset


def _p(
    name: str,
    codec_id: str,
    new_default: object,
    *,
    nullable: bool,
    required: bool = False,
) -> PropertySpec:
    return PropertySpec(
        name=name,
        codec_id=codec_id,
        new_default=new_default,  # type: ignore[arg-type]
        nullable=nullable,
        required=required,
    )


PAGE_PROPERTIES: dict[str, PropertySpec] = {
    spec.name: spec
    for spec in (
        _p("title", "string", "Untitled", nullable=False),
        _p("padding", "padding", 24, nullable=False),
        _p("scroll", "enum.ScrollMode", "AUTO", nullable=True),
        _p("theme_mode", "enum.ThemeMode", "LIGHT", nullable=False),
        _p(
            "theme",
            "theme",
            {"color_scheme_seed": "INDIGO"},
            nullable=True,
        ),
        _p("appbar", "appbar", None, nullable=True),
        _p("bgcolor", "color", Unset.VALUE, nullable=True),
        _p("adaptive", "boolean", Unset.VALUE, nullable=True),
        _p("rtl", "boolean", Unset.VALUE, nullable=False),
        _p(
            "horizontal_alignment",
            "enum.CrossAxisAlignment",
            Unset.VALUE,
            nullable=False,
        ),
    )
}


@dataclass(frozen=True, slots=True)
class PageSpec:
    properties: Mapping[str, PropertySpec]


PAGE_SPEC = PageSpec(properties=PAGE_PROPERTIES)
