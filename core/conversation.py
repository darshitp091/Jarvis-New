"""
Conversation memory: keeps the last N turns of the chat so Jarvis has a thread
of context within a session, and can persist it per session to disk.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from core.brain import Message
from core.config import settings


@dataclass
class Conversation:
    max_turns: int = 12  # user+assistant pairs kept in context
    session_id: str = ""
    messages: list[Message] = field(default_factory=list)

    def add_user(self, text: str) -> None:
        self.messages.append(Message("user", text))
        self._trim()

    def add_assistant(self, text: str) -> None:
        self.messages.append(Message("assistant", text))
        self._trim()

    def _trim(self) -> None:
        # keep the last max_turns*2 non-system messages
        limit = self.max_turns * 2
        if len(self.messages) > limit:
            self.messages = self.messages[-limit:]

    def history(self) -> list[Message]:
        """Messages to feed the agent loop (excludes system prompt)."""
        return list(self.messages)

    # --- persistence ------------------------------------------------------
    def save(self) -> None:
        if not self.session_id:
            return
        settings.ensure_dirs()
        path = settings.data_dir / f"session_{self.session_id}.json"
        data = [{"role": m.role, "content": m.content} for m in self.messages]
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, session_id: str, max_turns: int = 12) -> "Conversation":
        conv = cls(max_turns=max_turns, session_id=session_id)
        path = settings.data_dir / f"session_{session_id}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                for m in data:
                    conv.messages.append(Message(m["role"], m.get("content", "")))
            except Exception:  # noqa: BLE001
                pass
        return conv

    @staticmethod
    def new_session_id() -> str:
        return time.strftime("%Y%m%d-%H%M%S")
