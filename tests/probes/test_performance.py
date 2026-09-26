from __future__ import annotations

from src.engine.performance import TREE_FANOUT, build_tree, measure
from src.engine.tree_ops import walk


REQUIRED_KEYS = {
    "node_count",
    "build_ms",
    "walk_ms",
    "find_ms",
    "serialize_ms",
    "python_rss_mb",
}


def test_build_tree_has_requested_node_count() -> None:
    for count in (1, 8, 50):
        tree = build_tree(count)
        assert sum(1 for _ in walk(tree)) == count


def test_measure_returns_requested_counts_and_record_shape() -> None:
    counts = [50, 250, 1000]
    records = measure(counts)
    assert [record["node_count"] for record in records] == counts
    for record in records:
        assert REQUIRED_KEYS <= set(record)
        assert record["python_rss_mb"] > 0.0
        for key in ("build_ms", "walk_ms", "find_ms", "serialize_ms"):
            assert record[key] >= 0.0


def test_measure_build_time_is_monotonic_non_decreasing() -> None:
    records = measure([50, 250, 1000])
    build_times = [record["build_ms"] for record in records]
    assert build_times == sorted(build_times)
    assert TREE_FANOUT >= 1
