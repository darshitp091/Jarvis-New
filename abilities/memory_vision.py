"""Memory + vision abilities exposed as tools."""

from __future__ import annotations

import tools_registry as reg
from core.memory import get_memory
from core import vision


@reg.register(
    name="remember",
    description="Store a fact or note about the user into long-term memory for later recall.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "The fact/note to remember."}},
        "required": ["text"],
    },
)
def remember(text: str) -> str:
    note = get_memory().remember(text)
    return f"Saved to Obsidian vault as [[{note}]] — {text}"


@reg.register(
    name="recall",
    description="Search long-term memory for facts related to a query.",
    parameters={
        "type": "object",
        "properties": {"query": {"type": "string", "description": "What to search memory for."}},
        "required": ["query"],
    },
)
def recall(query: str) -> str:
    hits = get_memory().recall(query)
    return "\n".join(hits) if hits else "nothing relevant in memory"


@reg.register(
    name="look_at_screen",
    description="Take a screenshot and analyze/understand what is on the screen (incl. reading code and spotting errors).",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "What to look for on the screen.", "default": "Describe what's on the screen."}
        },
    },
)
def look_at_screen(question: str = "Describe what's on the screen.") -> str:
    return vision.analyze_screenshot(question)


@reg.register(
    name="look_at_me",
    description="Capture the webcam and analyze the user (mood/expression, clothing) for suggestions.",
    parameters={
        "type": "object",
        "properties": {
            "question": {"type": "string", "description": "What to assess.", "default": "Describe the person: mood, expression, clothing."}
        },
    },
)
def look_at_me(question: str = "Describe the person: mood, expression, clothing.") -> str:
    return vision.analyze_webcam(question)


@reg.register(
    name="assess_mood",
    description="Read the user's current mood from the webcam and suggest something helpful (e.g. music if tired/stressed).",
    parameters=reg.NO_PARAMS,
)
def assess_mood_tool() -> str:
    from senses import mood

    return mood.check_and_suggest()

