"""
Agent loop: the "think -> act -> observe" cycle.

Given a user message, it asks the Brain which tool (if any) to call, executes it
via the registry, feeds the result back, and repeats until the model produces a
final natural-language answer. Guarded by an approval hook for sensitive tools.
"""

from __future__ import annotations

import json
from typing import Callable

import tools_registry as reg
from core.brain import Brain, Message
from core.config import settings
from core.memory import get_memory

SYSTEM_PROMPT = """You are JARVIS, a personal AI assistant running locally on {user}'s Windows laptop — like Iron Man's JARVIS but real.
Personality:
- Calm, capable, quietly witty. Address the user as "{user}" or "sir" occasionally (not every line).
- Speak concisely and naturally; you may mix English and Hinglish to match the user.
- Confident and helpful; never robotic, never over-apologetic.
You CONTROL this machine through callable tools (functions) provided natively in every request -- they really exist and work.
Rules:
- When the user asks you to DO something on the machine, you MUST call the matching tool instead of saying you cannot.
- For this computer (RAM/CPU/OS) use `system_info` / `list_running_apps`; wifi -> `wifi_status`.
- Apps: open_app / close_app / list_running_apps. Media: media_play/pause/toggle/next/previous.
- Volume: set_volume/get_volume. Brightness: set_brightness. Clipboard: set_clipboard/get_clipboard.
- Windows: list_windows/focus_window. Keys/mouse: type_text/press_keys/click_at.
- Power: lock_screen/power_action. Web: open_url/search_web/fetch_page. Code: run_python/apply_code_fix.
- Memory: remember/recall. Vision: look_at_screen/look_at_me. Mood: assess_mood.
- Only run `security_audit` when explicitly asked for a security check-up.
- Files: read_file/write_file/list_dir.
- NEVER claim you lack a tool if one of the above fits -- call it.
- Remember earlier turns in this conversation; refer back naturally ("as you asked...").
- If a request is ambiguous or destructive, ask before acting.
- Only use the provided tools; do not invent tool names."""

# Backwards-compatible default (no user name); run() formats in the real name.
DEFAULT_SYSTEM_PROMPT = SYSTEM_PROMPT.format(user="the user")

# Approval hook: returns True if the action may proceed.
_approval: Callable[[str, dict], bool] | None = None


def set_approval_hook(fn: Callable[[str, dict], bool] | None) -> None:
    global _approval
    _approval = fn


def _default_approval(tool_name: str, args: dict) -> bool:
    if settings.auto_approve:
        return True
    print(f"\n  [APPROVAL] Jarvis wants to run `{tool_name}` with {args}")
    ans = input("  Allow? [y/N] ").strip().lower()
    return ans in {"y", "yes"}


def _needs_approval(tool_name: str, args: dict) -> bool:
    tool = reg.get(tool_name)
    if not tool or not tool.requires_approval:
        return False
    hook = _approval or _default_approval
    return not hook(tool_name, args)


def run(user_text: str, *, history: list[Message] | None = None, max_steps: int = 6) -> str:
    brain = Brain()
    mem = get_memory()

    # Build a system prompt enriched with relevant long-term memories.
    system = SYSTEM_PROMPT.format(user=settings.user_name)
    relevant = mem.recall(user_text, k=5)
    if relevant:
        system += (
            "\n\n=== YOUR LONG-TERM MEMORY (these are TRUE facts you already know about the user) ===\n- "
            + "\n- ".join(relevant)
            + "\n=== END MEMORY ===\n"
            "If the user asks something these facts answer, USE THEM directly instead of "
            "saying you don't remember. Do NOT call a recall tool for facts already listed above."
        )

    msgs: list[Message] = [Message("system", system)]
    if history:
        msgs.extend(history)
    msgs.append(Message("user", user_text))

    tools = reg.schemas()

    for _ in range(max_steps):
        content, calls = brain.tool_turn(msgs, tools)

        # No tool requested -> final answer.
        if not calls:
            return content or "(no answer)"

        # Record the assistant's tool-call message.
        msgs.append(
            Message(
                role="assistant",
                content=content,
                tool_calls=[
                    {
                        "id": c["id"],
                        "type": "function",
                        "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])},
                    }
                    for c in calls
                ],
            )
        )

        # Execute each call.
        for call in calls:
            name, args = call["name"], call["arguments"]
            if _needs_approval(name, args):
                result = f"User DENIED permission to run {name}."
            else:
                try:
                    result = reg.dispatch(name, args)
                except Exception as exc:  # noqa: BLE001
                    result = f"tool {name} failed: {exc}"
                mem.log_event(name, args, str(result))
                # Self-correction: if a tool reports an error, tell the model so
                # it can retry with different args or a different tool.
                if _looks_like_error(result):
                    result = (
                        f"{result}\n\n[SYSTEM: the previous tool call seems to have failed. "
                        "Diagnose the cause and either retry with corrected arguments or "
                        "use a different tool. Do not give up immediately.]"
                    )
            msgs.append(Message(role="tool", content=str(result), tool_call_id=call["id"]))

    return "(stopped: reached max tool steps)"


def _looks_like_error(result: object) -> bool:
    s = str(result).lower()
    markers = ("error", "failed", "denied", "not found", "no such", "timed out", "exception")
    return any(m in s for m in markers)

