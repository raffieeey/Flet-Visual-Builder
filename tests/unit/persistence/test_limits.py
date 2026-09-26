"""Persistence limits and unknown-schema refusal. Headless; no Flet."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.flet_visual_builder.model.validation import MAX_DEPTH, MAX_NODES
from src.flet_visual_builder.persistence.assets import (
    MAX_ASSET_BYTES,
    MAX_TOTAL_ASSET_BYTES,
    encode_data,
    sha256_hex,
)
from src.flet_visual_builder.persistence.json_repository import (
    MAX_PROJECT_FILE_BYTES,
    MAX_STRUCTURAL_JSON_BYTES,
    JsonRepository,
    load,
)
from tests.unit.persistence.helpers import (
    has_error_named,
    text_node,
    v2_envelope,
)


def _write(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def test_unknown_schema_version_does_not_overwrite_input(tmp_path: Path) -> None:
    repo = JsonRepository()
    for version in ("3", "9.9", 3):
        path = tmp_path / f"future-{version}.json"
        original = json.dumps(
            {"name": "x", "schema_version": version, "tree": {}},
            indent=2,
        ).encode("utf-8")
        path.write_bytes(original)
        result = repo.load(path)
        assert result.project is None
        blob = " ".join(f"{d.code} {d.message}" for d in result.diagnostics)
        assert "schema" in blob.lower() or "unsupported" in blob.lower()
        assert repr(version) in blob or str(version) in blob
        assert path.read_bytes() == original


def test_node_limit_trips(tmp_path: Path) -> None:
    count = MAX_NODES + 1
    nodes = {f"n{i}": text_node(f"n{i}") for i in range(count)}
    payload = v2_envelope(nodes, [f"n{i}" for i in range(count)])
    path = tmp_path / "nodes.json"
    _write(path, payload)
    result = load(path)
    assert result.project is None
    assert has_error_named(result.diagnostics, "nodes", str(MAX_NODES))


def test_depth_limit_trips(tmp_path: Path) -> None:
    depth = MAX_DEPTH + 1
    nodes: dict[str, object] = {}
    for level in range(1, depth):
        node_id = f"c{level}"
        child_id = f"c{level + 1}" if level + 1 < depth else "leaf"
        nodes[node_id] = {
            "id": node_id,
            "type_id": "Container",
            "props": {},
            "slots": {"content": [child_id]},
            "events": {},
        }
    nodes["leaf"] = text_node("leaf")
    payload = v2_envelope(nodes, ["c1"])  # type: ignore[arg-type]
    path = tmp_path / "depth.json"
    _write(path, payload)
    result = load(path)
    assert result.project is None
    assert has_error_named(result.diagnostics, "depth", str(MAX_DEPTH))


def test_structural_json_limit_trips(tmp_path: Path) -> None:
    huge = "x" * (MAX_STRUCTURAL_JSON_BYTES + 64)
    payload = v2_envelope({"root": text_node("root", huge)}, ["root"])
    path = tmp_path / "struct.json"
    _write(path, payload)
    before = path.read_bytes()
    result = load(path)
    assert result.project is None
    assert has_error_named(result.diagnostics, "structural", "json")
    assert path.read_bytes() == before


def test_file_bytes_limit_trips(tmp_path: Path) -> None:
    path = tmp_path / "huge.json"
    path.write_bytes(b"x" * (MAX_PROJECT_FILE_BYTES + 1))
    before = path.read_bytes()
    result = load(path)
    assert result.project is None
    assert has_error_named(result.diagnostics, "file")
    assert str(MAX_PROJECT_FILE_BYTES) in " ".join(
        f"{d.code} {d.message}" for d in result.diagnostics
    )
    assert path.read_bytes() == before


def test_per_asset_bytes_limit_trips(tmp_path: Path) -> None:
    blob = b"a" * (MAX_ASSET_BYTES + 1)
    digest = sha256_hex(blob)
    assets = {
        "a1": {
            "id": "a1",
            "media_type": "application/octet-stream",
            "sha256": digest,
            "data": encode_data(blob),
        }
    }
    payload = v2_envelope({"root": text_node("root")}, ["root"], assets=assets)
    path = tmp_path / "asset.json"
    _write(path, payload)
    result = load(path)
    assert result.project is None
    assert has_error_named(result.diagnostics, "asset")
    assert str(MAX_ASSET_BYTES) in " ".join(
        f"{d.code} {d.message}" for d in result.diagnostics
    )


def test_total_asset_bytes_limit_trips(tmp_path: Path) -> None:
    chunk = MAX_TOTAL_ASSET_BYTES // 5 + 1
    assets = {}
    for i in range(5):
        blob = bytes((i,)) * chunk
        assets[f"a{i}"] = {
            "id": f"a{i}",
            "media_type": "application/octet-stream",
            "sha256": sha256_hex(blob),
            "data": encode_data(blob),
        }
    payload = v2_envelope({"root": text_node("root")}, ["root"], assets=assets)
    path = tmp_path / "assets.json"
    _write(path, payload)
    result = load(path)
    assert result.project is None
    blob = " ".join(f"{d.code} {d.message}" for d in result.diagnostics).lower()
    assert "total" in blob and "asset" in blob
    assert str(MAX_TOTAL_ASSET_BYTES) in blob


@pytest.mark.parametrize("version", ["3", "9.9"])
def test_unknown_version_named_in_diagnostic(version: str) -> None:
    result = JsonRepository().loads({"schema_version": version, "name": "x"})
    assert result.project is None
    blob = " ".join(f"{d.code} {d.message}" for d in result.diagnostics)
    assert version in blob
