"""JSON project repository: load/save, limits, v2 decode. No Flet imports."""

from __future__ import annotations

import json
import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flet_visual_builder.catalogue import FrozenCatalogue
from flet_visual_builder.catalogue import catalogue as default_catalogue
from flet_visual_builder.contracts import (
    Asset,
    Diagnostic,
    EventSymbol,
    JsonValue,
    Node,
    Project,
    Severity,
)
from flet_visual_builder.model.validation import (
    MAX_DEPTH,
    MAX_NODES,
    validate_project,
)
from flet_visual_builder.persistence.assets import (
    MAX_ASSET_BYTES,
    MAX_TOTAL_ASSET_BYTES,
    decode_data,
    deduplicate_assets,
    encode_data,
    sha256_hex,
    verify_asset,
)
from flet_visual_builder.persistence.migrations import (
    EditorHints,
    migrate_to_v2,
)

MAX_STRUCTURAL_JSON_BYTES = 4 * 1024 * 1024
MAX_PROJECT_FILE_BYTES = 32 * 1024 * 1024

V2_REQUIRED = (
    "name",
    "page",
    "root_ids",
    "nodes",
    "assets",
    "schema_version",
    "catalogue_version",
    "target_flet",
)
V2_OPTIONAL_ENVELOPE = frozenset({"format"})
NODE_KEYS = frozenset({"id", "type_id", "props", "slots", "events"})
ASSET_KEYS = frozenset({"id", "media_type", "sha256", "data"})


@dataclass(frozen=True, slots=True)
class PersistenceResult:
    project: Project | None
    diagnostics: tuple[Diagnostic, ...] = ()
    editor_hints: EditorHints | None = None
    migrated_from: str | int | None = None

    @property
    def ok(self) -> bool:
        return self.project is not None and not any(
            d.severity == Severity.ERROR for d in self.diagnostics
        )


def _error(
    code: str,
    message: str,
    *,
    path: tuple[str | int, ...] = (),
    node_id: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        message=message,
        severity=Severity.ERROR,
        path=path,
        node_id=node_id,
    )


def _has_error(diagnostics: tuple[Diagnostic, ...] | list[Diagnostic]) -> bool:
    return any(d.severity == Severity.ERROR for d in diagnostics)


def freeze_json(value: Any) -> JsonValue:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, list):
        return tuple(freeze_json(item) for item in value)
    if isinstance(value, tuple):
        return tuple(freeze_json(item) for item in value)
    if isinstance(value, Mapping):
        return {str(key): freeze_json(item) for key, item in value.items()}
    raise TypeError(f"Unsupported JSON value type: {type(value)!r}")


def thaw_json(value: JsonValue) -> Any:
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    if isinstance(value, Mapping):
        return {key: thaw_json(item) for key, item in value.items()}
    return value


def structural_json_size(data: object) -> int:
    payload: object = data
    if isinstance(data, dict):
        assets = data.get("assets")
        if isinstance(assets, dict):
            stripped_assets: dict[str, Any] = {}
            for key, asset in assets.items():
                if isinstance(asset, dict):
                    copy = dict(asset)
                    copy["data"] = ""
                    stripped_assets[key] = copy
                else:
                    stripped_assets[key] = asset
            payload = dict(data)
            payload["assets"] = stripped_assets
    raw = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    return len(raw.encode("utf-8"))


class JsonRepository:
    def __init__(self, catalogue: FrozenCatalogue | None = None) -> None:
        self._catalogue = catalogue if catalogue is not None else default_catalogue

    def load(self, path: str | Path) -> PersistenceResult:
        """Read ``path``. Never writes; unknown schemas leave the file intact."""
        target = Path(path)
        try:
            raw = target.read_bytes()
        except OSError as exc:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "persistence.io",
                        f"Cannot read {target}: {exc}",
                    ),
                ),
            )
        if len(raw) > MAX_PROJECT_FILE_BYTES:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "limit.file_bytes",
                        (
                            "limit total project-file bytes exceeded: "
                            f"{len(raw)} > {MAX_PROJECT_FILE_BYTES}"
                        ),
                    ),
                ),
            )
        try:
            parsed = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "persistence.parse",
                        f"Invalid JSON: {exc}",
                    ),
                ),
            )
        return self._from_parsed(parsed)

    def loads(self, source: str | bytes | Mapping[str, Any]) -> PersistenceResult:
        if isinstance(source, (str, bytes)):
            raw = source.encode("utf-8") if isinstance(source, str) else source
            if len(raw) > MAX_PROJECT_FILE_BYTES:
                return PersistenceResult(
                    project=None,
                    diagnostics=(
                        _error(
                            "limit.file_bytes",
                            (
                                "limit total project-file bytes exceeded: "
                                f"{len(raw)} > {MAX_PROJECT_FILE_BYTES}"
                            ),
                        ),
                    ),
                )
            try:
                parsed = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                return PersistenceResult(
                    project=None,
                    diagnostics=(_error("persistence.parse", f"Invalid JSON: {exc}"),),
                )
            return self._from_parsed(parsed)
        return self._from_parsed(dict(source))

    def dump(self, project: Project) -> dict[str, Any]:
        assets = {
            key: {
                "id": asset.id,
                "media_type": asset.media_type,
                "sha256": asset.sha256.lower(),
                "data": encode_data(asset.data),
            }
            for key, asset in deduplicate_assets(project.assets).items()
        }
        nodes: dict[str, Any] = {}
        for key, node in project.nodes.items():
            nodes[key] = {
                "id": node.id,
                "type_id": node.type_id,
                "props": thaw_json(dict(node.props)),
                "slots": {slot: list(ids) for slot, ids in node.slots.items()},
                "events": {
                    event: {"name": symbol.name}
                    for event, symbol in node.events.items()
                },
            }
        return {
            "name": project.name,
            "page": thaw_json(dict(project.page)),
            "root_ids": list(project.root_ids),
            "nodes": nodes,
            "assets": assets,
            "schema_version": 2,
            "catalogue_version": 1,
            "target_flet": "1.0.1",
        }

    def save(self, project: Project, path: str | Path) -> PersistenceResult:
        checked = self._validate_project(project)
        if _has_error(checked.diagnostics) or checked.project is None:
            return PersistenceResult(
                project=None,
                diagnostics=checked.diagnostics,
            )
        payload = self.dump(checked.project)
        encoded = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False)
        data = (encoded + "\n").encode("utf-8")
        if len(data) > MAX_PROJECT_FILE_BYTES:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "limit.file_bytes",
                        (
                            "limit total project-file bytes exceeded: "
                            f"{len(data)} > {MAX_PROJECT_FILE_BYTES}"
                        ),
                    ),
                ),
            )
        structural = structural_json_size(payload)
        if structural > MAX_STRUCTURAL_JSON_BYTES:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "limit.structural_json",
                        (
                            "limit structural JSON bytes exceeded: "
                            f"{structural} > {MAX_STRUCTURAL_JSON_BYTES}"
                        ),
                    ),
                ),
            )
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            dir=str(target.parent), prefix=f".{target.name}.", suffix=".tmp"
        )
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, target)
        except Exception:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
            raise
        return PersistenceResult(
            project=checked.project,
            diagnostics=checked.diagnostics,
        )

    def _from_parsed(self, parsed: object) -> PersistenceResult:
        if not isinstance(parsed, dict):
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "persistence.parse",
                        "Document root must be a JSON object",
                    ),
                ),
            )
        size = structural_json_size(parsed)
        if size > MAX_STRUCTURAL_JSON_BYTES:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error(
                        "limit.structural_json",
                        (
                            "limit structural JSON bytes exceeded: "
                            f"{size} > {MAX_STRUCTURAL_JSON_BYTES}"
                        ),
                    ),
                ),
            )
        if "schema_version" not in parsed:
            version: object = "0.0"
        else:
            version = parsed["schema_version"]
        if version in ("0.0", "0.1"):
            outcome = migrate_to_v2(parsed)
            if outcome.document is None or _has_error(outcome.diagnostics):
                return PersistenceResult(
                    project=None,
                    diagnostics=outcome.diagnostics,
                    editor_hints=outcome.editor_hints,
                    migrated_from=outcome.source_version,
                )
            decoded = self._decode_v2(outcome.document)
            if decoded.project is None or _has_error(decoded.diagnostics):
                return PersistenceResult(
                    project=None,
                    diagnostics=outcome.diagnostics + decoded.diagnostics,
                    editor_hints=outcome.editor_hints,
                    migrated_from=outcome.source_version,
                )
            return PersistenceResult(
                project=decoded.project,
                diagnostics=decoded.diagnostics,
                editor_hints=outcome.editor_hints,
                migrated_from=outcome.source_version,
            )
        if version == 2 and not isinstance(version, bool):
            decoded = self._decode_v2(parsed)
            return decoded
        return PersistenceResult(
            project=None,
            diagnostics=(
                _error(
                    "schema.unsupported",
                    f"Unrecognized schema_version {version!r}",
                    path=("schema_version",),
                ),
            ),
        )

    def _decode_v2(self, data: Mapping[str, Any]) -> PersistenceResult:
        errors: list[Diagnostic] = []
        extra = set(data) - set(V2_REQUIRED) - V2_OPTIONAL_ENVELOPE
        if extra:
            errors.append(
                _error(
                    "schema.unexpected",
                    f"Unexpected top-level properties: {sorted(extra)}",
                )
            )
        for key in V2_REQUIRED:
            if key not in data:
                errors.append(
                    _error(
                        "schema.missing",
                        f"Missing required property {key!r}",
                        path=(key,),
                    )
                )
        if errors:
            return PersistenceResult(project=None, diagnostics=tuple(errors))

        if data["schema_version"] != 2 or isinstance(data["schema_version"], bool):
            errors.append(
                _error(
                    "schema.unsupported",
                    f"Unrecognized schema_version {data['schema_version']!r}",
                    path=("schema_version",),
                )
            )
        if data["catalogue_version"] != 1 or isinstance(
            data["catalogue_version"], bool
        ):
            errors.append(
                _error(
                    "version.unsupported",
                    f"catalogue_version {data['catalogue_version']!r} is not supported",
                    path=("catalogue_version",),
                )
            )
        if data["target_flet"] != "1.0.1":
            errors.append(
                _error(
                    "version.unsupported",
                    f"target_flet {data['target_flet']!r} is not supported",
                    path=("target_flet",),
                )
            )
        name = data["name"]
        page_raw = data["page"]
        root_ids_raw = data["root_ids"]
        nodes_raw = data["nodes"]
        assets_raw = data["assets"]
        if not isinstance(name, str):
            errors.append(
                _error("schema.type", "name must be a string", path=("name",))
            )
        if not isinstance(page_raw, dict):
            errors.append(
                _error("schema.type", "page must be an object", path=("page",))
            )
        if not isinstance(root_ids_raw, list) or not all(
            isinstance(item, str) for item in root_ids_raw
        ):
            errors.append(
                _error(
                    "schema.type",
                    "root_ids must be an array of strings",
                    path=("root_ids",),
                )
            )
        if not isinstance(nodes_raw, dict):
            errors.append(
                _error("schema.type", "nodes must be an object", path=("nodes",))
            )
        if not isinstance(assets_raw, dict):
            errors.append(
                _error("schema.type", "assets must be an object", path=("assets",))
            )
        if errors:
            return PersistenceResult(project=None, diagnostics=tuple(errors))

        assert isinstance(name, str)
        assert isinstance(page_raw, dict)
        assert isinstance(root_ids_raw, list)
        assert isinstance(nodes_raw, dict)
        assert isinstance(assets_raw, dict)

        if len(nodes_raw) > MAX_NODES:
            errors.append(
                _error(
                    "limit.nodes",
                    (
                        f"limit nodes exceeded: document has {len(nodes_raw)} "
                        f"nodes; maximum is {MAX_NODES}"
                    ),
                    path=("nodes",),
                )
            )

        nodes: dict[str, Node] = {}
        for key, raw_node in nodes_raw.items():
            node, node_errors = self._decode_node(str(key), raw_node)
            errors.extend(node_errors)
            if node is not None:
                nodes[node.id] = node

        assets: dict[str, Asset] = {}
        total_asset_bytes = 0
        for key, raw_asset in assets_raw.items():
            asset, asset_errors = self._decode_asset(str(key), raw_asset)
            errors.extend(asset_errors)
            if asset is None:
                continue
            total_asset_bytes += len(asset.data)
            assets[key] = asset
        if total_asset_bytes > MAX_TOTAL_ASSET_BYTES:
            errors.append(
                _error(
                    "limit.total_asset_bytes",
                    (
                        "limit total decoded assets exceeded: "
                        f"{total_asset_bytes} > {MAX_TOTAL_ASSET_BYTES}"
                    ),
                    path=("assets",),
                )
            )
        assets = deduplicate_assets(assets)

        if _has_error(errors):
            return PersistenceResult(project=None, diagnostics=tuple(errors))

        try:
            page = freeze_json(page_raw)
        except TypeError as exc:
            return PersistenceResult(
                project=None,
                diagnostics=(
                    _error("schema.type", f"page is not JSON-compatible: {exc}"),
                ),
            )
        if not isinstance(page, Mapping):
            return PersistenceResult(
                project=None,
                diagnostics=(_error("schema.type", "page must be an object"),),
            )

        project = Project(
            name=name,
            page=page,
            root_ids=tuple(str(item) for item in root_ids_raw),
            nodes=nodes,
            assets=assets,
        )
        return self._validate_project(project)

    def _decode_node(
        self, key: str, raw: object
    ) -> tuple[Node | None, list[Diagnostic]]:
        errors: list[Diagnostic] = []
        if not isinstance(raw, dict):
            return None, [
                _error(
                    "schema.node",
                    f"Node {key!r} is not an object",
                    path=("nodes", key),
                )
            ]
        extra = set(raw) - NODE_KEYS
        if extra:
            errors.append(
                _error(
                    "schema.unexpected",
                    f"Node {key!r} has unexpected properties {sorted(extra)}",
                    path=("nodes", key),
                    node_id=key,
                )
            )
        for field in ("id", "type_id", "props", "slots", "events"):
            if field not in raw:
                errors.append(
                    _error(
                        "schema.missing",
                        f"Node {key!r} is missing {field!r}",
                        path=("nodes", key, field),
                        node_id=key,
                    )
                )
        if errors:
            return None, errors
        node_id = raw["id"]
        type_id = raw["type_id"]
        props_raw = raw["props"]
        slots_raw = raw["slots"]
        events_raw = raw["events"]
        if node_id != key:
            errors.append(
                _error(
                    "id.mismatch",
                    f"Node map key {key!r} does not match node.id {node_id!r}",
                    path=("nodes", key),
                    node_id=str(node_id) if isinstance(node_id, str) else key,
                )
            )
        if not isinstance(node_id, str) or not isinstance(type_id, str):
            errors.append(
                _error(
                    "schema.type",
                    f"Node {key!r} id and type_id must be strings",
                    path=("nodes", key),
                    node_id=key,
                )
            )
            return None, errors
        if not isinstance(props_raw, dict):
            errors.append(
                _error(
                    "schema.type",
                    f"Node {key!r} props must be an object",
                    path=("nodes", key, "props"),
                    node_id=node_id,
                )
            )
            return None, errors
        if not isinstance(slots_raw, dict):
            errors.append(
                _error(
                    "schema.type",
                    f"Node {key!r} slots must be an object",
                    path=("nodes", key, "slots"),
                    node_id=node_id,
                )
            )
            return None, errors
        if not isinstance(events_raw, dict):
            errors.append(
                _error(
                    "schema.type",
                    f"Node {key!r} events must be an object",
                    path=("nodes", key, "events"),
                    node_id=node_id,
                )
            )
            return None, errors
        slots: dict[str, tuple[str, ...]] = {}
        for slot_name, ids in slots_raw.items():
            if not isinstance(slot_name, str) or not isinstance(ids, list):
                errors.append(
                    _error(
                        "schema.type",
                        f"Slot {slot_name!r} on {node_id} must map to an array",
                        path=("nodes", key, "slots", str(slot_name)),
                        node_id=node_id,
                    )
                )
                continue
            if not all(isinstance(item, str) for item in ids):
                errors.append(
                    _error(
                        "schema.type",
                        f"Slot {slot_name!r} on {node_id} must contain strings",
                        path=("nodes", key, "slots", slot_name),
                        node_id=node_id,
                    )
                )
                continue
            slots[slot_name] = tuple(ids)
        events: dict[str, EventSymbol] = {}
        for event_name, symbol_raw in events_raw.items():
            if not isinstance(event_name, str):
                errors.append(
                    _error(
                        "schema.type",
                        f"Event name on {node_id} must be a string",
                        path=("nodes", key, "events"),
                        node_id=node_id,
                    )
                )
                continue
            if not isinstance(symbol_raw, dict) or "name" not in symbol_raw:
                errors.append(
                    _error(
                        "schema.type",
                        f"Event {event_name!r} on {node_id} must be an object with name",
                        path=("nodes", key, "events", event_name),
                        node_id=node_id,
                    )
                )
                continue
            symbol_name = symbol_raw["name"]
            if not isinstance(symbol_name, str):
                errors.append(
                    _error(
                        "schema.type",
                        f"Event {event_name!r} name must be a string",
                        path=("nodes", key, "events", event_name),
                        node_id=node_id,
                    )
                )
                continue
            try:
                events[event_name] = EventSymbol(symbol_name)
            except ValueError:
                errors.append(
                    _error(
                        "event.symbol",
                        f"Invalid event symbol {symbol_name!r} on {node_id}",
                        path=("nodes", key, "events", event_name),
                        node_id=node_id,
                    )
                )
        if errors:
            return None, errors
        try:
            props = freeze_json(props_raw)
        except TypeError as exc:
            return None, [
                _error(
                    "schema.type",
                    f"Node {node_id} props are not JSON-compatible: {exc}",
                    path=("nodes", key, "props"),
                    node_id=node_id,
                )
            ]
        if not isinstance(props, Mapping):
            return None, [
                _error(
                    "schema.type",
                    f"Node {node_id} props must be an object",
                    path=("nodes", key, "props"),
                    node_id=node_id,
                )
            ]
        return (
            Node(
                id=node_id,
                type_id=type_id,
                props=props,
                slots=slots,
                events=events,
            ),
            [],
        )

    def _decode_asset(
        self, key: str, raw: object
    ) -> tuple[Asset | None, list[Diagnostic]]:
        errors: list[Diagnostic] = []
        path = ("assets", key)
        if not isinstance(raw, dict):
            return None, [
                _error("schema.asset", f"Asset {key!r} is not an object", path=path)
            ]
        extra = set(raw) - ASSET_KEYS
        if extra:
            errors.append(
                _error(
                    "schema.unexpected",
                    f"Asset {key!r} has unexpected properties {sorted(extra)}",
                    path=path,
                )
            )
        for field in ("id", "media_type", "sha256", "data"):
            if field not in raw:
                errors.append(
                    _error(
                        "schema.missing",
                        f"Asset {key!r} is missing {field!r}",
                        path=path + (field,),
                    )
                )
        if errors:
            return None, errors
        asset_id = raw["id"]
        media_type = raw["media_type"]
        digest = raw["sha256"]
        data_text = raw["data"]
        if not isinstance(asset_id, str) or not isinstance(media_type, str):
            return None, [
                _error(
                    "schema.type",
                    f"Asset {key!r} id and media_type must be strings",
                    path=path,
                )
            ]
        if not isinstance(digest, str) or not isinstance(data_text, str):
            return None, [
                _error(
                    "schema.type",
                    f"Asset {key!r} sha256 and data must be strings",
                    path=path,
                )
            ]
        if asset_id != key:
            errors.append(
                _error(
                    "asset.id",
                    f"Asset key {key!r} does not match asset.id {asset_id!r}",
                    path=path,
                )
            )
        try:
            blob = decode_data(data_text)
        except (ValueError, TypeError) as exc:
            return None, [
                _error(
                    "asset.data",
                    f"Asset {key!r} data is not valid base64: {exc}",
                    path=path,
                )
            ]
        computed = sha256_hex(blob)
        if digest.lower() != computed:
            errors.append(
                _error(
                    "asset.hash",
                    f"Asset {key!r} sha256 does not match data",
                    path=path,
                )
            )
        if len(blob) > MAX_ASSET_BYTES:
            errors.append(
                _error(
                    "limit.asset_bytes",
                    (
                        f"limit per-asset bytes exceeded: asset {key!r} is "
                        f"{len(blob)} bytes; maximum is {MAX_ASSET_BYTES}"
                    ),
                    path=path,
                )
            )
        if errors:
            return None, errors
        asset = Asset(
            id=asset_id,
            media_type=media_type,
            sha256=computed,
            data=blob,
        )
        extra_errors = [
            diag
            for diag in verify_asset(asset, path=path)
            if diag.code not in {"asset.hash"}
        ]
        return asset, extra_errors

    def _validate_project(self, project: Project) -> PersistenceResult:
        errors: list[Diagnostic] = []
        if len(project.nodes) > MAX_NODES:
            errors.append(
                _error(
                    "limit.nodes",
                    (
                        f"limit nodes exceeded: document has {len(project.nodes)} "
                        f"nodes; maximum is {MAX_NODES}"
                    ),
                    path=("nodes",),
                )
            )
        depth = _document_depth(project)
        if depth > MAX_DEPTH:
            errors.append(
                _error(
                    "limit.depth",
                    (
                        f"limit depth exceeded: deepest node is at depth "
                        f"{depth}; maximum is {MAX_DEPTH}"
                    ),
                    path=("nodes",),
                )
            )
        total = 0
        for key, asset in project.assets.items():
            errors.extend(verify_asset(asset, path=("assets", key)))
            total += len(asset.data)
        if total > MAX_TOTAL_ASSET_BYTES:
            errors.append(
                _error(
                    "limit.total_asset_bytes",
                    (
                        "limit total decoded assets exceeded: "
                        f"{total} > {MAX_TOTAL_ASSET_BYTES}"
                    ),
                    path=("assets",),
                )
            )
        errors.extend(validate_project(project))
        errors.extend(self._catalogue.validate_page(project.page))
        for node in project.nodes.values():
            errors.extend(self._catalogue.validate_node(node, nodes=project.nodes))
        if _has_error(errors):
            return PersistenceResult(project=None, diagnostics=tuple(errors))
        return PersistenceResult(project=project, diagnostics=tuple(errors))


def _document_depth(project: Project) -> int:
    max_depth = 0
    stack: list[tuple[str, int]] = [(rid, 1) for rid in project.root_ids]
    seen: set[str] = set()
    while stack:
        node_id, depth = stack.pop()
        if node_id in seen:
            continue
        seen.add(node_id)
        if depth > max_depth:
            max_depth = depth
        node = project.nodes.get(node_id)
        if node is None:
            continue
        for ids in node.slots.values():
            for child_id in ids:
                stack.append((child_id, depth + 1))
    return max_depth


_DEFAULT = JsonRepository()


def load(path: str | Path) -> PersistenceResult:
    return _DEFAULT.load(path)


def save(project: Project, path: str | Path) -> PersistenceResult:
    return _DEFAULT.save(project, path)


def loads(source: str | bytes | Mapping[str, Any]) -> PersistenceResult:
    return _DEFAULT.loads(source)


def dump(project: Project) -> dict[str, Any]:
    return _DEFAULT.dump(project)
