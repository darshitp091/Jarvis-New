"""
Runtime skill creation: Jarvis writes a new Python tool to abilities/_learned/
and registers it live. Approval-gated (runs arbitrary generated code).
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

import tools_registry as reg
from core.config import settings

_LEARNED = settings.project_root / "abilities" / "_learned"


@reg.register(
    name="create_skill",
    description=(
        "Create and register a NEW tool at runtime. Provide a snake_case name, a one-line description, "
        "and the body of a Python function of the same name that returns a string. "
        "The code may `import tools_registry as reg` only if needed. Approval required."
    ),
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "snake_case tool name."},
            "description": {"type": "string", "description": "One-line description of the tool."},
            "code": {"type": "string", "description": "Python function body/source (def <name>(...): ...)."},
        },
        "required": ["name", "description", "code"],
    },
    requires_approval=True,
)
def create_skill(name: str, description: str, code: str) -> str:
    if not re.match(r"^[a-z_][a-z0-9_]*$", name):
        return "create_skill: name must be snake_case"
    _LEARNED.mkdir(parents=True, exist_ok=True)
    file = _LEARNED / f"{name}.py"
    wrapper = f'''"""Auto-generated skill: {description}"""
from __future__ import annotations

import tools_registry as reg


@reg.register(
    name="{name}",
    description="{description}",
    parameters={{"type": "object", "properties": {{}}}},
)
{code.strip()}
'''
    file.write_text(wrapper, encoding="utf-8")
    try:
        spec = importlib.util.spec_from_file_location(f"abilities._learned.{name}", file)
        mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
        return f"Skill '{name}' created and registered -> {file}"
    except Exception as exc:  # noqa: BLE001
        return f"create_skill error loading generated code: {exc}"
