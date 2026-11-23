# Changelog

All notable changes to this project. The format follows Keep a Changelog, and versions use
semantic versioning.

## 0.2.0

The first release that is a usable editor rather than a prototype.

### Added

- **Designed templates, verified visually.** Login, Dashboard, Settings, Profile and
  Onboarding were rebuilt on a shared visual language (bounded centred content columns,
  per-template accent skins, stronger hierarchy) and each was reviewed from rendered
  screenshots rather than assumed.
- **`tools/shoot.py`**: renders a document's exported `app.py` in a real Flet client on a
  private X display and captures a PNG, so screenshots and visual review always reflect the
  shipped output.
- **Editor workspace** with a toolbar, widget palette, outline, design canvas, inspector,
  live preview, code view, diagnostics drawer and status bar.
- **Design canvas** that renders real Flet controls inside selectable frames, with hover
  feedback, drag-to-reorder and palette drops with before/inside/after indicators.
- **Widget catalogue expanded from 16 to 43 widgets**, including `Stack`, `GridView`,
  `ResponsiveRow`, `SafeArea`, `ExpansionTile`, `Markdown`, `Dropdown`, `Slider`,
  `RadioGroup`, `SegmentedButton`, `Tabs`, `TabBar`, `TabBarView`, `NavigationBar`,
  `ListTile`, `Chip`, `CircleAvatar`, `ProgressRing`, `FilledButton`, `OutlinedButton` and
  `FloatingActionButton`.
- **Page properties**: background colour, adaptive, RTL and page-level cross alignment, all
  rendered and exported.
- **Typed inspector** with per-codec editors (colour swatches, enum dropdowns, icon picker,
  padding/margin/radius composites, borders), reset-to-default, event binding and inline
  validation.
- **Template gallery** with five designed documents: Login, Dashboard, Settings, Profile and
  Onboarding.
- **New document, about and keyboard-shortcut dialogs.**
- **Project session**: dirty tracking, recent paths and a throttled crash-safe autosave that
  is offered back at the next launch.
- **Commands `RenameProject` and `PasteNodes`** so renaming keeps undo history and duplicating
  a container is a single atomic, undoable edit.
- **Browser target**: `flet-visual-builder --web`, with a `web` extra that pins the compatible
  FastAPI version.
- **`--mode design|preview|code`** to open straight into a view.
- **CI** running the test suite on Python 3.11 and 3.12, a format check, a wheel build and an
  install/entry-point smoke test.

### Changed

- Consolidated the repository onto a single package. The earlier parallel `src/` prototype was
  removed; everything now builds on the contract-driven engine.
- Repackaged as a proper src-layout distribution with a `flet-visual-builder` console script.
- Rewrote the README and architecture docs, and added a contributor guide with the verified
  Flet 1.0.1 API rules.
- Design frames use `StackFit.PASS_THROUGH` so selection chrome does not distort layout.
- Page roots stretch by default, matching a real Flet page.

### Fixed

- `Divider` no longer exposes a `width` property its Flet constructor rejects; setting it
  used to generate code that crashed at runtime. A new contract test checks every catalogue
  property and slot against the real Flet constructor, so this cannot recur.
- Duplicating a node with children no longer fails validation, and cloned event handlers get
  fresh symbol names.
- `Delete`/`Backspace` no longer deletes the selected node while typing in a text field.
- The status bar is a real mounted panel instead of an empty placeholder.
- Inspector metadata reads as human words (`Alignment`, `Number`, `Toggle`) instead of codec
  identifiers.
- Runtime and code-generation diagnostics are merged into the shared diagnostics list without
  duplicating lowering errors.

### Removed

- The legacy `src/engine`, `src/models`, `src/ui`, `src/state` and `src/utils` prototype and
  its tests, plus stale benchmark fixtures and 0.1 schema templates.
