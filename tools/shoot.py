#!/usr/bin/env python3
"""Render a document's *exported* app and capture it as a screenshot.

This is the honest visual check: it runs the generated `app.py` in a real Flet
desktop client on a private X display, so what you see is what a user ships.

    python tools/shoot.py --template dashboard --out /tmp/dashboard.png
    python tools/shoot.py --project demo.fvb.json --out /tmp/demo.png --display :105

Requires: flet (project venv), Xvfb, ffmpeg. Linux only.
"""

from __future__ import annotations

import argparse
import os
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from flet_visual_builder.catalogue import catalogue  # noqa: E402
from flet_visual_builder.contracts import DocumentSnapshot, ExportOptions  # noqa: E402
from flet_visual_builder.engine.codegen import Codegen  # noqa: E402
from flet_visual_builder.engine.lowering import Lowering  # noqa: E402
from flet_visual_builder.persistence.json_repository import JsonRepository  # noqa: E402

RUNNER = """\
import importlib.util
import sys

import flet as ft

spec = importlib.util.spec_from_file_location("exported_app", {source!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main(page: ft.Page):
    try:
        page.window.width = {width}
        page.window.height = {height}
    except Exception:
        pass
    module.main(page)


ft.run(main)
"""


def source_for_project(project) -> str:
    lowered = Lowering().lower_project(
        DocumentSnapshot(project=project, revision=0), catalogue
    )
    if lowered.plan is None:
        raise SystemExit(
            "document has blocking diagnostics: "
            + ", ".join(sorted({d.code for d in lowered.diagnostics}))
        )
    artifact = Codegen().generate_python(lowered.plan, ExportOptions())
    if artifact.diagnostics:
        raise SystemExit(
            "code generation failed: "
            + ", ".join(sorted({d.code for d in artifact.diagnostics}))
        )
    return artifact.source


def load_project(args):
    if args.template:
        from flet_visual_builder.services.templates import TEMPLATES

        template = next((t for t in TEMPLATES if t.id == args.template), None)
        if template is None:
            raise SystemExit(f"unknown template {args.template!r}")
        return template.builder()
    result = JsonRepository(catalogue).load(args.project)
    if not result.ok or result.project is None:
        raise SystemExit(f"could not load {args.project}: {result.diagnostics}")
    return result.project


def display_running(display: str) -> bool:
    return (
        subprocess.run(
            ["xdpyinfo", "-display", display],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ).returncode
        == 0
    )


def start_display(display: str, width: int, height: int) -> subprocess.Popen | None:
    if display_running(display):
        return None
    if shutil.which("Xvfb") is None:
        raise SystemExit("Xvfb is required for --out screenshots")
    process = subprocess.Popen(
        ["Xvfb", display, "-screen", "0", f"{width}x{height}x24", "-nolisten", "tcp"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(50):
        if display_running(display):
            return process
        time.sleep(0.1)
    process.kill()
    raise SystemExit("the virtual display did not start")


def window_ready(display: str) -> bool:
    out = subprocess.run(
        ["xwininfo", "-display", display, "-root", "-children"],
        capture_output=True,
        text=True,
    ).stdout
    return "flet" in out.lower()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--template", help="template id to render")
    group.add_argument("--project", help="path to a .fvb.json document")
    parser.add_argument("--out", required=True, help="screenshot path")
    parser.add_argument("--display", default=":101", help="X display to use")
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=800)
    parser.add_argument("--keep-open", action="store_true", help="do not stop the app")
    args = parser.parse_args()

    project = load_project(args)
    source = source_for_project(project)
    out = Path(args.out).expanduser().resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    workdir = Path(tempfile.mkdtemp(prefix="fvb-shot-"))
    app_path = workdir / "app.py"
    app_path.write_text(source, encoding="utf-8")
    runner = workdir / "runner.py"
    runner.write_text(
        RUNNER.format(source=str(app_path), width=args.width, height=args.height),
        encoding="utf-8",
    )

    owned_display = start_display(args.display, args.width, args.height)
    env = {
        **os.environ,
        "DISPLAY": args.display,
        "GDK_BACKEND": "x11",
        "LIBGL_ALWAYS_SOFTWARE": "1",
        "FLET_VISUAL_BUILDER_HOME": str(workdir / "home"),
    }
    app = subprocess.Popen(
        [sys.executable, str(runner)],
        env=env,
        cwd=str(workdir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        start_new_session=True,
    )
    try:
        deadline = time.time() + 40
        while time.time() < deadline and not window_ready(args.display):
            if app.poll() is not None:
                raise SystemExit("the app exited early:\n" + (app.stdout.read() or ""))
            time.sleep(0.4)
        time.sleep(2.0)
        subprocess.run(
            [
                "ffmpeg",
                "-loglevel",
                "error",
                "-f",
                "x11grab",
                "-video_size",
                f"{args.width}x{args.height}",
                "-i",
                args.display,
                "-frames:v",
                "1",
                "-y",
                str(out),
            ],
            check=True,
        )
        print(out)
    finally:
        if not args.keep_open:
            try:
                os.killpg(os.getpgid(app.pid), signal.SIGKILL)
            except ProcessLookupError:
                pass
            if owned_display is not None:
                owned_display.terminate()
        shutil.rmtree(workdir, ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
