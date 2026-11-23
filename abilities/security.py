"""
Ethical security — DEFENSIVE ONLY, on the local machine, approval-gated.

Nothing here attacks third parties. It audits the user's own system for common
weaknesses and suggests hardening. Examples:
  - open/listening ports
  - Windows Defender status
  - firewall status
  - weak/password hygiene reminders
"""

from __future__ import annotations

import socket
import subprocess

import tools_registry as reg


@reg.register(
    name="security_audit",
    description="Run a DEFENSIVE security audit of this Windows machine (firewall, Defender, listening ports). Approval required.",
    parameters=reg.NO_PARAMS,
    requires_approval=True,
)
def security_audit() -> str:
    findings: list[str] = []

    # Firewall status
    try:
        out = subprocess.run(
            ["netsh", "advfirewall", "show", "allprofiles", "state"],
            capture_output=True, text=True, timeout=15,
        ).stdout
        states = [ln.strip() for ln in out.splitlines() if "State" in ln or "Firewall" in ln]
        findings.append("Firewall:\n  " + "\n  ".join(states[:6]))
    except Exception as exc:  # noqa: BLE001
        findings.append(f"Firewall: check failed ({exc})")

    # Defender status
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-MpComputerStatus | Select-Object -Property RealTimeProtectionEnabled,AntivirusEnabled | Format-List"],
            capture_output=True, text=True, timeout=25,
        ).stdout
        findings.append("Defender:\n  " + out.strip().replace("\n", "\n  ")[:400])
    except Exception as exc:  # noqa: BLE001
        findings.append(f"Defender: check failed ({exc})")

    # Listening ports (local view only)
    try:
        out = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, timeout=15).stdout
        listening = [ln.strip() for ln in out.splitlines() if "LISTENING" in ln]
        findings.append(f"Listening TCP sockets: {len(listening)} (sample below)\n  " + "\n  ".join(listening[:10]))
    except Exception as exc:  # noqa: BLE001
        findings.append(f"Ports: check failed ({exc})")

    findings.append(
        "Recommendations: keep Windows Defender ON, firewall ON for all profiles, "
        "close unused listening ports, avoid reusing passwords, and enable 2FA."
    )
    return "\n\n".join(findings)


@reg.register(
    name="check_port",
    description="Check whether a local port is open on this machine (localhost only).",
    parameters={
        "type": "object",
        "properties": {"port": {"type": "integer", "description": "TCP port to check."}},
        "required": ["port"],
    },
)
def check_port(port: int) -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(1.0)
    try:
        result = s.connect_ex(("127.0.0.1", int(port)))
        return f"Port {port}: {'OPEN' if result == 0 else 'closed'}"
    finally:
        s.close()
