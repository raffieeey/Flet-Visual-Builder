from src.utils.serializer import migrate_project_dict


def test_migrate_0_0_to_0_1() -> None:
    data = {"name": "Old", "tree": {"id": "root", "type": "Column", "children": []}}
    out = migrate_project_dict(data)
    assert out["schema_version"] == "0.1"
    assert out["theme"] == "light"
