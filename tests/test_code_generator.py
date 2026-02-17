from src.engine.code_generator import generate_code
from src.models.widget_node import WidgetNode


def test_generate_code_with_event_handler() -> None:
    root = WidgetNode(
        id="root",
        type="Column",
        props={"alignment": "center"},
        children=[WidgetNode(id="btn", type="ElevatedButton", props={"text": "Go", "on_click": "on_go"}, slot="controls")],
    )
    code = generate_code(root)
    assert "def on_go(e: ft.ControlEvent):" in code
    assert "ft.Column" in code
    assert "ft.MainAxisAlignment.CENTER" in code
