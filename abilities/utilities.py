"""
Everyday utilities: time/date, weather (free, no key), math, unit conversion,
and translation (via the LLM).
"""

from __future__ import annotations

from datetime import datetime

import requests

import tools_registry as reg


@reg.register(
    name="current_time",
    description="Get the current date and time.",
    parameters=reg.NO_PARAMS,
)
def current_time() -> str:
    return datetime.now().strftime("%A, %Y-%m-%d %H:%M:%S")


@reg.register(
    name="weather",
    description="Get current weather for a city (free, no API key). Uses wttr.in.",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name.", "default": "auto"}},
    },
)
def weather(city: str = "auto") -> str:
    try:
        resp = requests.get(f"https://wttr.in/{city}?format=3", timeout=10,
                            headers={"User-Agent": "curl/8"})
        return resp.text.strip() or "weather unavailable"
    except Exception as exc:  # noqa: BLE001
        return f"weather error: {exc}"


@reg.register(
    name="calculate",
    description="Evaluate a math expression safely (e.g. '12*7+3', 'sqrt(2)', '100/4').",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string", "description": "Math expression."}},
        "required": ["expression"],
    },
)
def calculate(expression: str) -> str:
    import math as _m

    allowed = {k: getattr(_m, k) for k in dir(_m) if not k.startswith("_")}
    allowed.update({"abs": abs, "round": round, "min": min, "max": max, "sum": sum})
    try:
        # Only allow safe names/operators.
        value = eval(expression, {"__builtins__": {}}, allowed)  # noqa: S307
        return str(value)
    except Exception as exc:  # noqa: BLE001
        return f"calc error: {exc}"


@reg.register(
    name="convert_units",
    description="Convert a value between units (length, mass, temperature).",
    parameters={
        "type": "object",
        "properties": {
            "value": {"type": "number", "description": "Numeric value."},
            "from_unit": {"type": "string", "description": "Source unit (km, m, mi, kg, g, lb, C, F, K)."},
            "to_unit": {"type": "string", "description": "Target unit."},
        },
        "required": ["value", "from_unit", "to_unit"],
    },
)
def convert_units(value: float, from_unit: str, to_unit: str) -> str:
    f, t = from_unit.strip().lower(), to_unit.strip().lower()
    # temperature special-cases
    def to_c(v: float, u: str) -> float:
        return {"c": v, "f": (v - 32) * 5 / 9, "k": v - 273.15}[u]

    def from_c(v: float, u: str) -> float:
        return {"c": v, "f": v * 9 / 5 + 32, "k": v + 273.15}[u]

    try:
        if f in {"c", "f", "k"} and t in {"c", "f", "k"}:
            return f"{value} {from_unit} = {from_c(to_c(value, f), t):.2f} {to_unit}"
        length = {"km": 1000, "m": 1, "cm": 0.01, "mm": 0.001, "mi": 1609.34, "ft": 0.3048, "in": 0.0254}
        mass = {"kg": 1, "g": 0.001, "lb": 0.453592, "oz": 0.0283495}
        table = length if f in length and t in length else mass if f in mass and t in mass else None
        if table:
            return f"{value} {from_unit} = {value * table[f] / table[t]:.4g} {to_unit}"
        return "unsupported unit conversion"
    except Exception as exc:  # noqa: BLE001
        return f"convert error: {exc}"


@reg.register(
    name="translate",
    description="Translate text to another language (uses the LLM).",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to translate."},
            "to": {"type": "string", "description": "Target language (e.g. Hindi, English, Spanish)."},
        },
        "required": ["text", "to"],
    },
)
def translate(text: str, to: str) -> str:
    from core.brain import Brain

    try:
        return Brain().chat([{"role": "user", "content": f"Translate to {to}. Return only the translation:\n{text}"}])
    except Exception as exc:  # noqa: BLE001
        return f"translate error: {exc}"
