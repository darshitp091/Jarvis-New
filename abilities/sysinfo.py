"""System info abilities."""

from __future__ import annotations

import platform

import tools_registry as reg


@reg.register(
    name="system_info",
    description="Report basic system info: OS, CPU count, RAM, Python version.",
    parameters=reg.NO_PARAMS,
)
def system_info() -> str:
    bits = [platform.system(), platform.release(), platform.version()]
    try:
        import psutil

        vm = psutil.virtual_memory()
        bits.append(f"RAM {vm.total / 1024**3:.1f}GB (avail {vm.available / 1024**3:.1f}GB)")
        bits.append(f"CPU {psutil.cpu_count(logical=True)} cores")
    except Exception:  # noqa: BLE001
        pass
    bits.append(f"Python {platform.python_version()}")
    return " | ".join(bits)


@reg.register(
    name="system_monitor",
    description="Live CPU %, memory %, and disk % right now.",
    parameters=reg.NO_PARAMS,
)
def system_monitor() -> str:
    try:
        import psutil

        cpu = psutil.cpu_percent(interval=0.5)
        vm = psutil.virtual_memory()
        disk = psutil.disk_usage("C:\\" if platform.system() == "Windows" else "/").percent
        return f"CPU {cpu:.0f}% | RAM {vm.percent:.0f}% ({vm.available/1024**3:.1f}GB free) | Disk {disk:.0f}%"
    except Exception as exc:  # noqa: BLE001
        return f"system_monitor error: {exc}"

