from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
from datetime import date
import sqlite3
import os
from backend.schema_models.schema_models import Prompt, PromptCreate, PromptUpdate


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
                tags TEXT NOT NULL DEFAULT ''
    );""")
conn.commit()

existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(PromptHub)").fetchall()}
if "tags" not in existing_cols:
    cursor.execute("ALTER TABLE PromptHub ADD COLUMN tags TEXT NOT NULL DEFAULT ''")
    conn.commit()


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


def row_to_prompt(d) -> dict:
    return {
        "id": d[0],
        "title": d[1],
        "body": d[2],
        "date": d[3],
        "favorite": d[4],
        "type": d[5],
        "tags": parse_tags(d[6] if len(d) > 6 else ""),
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
    """Return unique custom tags used across prompts."""
    rows = cursor.execute("SELECT tags FROM PromptHub").fetchall()
    seen = set()
    out = []
    for (raw,) in rows:
        for tag in parse_tags(raw):
            key = tag.lower()
            if key not in seen:
                seen.add(key)
                out.append(tag)
    out.sort(key=str.lower)
    return out


@app.get("/api/prompts", response_model=List[Prompt])
def get_prompts(
    tag: Optional[str] = None,
    category: Optional[str] = None,
    custom_tag: Optional[str] = None,
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

    if search:
        search_lower = search.lower()
        result = [
            p for p in result
            if search_lower in p["title"].lower()
            or search_lower in p["body"].lower()
            or any(search_lower in t.lower() for t in p["tags"])
        ]

    return result

@app.post("/api/prompts", response_model=Prompt)
def create_prompt(prompt: PromptCreate):
    """Create a new prompt"""
    date_str = date.today().isoformat()
    tags = parse_tags(prompt.tags)

    cursor.execute("""
        INSERT INTO PromptHub (prompt_name, prompt_body, date, tag, category, tags)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (prompt.title, prompt.body, date_str, prompt.favorite, prompt.type, tags_to_db(tags)))

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
    cursor.execute("UPDATE PromptHub SET prompt_body = ? WHERE id = ?",(prompt_update.body, prompt_id))
    conn.commit()

    return {
        "message": "Update request received",
        "id": prompt_id,
        "body": prompt_update.body
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

@app.get("/index.html")
async def serve_index_alt():
    """Serve frontend/index.html via explicit path"""
    return FileResponse(get_file_path("frontend/index.html"))


app.mount("/frontend/static", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/static")), name="static")
app.mount("/frontend/scripts", StaticFiles(directory=os.path.join(BASE_DIR, "frontend/scripts")), name="scripts")

# Run with: uvicorn main:app --reload
