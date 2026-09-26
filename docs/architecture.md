# Architecture — module boundaries and ownership

Ratified from TDD v2 §2.3. This is a placement of the frozen contracts, not a redesign.

## Module tree (TDD v2 §2.3.2, rewritten with the real `src/` prefix)

```
src/flet_visual_builder/
  contracts.py

  model/
    reducer.py
    validation.py

  catalogue/
    widgets.py
    page.py
    codecs.py
    enum_manifest.py

  engine/
    lowering.py
    runtime.py
    codegen.py
    formatting.py

  interaction/
    hit_test.py
    drop_resolver.py
    drag_controller.py

  state/
    history_dispatcher.py
    editor_state.py

  persistence/
    json_repository.py
    migrations.py
    assets.py

  platform/
    file_gateway.py
    clipboard_gateway.py
    lifecycle.py

  ui/
    shell.py
    palette.py
    design_chrome.py
    node_frame.py
    tree_view.py
    properties.py
    live_preview.py
    code_preview.py
    diagnostics.py

  app.py
```

## Quoted rules (TDD v2 §2.3.2, exact)

model, catalogue, interaction, state, and JSON migration code must not import Flet at runtime.

Catalogue codecs produce typed symbolic values. Only engine/runtime.py, platform adapters, and UI modules turn those values into Flet objects.

## Ownership map

Ticket owners are taken from TDD v2 §2.9 ticket headers (`Files:`) and the §2.3.1 ownership table. Where the TDD does not name an owner, the module is `UNASSIGNED`.

| Module | Owner |
| --- | --- |
| `src/flet_visual_builder/contracts.py` | T03 |
| `src/flet_visual_builder/schema/project.schema.json` | T03 |
| `src/flet_visual_builder/model/reducer.py` | T04 |
| `src/flet_visual_builder/model/validation.py` | T04 |
| `src/flet_visual_builder/catalogue/widgets.py` | T05 |
| `src/flet_visual_builder/catalogue/page.py` | T05 |
| `src/flet_visual_builder/catalogue/codecs.py` | T05 |
| `src/flet_visual_builder/catalogue/enum_manifest.py` | T05 |
| `src/flet_visual_builder/engine/lowering.py` | T10 |
| `src/flet_visual_builder/engine/runtime.py` | T10 |
| `src/flet_visual_builder/engine/codegen.py` | T11 |
| `src/flet_visual_builder/engine/formatting.py` | T11 |
| `src/flet_visual_builder/interaction/hit_test.py` | T13 |
| `src/flet_visual_builder/interaction/drop_resolver.py` | T13 |
| `src/flet_visual_builder/interaction/drag_controller.py` | T13 |
| `src/flet_visual_builder/state/history_dispatcher.py` | T09 |
| `src/flet_visual_builder/state/editor_state.py` | T09 |
| `src/flet_visual_builder/persistence/json_repository.py` | T06 |
| `src/flet_visual_builder/persistence/migrations.py` | T06 |
| `src/flet_visual_builder/persistence/assets.py` | T06 |
| `src/flet_visual_builder/platform/file_gateway.py` | T15 |
| `src/flet_visual_builder/platform/clipboard_gateway.py` | T15 |
| `src/flet_visual_builder/platform/lifecycle.py` | T18 |
| `src/flet_visual_builder/ui/shell.py` | T08 |
| `src/flet_visual_builder/ui/palette.py` | T14 |
| `src/flet_visual_builder/ui/design_chrome.py` | T14 |
| `src/flet_visual_builder/ui/node_frame.py` | T14 |
| `src/flet_visual_builder/ui/tree_view.py` | T14 |
| `src/flet_visual_builder/ui/properties.py` | T12 |
| `src/flet_visual_builder/ui/live_preview.py` | T16 |
| `src/flet_visual_builder/ui/code_preview.py` | T16 |
| `src/flet_visual_builder/ui/diagnostics.py` | UNASSIGNED |
| `src/flet_visual_builder/app.py` | T16 |

§2.3.1 area owners (for interfaces, not extra modules): shared contracts T03; pure command reduction T04; final history-aware `CommandDispatcher` T09; widget definitions and pure value lowering T05; clean runtime rendering and leaf samples T10; drag session and drop resolution T13; Design frames, handles, rails, and targets T14 only; application composition T16.

T10 does not construct Design chrome. T14 does not implement a second application renderer. Only the contract owner changes `contracts.py`.
