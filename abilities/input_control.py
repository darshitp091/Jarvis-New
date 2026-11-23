"""
Input + window + power + wifi control (keyboard, mouse, windows, power).
"""

from __future__ import annotations

import subprocess

import tools_registry as reg


# ---- keyboard / mouse ------------------------------------------------------
@reg.register(
    name="type_text",
    description="Type text into the currently focused window (keyboard simulation).",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to type."}},
        "required": ["text"],
    },
    requires_approval=True,
)
def type_text(text: str) -> str:
    try:
        import pyautogui

        pyautogui.typewrite(text, interval=0.01)
        return f"Typed {len(text)} chars"
    except Exception as exc:  # noqa: BLE001
        return f"type_text error: {exc}"


@reg.register(
    name="press_keys",
    description="Press a key or key combo, e.g. 'enter', 'ctrl+s', 'alt+tab', 'win'.",
    parameters={
        "type": "object",
        "properties": {"keys": {"type": "string", "description": "Key or combo like 'ctrl+c'."}},
        "required": ["keys"],
    },
    requires_approval=True,
)
def press_keys(keys: str) -> str:
    try:
        import pyautogui

        if "+" in keys:
            combo = [k.strip() for k in keys.split("+")]
            pyautogui.hotkey(*combo)
        else:
            pyautogui.press(keys)
        return f"Pressed {keys}"
    except Exception as exc:  # noqa: BLE001
        return f"press_keys error: {exc}"


@reg.register(
    name="click_at",
    description="Move the mouse and click at screen coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate."},
            "y": {"type": "integer", "description": "Y coordinate."},
        },
        "required": ["x", "y"],
    },
    requires_approval=True,
)
def click_at(x: int, y: int) -> str:
    try:
        import pyautogui

        pyautogui.click(x=int(x), y=int(y))
        return f"Clicked ({x}, {y})"
    except Exception as exc:  # noqa: BLE001
        return f"click_at error: {exc}"


# ---- windows ---------------------------------------------------------------
@reg.register(
    name="list_windows",
    description="List open window titles.",
    parameters=reg.NO_PARAMS,
)
def list_windows() -> str:
    try:
        import pygetwindow as gw

        titles = [t for t in gw.getAllTitles() if t.strip()]
        return "\n".join(titles[:60]) or "(none)"
    except Exception as exc:  # noqa: BLE001
        return f"list_windows error: {exc}"


@reg.register(
    name="focus_window",
    description="Bring a window to the foreground by (partial) title.",
    parameters={
        "type": "object",
        "properties": {"title": {"type": "string", "description": "Window title or part of it."}},
        "required": ["title"],
    },
)
def focus_window(title: str) -> str:
    try:
        import pygetwindow as gw

        matches = [w for w in gw.getAllWindows() if title.lower() in (w.title or "").lower()]
        if not matches:
            return f"No window matching '{title}'"
        w = matches[0]
        if w.isMinimized:
            w.restore()
        w.activate()
        return f"Focused: {w.title}"
    except Exception as exc:  # noqa: BLE001
        return f"focus_window error: {exc}"


# ---- power ----------------------------------------------------------------
@reg.register(
    name="lock_screen",
    description="Lock the workstation.",
    parameters=reg.NO_PARAMS,
)
def lock_screen() -> str:
    try:
        subprocess.run(["rundll32.exe", "user32.dll,LockWorkStation"], timeout=5)
        return "Screen locked"
    except Exception as exc:  # noqa: BLE001
        return f"lock_screen error: {exc}"


@reg.register(
    name="power_action",
    description="Power action: 'sleep', 'shutdown', or 'restart'. Requires approval.",
    parameters={
        "type": "object",
        "properties": {"action": {"type": "string", "enum": ["sleep", "shutdown", "restart"]}},
        "required": ["action"],
    },
    requires_approval=True,
)
def power_action(action: str) -> str:
    cmds = {
        "sleep": ["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"],
        "shutdown": ["shutdown", "/s", "/t", "15"],
        "restart": ["shutdown", "/r", "/t", "15"],
    }
    if action not in cmds:
        return f"unknown action {action}"
    try:
        subprocess.run(cmds[action], timeout=5)
        return f"{action} initiated"
    except Exception as exc:  # noqa: BLE001
        return f"power_action error: {exc}"


# ---- wifi -----------------------------------------------------------------
@reg.register(
    name="wifi_status",
    description="Show current wifi connection status.",
    parameters=reg.NO_PARAMS,
)
def wifi_status() -> str:
    try:
        out = subprocess.run(["netsh", "wlan", "show", "interfaces"], capture_output=True, text=True).stdout
        keep = [ln.strip() for ln in out.splitlines() if any(k in ln for k in ("SSID", "State", "Signal", "Profile"))]
        return "\n".join(keep) or out[:400]
    except Exception as exc:  # noqa: BLE001
        return f"wifi_status error: {exc}"
