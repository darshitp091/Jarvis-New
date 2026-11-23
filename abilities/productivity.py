"""
Productivity extras: OCR text extraction, file search, file organization,
and drafting emails via the default mail client.
"""

from __future__ import annotations

import shutil
import webbrowser
from pathlib import Path

import tools_registry as reg


@reg.register(
    name="ocr_screen",
    description="Read the text currently visible on screen via OCR (returns recognized text).",
    parameters={
        "type": "object",
        "properties": {"max_chars": {"type": "integer", "description": "Max chars to return.", "default": 2000}},
    },
)
def ocr_screen(max_chars: int = 2000) -> str:
    try:
        import mss
        import pytesseract
        from PIL import Image

        with mss.MSS() as sct:
            img = sct.grab(sct.monitors[1])
            pil = Image.frombytes("RGB", img.size, img.rgb)
        text = pytesseract.image_to_string(pil)
        return text.strip()[:max_chars] or "(no text found)"
    except Exception as exc:  # noqa: BLE001
        return f"ocr_screen error: {exc}"


@reg.register(
    name="find_files",
    description="Find files by name substring under a folder.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "Folder to search (e.g. C:\\Users\\patel)."},
            "name_contains": {"type": "string", "description": "Filename substring to match."},
            "limit": {"type": "integer", "description": "Max results.", "default": 30},
        },
        "required": ["folder", "name_contains"],
    },
)
def find_files(folder: str, name_contains: str, limit: int = 30) -> str:
    try:
        root = Path(folder)
        hits = [str(p) for p in root.rglob(f"*{name_contains}*") if p.is_file()][:limit]
        return "\n".join(hits) if hits else "no matching files"
    except Exception as exc:  # noqa: BLE001
        return f"find_files error: {exc}"


@reg.register(
    name="organize_folder",
    description="Move files in a folder into subfolders by extension (e.g. Images/, Docs/, Code/). Dry-run unless confirm=true.",
    parameters={
        "type": "object",
        "properties": {
            "folder": {"type": "string", "description": "Folder to organize."},
            "confirm": {"type": "boolean", "description": "Actually move files.", "default": False},
        },
        "required": ["folder"],
    },
    requires_approval=True,
)
def organize_folder(folder: str, confirm: bool = False) -> str:
    groups = {
        "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"},
        "Docs": {".pdf", ".doc", ".docx", ".txt", ".md", ".xls", ".xlsx", ".ppt", ".pptx"},
        "Code": {".py", ".js", ".ts", ".html", ".css", ".java", ".c", ".cpp", ".json"},
        "Media": {".mp3", ".mp4", ".wav", ".mkv", ".mov"},
        "Archives": {".zip", ".rar", ".7z", ".tar", ".gz"},
    }
    root = Path(folder)
    if not root.is_dir():
        return f"not a folder: {folder}"
    plan: list[tuple[Path, str]] = []
    for f in root.iterdir():
        if not f.is_file():
            continue
        for group, exts in groups.items():
            if f.suffix.lower() in exts:
                plan.append((f, group))
                break
    if not plan:
        return "nothing to organize"
    if not confirm:
        return "DRY RUN (say confirm=true to move):\n" + "\n".join(f"{f.name} -> {g}/" for f, g in plan)
    for f, group in plan:
        dest = root / group
        dest.mkdir(exist_ok=True)
        shutil.move(str(f), str(dest / f.name))
    return f"Organized {len(plan)} files into subfolders."


@reg.register(
    name="draft_email",
    description="Open a pre-filled email draft in the default mail client (does NOT send).",
    parameters={
        "type": "object",
        "properties": {
            "to": {"type": "string", "description": "Recipient email."},
            "subject": {"type": "string", "description": "Subject."},
            "body": {"type": "string", "description": "Body text."},
        },
        "required": ["to", "subject", "body"],
    },
)
def draft_email(to: str, subject: str, body: str) -> str:
    from urllib.parse import quote

    url = f"mailto:{quote(to)}?subject={quote(subject)}&body={quote(body)}"
    try:
        webbrowser.open(url)
        return f"Opened email draft to {to} (not sent)."
    except Exception as exc:  # noqa: BLE001
        return f"draft_email error: {exc}"
