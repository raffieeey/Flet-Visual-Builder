# Architecture

The editor is a pipeline. A user action becomes a command, the command produces a new
immutable document, and every view is a projection of that document. Nothing in the UI
mutates the document directly.

```
UI event
  -> Workspace.dispatch(command)
      -> HistoryDispatcher.execute(command, expected_revision)
          -> Reducer.apply(snapshot, command)        pure, no Flet
              -> validation (slots, depth, ids, values)
          -> new DocumentSnapshot (revision + 1)
      -> panels refresh for a named reason

DocumentSnapshot
  -> Lowering.lower_project(snapshot, catalogue)     -> ControlPlan
      -> RuntimeRenderer.render_plan(plan)           -> live ft.Control tree
      -> Codegen.generate_python(plan, options)      -> Python source
```

## Modules

```
src/flet_visual_builder/
  contracts.py            frozen dataclasses shared by every layer
  app_context.py          Workspace: document, selection, dispatch, projections, panels

  catalogue/              widget specs, typed value codecs, page spec, enum/colour/icon allowlists
  model/                  command reducer and document invariants (no Flet)
  engine/                 lowering, runtime rendering, Python generation, formatting
  state/                  history dispatcher and editor chrome state (no Flet)
  persistence/            JSON repository, migrations, assets
  interaction/            drag protocol and drop resolution
  services/               project session, starter documents, templates
  ui/                     panels and the composition root
    theme.py              design tokens and shared primitives
    panel.py              BasePanel contract
    app.py                build(): page setup, panels, shell, shortcuts, file actions
```

`app_context.Workspace` is the only object panels share. A panel gets it in the constructor,
reads state from it, calls its command helpers, and implements `refresh(reason)`.

## Why the split exists

- **Determinism.** Documents are immutable and commands are pure, so undo/redo is a stack of
  snapshots and any projection can be recomputed from a revision.
- **Testability.** The reducer, catalogue, lowering and code generation are ordinary Python
  with no Flet import. The whole engine is covered by unit and contract tests that never need
  a display.
- **One source of truth for widgets.** The palette, inspector, validator, renderer and code
  generator all read the same `WidgetSpec`. Adding a widget is a catalogue change, not five
  coordinated edits.
- **Safety.** Generated code is produced from allowlisted symbols and validated as text
  (AST + `py_compile`). The editor never executes user documents.

## Screens and navigation

A document is multi-screen: every entry in `root_ids` is a screen, and `Project.screens` maps
that root to a `ScreenMeta(title, route)`. Documents written before screens existed have no
metadata, so `model/screens.py` derives stable defaults (`Home` at `/`, then `/screen-N`).

Navigation is data, not code:

```json
"nodes": {
  "cta": {
    "id": "cta", "type_id": "Button", "props": {"content": "Review queue"},
    "slots": {}, "events": {},
    "actions": {"on_click": {"type": "navigate", "route": "/reviews"}}
  }
}
```

The reducer validates that the route exists, retargets actions when a route is renamed, and
strips them when a screen is deleted. Codegen turns the plan into one builder per screen plus a
route table and a `ft.View` router; Flet 1.0.1 has no `page.go`, so navigation is emitted as
`page.run_task(page.push_route, route)`.

## Invariants

Enforced by `model/validation.py` on every commit:

- node ids are identifier-safe and unique; the node map key matches `node.id`
- every child id exists and appears in exactly one slot
- slot cardinality (`minimum`, `maximum`) and accepted types hold
- depth and node-count limits hold
- property values validate against their codec
- event symbols follow `handle_<node>_<event>`
- screen routes are unique, start with `/`, and `initial_route` matches one of them
- every navigation action targets a route that still exists

## Extension points

**Add a widget.** Add a `WidgetSpec` in `catalogue/widgets.py` (properties with codec ids,
creation defaults, slots, events). If a property needs a value shape no codec expresses, add
a codec in `catalogue/codecs.py`. Then add a conformance case: the suite in
`tests/catalogue_expansion/` runs every catalogue widget through validation, lowering,
rendering and code generation.

**Add a template.** Add a builder to `services/templates.py` returning a `Project`. Use only
catalogue widget types and declared property names; the template tests load, lower, compile
and render every template.

**Add a panel.** Subclass `ui.panel.BasePanel`, declare the refresh reasons you care about,
build your control in `build()`, register the panel in `ui/app.py` and mount it into a shell
region.

**Add a codec.** Implement `validate(value)` and `lower(value)` in `catalogue/codecs.py`,
register it in `CODECS`, and give the inspector an editor in `ui/editors.py`.

## Refresh reasons

Panels rebuild only for reasons they subscribe to:

| Reason | Meaning |
| --- | --- |
| `ALL` | initial mount, or an explicit full rebuild |
| `DOCUMENT` | the node graph or a property changed |
| `SELECTION` | selection moved, document unchanged |
| `PROJECT` | a different document was adopted |
| `CHROME` | save/dirty/undo availability changed |
| `LAYOUT` | device width or active tab changed |
| `STATUS` | status text only |

Panels that contain a text input must not rebuild on `DOCUMENT`; rebuilding recreates the
field and steals focus mid-typing. Those panels update dependent widgets in place instead.

## File format

`.fvb.json` is a versioned document:

```json
{
  "schema_version": 2,
  "catalogue_version": 1,
  "target_flet": "1.0.1",
  "name": "Dashboard",
  "page": {"title": "Dashboard", "padding": 0, "scroll": "AUTO"},
  "root_ids": ["root"],
  "nodes": {
    "root": {
      "id": "root",
      "type_id": "Column",
      "props": {},
      "slots": {"controls": []},
      "events": {}
    }
  },
  "assets": {}
}
```

Loading runs migrations for older schema versions, validates the whole document, and rejects
anything that violates an invariant. Saves are atomic and bounded in size.
