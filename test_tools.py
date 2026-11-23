"""Quick smoke test for tool dispatch (Phase 1)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import abilities.apps  # noqa: F401
import abilities.files  # noqa: F401
import abilities.media  # noqa: F401
import abilities.sysinfo  # noqa: F401
import tools_registry as reg

print("== registry ==")
for t in reg.all_tools():
    print(f"  {t.name}  (approval={t.requires_approval})")

print("\n== list_dir('.') ==")
print(reg.dispatch("list_dir", {"path": "."}))

print("\n== system_info() ==")
print(reg.dispatch("system_info", {}))

print("\n== media_toggle() ==")
print(reg.dispatch("media_toggle", {}))

print("\n== unknown tool ==")
try:
    reg.dispatch("does_not_exist", {})
except KeyError as exc:
    print("expected KeyError:", exc)
