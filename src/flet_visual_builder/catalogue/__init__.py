"""Frozen sixteen-widget catalogue plus PageSpec (TDD v2 §2.4).

Runtime Flet imports are forbidden in this package. Codecs emit ValueExpr
symbols; engine/runtime.py is the only consumer that materializes Flet objects.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace

from flet_visual_builder.catalogue.codecs import BUILTIN_IMAGE_PLACEHOLDER, CODECS
from flet_visual_builder.catalogue.enum_manifest import COLORS, ICONS, TARGET_FLET
from flet_visual_builder.catalogue.page import PAGE_PROPERTIES, PAGE_SPEC, PageSpec
from flet_visual_builder.catalogue.widgets import WIDGET_ORDER, WIDGET_SPECS
from flet_visual_builder.contracts import (
    Diagnostic,
    JsonObject,
    JsonValue,
    LiteralValue,
    Node,
    NodeId,
    PropertySpec,
    Severity,
    Unset,
    ValueCodec,
    ValueExpr,
    WidgetSpec,
)

CODE_UNKNOWN_PROPERTY = "CATALOGUE_UNKNOWN_PROPERTY"
CODE_UNKNOWN_EVENT = "CATALOGUE_UNKNOWN_EVENT"
CODE_UNKNOWN_WIDGET = "CATALOGUE_UNKNOWN_WIDGET"
CODE_NULL_NOT_ALLOWED = "CATALOGUE_NULL_NOT_ALLOWED"
CODE_REQUIRED_PROPERTY = "CATALOGUE_REQUIRED_PROPERTY"
CODE_BUTTON_CONTENT = "CATALOGUE_BUTTON_CONTENT"
CODE_CHECKBOX_TRISTATE = "CATALOGUE_CHECKBOX_TRISTATE"
CODE_SCALAR_CONTROL_UNION = "CATALOGUE_SCALAR_CONTROL_UNION"
CODE_LAYOUT_CONSTRAINT = "CATALOGUE_LAYOUT_CONSTRAINT"
CODE_REMOTE_IMAGE = "CATALOGUE_REMOTE_IMAGE"

_BUTTON_TYPES = frozenset({"Button", "TextButton"})


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    node_id: NodeId | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
        node_id=node_id,
    )


def _warning(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    node_id: NodeId | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.WARNING,
        path=path,
        node_id=node_id,
    )


def _rebase(
    diagnostic: Diagnostic,
    path_prefix: tuple[str | int, ...],
    node_id: NodeId | None,
) -> Diagnostic:
    return replace(
        diagnostic,
        path=path_prefix + diagnostic.path,
        node_id=node_id if node_id is not None else diagnostic.node_id,
    )


def _is_https_image(value: JsonValue) -> bool:
    if isinstance(value, str) and value.startswith("https://"):
        return True
    if isinstance(value, Mapping) and value.get("kind") == "url":
        url = value.get("url")
        return isinstance(url, str) and url.startswith("https://")
    return False


def _visible_child(
    child_ids: tuple[NodeId, ...], nodes: Mapping[NodeId, Node] | None
) -> bool:
    if not child_ids:
        return False
    if nodes is None:
        return True
    for child_id in child_ids:
        child = nodes.get(child_id)
        if child is None:
            continue
        visible = child.props.get("visible", True)
        if visible is not False:
            return True
    return False


def _scroll_active(props: Mapping[str, JsonValue]) -> bool:
    if "scroll" not in props:
        return False
    value = props["scroll"]
    return value not in (None, "none")


@dataclass(frozen=True, slots=True)
class FrozenCatalogue:
    version: int
    target_flet: str
    widgets: Mapping[str, WidgetSpec]
    page_properties: Mapping[str, PropertySpec]
    codecs: Mapping[str, ValueCodec]

    def widget(self, type_id: str) -> WidgetSpec:
        try:
            return self.widgets[type_id]
        except KeyError as exc:
            raise KeyError(f"Unknown widget type {type_id!r}") from exc

    def new_props(self, type_id: str) -> dict[str, JsonValue]:
        """Materialize creation defaults. Unset (U) keys are omitted."""
        spec = self.widget(type_id)
        materialized: dict[str, JsonValue] = {}
        for name, prop in spec.properties.items():
            if prop.new_default is Unset.VALUE:
                continue
            materialized[name] = prop.new_default  # type: ignore[assignment]
        return materialized

    def new_page(self) -> dict[str, JsonValue]:
        materialized: dict[str, JsonValue] = {}
        for name, prop in self.page_properties.items():
            if prop.new_default is Unset.VALUE:
                continue
            materialized[name] = prop.new_default  # type: ignore[assignment]
        return materialized

    def validate_value(
        self, spec: PropertySpec, value: JsonValue
    ) -> tuple[Diagnostic, ...]:
        if value is None:
            if spec.nullable:
                return ()
            return (
                _error(
                    CODE_NULL_NOT_ALLOWED,
                    f"property {spec.name!r} does not allow null",
                    path=(spec.name,),
                ),
            )
        codec = self.codecs[spec.codec_id]
        return codec.validate(value)

    def lower_value(self, spec: PropertySpec, value: JsonValue) -> ValueExpr:
        if value is None:
            return LiteralValue(None)
        return self.codecs[spec.codec_id].lower(value)

    def validate_props(
        self,
        type_id: str,
        props: Mapping[str, JsonValue],
        *,
        node_id: NodeId | None = None,
    ) -> tuple[Diagnostic, ...]:
        if type_id not in self.widgets:
            return (
                _error(
                    CODE_UNKNOWN_WIDGET,
                    f"Unknown widget type {type_id!r}",
                    node_id=node_id,
                ),
            )
        spec = self.widgets[type_id]
        diags: list[Diagnostic] = []
        for key, value in props.items():
            if key not in spec.properties:
                diags.append(
                    _error(
                        CODE_UNKNOWN_PROPERTY,
                        f"Unknown property {key!r} on {type_id}",
                        path=("props", key),
                        node_id=node_id,
                    )
                )
                continue
            prop = spec.properties[key]
            for diagnostic in self.validate_value(prop, value):
                diags.append(_rebase(diagnostic, ("props", key), node_id))
        for name, prop in spec.properties.items():
            if prop.required and name not in props:
                diags.append(
                    _error(
                        CODE_REQUIRED_PROPERTY,
                        f"required property {name!r} is missing on {type_id}",
                        path=("props", name),
                        node_id=node_id,
                    )
                )
        return tuple(diags)

    def validate_page(self, page: JsonObject) -> tuple[Diagnostic, ...]:
        diags: list[Diagnostic] = []
        for key, value in page.items():
            if key not in self.page_properties:
                diags.append(
                    _error(
                        CODE_UNKNOWN_PROPERTY,
                        f"Unknown property {key!r} on PageSpec",
                        path=("page", key),
                    )
                )
                continue
            prop = self.page_properties[key]
            for diagnostic in self.validate_value(prop, value):
                diags.append(_rebase(diagnostic, ("page", key), None))
        return tuple(diags)

    def validate_node(
        self,
        node: Node,
        *,
        nodes: Mapping[NodeId, Node] | None = None,
    ) -> tuple[Diagnostic, ...]:
        diags = list(
            self.validate_props(node.type_id, node.props, node_id=node.id)
        )
        if node.type_id not in self.widgets:
            return tuple(diags)
        spec = self.widgets[node.type_id]
        for event_name in node.events:
            if event_name not in spec.events:
                diags.append(
                    _error(
                        CODE_UNKNOWN_EVENT,
                        f"Unknown event {event_name!r} on {node.type_id}",
                        path=("events", event_name),
                        node_id=node.id,
                    )
                )
        diags.extend(self._supplementary(node, spec, nodes))
        return tuple(diags)

    def _supplementary(
        self,
        node: Node,
        spec: WidgetSpec,
        nodes: Mapping[NodeId, Node] | None,
    ) -> tuple[Diagnostic, ...]:
        diags: list[Diagnostic] = []
        props = node.props
        type_id = node.type_id

        if type_id in _BUTTON_TYPES:
            diags.extend(self._button_rules(node, nodes))

        if type_id == "Checkbox":
            if "value" in props and props["value"] is None:
                tristate = props.get("tristate", False)
                if tristate is not True:
                    diags.append(
                        _error(
                            CODE_CHECKBOX_TRISTATE,
                            "Checkbox.value=null requires tristate=true",
                            path=("props", "value"),
                            node_id=node.id,
                        )
                    )

        if type_id == "Image" and "src" in props and _is_https_image(props["src"]):
            diags.append(
                _warning(
                    CODE_REMOTE_IMAGE,
                    "Imported remote image URLs are not fetched by the Python "
                    "loader; preview requires the application's explicit "
                    "remote-resource policy",
                    path=("props", "src"),
                    node_id=node.id,
                )
            )

        if type_id == "Column" and _scroll_active(props) and props.get("tight") is True:
            diags.append(
                _error(
                    CODE_LAYOUT_CONSTRAINT,
                    "Column scroll is incompatible with tight=true",
                    path=("props", "scroll"),
                    node_id=node.id,
                )
            )

        if type_id == "Row" and _scroll_active(props) and props.get("wrap") is True:
            diags.append(
                _error(
                    CODE_LAYOUT_CONSTRAINT,
                    "Row scroll is incompatible with wrap=true",
                    path=("props", "scroll"),
                    node_id=node.id,
                )
            )

        if type_id == "ListView":
            height_unset = "height" not in props
            expand_unset = "expand" not in props or props.get("expand") in (None, False)
            if height_unset and expand_unset:
                diags.append(
                    _error(
                        CODE_LAYOUT_CONSTRAINT,
                        "ListView without height or expand is an unbounded layout constraint",
                        path=("props", "height"),
                        node_id=node.id,
                    )
                )

        return tuple(diags)

    def _button_rules(
        self, node: Node, nodes: Mapping[NodeId, Node] | None
    ) -> tuple[Diagnostic, ...]:
        diags: list[Diagnostic] = []
        props = node.props
        child_ids = node.slots.get("content", ())
        scalar = props.get("content") if "content" in props else Unset.VALUE
        has_scalar = scalar is not Unset.VALUE and scalar is not None
        meaningful = isinstance(scalar, str) and scalar.strip() != ""
        has_icon = "icon" in props and props["icon"] not in (None, "")
        has_visible_child = _visible_child(child_ids, nodes)

        if has_scalar and child_ids:
            diags.append(
                _error(
                    CODE_SCALAR_CONTROL_UNION,
                    "Single-child scalar/control unions cannot be populated both ways",
                    path=("props", "content"),
                    node_id=node.id,
                )
            )

        if not (meaningful or has_visible_child or has_icon):
            diags.append(
                _error(
                    CODE_BUTTON_CONTENT,
                    "A button requires meaningful scalar content, a visible "
                    "content child, or an icon",
                    path=("props", "content"),
                    node_id=node.id,
                )
            )
        return tuple(diags)


catalogue = FrozenCatalogue(
    version=1,
    target_flet=TARGET_FLET,
    widgets=WIDGET_SPECS,
    page_properties=PAGE_PROPERTIES,
    codecs=CODECS,
)

__all__ = [
    "BUILTIN_IMAGE_PLACEHOLDER",
    "COLORS",
    "CODECS",
    "FrozenCatalogue",
    "ICONS",
    "PAGE_PROPERTIES",
    "PAGE_SPEC",
    "PageSpec",
    "WIDGET_ORDER",
    "WIDGET_SPECS",
    "catalogue",
]
