"""
RAG over local files: index a folder of text/markdown/code and answer questions
from it. Lightweight (hashing embeddings + SQLite), no downloads.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path

import tools_registry as reg
from core.config import settings

_DIM = 512
_TOKEN = re.compile(r"[a-z0-9\u0900-\u097F]+", re.IGNORECASE)
_TEXT_EXT = {".txt", ".md", ".py", ".js", ".ts", ".json", ".csv", ".html", ".css", ".java", ".c", ".cpp"}
_CHUNK = 800  # chars


def _embed(text: str) -> list[float]:
    vec = [0.0] * _DIM
    for tok in _TOKEN.findall(text.lower()):
        h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
        vec[h % _DIM] += 1.0 if (h >> 16) & 1 else -1.0
    n = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / n for v in vec]


def _cos(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _db() -> sqlite3.Connection:
    settings.ensure_dirs()
    conn = sqlite3.connect(settings.data_dir / "rag.db")
    conn.row_factory = sqlite3.Row
    conn.execute("CREATE TABLE IF NOT EXISTS rag (id INTEGER PRIMARY KEY AUTOINCREMENT, path TEXT, chunk TEXT, vec TEXT)")
    return conn


@reg.register(
    name="index_folder",
    description="Index a folder of text/markdown/code files so you can ask questions about them (RAG).",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Folder to index."}},
        "required": ["path"],
    },
)
def index_folder(path: str) -> str:
    root = Path(path)
    if not root.is_dir():
        return f"Not a folder: {path}"
    count = 0
    with _db() as c:
        for f in root.rglob("*"):
            if f.suffix.lower() not in _TEXT_EXT or not f.is_file():
                continue
            try:
                text = f.read_text(encoding="utf-8", errors="replace")
            except Exception:  # noqa: BLE001
                continue
            for i in range(0, len(text), _CHUNK):
                chunk = text[i : i + _CHUNK].strip()
                if chunk:
                    c.execute("INSERT INTO rag(path,chunk,vec) VALUES(?,?,?)",
                              (str(f), chunk, json.dumps(_embed(chunk))))
                    count += 1
    return f"Indexed {count} chunks from {root}"


@reg.register(
    name="search_files",
    description="Search previously-indexed files and return the most relevant excerpts.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "What to look for."},
            "k": {"type": "integer", "description": "How many chunks.", "default": 4},
        },
        "required": ["query"],
    },
)
def search_files(query: str, k: int = 4) -> str:
    qv = _embed(query)
    hits: list[tuple[float, str, str]] = []
    with _db() as c:
        for r in c.execute("SELECT path,chunk,vec FROM rag"):
            s = _cos(qv, json.loads(r["vec"]))
            if s > 0.08:
                hits.append((s, r["path"], r["chunk"]))
    hits.sort(reverse=True)
    if not hits:
        return "No indexed matches. Run index_folder first."
    return "\n\n".join(f"[{p}]\n{chunk[:400]}" for _, p, chunk in hits[:k])
