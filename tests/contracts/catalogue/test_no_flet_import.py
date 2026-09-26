"""Catalogue modules must not import Flet at runtime."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]

MODULES = (
    "src.flet_visual_builder.catalogue",
    "src.flet_visual_builder.catalogue.widgets",
    "src.flet_visual_builder.catalogue.page",
    "src.flet_visual_builder.catalogue.codecs",
    "src.flet_visual_builder.catalogue.enum_manifest",
)


def test_each_catalogue_module_fresh_interpreter_has_no_flet() -> None:
    for mod in MODULES:
        script = f"""
import sys
from pathlib import Path
sys.path.insert(0, {str(REPO)!r})
import {mod} as m
assert "flet" not in sys.modules, sorted(k for k in sys.modules if "flet" in k)
print("ok", {mod!r})
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, f"{mod}\n{result.stdout}\n{result.stderr}"
        assert "ok" in result.stdout
