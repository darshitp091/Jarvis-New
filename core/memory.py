"""
Obsidian-backed long-term memory for Jarvis.

The Obsidian vault (plain markdown files) is the SOURCE OF TRUTH.
A SQLite index is derived from it purely for fast vector recall.

Vault layout:
  vault/
    Memory/                 one .md note per remembered fact
    Journal/
      YYYY-MM-DD.md         daily note; tool events appended here

Any edits you make in Obsidian are picked up on the next recall (mtime resync).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from .config import settings

_DIM = 512
_TOKEN = re.compile(r"[a-z0-9\u0900-\u097F]+", re.IGNORECASE)
_SLUG = re.compile(r"[^a-z0-9]+")


def _tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def _embed(text: str) -> list[float]:
    """Deterministic hashing vectorizer (bag of words -> fixed-size L2 vector)."""
    vec = [0.0] * _DIM
    for tok in _tokens(text):
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
        vec[h % _DIM] += 1.0 if (h >> 16) & 1 else -1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def _cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _slug(text: str, maxlen: int = 40) -> str:
    s = _SLUG.sub("-", text.lower()).strip("-")
    return s[:maxlen] or "note"


def _strip_frontmatter(raw: str) -> str:
    if raw.startswith("---"):
        parts = raw.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return raw.strip()


@dataclass
class Memory:
    db_path: Path = None  # type: ignore[assignment]
    vault: Path = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.vault = self.vault or settings.vault_dir
        self.db_path = self.db_path or (settings.data_dir / "memory_index.db")
        settings.ensure_dirs()
        (self.vault / "Memory").mkdir(parents=True, exist_ok=True)
        (self.vault / "Journal").mkdir(parents=True, exist_ok=True)
        self._init_db()
        self._resync()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as c:
            c.execute(
                """CREATE TABLE IF NOT EXISTS idx (
                    note TEXT PRIMARY KEY, text TEXT, vec TEXT, mtime REAL
                )"""
            )

    def _resync(self) -> None:
        """Index any .md notes in Memory/ that are new or changed on disk."""
        memdir = self.vault / "Memory"
        if not memdir.exists():
            return
        seen: set[str] = set()
        with self._conn() as c:
            for md in memdir.glob("*.md"):
                stem = md.stem
                seen.add(stem)
                mtime = md.stat().st_mtime
                row = c.execute("SELECT mtime FROM idx WHERE note=?", (stem,)).fetchone()
                if row and abs(row["mtime"] - mtime) < 0.5:
                    continue
                body = _strip_frontmatter(md.read_text(encoding="utf-8", errors="replace"))
                c.execute(
                    "INSERT OR REPLACE INTO idx(note,text,vec,mtime) VALUES(?,?,?,?)",
                    (stem, body, json.dumps(_embed(body)), mtime),
                )
            for row in c.execute("SELECT note FROM idx").fetchall():
                if row["note"] not in seen:
                    c.execute("DELETE FROM idx WHERE note=?", (row["note"],))

    # --- public API -------------------------------------------------------
    def remember(self, text: str, tag: str = "fact", links: list[str] | None = None) -> str:
        """Write a new markdown note into the vault and index it. Returns note name."""
        now = datetime.now()
        stem = f"{now:%Y%m%d-%H%M%S}-{_slug(text)}"
        title = text.strip().split(".")[0][:80] or stem
        link_line = ""
        if links:
            link_line = "related:: " + " ".join(f"[[{l}]]" for l in links) + "\n"

        body = (
            "---\n"
            f"created: {now.isoformat(timespec='seconds')}\n"
            f"tags: [jarvis, {tag}]\n"
            "source: jarvis\n"
            "---\n\n"
            f"# {title}\n\n"
            f"{text.strip()}\n\n"
            f"{link_line}".rstrip()
            + "\n"
        )
        (self.vault / "Memory" / f"{stem}.md").write_text(body, encoding="utf-8")

        with self._conn() as c:
            c.execute(
                "INSERT OR REPLACE INTO idx(note,text,vec,mtime) VALUES(?,?,?,?)",
                (stem, text.strip(), json.dumps(_embed(text)), time.time()),
            )
        return stem

    def recall(self, query: str, k: int = 5, min_score: float = 0.05) -> list[str]:
        self._resync()
        qv = _embed(query)
        rows: list[tuple[float, str]] = []
        with self._conn() as c:
            for row in c.execute("SELECT text, vec FROM idx"):
                score = _cosine(qv, json.loads(row["vec"]))
                if score >= min_score:
                    rows.append((score, row["text"]))
        rows.sort(reverse=True)
        return [t for _, t in rows[:k]]

    def all_memories(self, limit: int = 200) -> list[str]:
        with self._conn() as c:
            return [r["text"] for r in c.execute("SELECT text FROM idx ORDER BY rowid DESC LIMIT ?", (limit,))]

    # --- events -> daily journal note ------------------------------------
    def log_event(self, tool: str, args: dict, result: str) -> None:
        day = datetime.now().strftime("%Y-%m-%d")
        path = self.vault / "Journal" / f"{day}.md"
        if not path.exists():
            path.write_text(
                f"---\ndate: {day}\ntags: [jarvis, journal]\n---\n\n# Journal {day}\n\n## Actions\n",
                encoding="utf-8",
            )
        ts = datetime.now().strftime("%H:%M:%S")
        first = str(result).splitlines()[0][:160] if str(result) else ""
        line = f"- {ts} **{tool}** `{json.dumps(args, ensure_ascii=False)}` -> {first}\n"
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line)

    def recent_events(self, limit: int = 10) -> list[dict]:
        events: list[dict] = []
        journal = self.vault / "Journal"
        files = sorted(journal.glob("*.md"), reverse=True)[:7]
        for f in files:
            for ln in f.read_text(encoding="utf-8", errors="replace").splitlines():
                if ln.startswith("- ") and "**" in ln:
                    events.append({"line": ln.strip()})
                    if len(events) >= limit:
                        return events
        return events



# module-level singleton
_memory: Memory | None = None


def get_memory() -> Memory:
    global _memory
    if _memory is None:
        _memory = Memory()
    return _memory
