# Contributing

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest -q
```

The package is a src-layout project: `src/flet_visual_builder`. Run the app with
`flet-visual-builder` (desktop) or `flet-visual-builder --web --port 8000` (browser, needs the
`web` extra).

## Ground rules

- **No Flet imports** in `model/`, `catalogue/`, `state/` or `persistence/`. Tests enforce it.
  Those layers describe documents and values; only `engine/runtime.py` and `ui/` build controls.
- **Generated code is never executed.** Validate it with `ast.parse` and `py_compile`.
- **Every document change is a command.** Do not mutate `Project`, `Node` or their slots in
  place; build a new one (or add a reducer command) and let the dispatcher install it.
- **New behaviour comes with a test** that exercises the real path, not just imports.

## Panel contract

```python
from flet_visual_builder.app_context import Refresh
from flet_visual_builder.ui.panel import BasePanel


class MyPanel(BasePanel):
    interests = frozenset({Refresh.SELECTION, Refresh.PROJECT})

    def build(self) -> ft.Control:
        ...
```

`refresh(reason)` runs only for the reasons in `interests` (an empty set means every reason;
`Refresh.ALL` always runs). `BasePanel.refresh` tolerates an unmounted control, which makes
headless construction safe.

**Focus rule.** A panel containing a text input must not rebuild on `Refresh.DOCUMENT` —
rebuilding recreates the field and steals the caret mid-typing. Rebuild only on `SELECTION`
and `PROJECT`, and update dependent labels in place.

## Design language

Use `ui/theme.py` for everything: tokens (`T.panel`, `T.border`, `T.text_muted`,
`T.accent`, ...), spacing (`XS=4 SM=8 MD=12 LG=16 XL=24`), radii (`R_SM`, `R_MD`, `R_LG`),
chrome metrics (`TOOLBAR_H`, `STATUS_H`, `RAIL_W`, `INSPECTOR_W`) and the shared primitives
(`text`, `muted`, `faint`, `label`, `icon_button`, `button`, `divider`, `panel`, `section`,
`empty_state`, `pill`, `status_dot`, `separator_dot`, `scroll`).

Rules: no raw hex outside `theme.py`; one-pixel borders; quiet chrome, neutral canvas; the
accent is reserved for selection and primary actions; every icon-only control gets a tooltip.

## Verified Flet 1.0.1 API notes

These cost real debugging time. Confirm a signature before using an unfamiliar control:
`python -c "import dataclasses, flet as ft; print([f.name for f in dataclasses.fields(ft.X)])"`.

- Entry point is `ft.run(main)`. `ft.app` and `ft.ElevatedButton` do not exist.
- Buttons: `ft.Button(content=...)`, `ft.FilledButton`, `ft.OutlinedButton`, `ft.TextButton`,
  `ft.IconButton(icon_color=...)`.
- `ft.Dropdown` fires **`on_select`**, not `on_change`; options are
  `ft.DropdownOption(key=..., text=...)`; read `e.control.value`.
- `ft.InputBorder.NONE` is deprecated: use `ft.NoInputBorder()`,
  `ft.OutlineInputBorder(side=ft.BorderSide(...))`.
- `page.show_dialog(control)` / `page.pop_dialog()`; `ft.FilePicker` belongs in
  `page.services`, not `page.overlay`.
- `ft.Padding(left=, top=, right=, bottom=)`, `ft.Border.all(width, color)`,
  `ft.BorderRadius.all(radius)`.
- Verify icon names with `hasattr(ft.Icons, "NAME")`; the enum has no proxy fallback.
- `ft.Control.update()` raises `RuntimeError` when the control is not mounted.
- `ft.Pagelet` cannot live inside an unbounded scroll parent; it needs a bounded height.
- `ft.Stack` defaults to `StackFit.LOOSE`, which shrink-wraps children inside a stretching
  parent. Use `fit=ft.StackFit.PASS_THROUGH` when wrapping a control that must keep its
  parent's constraints (this is why design frames do not distort layout).
- A page-level `Column` needs `horizontal_alignment=STRETCH`, otherwise roots shrink-wrap.
- Drag and drop: `ft.Draggable(group=..., data=...)` and
  `ft.DragTarget(group=..., on_accept=, on_move=, on_leave=)`; `DragTargetEvent` exposes
  `data`, `local_position` and `src_id`.

## Adding a widget

1. Add a `WidgetSpec` in `catalogue/widgets.py`: properties with codec ids, creation defaults,
   slots (`minimum`, `maximum`, `accepted_types`), and the events the control really has.
2. If a property needs a shape no codec expresses, add a codec in `catalogue/codecs.py` and
   register it in `CODECS`.
3. Classify the widget in `ui/palette.py` (`CATEGORIES`, `ICONS`) — a test asserts the palette
   and catalogue agree exactly.
4. Run `pytest -q`. The conformance suite in `tests/catalogue_expansion/` lowers, renders and
   compiles every catalogue widget; a new widget with a bad default or an unrenderable symbol
   fails there.

## Adding a template

Add a builder to `services/templates.py` returning a `Project`, and register a `Template`.
Use only catalogue widget types and declared property names. The template tests round-trip
through the repository, lower, compile and render each template.

## Commands

```bash
python -m pytest -q                 # full suite
python -m pytest tests/canvas -q    # one area
python -m black src tests           # format (CI checks --check)
```
