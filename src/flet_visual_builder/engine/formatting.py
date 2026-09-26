"""Pinned Black 25.1.0 formatting for generated exports.

Black is invoked in-process through ``black.format_str`` and an explicit
``black.Mode``. An unavailable or unpinned Black installation is an error;
formatting is never skipped.
"""
from __future__ import annotations

import black

PINNED_BLACK_VERSION = "25.1.0"
FORMATTER_SPEC = "black==25.1.0"
DEFAULT_LINE_LENGTH = 88


def black_mode(*, line_length: int = DEFAULT_LINE_LENGTH) -> black.Mode:
    """Return the canonical Mode: Python 3.12, length 88, normalized strings."""
    return black.Mode(
        target_versions={black.TargetVersion.PY312},
        line_length=line_length,
        string_normalization=True,
        preview=False,
    )


def format_python(source: str, *, line_length: int = DEFAULT_LINE_LENGTH) -> str:
    """Format ``source`` with Black 25.1.0. UTF-8/LF, exactly one final newline."""
    installed = black.__version__
    if installed != PINNED_BLACK_VERSION:
        raise RuntimeError(
            f"Black {PINNED_BLACK_VERSION} is required for export; found {installed}"
        )
    formatted = black.format_str(source, mode=black_mode(line_length=line_length))
    formatted = formatted.replace("\r\n", "\n").replace("\r", "\n")
    if not formatted.endswith("\n"):
        formatted += "\n"
    while formatted.endswith("\n\n"):
        formatted = formatted[:-1]
    return formatted
