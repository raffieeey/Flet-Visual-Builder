"""Helpers for resolving icon names against the current Flet API."""
from __future__ import annotations

from typing import Any

import flet as ft


def resolve_icon(icon_name: Any) -> Any:
    """Resolve snake_case icon names to ``ft.Icons`` constants when possible.

    Newer Flet versions can be stricter about icon values on ``IconButton``.
    Using ``ft.Icons`` constants keeps controls compatible while still allowing
    arbitrary values to pass through unchanged.
    """
    if not isinstance(icon_name, str) or not icon_name:
        return icon_name

    attr_name = icon_name.upper()
    return getattr(ft.Icons, attr_name, icon_name)

