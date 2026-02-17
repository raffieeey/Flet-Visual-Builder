# Flet Visual Builder

Flet Visual Builder (FVB) is a drag-and-drop UI builder for Flet apps.

## Current MVP foundation

This repository now includes the core architecture required by the TDD:

- Widget tree model (`WidgetNode`) with slot-aware children
- Widget registry and centralized enum mapping
- Tree operations (insert/delete/move/reorder/wrap)
- Validation engine for export safety
- Code generation (`WidgetNode` → runnable Flet Python)
- Project serialization, migrations, save/load helpers
- App state with snapshot-based undo/redo
- Unit test suite for the core engine modules

## Run

```bash
pip install -r requirements.txt
python main.py
```

## Test

```bash
pytest -q
```
