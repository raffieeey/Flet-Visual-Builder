"""Regression: src/ must not reference Flet 0.x symbols removed in 1.0."""

from __future__ import annotations

from pathlib import Path

# Substring needles for Flet 1.0 removals. Keep this list focused.
FORBIDDEN_SUBSTRINGS = (
    "ft.ElevatedButton",
    "ft.app(",
    "ft.padding.",
    "ft.border.",
    "ft.alignment.",
    "ft.colors",
    "ft.icons.",
    "ft.UserControl",
)

SRC_ROOT = Path(__file__).resolve().parents[1] / "src"


def test_src_does_not_use_removed_flet_1_symbols() -> None:
    hits: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            for needle in FORBIDDEN_SUBSTRINGS:
                if needle in line:
                    rel = path.relative_to(SRC_ROOT.parent)
                    hits.append(f"{rel}:{lineno}: {line.strip()}")
    assert not hits, "Removed Flet 1.0 symbols found:\n" + "\n".join(hits)
