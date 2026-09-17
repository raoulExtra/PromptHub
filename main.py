from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from datetime import date, datetime
import sqlite3
import os
import re
from backend.schema_models.schema_models import (
    DerivedPrompt, Prompt, PromptCreate, PromptUpdate, TagCreate, TagUpdate,
)


app = FastAPI(title="PromptHub API")


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.makedirs("backend/database/", exist_ok=True)
DB_PATH = os.path.join(BASE_DIR, 'backend/database/prompthub.db')

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""CREATE TABLE IF NOT EXISTS PromptHub (
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
    );""")
conn.commit()

existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(PromptHub)").fetchall()}
if "tags" not in existing_cols:
    cursor.execute("ALTER TABLE PromptHub ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
    conn.commit()
if "updated_at" not in existing_cols:
    cursor.execute("ALTER TABLE PromptHub ADD COLUMN updated_at TEXT")
    cursor.execute("UPDATE PromptHub SET updated_at = date WHERE updated_at IS NULL")
if "cycle" not in existing_cols:
    cursor.execute("ALTER TABLE PromptHub ADD COLUMN cycle TEXT NOT NULL DEFAULT 'none'")
if "routine_confirmed" not in existing_cols:
    cursor.execute("ALTER TABLE PromptHub ADD COLUMN routine_confirmed INTEGER NOT NULL DEFAULT 0")
if "routine_period" not in existing_cols:
    cursor.execute("ALTER TABLE PromptHub ADD COLUMN routine_period TEXT NOT NULL DEFAULT ''")
conn.commit()

cursor.execute("CREATE TABLE IF NOT EXISTS tags_registered (name TEXT PRIMARY KEY NOT NULL, color TEXT, updated_at TEXT NOT NULL)")
tag_columns = {row[1] for row in cursor.execute("PRAGMA table_info(tags_registered)").fetchall()}
if "color" not in tag_columns:
    cursor.execute("ALTER TABLE tags_registered ADD COLUMN color TEXT")
if "updated_at" not in tag_columns:
    cursor.execute("ALTER TABLE tags_registered ADD COLUMN updated_at TEXT")
    cursor.execute("UPDATE tags_registered SET updated_at = ? WHERE updated_at IS NULL",
                   (datetime.now().isoformat(timespec="seconds"),))
    conn.commit()

# Criticality is deliberately derived from tags so old databases and arbitrary
# user tags remain compatible.  The view is also useful to SQL consumers.
cursor.execute("""CREATE VIEW IF NOT EXISTS agent_prompts AS
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
""")
conn.commit()


CRITICALITY_LEVELS = {"normal": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
COLOR_PRESETS = {
    "light_green": "#90ee90", "dark_green": "#006400",
    "light_blue": "#add8e6", "dark_blue": "#00008b",
    "light_red": "#ffcccb", "dark_red": "#8b0000",
    "light_yellow": "#ffffe0", "dark_yellow": "#b8860b",
    "purple": "#800080", "orange": "#ffa500", "gray": "#808080",
}


def resolve_color(color: Optional[str]) -> Optional[str]:
    if color is None:
        return None
    value = color.strip().lower()
    return COLOR_PRESETS.get(value, color.strip()) or None


def parse_tags(raw) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        parts = raw
    else:
        parts = str(raw).replace(";", ",").split(",")
    seen = set()
    out = []
    for part in parts:
        name = " ".join(str(part).strip().split())
        if not name:
            continue
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(name)
    return out


def tags_to_db(tags) -> str:
    return ",".join(parse_tags(tags))


def criticality_from_tags(tags) -> str:
    """Return the highest ``criticality:<level>`` tag, defaulting to normal."""
    selected = "normal"
    for tag in parse_tags(tags):
        prefix, separator, value = tag.partition(":")
        if prefix.lower() == "criticality" and separator and value.lower() in CRITICALITY_LEVELS:
            if CRITICALITY_LEVELS[value.lower()] > CRITICALITY_LEVELS[selected]:
                selected = value.lower()
    return selected


CYCLES = {"none", "hourly", "daily", "weekly", "monthly", "yearly"}


def current_period(cycle: str) -> str:
    now = datetime.now()
    if cycle == "hourly": return now.strftime("%Y-%m-%d-%H")
    if cycle == "daily": return now.strftime("%Y-%m-%d")
    if cycle == "weekly": return now.strftime("%G-W%V")
    if cycle == "monthly": return now.strftime("%Y-%m")
    if cycle == "yearly": return now.strftime("%Y")
    return ""


def reset_routine_if_needed(prompt_id: int, cycle: str, period: str) -> bool:
    if cycle == "none" or not period:
        return False
    row = cursor.execute("SELECT routine_period FROM PromptHub WHERE id = ?", (prompt_id,)).fetchone()
    if row and row[0] and row[0] != period:
        cursor.execute("UPDATE PromptHub SET routine_confirmed = 0, routine_period = ? WHERE id = ?", (period, prompt_id))
        conn.commit()
        return True
    return False


def row_to_prompt(d) -> dict:
    cycle = d[8] if len(d) > 8 else "none"
    period = d[10] if len(d) > 10 else ""
    reset_routine_if_needed(d[0], cycle, current_period(cycle))
    return {
        "id": d[0],
        "title": d[1],
        "body": d[2],
        "date": d[3],
        "favorite": d[4],
        "type": d[5],
        "tags": parse_tags(d[6] if len(d) > 6 else ""),
        "criticality": criticality_from_tags(d[6] if len(d) > 6 else ""),
        "updated_at": d[7] if len(d) > 7 else d[3],
        "cycle": cycle,
        "routine_confirmed": bool(d[9]) if len(d) > 9 else False,
    }


# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# ============ API ENDPOINTS ============

@app.get("/api/tags", response_model=List[str])
def list_tags():
    """Return registered tags for prompt entry and filtering."""
    rows = cursor.execute("SELECT name FROM tags_registered ORDER BY lower(name), name").fetchall()
    return [row[0] for row in rows]


@app.get("/api/tags/details")
def registered_tag_details():
    rows = cursor.execute(
        "SELECT name, color, updated_at FROM tags_registered ORDER BY lower(name), name"
    ).fetchall()
    return [{"name": row[0], "color": row[1], "updated_at": row[2]} for row in rows]


@app.post("/api/tags", response_model=str)
def create_registered_tag(tag: TagCreate):
    name = " ".join(tag.name.strip().split())
    if not name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="tag name must not be empty")
    try:
        cursor.execute(
            "INSERT INTO tags_registered (name, color, updated_at) VALUES (?, ?, ?)",
            (name, resolve_color(tag.color), datetime.now().isoformat(timespec="seconds")),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="tag already registered")
    return name


@app.put("/api/tags/{tag_name}", response_model=str)
def update_registered_tag(tag_name: str, tag: TagUpdate):
    new_name = " ".join(tag.new_name.strip().split())
    if not new_name:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="tag name must not be empty")
    try:
        cursor.execute(
            "UPDATE tags_registered SET name = ?, color = COALESCE(?, color), updated_at = ? WHERE lower(name) = lower(?)",
            (new_name, resolve_color(tag.color), datetime.now().isoformat(timespec="seconds"), tag_name),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="tag not found")
        conn.commit()
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=409, detail="tag already registered")
    return new_name


@app.delete("/api/tags/{tag_name}")
def delete_registered_tag(tag_name: str, detach: bool = Query(False)):
    matching = cursor.execute(
        "SELECT id, tags FROM PromptHub WHERE instr(lower(',' || tags || ','), lower(',' || ? || ',')) > 0",
        (tag_name,),
    ).fetchall()
    cursor.execute("DELETE FROM tags_registered WHERE lower(name) = lower(?)", (tag_name,))
    if cursor.rowcount == 0:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="tag not found")
    if detach:
        now = datetime.now().isoformat(timespec="seconds")
        for prompt_id, prompt_tags in matching:
            kept = [tag for tag in parse_tags(prompt_tags) if tag.lower() != tag_name.lower()]
            cursor.execute("UPDATE PromptHub SET tags = ?, updated_at = ? WHERE id = ?",
                           (tags_to_db(kept), now, prompt_id))
    conn.commit()
    return {"message": "Tag deleted", "detached": detach, "affected_prompts": len(matching)}


@app.get("/api/prompts", response_model=List[Prompt])
def get_prompts(
    tag: Optional[str] = None,
    category: Optional[str] = None,
    custom_tag: Optional[str] = None,
    criticality: Optional[str] = None,
    search: Optional[str] = None
):

    lis = cursor.execute("SELECT * FROM PromptHub").fetchall()

    result = [row_to_prompt(d) for d in lis]

    if tag and tag != "all":
        result = [p for p in result if p["favorite"] == tag]

    if category and category != "all":
        result = [p for p in result if p["type"] == category]

    if custom_tag and custom_tag != "all":
        needle = custom_tag.lower()
        result = [p for p in result if needle in [t.lower() for t in p["tags"]]]

    if criticality and criticality != "all":
        result = [p for p in result if p["criticality"] == criticality.lower()]

    if search:
        # Support SQL-style (%) and shell-style (*) wildcards while retaining
        # ordinary substring search when no wildcard is supplied.
        pattern = re.escape(search.lower()).replace("%", ".*").replace(r"\*", ".*").replace("_", ".").replace(r"\?", ".")
        if not any(mark in search for mark in ("%", "*", "_", "?")):
            pattern = ".*" + pattern + ".*"
        matcher = re.compile(pattern)
        has_wildcard = any(mark in search for mark in ("%", "*", "_", "?"))
        match = matcher.fullmatch if has_wildcard else matcher.search
        result = [
            p for p in result
            if match(p["title"].lower())
            or match(p["body"].lower())
            or any(match(t.lower()) for t in p["tags"])
        ]

    return result


@app.get("/api/prompts/agent", response_model=List[DerivedPrompt])
def get_agent_prompts(criticality: Optional[str] = None):
    """Return system/agent prompts in criticality order for prompt assembly.

    Add tags such as ``criticality:high`` or ``criticality:critical`` to a
    prompt. Prompts with equal criticality retain newest-first ordering.
    """
    if criticality and criticality.lower() not in CRITICALITY_LEVELS:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="criticality must be normal, low, medium, high, or critical")

    rows = cursor.execute("""
        SELECT id, prompt_name, prompt_body, date, category, tags, criticality_rank,
               (SELECT updated_at FROM PromptHub WHERE PromptHub.id = agent_prompts.id)
        FROM agent_prompts
        ORDER BY criticality_rank DESC, date DESC, id DESC
    """).fetchall()
    prompts = [{
        "id": row[0], "title": row[1], "body": row[2], "date": row[3],
        "type": row[4], "tags": parse_tags(row[5]),
        "criticality": criticality_from_tags(row[5]),
        "updated_at": row[7] or row[3],
    } for row in rows]
    if criticality:
        prompts = [p for p in prompts if p["criticality"] == criticality.lower()]
    return prompts


@app.post("/api/prompts", response_model=Prompt)
def create_prompt(prompt: PromptCreate):
    """Create a new prompt"""
    date_str = date.today().isoformat()
    tags = parse_tags(prompt.tags)
    if prompt.cycle not in CYCLES:
        raise ValueError("cycle must be none, hourly, daily, weekly, monthly, or yearly")

    cursor.execute("""
        INSERT INTO PromptHub (prompt_name, prompt_body, date, tag, category, tags, updated_at, cycle, routine_confirmed, routine_period)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (prompt.title, prompt.body, date_str, prompt.favorite, prompt.type,
          tags_to_db(tags), datetime.now().isoformat(timespec="seconds"), prompt.cycle,
          int(prompt.routine_confirmed), current_period(prompt.cycle)))

    conn.commit()

    new_id = cursor.lastrowid

    return {
        "id": new_id,
        "title": prompt.title,
        "body": prompt.body,
        "favorite": prompt.favorite,
        "type": prompt.type,
        "date": date_str,
        "tags": tags,
        "criticality": criticality_from_tags(tags),
    }


@app.delete("/api/prompts/{prompt_id}")
def delete_prompt(prompt_id: int):
    """Delete a prompt by ID"""
    cursor.execute("DELETE FROM PromptHub WHERE id = ?", (prompt_id,))
    conn.commit()
    return {"message": "Deleted successfully"}


@app.put("/api/prompts/{prompt_id}")
def update_prompt(prompt_id: int, prompt_update: PromptUpdate):
    """Update a prompt body by ID - prints values to console"""
    fields = ["prompt_body = ?"]
    values = [prompt_update.body]
    if prompt_update.type is not None:
        fields.append("category = ?")
        values.append(prompt_update.type)
    if prompt_update.tags is not None:
        fields.append("tags = ?")
        values.append(tags_to_db(prompt_update.tags))
    if prompt_update.cycle is not None:
        if prompt_update.cycle not in CYCLES:
            from fastapi import HTTPException
            raise HTTPException(status_code=400, detail="invalid cycle")
        fields.extend(["cycle = ?", "routine_period = ?"])
        values.extend([prompt_update.cycle, current_period(prompt_update.cycle)])
    if prompt_update.routine_confirmed is not None:
        fields.append("routine_confirmed = ?")
        values.append(int(prompt_update.routine_confirmed))
    fields.append("updated_at = ?")
    values.extend([datetime.now().isoformat(timespec="seconds"), prompt_id])
    cursor.execute(f"UPDATE PromptHub SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()

    return {
        "message": "Update request received",
        "id": prompt_id,
        "body": prompt_update.body,
        "type": prompt_update.type,
        "tags": prompt_update.tags,
    }


# ============ STATIC FILES & FRONTEND ROUTES ============


def get_file_path(filename):
    return os.path.join(BASE_DIR, filename)

@app.get("/")
async def serve_index():
    """Serve the main HTML page"""
    return FileResponse(get_file_path("frontend/index.html"))

@app.get("/write_prompt.html")
async def serve_write_prompt():
    """Serve the write prompt page"""
    return FileResponse(get_file_path("frontend/write_prompt.html"))

@app.get("/show_prompts.html")
async def serve_show_prompts():
    """Serve the show prompts page"""
    return FileResponse(get_file_path("frontend/show_prompts.html"))

@app.get("/manage_tags.html")
async def serve_manage_tags():
    """Serve the tag management page"""
    return FileResponse(get_file_path("frontend/manage_tags.html"))

@app.get("/index.html")
async def serve_index_alt():
    """Serve frontend/index.html via explicit path"""
    return FileResponse(get_file_path("frontend/index.html"))


app.mount("/frontend/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/static")), name="static")
app.mount("/frontend/scripts", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/scripts")), name="scripts")

# Run with: uvicorn main:app --reload
