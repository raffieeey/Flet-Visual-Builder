from src.models.widget_node import WidgetNode
from src.state.project_state import ProjectState
from src.utils.serializer import project_from_dict, project_to_dict


def test_project_roundtrip() -> None:
    root = WidgetNode(id="root", type="Column", children=[WidgetNode(id="t1", type="Text", slot="controls")])
    project = ProjectState(name="Demo", tree=root)
    restored = project_from_dict(project_to_dict(project))
    assert restored.name == "Demo"
    assert restored.tree.children[0].id == "t1"
