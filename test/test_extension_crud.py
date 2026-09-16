"""TDD coverage for extension.py prompt CRUD operations."""

import importlib.util
from pathlib import Path


ROOT = Path(__file__).parents[1]
spec = importlib.util.spec_from_file_location("prompthub_extension", ROOT / "extensions" / "extension.py")
extension = importlib.util.module_from_spec(spec)
spec.loader.exec_module(extension)


def test_extension_prompt_crud_with_registered_tags(tmp_path, monkeypatch):
    database = tmp_path / "prompthub.db"
    monkeypatch.setattr(extension, "DB_PATH", database)
    extension.init_db([])

    created = extension.create_prompt(
        title="CRUD agent",
        body="Follow the rules.",
        prompt_type="System prompt",
        tags=["criticality:high", "data:demo"],
        validate_tags=True,
    )
    assert created["id"] == 1
    assert created["tags"] == ["criticality:high", "data:demo"]
    assert created["updated_at"]
    assert extension.read_table("tags_registered")[0]["updated_at"]

    assert extension.get_prompt(created["id"])["body"] == "Follow the rules."
    updated = extension.update_prompt(
        created["id"], body="Follow the updated rules.", tags=["criticality:critical"]
    )
    assert updated["criticality"] == "critical"
    assert updated["tags"] == ["criticality:critical"]
    assert updated["updated_at"]

    assert extension.delete_prompt(created["id"]) is True
    assert extension.get_prompt(created["id"]) is None


def test_registered_tag_crud(tmp_path, monkeypatch):
    database = tmp_path / "prompthub.db"
    monkeypatch.setattr(extension, "DB_PATH", database)
    extension.init_db([])

    assert extension.create_tag("team:security") == "team:security"
    assert "team:security" in extension.read_tags()
    assert extension.update_tag("team:security", "team:safety") is True
    assert "team:safety" in extension.read_tags()
    assert extension.delete_tag("team:safety") is True
    assert "team:safety" not in extension.read_tags()


def test_registered_tag_rejects_duplicates(tmp_path, monkeypatch):
    database = tmp_path / "prompthub.db"
    monkeypatch.setattr(extension, "DB_PATH", database)
    extension.init_db([])
    extension.create_tag("team:security")
    try:
        extension.create_tag("TEAM:SECURITY")
    except ValueError as error:
        assert "already registered" in str(error)
    else:
        raise AssertionError("duplicate tag was accepted")


def test_extension_rejects_unregistered_tags(tmp_path, monkeypatch):
    database = tmp_path / "prompthub.db"
    monkeypatch.setattr(extension, "DB_PATH", database)
    extension.init_db([])

    try:
        extension.create_prompt("Invalid", "Body", tags=["not-registered"], validate_tags=True)
    except ValueError as error:
        assert "not registered" in str(error)
    else:
        raise AssertionError("unregistered tag was accepted")
