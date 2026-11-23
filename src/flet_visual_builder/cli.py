"""Console entry point: ``flet-visual-builder [project.fvb.json]``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import flet as ft

from flet_visual_builder import __version__
from flet_visual_builder.ui.app import main as app_main


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="flet-visual-builder",
        description="Visual drag-and-drop builder for Flet apps.",
    )
    parser.add_argument("project", nargs="?", help="path to a .fvb.json project")
    parser.add_argument("--web", action="store_true", help="run in a browser instead of a desktop window")
    parser.add_argument("--port", type=int, default=0, help="port for --web (0 picks a free port)")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    project = Path(args.project).expanduser() if args.project else None
    view = ft.AppView.WEB_BROWSER if args.web else ft.AppView.FLET_APP
    ft.run(
        lambda page: app_main(page, path=project),
        view=view,
        port=args.port,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
