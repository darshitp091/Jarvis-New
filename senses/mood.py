"""
Mood / emotion sensing via the webcam + vision model, plus music suggestions.

This is *sampled* awareness (not continuous 30fps): call `assess_mood()` when you
want a read, and `maybe_alert()` for a low-frequency background check.
"""

from __future__ import annotations

from core import vision
from core.memory import get_memory

_MOOD_PROMPT = (
    "Look at this person's facial expression, posture, and overall vibe. "
    "In 2-3 short sentences, describe their apparent mood (e.g. tired, stressed, "
    "happy, focused, sad) and note what they're wearing. Be warm and non-judgmental."
)


def assess_mood() -> str:
    """Capture a webcam frame and get a mood/expression read."""
    return vision.analyze_webcam(_MOOD_PROMPT)


def suggest_for_mood(mood_text: str) -> str:
    """Ask the brain for a gentle suggestion (e.g. music) based on the mood read."""
    from core.brain import Brain

    brain = Brain()
    prompt = (
        f"The user's current read is: '{mood_text}'. "
        "In one or two sentences, give a warm, practical suggestion. If they seem "
        "tired/stressed, suggest calming music (name a Spotify-playable genre or artist). "
        "Keep it kind and short, Hinglish-friendly."
    )
    try:
        return brain.chat([{"role": "user", "content": prompt}])
    except Exception as exc:  # noqa: BLE001
        return f"(couldn't generate suggestion: {exc})"


def check_and_suggest() -> str:
    """One-shot: read mood, then suggest. Also remembers the read."""
    mood = assess_mood()
    if mood.startswith("vision error") or mood.startswith("webcam error"):
        return mood
    get_memory().remember(f"Mood snapshot: {mood}", tag="mood")
    suggestion = suggest_for_mood(mood)
    return f"{mood}\n\nSuggestion: {suggestion}"
