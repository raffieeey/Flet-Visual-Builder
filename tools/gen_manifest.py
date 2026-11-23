#!/usr/bin/env python3
"""Generate the committed Colors/Icons allowlist from the pinned Flet package.

Run from the repository root:

    uv run --locked --extra dev python tools/gen_manifest.py

This script is the only catalogue-adjacent code allowed to import Flet. The
generated JSON is loaded at runtime by enum_manifest.py with no Flet import.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import flet as ft

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "src" / "flet_visual_builder" / "catalogue" / "allowlist_manifest.json"

# Naming traps verified against Flet 1.0.1 — the generator must observe them.
_REQUIRED_COLORS = ("BLACK_12", "INDIGO", "SURFACE_CONTAINER_HIGHEST")
_FORBIDDEN_COLORS = ("BLACK12", "SURFACE_VARIANT")
_REQUIRED_ICONS = ("HOME", "ADD", "PERSON", "SAVE")


def _colors() -> list[str]:
    names = sorted(ft.Colors.__members__)
    missing = [n for n in _REQUIRED_COLORS if n not in names]
    leaked = [n for n in _FORBIDDEN_COLORS if n in names]
    if missing or leaked:
        raise SystemExit(
            f"Colors allowlist failed checks: missing={missing} leaked={leaked}"
        )
    return names


def _icons() -> list[str]:
    # ft.Icons.__dir__ returns the empirical material-icons map keys.
    names = sorted(dir(ft.Icons))
    missing = [n for n in _REQUIRED_ICONS if n not in names]
    if missing:
        raise SystemExit(f"Icons allowlist missing required names: {missing}")
    if "random" in names:
        raise SystemExit("Icons allowlist included proxy methods; extraction is wrong")
    return names


def main() -> int:
    version = getattr(ft, "__version__", None)
    if version != "1.0.1":
        raise SystemExit(f"Expected flet 1.0.1, found {version!r}")
    payload = {
        "target_flet": "1.0.1",
        "flet_version": version,
        "colors": _colors(),
        "icons": _icons(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        json.dumps(payload, separators=(",", ":"), ensure_ascii=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {OUT}")
    print(f"colors={len(payload['colors'])} icons={len(payload['icons'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
