#!/usr/bin/env python3
"""Import and export PromptHub prompts.

Import Markdown files with:
    python import-export.py --import --contain agent

The optional front matter format is:
---
title: My prompt
type: System prompt
favorite: Favorite
tags: coding, criticality:high
---

Without front matter, the filename becomes the title and the complete file
contents become the prompt body.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from datetime import date, datetime
from pathlib import Path


# The script lives two levels below the project root.
BASE_DIR = Path(__file__).resolve().parents[2]
IMPORT_DIR = BASE_DIR / "protected" / "import"
DB_PATH = BASE_DIR / "backend" / "database" / "prompthub.db"


def parse_tags(value: str) -> str:
    """Normalize comma/semicolon-separated tags for SQLite storage."""
    seen = set()
    tags = []
    for item in value.replace(";", ",").split(","):
        tag = " ".join(item.strip().split())
        if tag and tag.lower() not in seen:
            seen.add(tag.lower())
            tags.append(tag)
    return ",".join(tags)


def parse_markdown(path: Path) -> tuple[str, str, str, str, str]:
    """Return title, body, favorite, type, and normalized tags."""
    text = path.read_text(encoding="utf-8")
    metadata = {}
    body = text

    lines = text.splitlines()
    if lines and lines[0].strip() == "---":
        try:
            end = next(i for i, line in enumerate(lines[1:], 1) if line.strip() == "---")
        except StopIteration:
            end = -1
        if end > 0:
            for line in lines[1:end]:
                key, separator, value = line.partition(":")
                if separator:
                    metadata[key.strip().lower()] = value.strip()
            body = "\n".join(lines[end + 1:])

    title = metadata.get("title", path.stem).strip() or path.stem
    body = body.strip()
    favorite = metadata.get("favorite", "Not favorite")
    prompt_type = metadata.get("type", metadata.get("category", "System prompt"))
    tags = parse_tags(metadata.get("tags", ""))
    return title, body, favorite, prompt_type, tags


def ensure_database(connection: sqlite3.Connection) -> None:
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
    connection.commit()


def _criticality(tags: list[str]) -> str:
    levels = {"normal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    selected = "normal"
    for tag in tags:
        prefix, separator, value = tag.partition(":")
        if prefix.lower() == "criticality" and separator and value.lower() in levels:
            if levels[value.lower()] > levels[selected]:
                selected = value.lower()
    return selected


def _safe_filename(value: str) -> str:
    """Make a prompt title safe and readable as a filename."""
    value = re.sub(r"[<>:\"/\\|?*\x00-\x1f]", "-", value)
    value = re.sub(r"\s+", "-", value).strip(".-")
    return (value or "untitled-prompt").lower()


def export_prompts(demo: bool = False) -> int:
    """Write prompts to Markdown, preserving the safety prompt file."""
    EXPORT_DIR = BASE_DIR / "protected" / "export"
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)
    for existing in EXPORT_DIR.iterdir():
        if existing.is_file() and "safety" not in existing.name.lower():
            existing.unlink()
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        ensure_database(connection)
        query = "SELECT id, prompt_name, prompt_body, date, tag, category, tags, updated_at FROM PromptHub"
        if demo:
            query += " WHERE (',' || lower(tags) || ',') LIKE '%,data:demo,%'"
        rows = connection.execute(query + " ORDER BY id").fetchall()
        if demo and not rows:
            print("WARNING: no prompts with the data:demo tag found in the database.")
        width = max(3, len(str(rows[-1]["id"])) if rows else 3)
        for row in rows:
            tags = _parse_export_tags(row["tags"])
            filename = f"{row['id']:0{width}d}-{_safe_filename(row['prompt_name'])}.md"
            content = (
                "---\n"
                f"title: {row['prompt_name']}\n"
                f"type: {row['category']}\n"
                f"favorite: {row['tag'] or 'Not favorite'}\n"
                f"tags: {', '.join(tags)}\n"
                "---\n\n"
                f"{row['prompt_body'].rstrip()}\n"
            )
            (EXPORT_DIR / filename).write_text(content, encoding="utf-8")
            yaml_content = (
                f"id: {row['id']}\n"
                f"title: {json.dumps(row['prompt_name'], ensure_ascii=False)}\n"
                f"date: {json.dumps(row['date'], ensure_ascii=False)}\n"
                f"favorite: {json.dumps(row['tag'] or 'Not favorite', ensure_ascii=False)}\n"
                f"type: {json.dumps(row['category'], ensure_ascii=False)}\n"
                f"criticality: {_criticality(tags)}\n"
                f"updated_at: {json.dumps(row['updated_at'], ensure_ascii=False)}\n"
                f"tags: {json.dumps(tags, ensure_ascii=False)}\n"
                "body: |\n"
                + "".join(f"  {line}\n" for line in row['prompt_body'].splitlines())
            )
            (EXPORT_DIR / f"{Path(filename).stem}.yaml").write_text(yaml_content, encoding="utf-8")
            print(f"Exported: {filename} and {Path(filename).stem}.yaml")
        print(f"Exported {len(rows)} prompt(s) to {EXPORT_DIR}")
        return len(rows)
    finally:
        connection.close()


def _parse_export_tags(raw: str | None) -> list[str]:
    return [tag.strip() for tag in (raw or "").replace(";", ",").split(",") if tag.strip()]


def import_prompts(name_part: str) -> int:
    IMPORT_DIR.mkdir(parents=True, exist_ok=True)
    files = sorted(
        path for path in IMPORT_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() == ".md"
        and name_part.lower() in path.name.lower()
    )

    if not files:
        print(f"No matching Markdown files found in {IMPORT_DIR}")
        return 0

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    try:
        ensure_database(connection)
        imported = 0
        for path in files:
            title, body, favorite, prompt_type, tags = parse_markdown(path)
            if not body:
                print(f"Skipped empty file: {path.name}")
                continue
            try:
                connection.execute(
                    """INSERT INTO PromptHub
                       (prompt_name, prompt_body, date, tag, category, tags, updated_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (title, body, date.today().isoformat(), favorite, prompt_type, tags,
                     datetime.now().isoformat(timespec="seconds")),
                )
                imported += 1
                print(f"Imported: {path.name} -> {title}")
            except sqlite3.IntegrityError:
                print(f"Skipped duplicate title: {title}")
        connection.commit()
        print(f"Imported {imported} prompt(s).")
        return imported
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Import/export PromptHub prompts using protected/import/ and protected/export/ by default.",
    )
    parser.add_argument(
        "--import", dest="do_import", action="store_true",
        help="import matching Markdown files from protected/import/",
    )
    parser.add_argument(
        "--export", dest="do_export", action="store_true",
        help="export every prompt to Markdown in protected/export/",
    )
    parser.add_argument("--contain", metavar="NAME_PART", default="", help="only use filenames containing this text when importing")
    args = parser.parse_args()

    if args.do_import == args.do_export:
        parser.error("choose exactly one of --import or --export")
    if args.do_export:
        export_prompts()
    else:
        import_prompts(args.contain)


if __name__ == "__main__":
    main()
