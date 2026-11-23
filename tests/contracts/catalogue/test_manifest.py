"""Committed Colors/Icons allowlist was generated from Flet 1.0.1."""

from __future__ import annotations

import json
from pathlib import Path

from flet_visual_builder.catalogue.enum_manifest import COLORS, ICONS, TARGET_FLET

MANIFEST = (
    Path(__file__).resolve().parents[3]
    / "src"
    / "flet_visual_builder"
    / "catalogue"
    / "allowlist_manifest.json"
)


def test_manifest_sizes_and_traps() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data["target_flet"] == "1.0.1"
    assert TARGET_FLET == "1.0.1"
    assert data["colors"]
    assert data["icons"]
    assert len(COLORS) == len(data["colors"]) == 352
    assert len(ICONS) == len(data["icons"]) == 8825
    assert "BLACK_12" in COLORS
    assert "BLACK12" not in COLORS
    assert "INDIGO" in COLORS
    assert "SURFACE_CONTAINER_HIGHEST" in COLORS
    assert "SURFACE_VARIANT" not in COLORS
    assert "HOME" in ICONS
    assert "ADD" in ICONS
    assert "PERSON" in ICONS
    assert "SAVE" in ICONS
