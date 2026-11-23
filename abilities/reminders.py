"""
Reminders & timers. Persistent (SQLite in the vault data dir), and checked by
the proactive watcher so Jarvis can actually alert you when they're due.
"""

from __future__ import annotations

import sqlite3
import time
from datetime import datetime, timedelta
from pathlib import Path

import tools_registry as reg
from core.config import settings


def _db() -> sqlite3.Connection:
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.data_dir / "reminders.db")
    conn.row_factory = sqlite3.Row
    conn.execute(
        "CREATE TABLE IF NOT EXISTS reminders (id INTEGER PRIMARY KEY AUTOINCREMENT, "
        "due REAL, text TEXT, done INTEGER DEFAULT 0)"
    )
    return conn


def _parse_when(when: str) -> float | None:
    """Accept 'HH:MM', 'in 5 minutes', 'in 2 hours', or 'YYYY-MM-DD HH:MM'."""
    when = when.strip().lower()
    now = datetime.now()
    if when.startswith("in "):
        parts = when[3:].split()
        try:
            n = float(parts[0])
            unit = parts[1].rstrip("s")
            secs = n * {"second": 1, "sec": 1, "minute": 60, "min": 60, "hour": 3600, "hr": 3600}.get(unit, 60)
            return time.time() + secs
        except Exception:  # noqa: BLE001
            return None
    for fmt in ("%H:%M", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(when, fmt)
            if fmt == "%H:%M":
                dt = now.replace(hour=dt.hour, minute=dt.minute, second=0, microsecond=0)
                if dt < now:
                    dt += timedelta(days=1)
            return dt.timestamp()
        except ValueError:
            continue
    return None


@reg.register(
    name="set_reminder",
    description="Set a reminder. 'when' accepts 'HH:MM', 'in 5 minutes', 'in 2 hours', or 'YYYY-MM-DD HH:MM'.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "What to remind about."},
            "when": {"type": "string", "description": "When (e.g. 'in 10 minutes' or '18:30')."},
        },
        "required": ["text", "when"],
    },
)
def set_reminder(text: str, when: str) -> str:
    ts = _parse_when(when)
    if ts is None:
        return f"Couldn't understand the time '{when}'. Try 'in 10 minutes' or '18:30'."
    with _db() as c:
        c.execute("INSERT INTO reminders(due,text) VALUES(?,?)", (ts, text))
    nice = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M")
    return f"Reminder set for {nice}: {text}"


@reg.register(
    name="list_reminders",
    description="List upcoming (not-yet-done) reminders.",
    parameters=reg.NO_PARAMS,
)
def list_reminders() -> str:
    now = time.time()
    with _db() as c:
        rows = c.execute("SELECT due,text FROM reminders WHERE done=0 ORDER BY due").fetchall()
    if not rows:
        return "No upcoming reminders."
    return "\n".join(f"- {datetime.fromtimestamp(r['due']):%Y-%m-%d %H:%M} — {r['text']}" for r in rows)


def due_reminders() -> list[str]:
    """Return reminder texts that are due now (and mark them done)."""
    now = time.time()
    out: list[str] = []
    with _db() as c:
        rows = c.execute("SELECT id,due,text FROM reminders WHERE done=0 AND due<=?", (now,)).fetchall()
        for r in rows:
            out.append(r["text"])
            c.execute("UPDATE reminders SET done=1 WHERE id=?", (r["id"],))
    return out
