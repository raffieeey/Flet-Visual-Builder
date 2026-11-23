# Build brief — Flet Visual Builder 0.2

Read this before touching code. It is the contract between parallel workstreams.

## Product definition

A visual builder for Flet interfaces: pick widgets from a palette, arrange them on a
canvas, edit typed properties, preview the real rendered result, and export clean,
runnable Python. It is a product, not a demo: no dead ends, no "coming soon" panels,
no silent failures.

Target the installed **Flet 1.0.1**. The repository is a normal src-layout package:

```
src/flet_visual_builder/
  contracts.py      frozen dataclasses shared by every layer
  app_context.py    Workspace controller (document, selection, dispatch, projections)
  catalogue/        widget specs, value codecs, page spec, enum/color/icon allowlists
  model/            pure reducer + validation (no Flet)
  engine/           lowering, runtime rendering, Python code generation
  state/            history dispatcher, editor state
  persistence/      JSON repository, migrations, assets
  interaction/      drag protocol, drop resolution (no Flet for pure parts)
  services/         session (dirty/recents/autosave), starter documents, templates
  ui/               every panel; theme.py holds the design tokens
```

Run tests with:

```bash
cd /home/afifah/flet-visual-builder && .venv/bin/python -m pytest -q
```

Do **not** run `git` commands, do not reformat unrelated files, and do not edit files
outside your lane's list. Another agent owns each neighbouring file.

## The one integration point: `Workspace`

`flet_visual_builder.app_context.Workspace` is passed to every panel. Panels never
talk to each other. Read the module; the important surface is:

| Member | Meaning |
| --- | --- |
| `ws.snapshot`, `ws.project`, `ws.revision` | current immutable document |
| `ws.catalogue` | widget specs (`widgets`, `new_props`, `page_properties`, codecs) |
| `ws.editor` | `selection`, `hover`, `active_tab`, `status` |
| `ws.session` | `path`, `dirty`, `label()`, `location()`, `recents()`, `remember()` |
| `ws.device`, `ws.device_width()` | canvas width preset |
| `ws.plan()`, `ws.plan_result()`, `ws.diagnostics()` | cached lowering output |
| `ws.artifact()` | cached generated Python artifact |
| `ws.renderer` | `RuntimeRenderer` (`render_plan`, `render_leaf_sample`) |
| `ws.select(id)`, `ws.set_tab(tab)`, `ws.set_device(key)` | chrome state |
| `ws.dispatch(command)` | execute a contract command; refreshes panels |
| `ws.insert/insert_relative/delete/move/wrap/duplicate` | structural edits |
| `ws.set_property/unset_property/set_event/rename_project` | property edits |
| `ws.undo/redo`, `ws.toast(msg, kind)`, `ws.report(diagnostics)` | actions |
| `ws.save_to/open_path/adopt/new_document` | document lifecycle |
| `ws.add_panel(panel)`, `ws.refresh(reason)` | panel registration and refresh |

### Panel contract

```python
class MyPanel(BasePanel):          # flet_visual_builder.ui.panel
    interests = frozenset({Refresh.SELECTION, Refresh.PROJECT})

    def __init__(self, workspace, extra=None):
        self.extra = extra
        super().__init__(workspace)   # calls build() once

    def build(self) -> ft.Control:
        ...
```

`refresh(reason)` rebuilds only when `reason` is in `interests` (empty set = always).
`Refresh.ALL` always rebuilds. `BasePanel.refresh` tolerates an unmounted control.

**Focus rule:** a panel that contains a text input must not rebuild on
`Refresh.DOCUMENT`, because a rebuild recreates the field and steals focus mid-typing.
Use `{Refresh.SELECTION, Refresh.PROJECT}` and update dependent widgets in place.

## Visual language

All colours, spacing, type sizes, and shared widgets come from
`flet_visual_builder.ui.theme`:

- tokens: `T.bg`, `T.panel`, `T.rail`, `T.border`, `T.border_soft`, `T.text`,
  `T.text_muted`, `T.text_faint`, `T.accent`, `T.accent_soft`, `T.canvas_bg`,
  `T.success`, `T.warning`, `T.danger`, `T.drop`, `T.code_bg`
- spacing: `XS=4 SM=8 MD=12 LG=16 XL=24`; radii `R_SM=4 R_MD=6 R_LG=10`
- metrics: `TOOLBAR_H=52 STATUS_H=26 RAIL_W=264 INSPECTOR_W=300`
- helpers: `text muted faint label icon_button button divider panel section
  empty_state pill status_dot separator_dot scroll`

Rules: no raw hex colours outside `theme.py`; 1px borders; 6px radii; quiet chrome and
a neutral canvas; the accent is reserved for selection and primary actions. Every
icon-only control needs a tooltip.

## Verified Flet 1.0.1 API rules

Never guess a parameter. Confirm with
`python -c "import dataclasses, flet as ft; print([f.name for f in dataclasses.fields(ft.X)])"`.

- Entry point is `ft.run(main)`. `ft.app` and `ft.ElevatedButton` do not exist.
- Buttons: `ft.Button(content=...)`, `ft.FilledButton`, `ft.OutlinedButton`,
  `ft.TextButton`, `ft.IconButton(icon_color=...)`.
- `ft.Dropdown` fires **`on_select`** (not `on_change`); options are
  `ft.DropdownOption(key=..., text=...)`; read `e.control.value`.
- Input borders: `ft.NoInputBorder()`, `ft.OutlineInputBorder(side=ft.BorderSide(...))`.
  `ft.InputBorder.NONE` is deprecated and fails the warning filter.
- `page.show_dialog(control)` / `page.pop_dialog()`; `ft.FilePicker` belongs in
  `page.services` (not `page.overlay`).
- `ft.Padding(left=, top=, right=, bottom=)`, `ft.Border.all(width, color)`,
  `ft.BorderRadius.all(radius)`, `ft.BorderSide(width=, color=)`.
- Verify every icon with `hasattr(ft.Icons, "NAME")` before shipping it.
- `ft.Control.update()` raises `RuntimeError` when the control is not mounted.
- Drag and drop: `ft.Draggable(group=..., data=...)` and
  `ft.DragTarget(group=..., on_accept=..., on_move=..., on_leave=...)`.
  `DragTargetEvent` exposes `data`, `local_position` (`x`, `y`), `src_id`.
- `ft.Container` accepts `on_click`, `on_tap_down`, `on_size_change`; `ft.Text`
  accepts `on_tap`.
- `ft.Markdown(value="```python\n...\n```")` renders highlighted code.

## Drag protocol (shared between palette and canvas)

```python
from flet_visual_builder.interaction.protocol import (
    DRAG_GROUP, encode_create, encode_move, decode_drag,
)
```

`encode_create("Text") -> "create:Text"`, `encode_move(node_id) -> "move:<id>"`,
`decode_drag(payload) -> ("create", "Text") | ("move", "<id>") | None`.
Both sides must use `DRAG_GROUP`.

## Definition of done for a lane

1. Your panels construct headlessly (`tests/support/fake_page.py`) and your module has
   focused tests that exercise real behaviour, not just imports.
2. `cd /home/afifah/flet-visual-builder && .venv/bin/python -m pytest -q` is green.
3. No new deprecation warnings (the suite treats them as errors in `flet_visual_builder.*`).
4. Your files pass `python -m py_compile`.
5. Report: files changed, what you verified, exact commands, and anything you could not
   finish. Never claim a check you did not run.

## Known environment limits

- The desktop GUI can only be exercised by the integrator; do headless construction tests.
- `pip install` is slow on this network; do not add dependencies.
