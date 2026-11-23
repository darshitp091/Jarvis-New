"""
Proactive watcher + ambient dialogue.

Checks system health and (optionally) speaks up unprompted with a suggestion —
closest thing to Iron-Man JARVIS noticing things on its own. Run in background:

    python proactive.py                 # silent alerts, every 60s
    python proactive.py --speak          # speaks alerts aloud
    python proactive.py --fast --speak   # every 15s, spoken
    python proactive.py --mood           # also periodically read mood (camera)

Safe: reads metrics only; suggestions/actions are non-destructive.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    import psutil
except ImportError:
    print("psutil required: pip install psutil")
    raise SystemExit(1)

from core.memory import get_memory

CPU_WARN = 90.0
RAM_WARN = 92.0
DISK_WARN = 90.0

_last: dict[str, float] = {}
COOLDOWN = 300.0


def _say(message: str, speak: bool) -> None:
    if speak:
        try:
            from senses import voice

            voice.speak(message)
        except Exception:  # noqa: BLE001
            pass


def _alert(kind: str, message: str, speak: bool) -> None:
    now = time.time()
    if now - _last.get(kind, 0) < COOLDOWN:
        return
    _last[kind] = now
    ts = time.strftime("%H:%M:%S")
    print(f"[{ts}] JARVIS: {message}")
    get_memory().log_event("proactive_warning", {"kind": kind}, message)
    _say(message, speak)


def check_system(speak: bool = False) -> None:
    cpu = psutil.cpu_percent(interval=1.0)
    ram = psutil.virtual_memory()
    disk_path = "C:\\" if sys.platform == "win32" else "/"
    disk = psutil.disk_usage(disk_path).percent

    if cpu >= CPU_WARN:
        _alert("cpu", f"CPU bahut high hai ({cpu:.0f}%). Kuch stuck lag raha hai.", speak)
    if ram.percent >= RAM_WARN:
        _alert(
            "ram",
            f"Memory almost full hai ({ram.percent:.0f}%, {ram.available/1024**3:.1f}GB free). "
            "Main kuch heavy apps band kar sakta hoon — bataiye.",
            speak,
        )
    if disk >= DISK_WARN:
        _alert("disk", f"Disk nearly full hai ({disk:.0f}%). Cleanup dekh lein.", speak)


def check_mood(speak: bool = False) -> None:
    """Periodic (cooldown-gated) mood read + suggestion."""
    try:
        from senses import mood

        read = mood.check_and_suggest()
        _alert("mood", read, speak)
    except Exception as exc:  # noqa: BLE001
        print(f"[mood] skipped: {exc}")


def check_reminders(speak: bool = False) -> None:
    """Speak any reminders that are now due."""
    try:
        import abilities.reminders as rem

        for text in rem.due_reminders():
            _alert(f"reminder_{int(time.time())}", f"Reminder: {text}", speak)
    except Exception as exc:  # noqa: BLE001
        print(f"[reminders] skipped: {exc}")


def main() -> int:
    fast = "--fast" in sys.argv
    speak = "--speak" in sys.argv
    do_mood = "--mood" in sys.argv
    interval = 15 if fast else 60
    print(f"Jarvis watcher started (every {interval}s, speak={speak}, mood={do_mood}). Ctrl+C to stop.")
    tick = 0
    try:
        while True:
            check_system(speak=speak)
            check_reminders(speak=speak)
            if do_mood and tick % 10 == 0:
                check_mood(speak=speak)
            tick += 1
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nwatcher stopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

