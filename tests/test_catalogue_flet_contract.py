"""The catalogue must describe real Flet constructors.

A widget spec that names a property Flet does not accept produces code that
looks valid, passes lowering, and then crashes in the exported app (or refuses
to render). This test is the contract between the catalogue and the pinned Flet
release, so an unsupported property fails here instead of in a user's app.
"""

from __future__ import annotations

import dataclasses
import inspect

import flet as ft
import pytest

from flet_visual_builder.catalogue import catalogue


def accepted_arguments(control_type: type) -> set[str]:
    if dataclasses.is_dataclass(control_type):
        return {field.name for field in dataclasses.fields(control_type)}
    return set(inspect.signature(control_type.__init__).parameters) - {"self"}


@pytest.mark.parametrize("type_id", sorted(catalogue.widgets))
def test_widget_properties_exist_on_the_flet_constructor(type_id: str) -> None:
    control_type = getattr(ft, type_id, None)
    assert control_type is not None, f"{type_id} is not a Flet control"
    accepted = accepted_arguments(control_type)
    spec = catalogue.widgets[type_id]
    unsupported = sorted(set(spec.properties) - accepted)
    assert unsupported == [], (
        f"{type_id} exposes properties Flet does not accept: {unsupported}. "
        "Set omit_shared= on the spec or drop the property."
    )


@pytest.mark.parametrize("type_id", sorted(catalogue.widgets))
def test_widget_slots_exist_on_the_flet_constructor(type_id: str) -> None:
    accepted = accepted_arguments(getattr(ft, type_id))
    spec = catalogue.widgets[type_id]
    unsupported = sorted(set(spec.slots) - accepted)
    assert (
        unsupported == []
    ), f"{type_id} declares slots Flet does not accept: {unsupported}"


# Page properties are a document vocabulary projected onto a Pagelet host
# (`runtime._project_page`), not raw ft.Page keyword arguments, so they are
# covered by the page projection tests rather than this constructor audit.
