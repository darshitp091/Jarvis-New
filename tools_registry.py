"""
Tool registry: every capability declares a JSON schema (OpenAI function format)
plus a Python callable. The agent loop hands schemas to the LLM and dispatches
the chosen tool here.

Adding a new capability = write a function + register() it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict
    func: Callable[..., Any]
    requires_approval: bool = False

    def schema(self) -> dict:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


_REGISTRY: dict[str, Tool] = {}


def register(
    name: str,
    description: str,
    parameters: dict,
    requires_approval: bool = False,
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    def _wrap(fn: Callable[..., Any]) -> Callable[..., Any]:
        _REGISTRY[name] = Tool(
            name=name,
            description=description,
            parameters=parameters,
            func=fn,
            requires_approval=requires_approval,
        )
        return fn

    return _wrap


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def all_tools() -> list[Tool]:
    return list(_REGISTRY.values())


def schemas() -> list[dict]:
    return [t.schema() for t in _REGISTRY.values()]


def dispatch(name: str, arguments: dict) -> Any:
    tool = _REGISTRY.get(name)
    if tool is None:
        raise KeyError(f"unknown tool: {name}")
    return tool.func(**arguments)


# Convenience schema fragments
NO_PARAMS = {"type": "object", "properties": {}}
