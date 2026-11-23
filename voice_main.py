"""
Voice entrypoint: talk to Jarvis.

    python voice_main.py
        -> press Enter to start talking (records 5s), or type 'q' to quit.
        -> Jarvis transcribes, thinks, and speaks the reply.

Fully offline except the LLM call. TTS=Edge, STT=Whisper tiny-int8.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# register all abilities
import main as _abilities  # noqa: F401,E402  (imports all ability modules)

import agent_loop  # noqa: E402
from senses import voice  # noqa: E402

RECORD_SECONDS = 5.0


def repl() -> int:
    print("=" * 60)
    print(" Jarvis VOICE mode — press Enter to talk, 'q' to quit")
    print("=" * 60)
    agent_loop.set_approval_hook(lambda name, a: False)  # deny sensitive in voice mode
    while True:
        try:
            cmd = input("\n[Enter] to speak > ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            break
        if cmd in {"q", "quit", "exit"}:
            break

        text = voice.listen_once(RECORD_SECONDS)
        print(f"you (heard)> {text}")
        if not text.strip():
            print("  (didn't catch that)")
            continue

        try:
            answer = agent_loop.run(text)
        except Exception as exc:  # noqa: BLE001
            answer = f"Sorry, error: {exc}"
        print(f"jarvis> {answer}")
        try:
            voice.speak(answer)
        except Exception as exc:  # noqa: BLE001
            print(f"  (tts error: {exc})")
    print("bye.")
    return 0


if __name__ == "__main__":
    raise SystemExit(repl())
