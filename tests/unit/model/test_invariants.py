"""Deterministic generated cases standing in for property-based tests.

hypothesis is not installed and must not be added. Each enumerated shape is
run through a fixed catalogue of commands; every committed result must satisfy
§2.3.4, and rejected/noop results must not mutate revision or document.
"""

from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from flet_visual_builder.contracts import (
    CommandADT,
    CommandStatus,
    DeleteNode,
    DropIntent,
    EventSymbol,
    InsertNode,
    MoveNode,
    SetEvent,
    SetProperty,
    UnsetProperty,
    WrapNode,
)
from flet_visual_builder.model.reducer import apply
from flet_visual_builder.model.validation import validate_project
from tests.unit.model.helpers import (
    column_named,
    column_with_texts,
    make_node,
    nested_containers,
)

MODEL_DIR = (
    Path(__file__).resolve().parents[3] / "src" / "flet_visual_builder" / "model"
)


def _shapes() -> list[tuple[str, object]]:
    shapes: list[tuple[str, object]] = []
    for count in range(0, 5):
        shapes.append((f"column_{count}", column_with_texts(count)))
    for depth in range(1, 6):
        shapes.append((f"nested_{depth}", nested_containers(depth)))
    shapes.append(("named4", column_named(("n0", "n1", "n2", "n3"))))
    return shapes


def _commands_for(snapshot) -> list[CommandADT]:
    project = snapshot.project
    commands: list[CommandADT] = [
        SetProperty(command_id="p0", node_id=None, name="title", value="T"),
        SetProperty(command_id="pnull", node_id=None, name="k", value=None),
        SetProperty(command_id="pfalse", node_id=None, name="k", value=False),
        SetProperty(command_id="pzero", node_id=None, name="k", value=0),
        UnsetProperty(command_id="u", node_id=None, name="missing"),
        InsertNode(
            command_id="ins",
            node=make_node("fresh", "Text", props={"value": "n"}),
            destination=DropIntent(parent_id=None, slot_name="controls", index=0),
        ),
    ]
    # Per-node ops.
    for node_id, node in project.nodes.items():
        commands.append(
            SetProperty(
                command_id=f"sp-{node_id}", node_id=node_id, name="visible", value=False
            )
        )
        commands.append(
            SetProperty(command_id=f"sz-{node_id}", node_id=node_id, name="n", value=0)
        )
        commands.append(
            UnsetProperty(command_id=f"un-{node_id}", node_id=node_id, name="nope")
        )
        commands.append(
            SetEvent(
                command_id=f"ev-{node_id}",
                node_id=node_id,
                event_name="on_click",
                symbol=EventSymbol(f"handle_{node_id}_click"),
            )
        )
        commands.append(
            SetEvent(
                command_id=f"evrm-{node_id}",
                node_id=node_id,
                event_name="on_click",
                symbol=None,
            )
        )
        commands.append(DeleteNode(command_id=f"del-{node_id}", node_id=node_id))
        commands.append(
            WrapNode(
                command_id=f"wrap-{node_id}",
                node_id=node_id,
                wrapper=make_node(f"w_{node_id}", "Container", slots={"content": ()}),
                wrapper_slot="content",
            )
        )
        for slot_name, children in node.slots.items():
            if children:
                commands.append(
                    MoveNode(
                        command_id=f"mv0-{node_id}",
                        node_id=children[0],
                        destination=DropIntent(
                            parent_id=node_id,
                            slot_name=slot_name,
                            index=len(children) - 1,
                        ),
                    )
                )
            commands.append(
                InsertNode(
                    command_id=f"ins-{node_id}-{slot_name}",
                    node=make_node(
                        f"x_{node_id}_{slot_name}",
                        "Text",
                        props={"value": "x"},
                    ),
                    destination=DropIntent(
                        parent_id=node_id, slot_name=slot_name, index=0
                    ),
                )
            )
    return commands


@pytest.mark.parametrize(
    "shape_id,snapshot", _shapes(), ids=lambda v: v if isinstance(v, str) else None
)
def test_generated_commands_preserve_invariants(
    shape_id: str, snapshot: object
) -> None:
    frozen = copy.deepcopy(snapshot)
    assert validate_project(snapshot.project) == ()  # type: ignore[attr-defined]
    for command in _commands_for(snapshot):  # type: ignore[arg-type]
        result = apply(snapshot, command)  # type: ignore[arg-type]
        assert copy.deepcopy(snapshot) == frozen
        if result.status is CommandStatus.COMMITTED:
            assert result.snapshot.revision == snapshot.revision + 1  # type: ignore[attr-defined]
            assert result.snapshot.project != snapshot.project  # type: ignore[attr-defined]
            assert validate_project(result.snapshot.project) == ()
        else:
            assert result.snapshot.revision == snapshot.revision  # type: ignore[attr-defined]
            assert result.snapshot.project == snapshot.project  # type: ignore[attr-defined]
            assert result.status in {CommandStatus.NOOP, CommandStatus.REJECTED}


def test_generated_shape_count_is_fixed() -> None:
    # Guard against silently shrinking the enumeration.
    assert len(_shapes()) == 5 + 5 + 1


def test_model_modules_do_not_import_flet() -> None:
    files = list(MODEL_DIR.glob("*.py"))
    assert files, f"no model modules under {MODEL_DIR}"
    for path in files:
        tree = ast.parse(path.read_text(encoding="utf-8"))

        class Visitor(ast.NodeVisitor):
            def visit_Import(self, node: ast.Import) -> None:
                for alias in node.names:
                    assert alias.name != "flet" and not alias.name.startswith("flet.")

            def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
                assert node.module != "flet"
                assert not (node.module or "").startswith("flet.")

        Visitor().visit(tree)
