"""Safety: the generator never eval/exec/import project expressions."""

from __future__ import annotations

import ast
from pathlib import Path

ENGINE = Path(__file__).resolve().parents[2] / "src" / "flet_visual_builder" / "engine"
BANNED_CALLS = frozenset({"eval", "exec", "__import__", "getattr"})


def _assert_no_banned_calls(path: Path) -> None:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            assert func.id not in BANNED_CALLS, f"{path.name} calls {func.id}"
        if isinstance(func, ast.Attribute):
            assert func.attr not in BANNED_CALLS, f"{path.name} calls {func.attr}"


def test_codegen_and_formatting_have_no_eval_exec_getattr() -> None:
    _assert_no_banned_calls(ENGINE / "codegen.py")
    _assert_no_banned_calls(ENGINE / "formatting.py")


def _is_flet_module(name: str) -> bool:
    return name == "flet" or name.startswith("flet.")


def test_codegen_does_not_import_flet_or_importlib() -> None:
    source = (ENGINE / "codegen.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert not _is_flet_module(alias.name)
                assert not alias.name.startswith("importlib")
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert not _is_flet_module(module)
            assert not module.startswith("importlib")
