"""File system abilities: read, write, list, search (text)."""

from __future__ import annotations

from pathlib import Path

import tools_registry as reg


@reg.register(
    name="read_file",
    description="Read a text file and return its contents (truncated if very large).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "Absolute or relative file path."},
            "max_chars": {"type": "integer", "description": "Max characters to return.", "default": 8000},
        },
        "required": ["path"],
    },
)
def read_file(path: str, max_chars: int = 8000) -> str:
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
        return text[:max_chars]
    except Exception as exc:  # noqa: BLE001
        return f"read_file error: {exc}"


@reg.register(
    name="write_file",
    description="Write text to a file (creates or overwrites).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File path to write."},
            "content": {"type": "string", "description": "Text content."},
        },
        "required": ["path", "content"],
    },
    requires_approval=True,
)
def write_file(path: str, content: str) -> str:
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {p}"
    except Exception as exc:  # noqa: BLE001
        return f"write_file error: {exc}"


@reg.register(
    name="list_dir",
    description="List the entries in a directory.",
    parameters={
        "type": "object",
        "properties": {"path": {"type": "string", "description": "Directory path.", "default": "."}},
    },
)
def list_dir(path: str = ".") -> str:
    try:
        p = Path(path)
        entries = [f"{e.name}/" if e.is_dir() else e.name for e in sorted(p.iterdir())]
        return "\n".join(entries[:200]) or "(empty)"
    except Exception as exc:  # noqa: BLE001
        return f"list_dir error: {exc}"
