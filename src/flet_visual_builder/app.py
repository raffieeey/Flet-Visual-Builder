"""Public application entry point.

Kept as a thin re-export so ``flet run app.py``, ``python -m flet_visual_builder``,
and the console script all start the same product.
"""

from __future__ import annotations

from flet_visual_builder.ui.app import build, main

__all__ = ["build", "main"]

if __name__ == "__main__":  # pragma: no cover - manual launch helper
    import flet as ft

    from flet_visual_builder.cli import main as cli_main

    ft.run(lambda page: main(page))
