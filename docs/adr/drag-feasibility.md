# Drag feasibility (T02a status)

T02a measured the headless half of drag-and-drop: pure geometry, model-level drop rejection, and synthetic-tree cost. It did not run a live native drag session.

## What was proved headlessly

Geometry primitives in `src/engine/geometry.py` (`rect_contains`, `rect_overlap`, `rect_intersects`, `classify_zone`, `to_target_local`, `in_target_local_bounds`) are pure functions. `classify_zone` was checked against `HitTestEngine._compute_zone` over a sweep of origins, heights (including zero), `accepts_children` flags, and vertical samples; the two agree. Coordinate conversion subtracts the aperture origin only — no scale, round, or extra transform.

`src/engine/drop_resolver.py` encodes the model rejection rules (self drop, descendant drop, vanished source, stale revision, incompatible slot, occupied single-child slot, invalid index, duplicate commit). Every reason has a test. Rejected resolutions do not mutate the tree: a `clone(deep_new_ids=False)` snapshot taken before `resolve_drop` compares equal afterwards. Index correction from pre-removal boundary to post-removal insert index happens once in the resolver.

Performance, measured on this machine by `src.engine.performance.measure([50, 250, 1000])` and stored in `benchmark/results/measure_50_250_1000.json`:

| node_count | build_ms | walk_ms | find_ms | serialize_ms | python_rss_mb |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 50 | 0.0993 | 0.0162 | 0.0171 | 0.1711 | 17.64 |
| 250 | 0.4320 | 0.0750 | 0.0759 | 0.7691 | 18.07 |
| 1000 | 1.4962 | 0.3088 | 0.3307 | 3.8481 | 19.30 |

These are one real run, not interpolated. Build time rose with node count. A thousand-node tree stayed well under a few milliseconds for walk/find and used about 19 MB RSS in this process. That is evidence that the Python tree engine is cheap at the T02 sizes; it is not evidence that a live canvas drag is viable.

## What was not run

The live native-drag gate and the 1280×800 geometry matrix (`flet test` / Flutter Linux desktop) were not run. That path needs system packages (`clang`, `libgtk-3-dev`, `pkg-config`) that require sudo, and those were not available for this ticket. T02b is the place for that gate.

## Open decision: geometry failure → rails-only mode

T02's rule that a geometry failure selects rails-only mode is still **open**. Headless math can be correct while pointer coordinates from a real Flet/Flutter hit test are not. Settling the decision needs T02b: a `flet test` run that compares native drag coordinates to `to_target_local` / `in_target_local_bounds` on a 1280×800 matrix, within one logical pixel. Until that run exists, this record does not choose rails-only or free-form drag.

No claim is made that drag-and-drop works in the builder UI. No native-drag result was invented.
