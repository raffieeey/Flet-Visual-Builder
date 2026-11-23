"""ValueCodec implementations. No Flet imports — only symbolic ValueExpr output."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeGuard
from urllib.parse import urlparse

from flet_visual_builder.catalogue.enum_manifest import (
    ALIGNMENT,
    BOX_FIT,
    COLORS,
    CONTROL_STATE,
    CROSS_AXIS_ALIGNMENT,
    FONT_WEIGHT,
    ICONS,
    MAIN_AXIS_ALIGNMENT,
    SCROLL_MODE,
    TEXT_ALIGN,
    THEME_MODE,
)
from flet_visual_builder.contracts import (
    AssetValue,
    CallValue,
    Diagnostic,
    JsonValue,
    LiteralValue,
    MappingValue,
    Severity,
    SymbolRef,
    ValueCodec,
    ValueExpr,
)

# ---------------------------------------------------------------------------
# Diagnostic helpers
# ---------------------------------------------------------------------------

CODE_INVALID_TYPE = "CATALOGUE_INVALID_TYPE"
CODE_INVALID_VALUE = "CATALOGUE_INVALID_VALUE"
CODE_BORDER_SHAPE = "CATALOGUE_BORDER_SHAPE"
CODE_INPUT_BORDER = "CATALOGUE_INPUT_BORDER"


def _error(
    code: str, message: str, path: tuple[str | int, ...] = ()
) -> Diagnostic:
    return Diagnostic(code=code, message=message, severity=Severity.ERROR, path=path)


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_finite_number(value: object) -> bool:
    return _is_number(value) and math.isfinite(value)  # type: ignore[arg-type]


def _is_mapping(value: object) -> TypeGuard[Mapping[str, JsonValue]]:
    return isinstance(value, Mapping) and not isinstance(value, (str, bytes))


def _call(
    path: tuple[str, ...],
    args: tuple[ValueExpr, ...] = (),
    kwargs: Mapping[str, ValueExpr] | None = None,
) -> CallValue:
    return CallValue(constructor=SymbolRef(path), args=args, kwargs=kwargs or {})


# ---------------------------------------------------------------------------
# Scalar codecs
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StringCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if not isinstance(value, str):
            return (_error(CODE_INVALID_TYPE, "expected string"),)
        return ()

    def lower(self, value: JsonValue) -> ValueExpr:
        assert isinstance(value, str)
        return LiteralValue(value)


@dataclass(frozen=True, slots=True)
class BooleanCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if not isinstance(value, bool):
            return (_error(CODE_INVALID_TYPE, "expected boolean"),)
        return ()

    def lower(self, value: JsonValue) -> ValueExpr:
        assert isinstance(value, bool)
        return LiteralValue(value)


@dataclass(frozen=True, slots=True)
class NumberCodec:
    """Finite number. Booleans are not numbers (TDD §2.4.1 N)."""

    minimum: float | None = None
    maximum: float | None = None
    integer: bool = False

    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if not _is_finite_number(value):
            return (_error(CODE_INVALID_TYPE, "expected finite number"),)
        number = float(value)  # type: ignore[arg-type]
        if self.integer and not isinstance(value, int):
            return (_error(CODE_INVALID_TYPE, "expected integer"),)
        if self.minimum is not None and number < self.minimum:
            return (
                _error(
                    CODE_INVALID_VALUE,
                    f"expected number >= {self.minimum}",
                ),
            )
        if self.maximum is not None and number > self.maximum:
            return (
                _error(
                    CODE_INVALID_VALUE,
                    f"expected number <= {self.maximum}",
                ),
            )
        return ()

    def lower(self, value: JsonValue) -> ValueExpr:
        assert _is_finite_number(value)
        return LiteralValue(value)  # type: ignore[arg-type]


@dataclass(frozen=True, slots=True)
class ExpandCodec:
    """boolean, positive integer, or null (null handled by PropertySpec.nullable)."""

    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if isinstance(value, bool):
            return ()
        if isinstance(value, int) and not isinstance(value, bool) and value >= 1:
            return ()
        return (
            _error(
                CODE_INVALID_TYPE,
                "expected boolean or positive integer",
            ),
        )

    def lower(self, value: JsonValue) -> ValueExpr:
        return LiteralValue(value)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Enum / color / icon
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EnumCodec:
    family: str
    members: frozenset[str]
    # ScrollMode only: legacy "none" is null/omission, not a member.
    none_is_null: bool = False

    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if self.none_is_null and value == "none":
            return ()
        if isinstance(value, str) and value in self.members:
            return ()
        return (
            _error(
                CODE_INVALID_VALUE,
                f"expected {self.family} member "
                f"({', '.join(sorted(self.members))})",
            ),
        )

    def lower(self, value: JsonValue) -> ValueExpr:
        if self.none_is_null and value == "none":
            return LiteralValue(None)
        assert isinstance(value, str)
        return SymbolRef((self.family, value))


_HEX_LITERAL = re.compile(
    r"^(?:#(?:[0-9A-Fa-f]{3,4}|[0-9A-Fa-f]{6}|[0-9A-Fa-f]{8})|0x[0-9A-Fa-f]{6,8})$"
)


@dataclass(frozen=True, slots=True)
class ColorCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if isinstance(value, str) and (value in COLORS or _HEX_LITERAL.fullmatch(value)):
            return ()
        return (
            _error(
                CODE_INVALID_VALUE,
                "expected allowlisted Colors member or hex color literal",
            ),
        )

    def lower(self, value: JsonValue) -> ValueExpr:
        assert isinstance(value, str)
        if value in COLORS:
            return SymbolRef(("Colors", value))
        return LiteralValue(value)


@dataclass(frozen=True, slots=True)
class IconCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if isinstance(value, str) and value in ICONS:
            return ()
        return (
            _error(
                CODE_INVALID_VALUE,
                "expected allowlisted Icons member",
            ),
        )

    def lower(self, value: JsonValue) -> ValueExpr:
        assert isinstance(value, str)
        return SymbolRef(("Icons", value))


# ---------------------------------------------------------------------------
# Compound shapes
# ---------------------------------------------------------------------------

_INSETS_KEYS = ("left", "top", "right", "bottom")
_RADIUS_KEYS = ("top_left", "top_right", "bottom_left", "bottom_right")
_SIDE_KEYS = ("left", "top", "right", "bottom")
_BORDER_SIDE_KEYS = frozenset({"width", "color"})
def _validate_nonneg_number(value: JsonValue, path: tuple[str | int, ...]) -> tuple[Diagnostic, ...]:
    if not _is_finite_number(value):
        return (_error(CODE_INVALID_TYPE, "expected finite nonnegative number", path),)
    if float(value) < 0:  # type: ignore[arg-type]
        return (_error(CODE_INVALID_VALUE, "expected nonnegative number", path),)
    return ()


def _lower_nonneg(value: JsonValue) -> LiteralValue:
    assert _is_finite_number(value)
    return LiteralValue(value)  # type: ignore[arg-type]


def _validate_insets(
    value: JsonValue, *, constructor: str
) -> tuple[Diagnostic, ...]:
    if _is_finite_number(value):
        if float(value) < 0:  # type: ignore[arg-type]
            return (_error(CODE_INVALID_VALUE, "expected nonnegative number"),)
        return ()
    if not _is_mapping(value):
        return (
            _error(
                CODE_INVALID_TYPE,
                f"expected uniform scalar or {constructor} record",
            ),
        )
    mapping = value  # type: ignore[assignment]
    extras = [k for k in mapping if k not in _INSETS_KEYS]
    if extras:
        return (
            _error(
                CODE_INVALID_VALUE,
                f"unknown {constructor} field {extras[0]!r}",
            ),
        )
    if not mapping:
        return (_error(CODE_INVALID_VALUE, f"empty {constructor} record"),)
    diags: list[Diagnostic] = []
    for key in _INSETS_KEYS:
        if key not in mapping:
            continue
        diags.extend(_validate_nonneg_number(mapping[key], (key,)))
    return tuple(diags)


def _lower_insets(value: JsonValue, *, constructor: str) -> ValueExpr:
    if _is_finite_number(value):
        return _call((constructor, "all"), args=(_lower_nonneg(value),))
    assert _is_mapping(value)
    kwargs = {
        key: _lower_nonneg(value[key])  # type: ignore[index]
        for key in _INSETS_KEYS
        if key in value  # type: ignore[operator]
    }
    return _call((constructor,), kwargs=kwargs)


@dataclass(frozen=True, slots=True)
class PaddingCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        return _validate_insets(value, constructor="Padding")

    def lower(self, value: JsonValue) -> ValueExpr:
        return _lower_insets(value, constructor="Padding")


@dataclass(frozen=True, slots=True)
class MarginCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        return _validate_insets(value, constructor="Margin")

    def lower(self, value: JsonValue) -> ValueExpr:
        return _lower_insets(value, constructor="Margin")


@dataclass(frozen=True, slots=True)
class RadiusCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if _is_finite_number(value):
            if float(value) < 0:  # type: ignore[arg-type]
                return (_error(CODE_INVALID_VALUE, "expected nonnegative number"),)
            return ()
        if not _is_mapping(value):
            return (
                _error(
                    CODE_INVALID_TYPE,
                    "expected uniform scalar or radius record",
                ),
            )
        mapping = value  # type: ignore[assignment]
        extras = [k for k in mapping if k not in _RADIUS_KEYS]
        if extras:
            return (
                _error(CODE_INVALID_VALUE, f"unknown radius field {extras[0]!r}"),
            )
        if not mapping:
            return (_error(CODE_INVALID_VALUE, "empty radius record"),)
        diags: list[Diagnostic] = []
        for key in _RADIUS_KEYS:
            if key in mapping:
                diags.extend(_validate_nonneg_number(mapping[key], (key,)))
        return tuple(diags)

    def lower(self, value: JsonValue) -> ValueExpr:
        if _is_finite_number(value):
            return _call(("BorderRadius", "all"), args=(_lower_nonneg(value),))
        assert _is_mapping(value)
        kwargs = {
            key: _lower_nonneg(value[key])  # type: ignore[index]
            for key in _RADIUS_KEYS
            if key in value  # type: ignore[operator]
        }
        return _call(("BorderRadius",), kwargs=kwargs)


_COLOR = ColorCodec()
_RADIUS = RadiusCodec()
_NONNEG = NumberCodec(minimum=0.0)


def _validate_border_side(
    value: JsonValue, path: tuple[str | int, ...]
) -> tuple[Diagnostic, ...]:
    if not _is_mapping(value):
        return (_error(CODE_INVALID_TYPE, "expected border side record", path),)
    mapping = value  # type: ignore[assignment]
    extras = [k for k in mapping if k not in _BORDER_SIDE_KEYS]
    if extras:
        return (
            _error(
                CODE_INVALID_VALUE,
                f"unknown border side field {extras[0]!r}",
                path,
            ),
        )
    if not mapping:
        return (_error(CODE_INVALID_VALUE, "empty border side record", path),)
    diags: list[Diagnostic] = []
    if "width" in mapping:
        for d in _NONNEG.validate(mapping["width"]):
            diags.append(
                Diagnostic(
                    code=d.code,
                    message=d.message,
                    severity=d.severity,
                    path=path + ("width",),
                )
            )
    if "color" in mapping:
        for d in _COLOR.validate(mapping["color"]):
            diags.append(
                Diagnostic(
                    code=d.code,
                    message=d.message,
                    severity=d.severity,
                    path=path + ("color",),
                )
            )
    return tuple(diags)


def _lower_border_side(value: JsonValue) -> ValueExpr:
    assert _is_mapping(value)
    kwargs: dict[str, ValueExpr] = {}
    if "width" in value:
        kwargs["width"] = _NONNEG.lower(value["width"])  # type: ignore[index]
    if "color" in value:
        kwargs["color"] = _COLOR.lower(value["color"])  # type: ignore[index]
    return _call(("BorderSide",), kwargs=kwargs)


@dataclass(frozen=True, slots=True)
class BorderCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if not _is_mapping(value):
            return (_error(CODE_INVALID_TYPE, "expected border record"),)
        mapping = value  # type: ignore[assignment]
        has_all = "all" in mapping
        side_keys = [k for k in _SIDE_KEYS if k in mapping]
        extras = [k for k in mapping if k not in ("all", *_SIDE_KEYS)]
        if extras:
            return (
                _error(
                    CODE_BORDER_SHAPE,
                    f"unknown border field {extras[0]!r}",
                ),
            )
        if has_all and side_keys:
            return (
                _error(
                    CODE_BORDER_SHAPE,
                    "border accepts either all or explicit side records, never both",
                ),
            )
        if not has_all and not side_keys:
            return (
                _error(
                    CODE_BORDER_SHAPE,
                    "border requires all or at least one side record",
                ),
            )
        if has_all:
            return _validate_border_side(mapping["all"], ("all",))
        diags: list[Diagnostic] = []
        for key in side_keys:
            diags.extend(_validate_border_side(mapping[key], (key,)))
        return tuple(diags)

    def lower(self, value: JsonValue) -> ValueExpr:
        assert _is_mapping(value)
        if "all" in value:
            side = value["all"]  # type: ignore[index]
            assert _is_mapping(side)
            kwargs: dict[str, ValueExpr] = {}
            if "width" in side:
                kwargs["width"] = _NONNEG.lower(side["width"])
            if "color" in side:
                kwargs["color"] = _COLOR.lower(side["color"])
            return _call(("Border", "all"), kwargs=kwargs)
        kwargs = {
            key: _lower_border_side(value[key])  # type: ignore[index]
            for key in _SIDE_KEYS
            if key in value  # type: ignore[operator]
        }
        return _call(("Border", "only"), kwargs=kwargs)


_OUTLINE_FIELDS = frozenset({"kind", "side", "border_radius", "gap_padding"})
_UNDERLINE_FIELDS = frozenset({"kind", "side", "border_radius"})
_NONE_FIELDS = frozenset({"kind"})


def _validate_input_border_record(
    value: JsonValue, path: tuple[str | int, ...] = ()
) -> tuple[Diagnostic, ...]:
    if isinstance(value, str):
        return (
            _error(
                CODE_INPUT_BORDER,
                "deprecated input-border enum strings are not accepted; "
                "use {\"kind\": \"outline\"|\"underline\"|\"none\"}",
                path,
            ),
        )
    if not _is_mapping(value):
        return (_error(CODE_INVALID_TYPE, "expected input-border record", path),)
    mapping = value  # type: ignore[assignment]
    kind = mapping.get("kind")
    if kind not in {"outline", "underline", "none"}:
        return (
            _error(
                CODE_INPUT_BORDER,
                "input-border kind must be outline, underline, or none",
                path + ("kind",) if path or "kind" in mapping else path,
            ),
        )
    allowed = {
        "outline": _OUTLINE_FIELDS,
        "underline": _UNDERLINE_FIELDS,
        "none": _NONE_FIELDS,
    }[kind]
    extras = [k for k in mapping if k not in allowed]
    if extras:
        return (
            _error(
                CODE_INPUT_BORDER,
                f"input-border kind {kind!r} does not accept field {extras[0]!r}",
                path + (extras[0],),
            ),
        )
    diags: list[Diagnostic] = []
    if "side" in mapping:
        diags.extend(_validate_border_side(mapping["side"], path + ("side",)))
    if "border_radius" in mapping:
        for d in _RADIUS.validate(mapping["border_radius"]):
            diags.append(
                Diagnostic(
                    code=d.code,
                    message=d.message,
                    severity=d.severity,
                    path=path + ("border_radius",) + d.path,
                )
            )
    if "gap_padding" in mapping:
        diags.extend(
            _validate_nonneg_number(mapping["gap_padding"], path + ("gap_padding",))
        )
    return tuple(diags)


def _lower_input_border_record(value: JsonValue) -> ValueExpr:
    assert _is_mapping(value)
    kind = value["kind"]  # type: ignore[index]
    if kind == "none":
        return _call(("NoInputBorder",))
    kwargs: dict[str, ValueExpr] = {}
    if "side" in value:
        kwargs["side"] = _lower_border_side(value["side"])  # type: ignore[index]
    if "border_radius" in value:
        kwargs["border_radius"] = _RADIUS.lower(value["border_radius"])  # type: ignore[index]
    if kind == "outline":
        if "gap_padding" in value:
            kwargs["gap_padding"] = _lower_nonneg(value["gap_padding"])  # type: ignore[index]
        return _call(("OutlineInputBorder",), kwargs=kwargs)
    return _call(("UnderlineInputBorder",), kwargs=kwargs)


@dataclass(frozen=True, slots=True)
class InputBorderCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if isinstance(value, str):
            return _validate_input_border_record(value)
        if not _is_mapping(value):
            return (_error(CODE_INVALID_TYPE, "expected input-border record or state map"),)
        mapping = value  # type: ignore[assignment]
        if "kind" in mapping:
            return _validate_input_border_record(mapping)
        if mapping and all(k in CONTROL_STATE for k in mapping):
            diags: list[Diagnostic] = []
            for key, inner in mapping.items():
                diags.extend(_validate_input_border_record(inner, (key,)))
            return tuple(diags)
        return (
            _error(
                CODE_INPUT_BORDER,
                "expected {\"kind\": ...} or a ControlState map of input-border records",
            ),
        )

    def lower(self, value: JsonValue) -> ValueExpr:
        assert _is_mapping(value)
        if "kind" in value:
            return _lower_input_border_record(value)
        items = tuple(
            (
                SymbolRef(("ControlState", key)),
                _lower_input_border_record(inner),
            )
            for key, inner in value.items()  # type: ignore[union-attr]
        )
        return MappingValue(items=items)


BUILTIN_IMAGE_PLACEHOLDER: dict[str, str] = {"kind": "builtin"}


def _https_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


@dataclass(frozen=True, slots=True)
class ImageSourceCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if isinstance(value, str):
            if _https_url(value):
                return ()
            return (_error(CODE_INVALID_VALUE, "image URL must be https"),)
        if not _is_mapping(value):
            return (
                _error(
                    CODE_INVALID_TYPE,
                    "expected image source record or https URL",
                ),
            )
        mapping = value  # type: ignore[assignment]
        kind = mapping.get("kind")
        if kind == "builtin":
            extras = [k for k in mapping if k != "kind"]
            if extras:
                return (
                    _error(
                        CODE_INVALID_VALUE,
                        f"builtin image source does not accept field {extras[0]!r}",
                    ),
                )
            return ()
        if kind == "asset":
            asset_id = mapping.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id:
                return (_error(CODE_INVALID_VALUE, "asset image source requires asset_id"),)
            extras = [k for k in mapping if k not in {"kind", "asset_id"}]
            if extras:
                return (
                    _error(
                        CODE_INVALID_VALUE,
                        f"asset image source does not accept field {extras[0]!r}",
                    ),
                )
            return ()
        if kind == "url":
            url = mapping.get("url")
            if not isinstance(url, str) or not _https_url(url):
                return (_error(CODE_INVALID_VALUE, "url image source requires an https URL"),)
            extras = [k for k in mapping if k not in {"kind", "url"}]
            if extras:
                return (
                    _error(
                        CODE_INVALID_VALUE,
                        f"url image source does not accept field {extras[0]!r}",
                    ),
                )
            return ()
        return (
            _error(
                CODE_INVALID_VALUE,
                "image source kind must be builtin, asset, or url",
            ),
        )

    def lower(self, value: JsonValue) -> ValueExpr:
        if isinstance(value, str):
            return LiteralValue(value)
        assert _is_mapping(value)
        kind = value["kind"]  # type: ignore[index]
        if kind == "builtin":
            return LiteralValue("builtin")
        if kind == "asset":
            return AssetValue(asset_id=str(value["asset_id"]))  # type: ignore[index]
        return LiteralValue(str(value["url"]))  # type: ignore[index]


@dataclass(frozen=True, slots=True)
class ThemeCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if not _is_mapping(value):
            return (_error(CODE_INVALID_TYPE, "expected theme record"),)
        mapping = value  # type: ignore[assignment]
        extras = [k for k in mapping if k != "color_scheme_seed"]
        if extras:
            return (
                _error(CODE_INVALID_VALUE, f"unknown theme field {extras[0]!r}"),
            )
        if "color_scheme_seed" not in mapping:
            return (_error(CODE_INVALID_VALUE, "theme requires color_scheme_seed"),)
        return _COLOR.validate(mapping["color_scheme_seed"])

    def lower(self, value: JsonValue) -> ValueExpr:
        assert _is_mapping(value)
        return _call(
            ("Theme",),
            kwargs={"color_scheme_seed": _COLOR.lower(value["color_scheme_seed"])},  # type: ignore[index]
        )


@dataclass(frozen=True, slots=True)
class AppBarCodec:
    def validate(self, value: JsonValue) -> tuple[Diagnostic, ...]:
        if not _is_mapping(value):
            return (_error(CODE_INVALID_TYPE, "expected appbar record"),)
        mapping = value  # type: ignore[assignment]
        extras = [k for k in mapping if k != "title"]
        if extras:
            return (
                _error(CODE_INVALID_VALUE, f"unknown appbar field {extras[0]!r}"),
            )
        if "title" not in mapping or not isinstance(mapping["title"], str):
            return (_error(CODE_INVALID_VALUE, "appbar requires string title"),)
        return ()

    def lower(self, value: JsonValue) -> ValueExpr:
        assert _is_mapping(value)
        title = LiteralValue(value["title"])  # type: ignore[arg-type, index]
        return _call(
            ("AppBar",),
            kwargs={"title": _call(("Text",), kwargs={"value": title})},
        )


CODECS: dict[str, ValueCodec] = {
    "string": StringCodec(),
    "boolean": BooleanCodec(),
    "nonneg_number": NumberCodec(minimum=0.0),
    "unit_interval": NumberCodec(minimum=0.0, maximum=1.0),
    "expand": ExpandCodec(),
    "color": ColorCodec(),
    "icon": IconCodec(),
    "enum.MainAxisAlignment": EnumCodec("MainAxisAlignment", MAIN_AXIS_ALIGNMENT),
    "enum.CrossAxisAlignment": EnumCodec("CrossAxisAlignment", CROSS_AXIS_ALIGNMENT),
    "enum.TextAlign": EnumCodec("TextAlign", TEXT_ALIGN),
    "enum.FontWeight": EnumCodec("FontWeight", FONT_WEIGHT),
    "enum.Alignment": EnumCodec("Alignment", ALIGNMENT),
    "enum.BoxFit": EnumCodec("BoxFit", BOX_FIT),
    "enum.ScrollMode": EnumCodec("ScrollMode", SCROLL_MODE, none_is_null=True),
    "enum.ThemeMode": EnumCodec("ThemeMode", THEME_MODE),
    "padding": PaddingCodec(),
    "margin": MarginCodec(),
    "radius": RadiusCodec(),
    "border": BorderCodec(),
    "input_border": InputBorderCodec(),
    "image_source": ImageSourceCodec(),
    "theme": ThemeCodec(),
    "appbar": AppBarCodec(),
}
