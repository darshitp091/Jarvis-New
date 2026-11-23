"""LIVE feature test battery for Jarvis — exercises every category via dispatch."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import main  # noqa: F401  (registers all abilities)
import tools_registry as reg


def show(label, tool, args, limit=240):
    try:
        out = reg.dispatch(tool, args)
    except Exception as exc:  # noqa: BLE001
        out = f"ERROR: {exc}"
    text = str(out).replace("\n", " | ")
    if len(text) > limit:
        text = text[:limit] + "..."
    print(f"[{label}] {tool} -> {text}")


print("=" * 70)
print(f"JARVIS LIVE TEST BATTERY  |  total tools = {len(reg.all_tools())}")
print("=" * 70)

print("\n--- 1. SYSTEM ---")
show("sysinfo", "system_info", {})
show("monitor", "system_monitor", {})

print("\n--- 2. TIME / MATH / UNITS / TRANSLATE ---")
show("time", "current_time", {})
show("calc", "calculate", {"expression": "(12*7+3)**0.5"})
show("units-temp", "convert_units", {"value": 100, "from_unit": "C", "to_unit": "F"})
show("units-len", "convert_units", {"value": 50, "from_unit": "km", "to_unit": "mi"})
show("translate", "translate", {"text": "Good morning, how are you?", "to": "Hindi"})

print("\n--- 3. WEATHER (free, no key) ---")
show("weather", "weather", {"city": "Delhi"})

print("\n--- 4. MEMORY (Obsidian) ---")
show("remember", "remember", {"text": "My test colour is teal"})
show("recall", "recall", {"query": "test colour teal"})

print("\n--- 5. REMINDERS / TODOS ---")
show("reminder", "set_reminder", {"text": "live test reminder", "when": "in 5 minutes"})
show("list-rem", "list_reminders", {})
show("todo-add", "add_todo", {"text": "live test task"})
show("todo-list", "list_todos", {})

print("\n--- 6. VOLUME / CLIPBOARD ---")
show("get-vol", "get_volume", {})
show("set-vol", "set_volume", {"percent": 45})
show("get-vol2", "get_volume", {})
show("clip-set", "set_clipboard", {"text": "jarvis live test"})
show("clip-get", "get_clipboard", {})
show("clip-save", "clipboard_save", {})

print("\n--- 7. APPS / WINDOWS / MEDIA ---")
show("apps", "list_running_apps", {}, limit=160)
show("windows", "list_windows", {}, limit=160)
show("media", "media_toggle", {})

print("\n--- 8. FILES ---")
show("list-dir", "list_dir", {"path": str(Path(__file__).parent)}, limit=200)
show("find", "find_files", {"folder": str(Path(__file__).parent), "name_contains": "README"})
show("read", "read_file", {"path": str(Path(__file__).parent / "requirements.txt")}, limit=120)

print("\n--- 9. WEB / SCRAPE / PLAYWRIGHT ---")
show("fetch", "fetch_page", {"url": "https://example.com"}, limit=120)
show("browse", "browse", {"url": "https://example.com", "max_chars": 100}, limit=120)

print("\n--- 10. CODE ---")
show("runpy", "run_python", {"code": "print(sum(range(11)))"})

print("\n--- 11. RAG OVER LOCAL FILES ---")
show("index", "index_folder", {"path": str(Path(__file__).parent / "core")})
show("search", "search_files", {"query": "obsidian vault memory"})

print("\n--- 12. VISION / OCR / MOOD ---")
show("ocr-screen", "ocr_screen", {"max_chars": 100})
show("look-screen", "look_at_screen", {"question": "What is on the screen? One sentence."}, limit=200)

print("\n--- 13. SECURITY (defensive) ---")
show("audit", "security_audit", {}, limit=200)

print("\n" + "=" * 70)
print("BATTERY COMPLETE")
print("=" * 70)
