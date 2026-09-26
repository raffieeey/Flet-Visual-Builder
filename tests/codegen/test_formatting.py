"""Black 25.1.0 wrapper: pinned Mode, stable output, line length 88."""
from __future__ import annotations

from pathlib import Path

import black

from src.flet_visual_builder.engine.formatting import (
    PINNED_BLACK_VERSION,
    black_mode,
    format_python,
)

FORMATTING_PY = (
    Path(__file__).resolve().parents[2]
    / "src"
    / "flet_visual_builder"
    / "engine"
    / "formatting.py"
)


def test_black_version_is_pinned() -> None:
    assert black.__version__ == "25.1.0"
    assert PINNED_BLACK_VERSION == "25.1.0"


def test_mode_is_py312_length_88() -> None:
    mode = black_mode()
    assert mode.line_length == 88
    assert black.TargetVersion.PY312 in mode.target_versions
    assert mode.string_normalization is True
    assert mode.preview is False


def test_invokes_format_str_in_process() -> None:
    source = FORMATTING_PY.read_text(encoding="utf-8")
    assert "black.format_str" in source
    assert "black.Mode" in source
    assert "TargetVersion.PY312" in source


def test_format_python_is_stable() -> None:
    raw = "def f(a,b,c):\n    return a+b+c\n"
    first = format_python(raw)
    second = format_python(first)
    assert first == second
    assert first == format_python(first, line_length=88)
    assert first.endswith("\n")
    assert not first.endswith("\n\n")
    assert "\r" not in first


def test_line_length_88_is_honoured() -> None:
    call = "def f():\n    return (" + ", ".join(str(i) for i in range(40)) + ")\n"
    formatted = format_python(call, line_length=88)
    assert formatted == format_python(formatted, line_length=88)
    assert max(len(line) for line in formatted.splitlines()) <= 88
