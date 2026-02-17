import pytest

from src.engine.validator import ValidationError, validate_tree
from src.models.widget_node import WidgetNode


def test_validation_rejects_invalid_enum() -> None:
    node = WidgetNode(id="x", type="Text", props={"weight": "extra"})
    with pytest.raises(ValidationError, match="Invalid value"):
        validate_tree(node)


def test_validation_rejects_leaf_children() -> None:
    node = WidgetNode(id="x", type="Text", children=[WidgetNode(id="c", type="Text")])
    with pytest.raises(ValidationError, match="does not accept children"):
        validate_tree(node)
