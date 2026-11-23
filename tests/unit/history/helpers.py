"""Shared builders for history dispatcher tests."""

from __future__ import annotations

from flet_visual_builder.contracts import (
    CommandADT,
    DropIntent,
    InsertNode,
    SetProperty,
)
from flet_visual_builder.state.history_dispatcher import HistoryDispatcher
from tests.unit.model.helpers import column_with_texts, make_node, make_snapshot

__all__ = [
    "FakeClock",
    "column_with_texts",
    "insert_text",
    "make_node",
    "make_snapshot",
    "run",
    "set_prop",
]


class FakeClock:
    def __init__(self, t: float = 0.0) -> None:
        self.t = t

    def __call__(self) -> float:
        return self.t

    def advance(self, seconds: float) -> None:
        self.t += seconds


def run(dispatcher: HistoryDispatcher, command: CommandADT):
    return dispatcher.execute(command, expected_revision=dispatcher.snapshot.revision)


def insert_text(
    dispatcher: HistoryDispatcher,
    node_id: str,
    *,
    command_id: str | None = None,
    index: int | None = None,
):
    controls = dispatcher.snapshot.project.nodes["root"].slots["controls"]
    at = len(controls) if index is None else index
    return run(
        dispatcher,
        InsertNode(
            command_id=command_id or f"ins-{node_id}",
            node=make_node(node_id, "Text", props={"value": node_id}),
            destination=DropIntent(parent_id="root", slot_name="controls", index=at),
        ),
    )


def set_prop(
    dispatcher: HistoryDispatcher,
    *,
    command_id: str,
    node_id: str | None,
    name: str,
    value: object,
    gesture_id: str | None = None,
):
    return run(
        dispatcher,
        SetProperty(
            command_id=command_id,
            gesture_id=gesture_id,
            node_id=node_id,
            name=name,
            value=value,  # type: ignore[arg-type]
        ),
    )
