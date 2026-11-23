"""
Coding ability: create/edit files and run Python, capturing output.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import tools_registry as reg


@reg.register(
    name="run_python",
    description="Run a Python code snippet and return stdout/stderr. Use for quick calculations or testing code.",
    parameters={
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python code to execute."}},
        "required": ["code"],
    },
    requires_approval=True,
)
def run_python(code: str) -> str:
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as fh:
            fh.write(code)
            path = fh.name
        proc = subprocess.run(
            [sys.executable, path], capture_output=True, text=True, timeout=60
        )
        out = (proc.stdout or "") + (("\n[stderr]\n" + proc.stderr) if proc.stderr else "")
        return out.strip()[:4000] or "(no output)"
    except subprocess.TimeoutExpired:
        return "run_python error: timed out (60s)"
    except Exception as exc:  # noqa: BLE001
        return f"run_python error: {exc}"
    finally:
        try:
            Path(path).unlink(missing_ok=True)  # type: ignore[name-defined]
        except Exception:  # noqa: BLE001
            pass


@reg.register(
    name="apply_code_fix",
    description="Replace a substring in a file with corrected code (first occurrence, or all if 'all' is true).",
    parameters={
        "type": "object",
        "properties": {
            "path": {"type": "string", "description": "File to edit."},
            "old": {"type": "string", "description": "Exact text to replace."},
            "new": {"type": "string", "description": "Replacement text."},
            "all": {"type": "boolean", "description": "Replace all occurrences.", "default": False},
        },
        "required": ["path", "old", "new"],
    },
    requires_approval=True,
)
def apply_code_fix(path: str, old: str, new: str, all: bool = False) -> str:
    try:
        p = Path(path)
        src = p.read_text(encoding="utf-8")
        if old not in src:
            return "apply_code_fix: 'old' text not found in file"
        count = src.count(old)
        src = src.replace(old, new, -1 if all else 1)
        p.write_text(src, encoding="utf-8")
        return f"Replaced {count if all else 1} occurrence(s) in {p}"
    except Exception as exc:  # noqa: BLE001
        return f"apply_code_fix error: {exc}"
