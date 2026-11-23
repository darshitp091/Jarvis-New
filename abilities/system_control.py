"""
System control: volume, brightness, clipboard.
"""

from __future__ import annotations

import subprocess

import tools_registry as reg


# ---- volume (pycaw) --------------------------------------------------------
def _volume_device():
    """Return the default speaker AudioDevice (endpoint volume accessible)."""
    from pycaw.pycaw import AudioUtilities

    return AudioUtilities.GetSpeakers()


@reg.register(
    name="set_volume",
    description="Set system volume to a percentage (0-100).",
    parameters={
        "type": "object",
        "properties": {"percent": {"type": "integer", "description": "Volume 0-100."}},
        "required": ["percent"],
    },
)
def set_volume(percent: int) -> str:
    try:
        p = max(0, min(100, int(percent)))
        device = _volume_device()
        device.EndpointVolume.SetMasterVolumeLevelScalar(p / 100.0, None)
        return f"Volume set to {p}%"
    except Exception as exc:  # noqa: BLE001
        return f"set_volume error: {exc}"


@reg.register(
    name="get_volume",
    description="Get the current system volume percentage.",
    parameters=reg.NO_PARAMS,
)
def get_volume() -> str:
    try:
        device = _volume_device()
        scalar = device.EndpointVolume.GetMasterVolumeLevelScalar()
        return f"Volume is {int(round(scalar * 100))}%"
    except Exception as exc:  # noqa: BLE001
        return f"get_volume error: {exc}"


# ---- brightness (PowerShell WMI) ------------------------------------------
@reg.register(
    name="set_brightness",
    description="Set screen brightness percentage (0-100).",
    parameters={
        "type": "object",
        "properties": {"percent": {"type": "integer", "description": "Brightness 0-100."}},
        "required": ["percent"],
    },
)
def set_brightness(percent: int) -> str:
    p = max(0, min(100, int(percent)))
    ps = (
        "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
        f".WmiSetBrightness(1,{p})"
    )
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, timeout=10)
        return f"Brightness set to {p}%"
    except Exception as exc:  # noqa: BLE001
        return f"set_brightness error: {exc}"


# ---- clipboard -------------------------------------------------------------
@reg.register(
    name="set_clipboard",
    description="Copy text to the system clipboard.",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "Text to copy."}},
        "required": ["text"],
    },
)
def set_clipboard(text: str) -> str:
    try:
        import pyperclip

        pyperclip.copy(text)
        return f"Copied {len(text)} chars to clipboard"
    except Exception as exc:  # noqa: BLE001
        return f"set_clipboard error: {exc}"


@reg.register(
    name="get_clipboard",
    description="Read the current system clipboard text.",
    parameters=reg.NO_PARAMS,
)
def get_clipboard() -> str:
    try:
        import pyperclip

        return pyperclip.paste()[:2000]
    except Exception as exc:  # noqa: BLE001
        return f"get_clipboard error: {exc}"
