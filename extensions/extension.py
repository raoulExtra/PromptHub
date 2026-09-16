"""Read PromptHub prompts for Python integrations and LLM extensions.

This module is intentionally read-only. It exposes small Python functions so an
extension can retrieve prompts without duplicating PromptHub's database logic.
"""

from __future__ import annotations

import argparse
import importlib.util
import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Any


EXTENSION_VERSION = "1.0"
DB_PATH = Path(__file__).resolve().parents[1] / "backend" / "database" / "prompthub.db"
IMPORT_EXPORT_PATH = Path(__file__).resolve().parent / "import-export" / "import-export.py"
CRITICALITY_LEVELS = {"normal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
COLOR_PRESETS = {
    "light_green": "#90ee90", "dark_green": "#006400",
    "light_blue": "#add8e6", "dark_blue": "#00008b",
    "light_red": "#ffcccb", "dark_red": "#8b0000",
    "light_yellow": "#ffffe0", "dark_yellow": "#b8860b",
    "purple": "#800080", "orange": "#ffa500", "gray": "#808080",
}


def resolve_color(color: str | None) -> str | None:
    if color is None:
        return None
    value = color.strip().lower()
    return COLOR_PRESETS.get(value, color.strip()) or None


def _import_export_module():
    """Load the hyphenated import/export utility as a Python submodule."""
    spec = importlib.util.spec_from_file_location("prompthub_import_export", IMPORT_EXPORT_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load import/export module: {IMPORT_EXPORT_PATH}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Prompt database not found: {DB_PATH}")
    # SQLite URI mode=ro prevents an extension from accidentally changing data.
    connection = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def _write_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def _quote_identifier(name: str) -> str:
    """Quote a SQLite identifier after validating it is a non-empty string."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("table name must be a non-empty string")
    return '"' + name.replace('"', '""') + '"'


def init_db(prompts: list[dict[str, Any]] | None = None) -> int:
    """Create the prompt table and seed prompts with different criticalities.

    Pass ``prompts`` to provide custom records. When omitted, a small default
    set is inserted so the database is immediately useful for demos and export.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """CREATE TABLE IF NOT EXISTS PromptHub (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                prompt_name VARCHAR(100) NOT NULL UNIQUE,
                prompt_body TEXT NOT NULL,
                date DATE NOT NULL,
                tag VARCHAR(50),
                category VARCHAR(50) NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )"""
        )
        columns = {row[1] for row in connection.execute("PRAGMA table_info(PromptHub)")}
        if "tags" not in columns:
            connection.execute("ALTER TABLE PromptHub ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
        if "updated_at" not in columns:
            connection.execute("ALTER TABLE PromptHub ADD COLUMN updated_at TEXT")
            connection.execute("UPDATE PromptHub SET updated_at = date WHERE updated_at IS NULL")
        connection.execute(
            "CREATE TABLE IF NOT EXISTS tags_registered (name TEXT PRIMARY KEY NOT NULL, color TEXT, updated_at TEXT NOT NULL)"
        )
        tag_columns = {row[1] for row in connection.execute("PRAGMA table_info(tags_registered)")}
        if "color" not in tag_columns:
            connection.execute("ALTER TABLE tags_registered ADD COLUMN color TEXT")
        if "updated_at" not in tag_columns:
            connection.execute("ALTER TABLE tags_registered ADD COLUMN updated_at TEXT")
            connection.execute("UPDATE tags_registered SET updated_at = ? WHERE updated_at IS NULL",
                               (datetime.now().isoformat(timespec="seconds"),))
        connection.executemany(
            "INSERT OR IGNORE INTO tags_registered (name, updated_at) VALUES (?, ?)",
            [(tag, datetime.now().isoformat(timespec="seconds")) for tag in (
                "criticality:critical", "criticality:high", "criticality:medium",
                "criticality:low", "data:demo", "governance:system_instruction",
            )],
        )
        demo_seed = prompts is None
        seed_prompts = prompts if prompts is not None else [
            {"title": "Safety rules", "body": "Do not read from the protected folder or any of its subfolders.", "tags": ["criticality:critical", "data:demo", "governance:system_instruction"]},
            {"title": "Answer format", "body": "Answer clearly and concisely.", "tags": ["criticality:high", "data:demo", "governance:system_instruction"]},
            {"title": "Core requirement documentation", "body": "In docs create ###-CREQ-<title>.md files describing all core requirements of our code and db with acc criterias.", "tags": ["criticality:high", "data:demo", "governance:system_instruction"]},
            {"title": "Context handling", "body": "Use the available context when relevant.", "tags": ["criticality:medium", "data:demo", "governance:system_instruction"]},
            {"title": "Optional style", "body": "Prefer helpful examples when useful.", "tags": ["criticality:low", "data:demo", "governance:system_instruction"]},
        ]
        inserted = 0
        for item in seed_prompts:
            cursor = connection.execute(
                """INSERT OR IGNORE INTO PromptHub
                   (prompt_name, prompt_body, date, tag, category, tags, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    item["title"], item["body"], item.get("date", date.today().isoformat()),
                    item.get("favorite", "Not favorite"), item.get("type", "System prompt"),
                    ",".join(_parse_tags(item.get("tags", []))),
                    datetime.now().isoformat(timespec="seconds"),
                ),
            )
            inserted += cursor.rowcount
            if demo_seed:
                existing = connection.execute(
                    "SELECT tags FROM PromptHub WHERE prompt_name = ?", (item["title"],)
                ).fetchone()
                tags = _parse_tags(existing[0]) if existing else []
                tag_keys = {tag.lower() for tag in tags}
                required_tags = ["data:demo", "governance:system_instruction"]
                missing_tags = [tag for tag in required_tags if tag.lower() not in tag_keys]
                if missing_tags:
                    tags.extend(missing_tags)
                    connection.execute(
                        "UPDATE PromptHub SET tags = ?, updated_at = ? WHERE prompt_name = ?",
                        (",".join(tags), datetime.now().isoformat(timespec="seconds"), item["title"]),
                    )
        return inserted


def create_tag(name: str, color: str | None = None) -> str:
    """Register a tag with an optional display color."""
    name = " ".join(name.strip().split())
    if not name:
        raise ValueError("tag name must not be empty")
    if not DB_PATH.exists():
        init_db([])
    with _write_connection() as connection:
        exists = connection.execute(
            "SELECT 1 FROM tags_registered WHERE lower(name) = lower(?)", (name,)
        ).fetchone()
        if exists:
            raise ValueError(f"tag already registered: {name}")
        connection.execute(
            "INSERT INTO tags_registered (name, color, updated_at) VALUES (?, ?, ?)",
            (name, resolve_color(color), datetime.now().isoformat(timespec="seconds")),
        )
    return name


def read_tag_details() -> list[dict[str, Any]]:
    """Return registered tags with colors and update timestamps."""
    with _connect() as connection:
        return [dict(row) for row in connection.execute(
            "SELECT name, color, updated_at FROM tags_registered ORDER BY lower(name), name"
        )]


def read_tags() -> list[str]:
    """Return registered tags in alphabetical order."""
    with _connect() as connection:
        return [row[0] for row in connection.execute(
            "SELECT name FROM tags_registered ORDER BY lower(name), name"
        )]


def update_tag(name: str, new_name: str | None = None, color: str | None = None) -> bool:
    """Rename and/or recolor a registered tag."""
    new_name = " ".join((new_name or name).strip().split())
    if not new_name:
        raise ValueError("new tag name must not be empty")
    with _write_connection() as connection:
        duplicate = connection.execute(
            "SELECT 1 FROM tags_registered WHERE lower(name) = lower(?) AND lower(name) != lower(?)",
            (new_name, name),
        ).fetchone()
        if duplicate:
            raise ValueError(f"tag already registered: {new_name}")
        cursor = connection.execute(
            "UPDATE tags_registered SET name = ?, color = COALESCE(?, color), updated_at = ? WHERE lower(name) = lower(?)",
            (new_name, resolve_color(color), datetime.now().isoformat(timespec="seconds"), name),
        )
        return cursor.rowcount > 0


def delete_tag(name: str) -> bool:
    """Delete a registered tag, returning whether it existed."""
    with _write_connection() as connection:
        cursor = connection.execute(
            "DELETE FROM tags_registered WHERE lower(name) = lower(?)", (name,)
        )
        return cursor.rowcount > 0


def list_tables() -> list[str]:
    """Return all user tables in the PromptHub database."""
    with _connect() as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        )
        return [row[0] for row in rows]


def read_table(table_name: str) -> list[dict[str, Any]]:
    """Read every row from one user table as dictionaries."""
    if table_name not in list_tables():
        raise ValueError(f"unknown database table: {table_name}")
    with _connect() as connection:
        rows = connection.execute(f"SELECT * FROM {_quote_identifier(table_name)}")
        return [dict(row) for row in rows]


def read_all_tables() -> dict[str, list[dict[str, Any]]]:
    """Read every user table and return ``{table_name: rows}``."""
    return {table_name: read_table(table_name) for table_name in list_tables()}


def _validate_tags(connection: sqlite3.Connection, tags: list[str]) -> None:
    registered = {
        row[0].lower()
        for row in connection.execute("SELECT name FROM tags_registered")
    }
    unknown = [tag for tag in tags if tag.lower() not in registered]
    if unknown:
        raise ValueError(f"tag(s) not registered: {', '.join(unknown)}")


def _parse_tags(raw: str | list[str] | None) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, list):
        return [tag.strip() for tag in raw if tag.strip()]
    return [tag.strip() for tag in raw.replace(";", ",").split(",") if tag.strip()]


def create_prompt(
    title: str,
    body: str,
    *,
    prompt_type: str = "System prompt",
    favorite: str = "Not favorite",
    tags: str | list[str] | None = None,
    validate_tags: bool = False,
) -> dict[str, Any]:
    """Create a prompt and return it as a dictionary."""
    normalized_tags = _parse_tags(tags)
    if not DB_PATH.exists():
        init_db([])
    with _write_connection() as connection:
        if validate_tags:
            _validate_tags(connection, normalized_tags)
        cursor = connection.execute(
            """INSERT INTO PromptHub
               (prompt_name, prompt_body, date, tag, category, tags, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, body, date.today().isoformat(), favorite, prompt_type, ",".join(normalized_tags), datetime.now().isoformat(timespec="seconds")),
        )
        row = connection.execute("SELECT * FROM PromptHub WHERE id = ?", (cursor.lastrowid,)).fetchone()
        return _prompt(row)


def get_prompt(prompt_id: int) -> dict[str, Any] | None:
    """Read one prompt by ID, returning None when it does not exist."""
    with _connect() as connection:
        row = connection.execute("SELECT * FROM PromptHub WHERE id = ?", (prompt_id,)).fetchone()
    return _prompt(row) if row else None


def update_prompt(
    prompt_id: int,
    *,
    body: str | None = None,
    tags: str | list[str] | None = None,
    validate_tags: bool = False,
) -> dict[str, Any] | None:
    """Update a prompt body and/or replace its tags."""
    if body is None and tags is None:
        raise ValueError("provide body or tags")
    with _write_connection() as connection:
        changes = []
        values: list[str | int] = []
        if body is not None:
            changes.extend(["prompt_body = ?"])
            values.append(body)
        if tags is not None:
            normalized_tags = _parse_tags(tags)
            if validate_tags:
                _validate_tags(connection, normalized_tags)
            changes.append("tags = ?")
            values.append(",".join(normalized_tags))
        changes.append("updated_at = ?")
        values.append(datetime.now().isoformat(timespec="seconds"))
        values.append(prompt_id)
        cursor = connection.execute(
            f"UPDATE PromptHub SET {', '.join(changes)} WHERE id = ?", values
        )
        if cursor.rowcount == 0:
            return None
        row = connection.execute("SELECT * FROM PromptHub WHERE id = ?", (prompt_id,)).fetchone()
        return _prompt(row)


def delete_prompt(prompt_id: int) -> bool:
    """Delete a prompt by ID and report whether a row was removed."""
    with _write_connection() as connection:
        cursor = connection.execute("DELETE FROM PromptHub WHERE id = ?", (prompt_id,))
        return cursor.rowcount > 0


def _prompt(row: sqlite3.Row) -> dict[str, Any]:
    tags = _parse_tags(row["tags"])
    criticality = "normal"
    levels = {"low": 1, "medium": 2, "high": 3, "critical": 4}
    for tag in tags:
        prefix, separator, value = tag.partition(":")
        if prefix.lower() == "criticality" and separator and value.lower() in levels:
            if levels[value.lower()] > levels.get(criticality, 0):
                criticality = value.lower()
    return {
        "id": row["id"],
        "title": row["prompt_name"],
        "body": row["prompt_body"],
        "date": row["date"],
        "favorite": row["tag"],
        "type": row["category"],
        "tags": tags,
        "criticality": criticality,
        "updated_at": row["updated_at"],
    }


def read_prompts(
    *,
    category: str | None = None,
    tag: str | None = None,
    criticality: str | None = None,
) -> list[dict[str, Any]]:
    """Read prompts, optionally filtered by category, favorite tag, or priority."""
    clauses = []
    values: list[str] = []
    if category:
        clauses.append("category = ?")
        values.append(category)
    if tag:
        clauses.append("tag = ?")
        values.append(tag)

    query = "SELECT * FROM PromptHub"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY date DESC, id DESC"

    with _connect() as connection:
        prompts = [_prompt(row) for row in connection.execute(query, values)]
    if criticality:
        prompts = [item for item in prompts if item["criticality"] == criticality.lower()]
    return prompts


def generate_system_prompt(min_crit: str = "normal") -> str:
    """Combine agent prompt contents at or above ``min_crit`` priority."""
    minimum = min_crit.lower()
    if minimum not in CRITICALITY_LEVELS:
        raise ValueError("min_crit must be normal, low, medium, high, or critical")
    prompts = [
        item for item in read_agent_prompts()
        if CRITICALITY_LEVELS[item["criticality"]] >= CRITICALITY_LEVELS[minimum]
    ]
    return "\n\n".join(item["body"] for item in prompts)


def read_agent_prompts(criticality: str | None = None) -> list[dict[str, Any]]:
    """Read system/agent prompts ordered from most to least critical."""
    prompts = [
        item for item in read_prompts(criticality=criticality)
        if item["type"].lower() in {"system prompt", "agent prompt"}
    ]
    return sorted(
        prompts,
        key=lambda item: ({"normal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}[item["criticality"]], item["id"]),
        reverse=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Read, initialize, import, export, or generate a system prompt.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=("Without an operation, print system/agent prompts ordered by criticality. "
                "Import and export use protected/import/ and protected/export/; "
                "--gen_sys_prompt combines prompts at or above --min_crit.\n\n"
                "Examples:\n"
                "  extension.py --create --title Safety --body 'Follow rules' "
                "--tags 'criticality:critical,data:demo' --validate-tags\n"
                "  extension.py --read --id 1\n"
                "  extension.py --update --id 1 --body 'Updated text'\n"
                "  extension.py --delete --id 1\n"
                "  extension.py --tag-create --tag 'team:security'\n"
                "  extension.py --tag-read\n"
                "  extension.py --tag-update --tag 'team:security' --new-tag 'team:safety'\n"
                "  extension.py --tag-delete --tag 'team:safety'"),
    )
    parser.add_argument("--version", action="version", version=f"PromptHub extension v{EXTENSION_VERSION}")
    operations = parser.add_mutually_exclusive_group()
    operations.add_argument(
        "--init_db", action="store_true",
        help="initialize the database and add default prompts with varied criticality (safe to repeat)",
    )
    operations.add_argument("--import", dest="do_import", action="store_true", help="import Markdown prompts")
    operations.add_argument("--export", dest="do_export", action="store_true", help="export prompts to Markdown")
    operations.add_argument("--gen_sys_prompt", action="store_true", help="combine system/agent prompt contents by priority")
    operations.add_argument("--create", action="store_true", help="create a prompt")
    operations.add_argument("--read", action="store_true", help="read one prompt by --id")
    operations.add_argument("--update", action="store_true", help="update a prompt by --id")
    operations.add_argument("--delete", action="store_true", help="delete a prompt by --id")
    operations.add_argument("--tag-create", action="store_true", help="register a tag")
    operations.add_argument("--tag-read", action="store_true", help="list registered tags or read --tag")
    operations.add_argument("--tag-update", action="store_true", help="rename a registered --tag to --new-tag")
    operations.add_argument("--tag-delete", action="store_true", help="delete a registered --tag")
    parser.add_argument("--id", type=int, help="prompt ID for --read, --update, or --delete")
    parser.add_argument("--title", help="prompt title for --create")
    parser.add_argument("--body", help="prompt body for --create or --update")
    parser.add_argument("--type", dest="prompt_type", default="System prompt", help="category for --create")
    parser.add_argument("--favorite", default="Not favorite", help="favorite status for --create")
    parser.add_argument("--tags", default="", help="comma-separated tags for --create or --update")
    parser.add_argument("--validate-tags", action="store_true", help="reject tags absent from tags_registered")
    parser.add_argument("--tag", help="registered tag name for tag operations")
    parser.add_argument("--new-tag", help="replacement name for --tag-update")
    parser.add_argument("--color", help="optional hex color or preset: light_green, dark_blue, purple, orange")
    parser.add_argument("--contain", metavar="NAME_PART", default="", help="filename filter used with --import")
    parser.add_argument("--demo", action="store_true", help="with --export, export only prompts tagged data:demo")
    parser.add_argument("--min_crit", choices=sorted(CRITICALITY_LEVELS), default="normal", help="minimum criticality for --gen_sys_prompt")
    args = parser.parse_args()
    if args.init_db:
        init_db()
        print(f"Initialized {DB_PATH}")
        raise SystemExit(0)
    if args.gen_sys_prompt:
        print(generate_system_prompt(args.min_crit))
        raise SystemExit(0)
    if args.create:
        if not args.title or args.body is None:
            parser.error("--create requires --title and --body")
        print(create_prompt(args.title, args.body, prompt_type=args.prompt_type,
                            favorite=args.favorite, tags=args.tags,
                            validate_tags=args.validate_tags))
        raise SystemExit(0)
    if args.read:
        if args.id is None:
            parser.error("--read requires --id")
        print(get_prompt(args.id))
        raise SystemExit(0)
    if args.update:
        if args.id is None or (args.body is None and not args.tags):
            parser.error("--update requires --id and --body or --tags")
        print(update_prompt(args.id, body=args.body, tags=args.tags or None,
                             validate_tags=args.validate_tags))
        raise SystemExit(0)
    if args.delete:
        if args.id is None:
            parser.error("--delete requires --id")
        print("Deleted" if delete_prompt(args.id) else "Prompt not found")
        raise SystemExit(0)
    if args.tag_create:
        if not args.tag:
            parser.error("--tag-create requires --tag")
        print(create_tag(args.tag, color=args.color))
        raise SystemExit(0)
    if args.tag_read:
        print(read_tags() if not args.tag else [tag for tag in read_tags() if tag.lower() == args.tag.lower()])
        raise SystemExit(0)
    if args.tag_update:
        if not args.tag or not args.new_tag:
            parser.error("--tag-update requires --tag and --new-tag")
        print("Updated" if update_tag(args.tag, args.new_tag, color=args.color) else "Tag not found")
        raise SystemExit(0)
    if args.tag_delete:
        if not args.tag:
            parser.error("--tag-delete requires --tag")
        print("Deleted" if delete_tag(args.tag) else "Tag not found")
        raise SystemExit(0)
    if args.do_import or args.do_export:
        utility = _import_export_module()
        if args.do_import:
            utility.import_prompts(args.contain)
        else:
            utility.export_prompts(demo=args.demo)
        raise SystemExit(0)

    for item in read_agent_prompts():
        print(f"[{item['criticality']}] {item['title']}")
        print(item["body"])
        print()
