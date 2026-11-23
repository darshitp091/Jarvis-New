"""
Quick notes and a to-do list, stored as Obsidian notes in the vault (so they're
browsable), plus a persistent clipboard history.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime

import tools_registry as reg
from core.config import settings
from core.memory import get_memory


@reg.register(
    name="add_note",
    description="Save a quick note (also appears in the Obsidian vault).",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Note content."}},
        "required": ["text"],
    },
)
def add_note(text: str) -> str:
    note = get_memory().remember(text, tag="note")
    return f"Note saved as [[{note}]]"


@reg.register(
    name="add_todo",
    description="Add an item to the to-do list.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Task to add."}},
        "required": ["text"],
    },
)
def add_todo(text: str) -> str:
    settings.ensure_dirs()
    path = settings.vault_dir / "Todos.md"
    if not path.exists():
        path.write_text("# To-Do\n\n", encoding="utf-8")
    with path.open("a", encoding="utf-8") as fh:
        fh.write(f"- [ ] {text}\n")
    return f"Added to-do: {text}"


@reg.register(
    name="list_todos",
    description="List open to-do items.",
    parameters=reg.NO_PARAMS,
)
def list_todos() -> str:
    path = settings.vault_dir / "Todos.md"
    if not path.exists():
        return "No to-dos yet."
    items = [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip().startswith("- [ ]")]
    return "\n".join(items) if items else "No open to-dos."


# --- clipboard history ------------------------------------------------------
def _clip_db() -> sqlite3.Connection:
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.data_dir / "clipboard.db")
    conn.execute("CREATE TABLE IF NOT EXISTS clips (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, text TEXT)")
    return conn


@reg.register(
    name="clipboard_save",
    description="Save the current clipboard text into clipboard history.",
    parameters=reg.NO_PARAMS,
)
def clipboard_save() -> str:
    try:
        import pyperclip

        text = pyperclip.paste()
    except Exception as exc:  # noqa: BLE001
        return f"clipboard error: {exc}"
    if not text:
        return "clipboard is empty"
    with _clip_db() as c:
        c.execute("INSERT INTO clips(ts,text) VALUES(?,?)", (time.time(), text))
    return f"Saved clipboard ({len(text)} chars) to history"


@reg.register(
    name="clipboard_history",
    description="Show recent clipboard history.",
    parameters={
        "type": "object",
        "properties": {"limit": {"type": "integer", "description": "How many entries.", "default": 10}},
    },
)
def clipboard_history(limit: int = 10) -> str:
    with _clip_db() as c:
        rows = c.execute("SELECT ts,text FROM clips ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    if not rows:
        return "No clipboard history."
    return "\n".join(f"{datetime.fromtimestamp(r[0]):%H:%M} — {r[1][:80]}" for r in rows)
