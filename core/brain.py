"""
Brain: thin, provider-agnostic wrapper around an OpenAI-compatible
chat-completions endpoint.

Confirmed working against https://100milionseek.top/v1
  models: deepseek-v4.1-flash-free, jev-1.13-free
  auth:   Authorization: Bearer <key>
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Iterable

from openai import OpenAI

from .config import settings


@dataclass
class Message:
    role: str  # system | user | assistant | tool
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict] | None = None

    def as_dict(self) -> dict:
        d: dict[str, Any] = {"role": self.role}
        if self.content:
            d["content"] = self.content
        if self.name:
            d["name"] = self.name
        if self.tool_call_id:
            d["tool_call_id"] = self.tool_call_id
        if self.tool_calls:
            d["tool_calls"] = self.tool_calls
        return d


@dataclass
class Brain:
    model: str = field(default=None)  # type: ignore[assignment]
    temperature: float = 0.3
    max_tokens: int = 1024

    def __post_init__(self) -> None:
        self.model = self.model or settings.llm_model
        self._client = OpenAI(
            base_url=settings.llm_base_url,
            api_key=settings.llm_api_key,
        )

    # ---- simple completion -------------------------------------------------
    def chat(self, messages: Iterable[Message | dict], *, temperature: float | None = None) -> str:
        payload = [m.as_dict() if isinstance(m, Message) else m for m in messages]
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=payload,  # type: ignore[arg-type]
            temperature=self.temperature if temperature is None else temperature,
            max_tokens=self.max_tokens,
        )
        return (resp.choices[0].message.content or "").strip()

    # ---- streaming completion ---------------------------------------------
    def stream(self, messages: Iterable[Message | dict], *, on_token: Callable[[str], None] | None = None) -> str:
        payload = [m.as_dict() if isinstance(m, Message) else m for m in messages]
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=payload,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        parts: list[str] = []
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                parts.append(delta)
                if on_token:
                    on_token(delta)
        return "".join(parts).strip()

    # ---- token generator (for streaming to speakers) ----------------------
    def stream_tokens(self, messages: Iterable[Message | dict]):
        """Yield text tokens as they arrive (for live TTS / typing)."""
        payload = [m.as_dict() if isinstance(m, Message) else m for m in messages]
        stream = self._client.chat.completions.create(
            model=self.model,
            messages=payload,  # type: ignore[arg-type]
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta

    # ---- tool-calling turn -------------------------------------------------
    def tool_turn(
        self,
        messages: Iterable[Message | dict],
        tools: list[dict],
        *,
        temperature: float = 0.0,
    ) -> tuple[str, list[dict]]:
        """
        Ask the model for either a normal answer or tool calls.
        Returns (content, tool_calls). tool_calls is [] when none requested.
        Temperature defaults to 0 for reliable, deterministic tool selection.
        """
        payload = [m.as_dict() if isinstance(m, Message) else m for m in messages]
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=payload,  # type: ignore[arg-type]
            temperature=temperature,
            max_tokens=self.max_tokens,
            tools=tools or None,
            tool_choice="auto" if tools else None,
        )
        msg = resp.choices[0].message
        calls: list[dict] = []
        if getattr(msg, "tool_calls", None):
            for tc in msg.tool_calls:
                calls.append(
                    {
                        "id": tc.id,
                        "name": tc.function.name,
                        "arguments": _safe_json(tc.function.arguments),
                    }
                )
        return (msg.content or "").strip(), calls


def _safe_json(raw: str) -> dict:
    try:
        return json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
