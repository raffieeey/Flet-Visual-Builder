"""Asset hashing, mismatch, and content-hash deduplication."""

from __future__ import annotations

import hashlib
from pathlib import Path

from src.flet_visual_builder.contracts import Asset
from src.flet_visual_builder.persistence.assets import (
    deduplicate_assets,
    encode_data,
    sha256_hex,
)
from src.flet_visual_builder.persistence.json_repository import (
    JsonRepository,
    dump,
    load,
)
from tests.unit.persistence.helpers import (
    make_node,
    make_project,
    text_node,
    v2_envelope,
)


def test_sha256_mismatch_rejects(tmp_path: Path) -> None:
    blob = b"hello-asset"
    assets = {
        "a1": {
            "id": "a1",
            "media_type": "text/plain",
            "sha256": "00" * 32,
            "data": encode_data(blob),
        }
    }
    payload = v2_envelope({"root": text_node("root")}, ["root"], assets=assets)
    path = tmp_path / "mismatch.json"
    repo = JsonRepository()
    saved = path.write_text(__import__("json").dumps(payload), encoding="utf-8")
    del saved
    result = load(path)
    assert result.project is None
    blob_text = " ".join(f"{d.code} {d.message}" for d in result.diagnostics).lower()
    assert "hash" in blob_text or "sha256" in blob_text


def test_identical_bytes_deduplicate_to_one_stored_asset(tmp_path: Path) -> None:
    data = b"same-bytes"
    digest = hashlib.sha256(data).hexdigest()
    a1 = Asset(id="a1", media_type="text/plain", sha256=digest, data=data)
    a2 = Asset(id="a2", media_type="text/plain", sha256=digest, data=data)
    collapsed = deduplicate_assets({"a1": a1, "a2": a2})
    assert len(collapsed) == 1
    assert "a1" in collapsed

    root = make_node("root", "Text", props={"value": "x"})
    project = make_project(root, assets={"a1": a1, "a2": a2})
    payload = dump(project)
    assert len(payload["assets"]) == 1

    path = tmp_path / "dedup.json"
    result = JsonRepository().save(project, path)
    assert result.project is not None
    loaded = load(path)
    assert loaded.project is not None
    assert len(loaded.project.assets) == 1
    stored = next(iter(loaded.project.assets.values()))
    assert stored.data == data
    assert stored.sha256 == digest


def test_matching_hash_is_accepted(tmp_path: Path) -> None:
    data = b"ok"
    digest = sha256_hex(data)
    root = make_node("root", "Text", props={"value": "x"})
    asset = Asset(id="a1", media_type="text/plain", sha256=digest, data=data)
    project = make_project(root, assets={"a1": asset})
    path = tmp_path / "ok.json"
    written = JsonRepository().save(project, path)
    assert written.project is not None
    loaded = load(path)
    assert loaded.project is not None
    assert loaded.project.assets["a1"].data == data
    assert loaded.project.assets["a1"].sha256 == digest
