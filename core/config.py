"""
Central configuration for Jarvis.

Reads values from environment / .env. Everything else in the app imports
`settings` from here so there is a single source of truth.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # dotenv not installed yet (Phase 0 partial install)
    def load_dotenv(*_a, **_k):  # noqa: D401 - tiny fallback
        return False


# Load .env from the project root (the folder this file lives in).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default


@dataclass
class Settings:
    # --- Identity ---
    user_name: str = os.getenv("JARVIS_USER_NAME", "Darshit")

    # --- LLM provider ---
    llm_base_url: str = os.getenv("JARVIS_LLM_BASE_URL", "https://100milionseek.top/v1")
    llm_api_key: str = os.getenv("JARVIS_LLM_API_KEY", "")
    llm_model: str = os.getenv("JARVIS_LLM_MODEL", "deepseek-v4.1-flash-free").strip()

    # --- Voice ---
    tts_voice: str = os.getenv("JARVIS_TTS_VOICE", "hi-IN-MadhurNeural")
    stt_model: str = os.getenv("JARVIS_STT_MODEL", "tiny")
    stt_compute: str = os.getenv("JARVIS_STT_COMPUTE", "int8")

    # --- Wake word ---
    wake_word: str = os.getenv("JARVIS_WAKE_WORD", "hey jarvis")

    # --- Feature flags ---
    enable_camera: bool = field(default_factory=lambda: _get_bool("JARVIS_ENABLE_CAMERA", False))
    enable_screen_watch: bool = field(default_factory=lambda: _get_bool("JARVIS_ENABLE_SCREEN_WATCH", False))
    enable_spotify_ui: bool = field(default_factory=lambda: _get_bool("JARVIS_ENABLE_SPOTIFY_UI", True))
    enable_ethical_security: bool = field(default_factory=lambda: _get_bool("JARVIS_ENABLE_ETHICAL_SECURITY", True))

    # --- Safety ---
    auto_approve: bool = field(default_factory=lambda: _get_bool("JARVIS_AUTO_APPROVE", False))

    # --- Paths ---
    project_root: Path = _PROJECT_ROOT
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("JARVIS_DATA_DIR", str(_PROJECT_ROOT / "data")))
    )
    # Obsidian vault folder (markdown memory). Open this folder in Obsidian.
    vault_dir: Path = field(
        default_factory=lambda: Path(os.getenv("JARVIS_VAULT_DIR", str(_PROJECT_ROOT / "vault")))
    )

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        (self.vault_dir / "Memory").mkdir(parents=True, exist_ok=True)
        (self.vault_dir / "Journal").mkdir(parents=True, exist_ok=True)

    def redacted(self) -> dict:
        """Safe-to-print view of the settings (hides the API key)."""
        key = self.llm_api_key or ""
        shown = (key[:4] + "..." + key[-4:]) if len(key) > 8 else ("<empty>" if not key else "***")
        return {
            "llm_base_url": self.llm_base_url,
            "llm_model": self.llm_model or "<auto>",
            "llm_api_key": shown,
            "tts_voice": self.tts_voice,
            "stt_model": self.stt_model,
            "stt_compute": self.stt_compute,
            "wake_word": self.wake_word,
            "enable_camera": self.enable_camera,
            "enable_screen_watch": self.enable_screen_watch,
            "enable_spotify_ui": self.enable_spotify_ui,
            "enable_ethical_security": self.enable_ethical_security,
            "auto_approve": self.auto_approve,
            "data_dir": str(self.data_dir),
            "vault_dir": str(self.vault_dir),
        }


settings = Settings()
