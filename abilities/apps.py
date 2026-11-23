"""
App control: launch / close / list running apps on Windows.

Uses os.startfile / subprocess for launch and taskkill/tasklist for processes.
"""

from __future__ import annotations

import os
import subprocess

import tools_registry as reg


@reg.register(
    name="open_app",
    description="Open/launch an application by name or path (e.g. 'notepad', 'chrome', 'calc', or a full .exe path).",
    parameters={
        "type": "object",
        "properties": {
            "target": {"type": "string", "description": "App name or executable path to launch."},
        },
        "required": ["target"],
    },
)
def open_app(target: str) -> str:
    target = target.strip()
    # Try common Windows launch approaches in order.
    try:
        os.startfile(target)  # works for registered apps / file paths
        return f"Launched {target}"
    except OSError:
        pass
    try:
        subprocess.Popen(target, shell=True)
        return f"Started {target}"
    except Exception as exc:  # noqa: BLE001
        return f"Failed to open {target}: {exc}"


@reg.register(
    name="close_app",
    description="Close/kill a running application by process image name (e.g. 'notepad.exe', 'chrome.exe').",
    parameters={
        "type": "object",
        "properties": {
            "process": {"type": "string", "description": "Process image name to terminate."},
        },
        "required": ["process"],
    },
    requires_approval=True,
)
def close_app(process: str) -> str:
    proc = process if process.lower().endswith(".exe") else process + ".exe"
    try:
        subprocess.run(["taskkill", "/IM", proc, "/F"], capture_output=True, text=True, check=False)
        return f"Closed {proc}"
    except Exception as exc:  # noqa: BLE001
        return f"Failed to close {proc}: {exc}"


@reg.register(
    name="list_running_apps",
    description="List currently running top-level processes (best effort).",
    parameters=reg.NO_PARAMS,
)
def list_running_apps() -> str:
    try:
        out = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            check=False,
        ).stdout
        names = []
        for line in out.splitlines():
            parts = line.split(",")
            if parts and parts[0].strip('"'):
                names.append(parts[0].strip('"'))
        # de-dup, keep it short
        uniq = sorted(set(names))
        return ", ".join(uniq[:80])
    except Exception as exc:  # noqa: BLE001
        return f"Failed to list apps: {exc}"
