from __future__ import annotations

import json
import os
import resource
import time
from collections import deque
from collections.abc import Sequence

from src.engine.tree_ops import find_node, insert_child, walk
from src.models.widget_node import WidgetNode
from src.utils.serializer import node_to_dict

# Fan-out used by build_tree. Documented in benchmark/fixtures/.
TREE_FANOUT = 8
ROOT_TYPE = "Column"
CHILD_TYPE = "Column"
CHILD_SLOT = "controls"


def build_tree(node_count: int) -> WidgetNode:
    """Build a synthetic widget tree with exactly *node_count* nodes."""
    if node_count < 1:
        raise ValueError("node_count must be >= 1")
    root = WidgetNode(id="n0", type=ROOT_TYPE)
    if node_count == 1:
        return root
    frontier: deque[WidgetNode] = deque([root])
    created = 1
    while created < node_count:
        parent = frontier[0]
        child = WidgetNode(id=f"n{created}", type=CHILD_TYPE)
        insert_child(parent, child, slot=CHILD_SLOT)
        frontier.append(child)
        created += 1
        if len(parent.children) >= TREE_FANOUT:
            frontier.popleft()
    return root


def measure(node_counts: Sequence[int]) -> list[dict]:
    """Measure build/walk/find/serialize cost for each requested node count."""
    records: list[dict] = []
    for node_count in node_counts:
        t0 = time.perf_counter()
        tree = build_tree(node_count)
        build_ms = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        nodes = list(walk(tree))
        walk_ms = (time.perf_counter() - t0) * 1000.0

        last_id = nodes[-1].id
        t0 = time.perf_counter()
        find_node(tree, last_id)
        find_ms = (time.perf_counter() - t0) * 1000.0

        t0 = time.perf_counter()
        json.dumps(node_to_dict(tree))
        serialize_ms = (time.perf_counter() - t0) * 1000.0

        records.append(
            {
                "node_count": node_count,
                "build_ms": build_ms,
                "walk_ms": walk_ms,
                "find_ms": find_ms,
                "serialize_ms": serialize_ms,
                "python_rss_mb": _python_rss_mb(),
            }
        )
    return records


def _python_rss_mb() -> float:
    """Current process RSS in mebibytes (Linux /proc, else ru_maxrss)."""
    try:
        with open("/proc/self/statm", encoding="utf-8") as fh:
            resident_pages = int(fh.read().split()[1])
        page_size = os.sysconf("SC_PAGE_SIZE")
        return resident_pages * page_size / (1024.0 * 1024.0)
    except OSError:
        # Linux reports ru_maxrss in kilobytes.
        return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0
