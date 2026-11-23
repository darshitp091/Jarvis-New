"""
Media control for the active media session on Windows.

Uses the WinRT GSMTC API via a tiny PowerShell shim so no extra Python deps are
needed, and it controls whatever app is currently playing (Spotify, browser,
VLC, etc.) -- including Spotify WITHOUT any Spotify API key.
"""

from __future__ import annotations

import subprocess

import tools_registry as reg

# PowerShell using Windows.Media.Control (GlobalSystemMediaTransportControls).
_PS_TEMPLATE = r"""
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager,Windows.Media.Control,ContentType=WindowsRuntime]

$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
})[0]

function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
}

$mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
$session = $mgr.GetCurrentSession()
if ($session -eq $null) { Write-Output "NO_SESSION"; return }

{ACTION}
"""

_ACTIONS = {
    "play": "$session.TryPlayAsync() | Out-Null; Write-Output 'PLAY'",
    "pause": "$session.TryPauseAsync() | Out-Null; Write-Output 'PAUSE'",
    "playpause": "$session.TryTogglePlayPauseAsync() | Out-Null; Write-Output 'TOGGLE'",
    "next": "$session.TrySkipNextAsync() | Out-Null; Write-Output 'NEXT'",
    "previous": "$session.TrySkipPreviousAsync() | Out-Null; Write-Output 'PREV'",
}


def _run_ps(action: str) -> str:
    script = _PS_TEMPLATE.replace("{ACTION}", _ACTIONS[action])
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            capture_output=True,
            text=True,
            check=False,
            timeout=20,
        )
        result = (out.stdout or out.stderr).strip()
        return result or "done"
    except Exception as exc:  # noqa: BLE001
        return f"media error: {exc}"


def _media_action(action: str) -> str:
    return _run_ps(action)


@reg.register(
    name="media_play",
    description="Resume/play the current media session (Spotify, browser, VLC, etc.).",
    parameters=reg.NO_PARAMS,
)
def media_play() -> str:
    return _media_action("play")


@reg.register(
    name="media_pause",
    description="Pause the current media session.",
    parameters=reg.NO_PARAMS,
)
def media_pause() -> str:
    return _media_action("pause")


@reg.register(
    name="media_toggle",
    description="Toggle play/pause for the current media session.",
    parameters=reg.NO_PARAMS,
)
def media_toggle() -> str:
    return _media_action("playpause")


@reg.register(
    name="media_next",
    description="Skip to the next track.",
    parameters=reg.NO_PARAMS,
)
def media_next() -> str:
    return _media_action("next")


@reg.register(
    name="media_previous",
    description="Go to the previous track.",
    parameters=reg.NO_PARAMS,
)
def media_previous() -> str:
    return _media_action("previous")
