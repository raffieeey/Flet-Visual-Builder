from src.engine.tree_ops import delete_node, insert_child, move_node, reorder_sibling, wrap_node
from src.models.widget_node import WidgetNode


def test_insert_and_delete_node() -> None:
    root = WidgetNode(id="root", type="Column")
    child = WidgetNode(id="t1", type="Text")
    insert_child(root, child, slot="controls")
    assert len(root.children) == 1
    assert delete_node(root, "t1") is True
    assert not root.children


def test_move_and_reorder_node() -> None:
    root = WidgetNode(id="root", type="Column")
    a = WidgetNode(id="a", type="Text")
    b = WidgetNode(id="b", type="Text")
    target = WidgetNode(id="target", type="Column")
    insert_child(root, a, slot="controls")
    insert_child(root, b, slot="controls")
    insert_child(root, target, slot="controls")
    assert reorder_sibling(root, "b", -1)
    assert root.children[0].id == "b"
    assert move_node(root, "a", "target", slot="controls")
    assert target.children[0].id == "a"


def test_wrap_node() -> None:
    root = WidgetNode(id="root", type="Column")
    text = WidgetNode(id="t1", type="Text", slot="controls")
    root.children = [text]
    wrapper = WidgetNode(id="c1", type="Container")
    assert wrap_node(root, "t1", wrapper)
    assert root.children[0].id == "c1"
    assert wrapper.children[0].id == "t1"
    assert wrapper.children[0].slot == "content"
