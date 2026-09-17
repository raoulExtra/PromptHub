"""API coverage for PromptHub's FastAPI application."""

import sqlite3

import pytest
from fastapi.testclient import TestClient

import main
from extensions import extension


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Replace main.py's process-global database with a temporary one."""
    connection = sqlite3.connect(":memory:", check_same_thread=False)
    cursor = connection.cursor()
    cursor.execute(
        """CREATE TABLE PromptHub (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            prompt_name VARCHAR(100) NOT NULL UNIQUE,
            prompt_body TEXT NOT NULL,
            date DATE NOT NULL,
            tag VARCHAR(50),
            category VARCHAR(50) NOT NULL,
            tags TEXT NOT NULL DEFAULT '',
            updated_at TEXT NOT NULL,
            cycle TEXT NOT NULL DEFAULT 'none',
            routine_confirmed INTEGER NOT NULL DEFAULT 0,
            routine_period TEXT NOT NULL DEFAULT ''
        )"""
    )
    cursor.execute("CREATE TABLE tags_registered (name TEXT PRIMARY KEY NOT NULL, color TEXT, updated_at TEXT NOT NULL)")
    connection.commit()
    cursor.execute(
        """CREATE VIEW agent_prompts AS
        SELECT id, prompt_name, prompt_body, date, category, tags,
               CASE
                 WHEN (',' || lower(tags) || ',') LIKE '%,criticality:critical,%' THEN 4
                 WHEN (',' || lower(tags) || ',') LIKE '%,criticality:high,%' THEN 3
                 WHEN (',' || lower(tags) || ',') LIKE '%,criticality:medium,%' THEN 2
                 WHEN (',' || lower(tags) || ',') LIKE '%,criticality:low,%' THEN 1
                 ELSE 0
               END AS criticality_rank
        FROM PromptHub
        WHERE lower(category) IN ('system prompt', 'agent prompt')
        """
    )
    connection.commit()
    monkeypatch.setattr(main, "conn", connection)
    monkeypatch.setattr(main, "cursor", cursor)
    yield TestClient(main.app)
    connection.close()


def prompt(title="Agent", body="Do the work", prompt_type="System prompt", tags=None):
    return {
        "title": title,
        "body": body,
        "favorite": "Favorite",
        "type": prompt_type,
        "tags": tags or [],
    }


def test_registered_tag_api(client):
    response = client.post("/api/tags", json={"name": "team:security"})
    assert response.status_code == 200
    assert response.json() == "team:security"
    assert "team:security" in client.get("/api/tags").json()

    response = client.put("/api/tags/team:security", json={"new_name": "team:safety"})
    assert response.status_code == 200
    assert response.json() == "team:safety"
    assert client.delete("/api/tags/team:safety").status_code == 200


def test_delete_tag_can_detach_prompt_assignments(client):
    client.post("/api/tags", json={"name": "team:ops"})
    created = client.post("/api/prompts", json=prompt(tags=["team:ops"])).json()
    response = client.delete("/api/tags/team:ops?detach=true")
    assert response.status_code == 200
    assert response.json()["detached"] is True
    assert "team:ops" not in client.get("/api/prompts").json()[0]["tags"]


def test_create_and_list_prompts(client):
    response = client.post("/api/prompts", json=prompt(tags=["coding", "criticality:high"]))
    assert response.status_code == 200
    created = response.json()
    assert created["title"] == "Agent"
    assert created["criticality"] == "high"
    other = client.post("/api/prompts", json=prompt(title="Misc", prompt_type="Other")).json()
    assert other["type"] == "Other"
    assert len(client.get("/api/prompts?search=Age*").json()) == 1
    assert [item["title"] for item in client.get("/api/prompts?search=A%25").json()] == ["Agent"]

    response = client.get("/api/prompts")
    assert response.status_code == 200
    assert response.json()[0]["tags"] == ["coding", "criticality:high"]


def test_prompt_filters_and_search(client):
    client.post("/api/prompts", json=prompt(tags=["coding", "criticality:high"]))
    client.post(
        "/api/prompts",
        json=prompt(
            title="User note",
            body="Write a report",
            prompt_type="User prompt",
            tags=["writing", "criticality:low"],
        ),
    )

    assert len(client.get("/api/prompts?tag=Favorite").json()) == 2
    assert len(client.get("/api/prompts?category=User%20prompt").json()) == 1
    assert len(client.get("/api/prompts?custom_tag=coding").json()) == 1
    assert len(client.get("/api/prompts?criticality=low").json()) == 1
    assert len(client.get("/api/prompts?search=writing").json()) == 1


def test_tags_endpoint_excludes_criticality_tags(client):
    client.post("/api/tags", json={"name": "coding"})
    client.post("/api/prompts", json=prompt(tags=["coding", "criticality:critical"]))
    response = client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == ["coding"]


def test_agent_feed_is_criticality_ordered_and_filterable(client):
    client.post("/api/prompts", json=prompt(title="Low", tags=["criticality:low"]))
    client.post("/api/prompts", json=prompt(title="Critical", tags=["criticality:critical"]))
    client.post("/api/prompts", json=prompt(title="User", prompt_type="User prompt", tags=["criticality:critical"]))

    response = client.get("/api/prompts/agent")
    assert response.status_code == 200
    assert [item["title"] for item in response.json()] == ["Critical", "Low"]
    assert [item["title"] for item in client.get("/api/prompts/agent?criticality=critical").json()] == ["Critical"]
    assert client.get("/api/prompts/agent?criticality=bogus").status_code == 400


def test_extension_reads_all_tables(tmp_path, monkeypatch):
    database = tmp_path / "prompthub.db"
    connection = sqlite3.connect(database)
    connection.executescript(
        """CREATE TABLE PromptHub (id INTEGER PRIMARY KEY, prompt_name TEXT, prompt_body TEXT,
           date TEXT, tag TEXT, category TEXT, tags TEXT);
        CREATE TABLE tags_registered (name TEXT PRIMARY KEY);
        INSERT INTO PromptHub VALUES (1, 'Agent', 'Be precise', '2026-01-01', 'Favorite', 'System prompt', 'coding');
        INSERT INTO tags_registered VALUES ('coding');"""
    )
    connection.commit()
    connection.close()
    monkeypatch.setattr(extension, "DB_PATH", database)

    assert extension.list_tables() == ["PromptHub", "tags_registered"]
    assert extension.read_table("tags_registered") == [{"name": "coding"}]
    tables = extension.read_all_tables()
    assert tables["PromptHub"][0]["prompt_name"] == "Agent"
    assert tables["tags_registered"] == [{"name": "coding"}]


def test_update_and_delete_prompt(client):
    created = client.post("/api/prompts", json=prompt()).json()
    prompt_id = created["id"]

    response = client.put(f"/api/prompts/{prompt_id}", json={"body": "Updated", "type": "User prompt"})
    assert response.status_code == 200
    assert response.json() == {"message": "Update request received", "id": prompt_id, "body": "Updated", "type": "User prompt", "tags": None}
    assert client.get("/api/prompts").json()[0]["body"] == "Updated"
    assert client.get("/api/prompts").json()[0]["type"] == "User prompt"

    response = client.delete(f"/api/prompts/{prompt_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Deleted successfully"}
    assert client.get("/api/prompts").json() == []
