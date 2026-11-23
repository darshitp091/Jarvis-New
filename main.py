"""
Jarvis CLI (Phase 1).

Type a command in natural language; Jarvis decides which tool to call and
answers. Voice (STT/TTS/wake word) is wired in a later phase.

    python main.py
    python main.py "open notepad and tell me my system info"
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Ensure UTF-8 console output so Hindi/Hinglish replies never crash printing.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:  # noqa: BLE001
    pass

# Import abilities so they self-register into the tool registry.
import abilities.apps  # noqa: F401,E402
import abilities.files  # noqa: F401,E402
import abilities.media  # noqa: F401,E402
import abilities.sysinfo  # noqa: F401,E402
import abilities.memory_vision  # noqa: F401,E402
import abilities.system_control  # noqa: F401,E402
import abilities.input_control  # noqa: F401,E402
import abilities.browser  # noqa: F401,E402
import abilities.coder  # noqa: F401,E402
import abilities.security  # noqa: F401,E402
import abilities.skills  # noqa: F401,E402
import abilities.reminders  # noqa: F401,E402
import abilities.rag  # noqa: F401,E402
import abilities.utilities  # noqa: F401,E402
import abilities.notes  # noqa: F401,E402
import abilities.browser_auto  # noqa: F401,E402
import abilities.productivity  # noqa: F401,E402

import agent_loop  # noqa: E402
import tools_registry as reg  # noqa: E402
from core.config import settings  # noqa: E402
from core.conversation import Conversation  # noqa: E402


def banner() -> None:
    print("=" * 60)
    print(" Jarvis CLI — type a command, 'tools' to list, 'quit' to exit")
    print("=" * 60)
    print(f" model: {settings.llm_model}   provider: {settings.llm_base_url}")
    print(f" tools: {len(reg.all_tools())} registered")
    print()


def repl() -> int:
    banner()
    conv = Conversation(session_id=Conversation.new_session_id())
    print(f" (session {conv.session_id} — I'll remember this chat until you quit)\n")
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        if line.lower() in {"quit", "exit", "q"}:
            break
        if line.lower() == "tools":
            for t in reg.all_tools():
                flag = " [approval]" if t.requires_approval else ""
                print(f"  - {t.name}{flag}: {t.description}")
            continue
        if line.lower() == "clear":
            conv.messages.clear()
            print(" (conversation cleared)")
            continue
        print("jarvis>", end=" ", flush=True)
        try:
            answer = agent_loop.run(line, history=conv.history())
            conv.add_user(line)
            conv.add_assistant(answer)
            print(answer)
        except Exception as exc:  # noqa: BLE001
            print(f"[error] {exc}")
    conv.save()
    print("bye.")
    return 0


def main() -> int:
    if len(sys.argv) > 1:
        args = [a for a in sys.argv[1:] if a not in {"--yes", "-y", "--approve"}]
        auto_yes = len(args) != len(sys.argv[1:])

        # One-shot mode must NOT block on input(). Default = deny sensitive tools.
        if auto_yes:
            agent_loop.set_approval_hook(lambda name, a: True)
        else:
            agent_loop.set_approval_hook(lambda name, a: False)

        query = " ".join(args)
        print(agent_loop.run(query))
        return 0
    return repl()


if __name__ == "__main__":
    raise SystemExit(main())
