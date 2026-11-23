"""Typed property controls. Values sent to the workspace use catalogue JSON shapes."""

from __future__ import annotations

import inspect
import math
from collections.abc import Mapping
from typing import Callable

import flet as ft

from flet_visual_builder.contracts import PropertySpec
from flet_visual_builder.ui.theme import F_BODY, SM, T, faint


class Editor:
    def __init__(self, ws, node_id, spec: PropertySpec, value, changed: Callable):
        self.ws, self.node_id, self.spec, self.value = ws, node_id, spec, value
        self.changed = changed
        self.fields: list[ft.TextField] = []
        self.control = self._build()

    def send(self, value, field=None):
        errors = self.ws.catalogue.validate_value(self.spec, value)
        if (
            self.spec.codec_id == "icon"
            and isinstance(value, str)
            and not hasattr(ft.Icons, value)
        ):
            errors = ("Unknown Flet icon",)
        if errors:
            if field is not None:
                field.error = getattr(errors[0], "message", str(errors[0]))
            return False
        if field is not None:
            field.error = None
        result = self.ws.set_property(self.node_id, self.spec.name, value)
        if result.status.value == "rejected":
            if field is not None:
                field.error = (
                    result.diagnostics[0].message
                    if result.diagnostics
                    else "Change rejected"
                )
            return False
        self.value = value
        self.changed()
        return True

    def unset(self):
        result = self.ws.unset_property(self.node_id, self.spec.name)
        if result.status.value != "rejected":
            self.value = None
            self.changed()
            return True
        return False

    def field(self, value, callback, *, tag=None, label=None, multiline=False):
        field = ft.TextField(
            value="" if value is None else str(value),
            dense=True,
            text_size=F_BODY,
            label=label,
            multiline=multiline,
            min_lines=2 if multiline else None,
            data=(
                ("editor", self.spec.name)
                if tag is None
                else ("part", self.spec.name, tag)
            ),
        )
        field.on_change = lambda e: callback(e.control)
        field.on_focus = lambda e: self.ws.set_text_focus(True)
        field.on_blur = lambda e: self.ws.set_text_focus(False)
        self.fields.append(field)
        return field

    def numeric(
        self,
        value,
        callback,
        *,
        tag=None,
        label=None,
        maximum=None,
        integer=False,
        allow_empty=True,
    ):
        def change(field):
            raw = field.value.strip()
            if not raw:
                field.error = None
                if allow_empty:
                    callback(None, field)
                return
            try:
                number = float(raw)
                if (
                    not math.isfinite(number)
                    or number < 0
                    or (maximum is not None and number > maximum)
                    or (integer and not number.is_integer())
                ):
                    raise ValueError
            except ValueError:
                field.error = (
                    f"Enter {'a whole number' if integer else 'a number'} from 0"
                    + (f" to {maximum}" if maximum is not None else " or greater")
                )
                return
            callback(int(number) if number.is_integer() else number, field)

        return self.field(value, change, tag=tag, label=label)

    def scalar_number(self, maximum=None, integer=False):
        value = self.value
        if self.spec.codec_id == "expand" and isinstance(value, bool):
            value = 1 if value else 0

        def commit(number, field):
            if number is None:
                self.unset()
            else:
                self.send(
                    False if self.spec.codec_id == "expand" and number == 0 else number,
                    field,
                )

        return self.numeric(value, commit, maximum=maximum, integer=integer)

    def string(self):
        return self.field(
            self.value,
            lambda f: self.send(f.value, f),
            multiline=isinstance(self.value, str)
            and (len(self.value) > 80 or "\n" in self.value),
        )

    def boolean(self):
        value = self.value
        if value is None and self.node_id is not None:
            node = self.ws.node(self.node_id)
            constructor = getattr(ft, node.type_id, None) if node else None
            if constructor is not None:
                parameter = inspect.signature(constructor).parameters.get(
                    self.spec.name
                )
                if parameter and isinstance(parameter.default, bool):
                    value = parameter.default
        return ft.Switch(
            value=bool(value),
            data=("editor", self.spec.name),
            on_change=lambda e: self.send(e.control.value),
        )

    def enum(self):
        codec = self.ws.catalogue.codecs[self.spec.codec_id]
        members = sorted(codec.members)
        if getattr(codec, "none_is_null", False):
            members.append("none")
        return ft.Dropdown(
            value=self.value,
            dense=True,
            text_size=F_BODY,
            data=("editor", self.spec.name),
            options=[ft.DropdownOption(key=m, text=m) for m in members],
            on_select=lambda e: self.send(e.control.value),
        )

    def color(self):
        field = self.field(self.value, lambda f: self.send(f.value, f))
        swatches = []
        for name, color in (
            ("accent", T.accent),
            ("text", T.text),
            ("success", T.success),
            ("warning", T.warning),
            ("danger", T.danger),
        ):

            def choose(e, color=color):
                if self.send(color, field):
                    field.value = color

            swatches.append(
                ft.Container(
                    width=20,
                    height=20,
                    bgcolor=color,
                    border_radius=4,
                    tooltip=name,
                    on_click=choose,
                )
            )

        def clear(e):
            if self.unset():
                field.value = ""
                field.error = None

        swatches.append(ft.TextButton(content="Clear", on_click=clear))
        return ft.Column(
            controls=[field, ft.Row(controls=swatches, spacing=SM)],
            tight=True,
            spacing=2,
        )

    def icon(self):
        field = self.field(
            self.value, lambda f: self.send(f.value, f), label="Icon name"
        )
        names = [
            n
            for n in ("HOME", "SEARCH", "STAR", "ADD", "SETTINGS", "FAVORITE", "DELETE")
            if hasattr(ft.Icons, n) and not self.ws.catalogue.codecs["icon"].validate(n)
        ]

        def select(e):
            if self.send(e.control.value, field):
                field.value = e.control.value

        choices = ft.Dropdown(
            label="Find an icon",
            editable=True,
            enable_filter=True,
            enable_search=True,
            options=[ft.DropdownOption(key=n, text=n) for n in names],
            on_select=select,
        )
        return ft.Column(controls=[field, choices], tight=True, spacing=2)

    def insets(self):
        keys = (
            ("top_left", "top_right", "bottom_left", "bottom_right")
            if self.spec.codec_id == "radius"
            else ("left", "top", "right", "bottom")
        )
        value = self.value
        uniform = (
            value
            if isinstance(value, (float, int)) and not isinstance(value, bool)
            else None
        )
        sides = []

        def set_uniform(n, field):
            ok = self.unset() if n is None else self.send(n, field)
            if ok:
                for side_field in sides:
                    side_field.value = "" if n is None else str(n)
                    side_field.error = None

        main = self.numeric(uniform, set_uniform, label="Uniform")
        for key in keys:
            current = value.get(key) if isinstance(value, Mapping) else uniform

            def set_side(n, field, key=key):
                current_value = self.value
                if isinstance(current_value, Mapping):
                    mapping = dict(current_value)
                elif isinstance(current_value, (int, float)) and not isinstance(
                    current_value, bool
                ):
                    mapping = {k: current_value for k in keys}
                else:
                    mapping = {}
                if n is None:
                    mapping.pop(key, None)
                else:
                    mapping[key] = n
                ok = self.send(mapping, field) if mapping else self.unset()
                if ok:
                    main.value = ""
                    main.error = None

            sides.append(
                self.numeric(current, set_side, tag=key, label=key.replace("_", " "))
            )
        return ft.Column(
            controls=[
                main,
                ft.ExpansionTile(
                    title="Individual sides", controls=sides, maintain_state=True
                ),
            ],
            tight=True,
            spacing=2,
        )

    def border(self):
        value = self.value if isinstance(self.value, Mapping) else {}
        side = value.get("all", {}) if isinstance(value.get("all", {}), Mapping) else {}
        note = faint("Editing applies one border to all sides.")

        def update(key, val, field):
            existing = self.value if isinstance(self.value, Mapping) else {}
            side_value = (
                dict(existing.get("all", {}))
                if isinstance(existing.get("all"), Mapping)
                else {}
            )
            if val is None or val == "":
                side_value.pop(key, None)
            else:
                side_value[key] = val
            if side_value:
                self.send({"all": side_value}, field)
            else:
                self.unset()

        width = self.numeric(
            side.get("width"),
            lambda n, f: update("width", n, f),
            tag="width",
            label="Width",
        )
        color = self.field(
            side.get("color"),
            lambda f: update("color", f.value, f),
            tag="color",
            label="Color",
        )
        return ft.Column(controls=[note, width, color], tight=True, spacing=2)

    def image_source(self):
        value = self.value
        url = value.get("url", "") if isinstance(value, Mapping) else value or ""
        note = "HTTPS URL; empty uses the default."
        if isinstance(value, Mapping) and value.get("kind") == "asset":
            note = (
                f"Current asset: {value.get('asset_id')}; entering a URL replaces it."
            )
        elif isinstance(value, Mapping) and value.get("kind") == "builtin":
            note = "Built-in placeholder; enter an HTTPS URL to replace it."

        def change(f):
            if f.value:
                self.send(f.value, f)
            else:
                self.send({"kind": "builtin"}, f)

        return ft.Column(
            controls=[self.field(url, change, label="HTTPS URL"), faint(note)],
            tight=True,
            spacing=2,
        )

    def composite(self):
        key = "title" if self.spec.codec_id == "appbar" else "color_scheme_seed"
        value = self.value.get(key, "") if isinstance(self.value, Mapping) else ""

        def change(f):
            self.send({key: f.value}, f)

        return self.field(value, change, label=key.replace("_", " "))

    def input_border(self):
        value = self.value if isinstance(self.value, Mapping) else {}
        # Preserve state maps unless the user explicitly chooses a replacement.
        if value and "kind" not in value:
            initial = None
            note = "State-specific border; choosing a kind replaces the state map."
        else:
            initial = value.get("kind")
            note = "Choose a border kind."

        def choose(e):
            existing = (
                self.value
                if isinstance(self.value, Mapping) and "kind" in self.value
                else {}
            )
            kind = e.control.value
            allowed = (
                {"kind", "side", "border_radius", "gap_padding"}
                if kind == "outline"
                else (
                    {"kind", "side", "border_radius"}
                    if kind == "underline"
                    else {"kind"}
                )
            )
            updated = {k: v for k, v in existing.items() if k in allowed}
            updated["kind"] = kind
            self.send(updated)

        drop = ft.Dropdown(
            value=initial,
            data=("editor", self.spec.name),
            dense=True,
            options=[
                ft.DropdownOption(key=k, text=k)
                for k in ("outline", "underline", "none")
            ],
            on_select=choose,
        )
        return ft.Column(controls=[drop, faint(note)], tight=True, spacing=2)

    def _build(self):
        codec = self.spec.codec_id
        if codec == "string":
            return self.string()
        if codec == "boolean":
            return self.boolean()
        if codec == "nonneg_number":
            return self.scalar_number()
        if codec == "unit_interval":
            return self.scalar_number(maximum=1)
        if codec == "expand":
            return self.scalar_number(maximum=10, integer=True)
        if codec.startswith("enum."):
            return self.enum()
        if codec == "color":
            return self.color()
        if codec == "icon":
            return self.icon()
        if codec in ("padding", "margin", "radius"):
            return self.insets()
        if codec == "border":
            return self.border()
        if codec == "image_source":
            return self.image_source()
        if codec in ("theme", "appbar"):
            return self.composite()
        if codec == "input_border":
            return self.input_border()
        return faint(f"Unsupported codec: {codec}")


def create_editor(ws, node_id, spec, value, changed):
    return Editor(ws, node_id, spec, value, changed)
