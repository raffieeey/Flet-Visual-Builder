from src.models.enum_map import ENUM_MAP
from src.models.widget_registry import WIDGET_REGISTRY, enum_key_for


def test_registry_enum_values_exist_in_map() -> None:
    for widget_name, widget in WIDGET_REGISTRY.items():
        for prop_name, prop_spec in widget["props"].items():
            if prop_spec["type"] == "enum":
                key = enum_key_for(widget_name, prop_name)
                assert key in ENUM_MAP
                for option in prop_spec["options"]:
                    assert option in ENUM_MAP[key]
