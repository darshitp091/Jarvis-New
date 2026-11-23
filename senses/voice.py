"""
Voice I/O: TTS (Edge TTS, Hinglish) + STT (faster-whisper tiny-int8) +
a simple push-to-talk / record-and-transcribe loop.

No API keys for TTS/STT; both run locally (TTS uses Microsoft's free endpoint).
"""

from __future__ import annotations

import asyncio
import tempfile
import time
from pathlib import Path

from core.config import settings

# --------------------------------------------------------------------------- #
# TTS
# --------------------------------------------------------------------------- #
def speak(text: str, voice: str | None = None, play: bool = True) -> Path:
    """Synthesize `text` to an mp3 and (optionally) play it. Returns the file path."""
    import edge_tts

    out = Path(tempfile.gettempdir()) / f"jarvis_tts_{int(time.time() * 1000)}.mp3"
    voice = voice or settings.tts_voice

    async def _run() -> None:
        await edge_tts.Communicate(text, voice=voice).save(str(out))

    asyncio.run(_run())
    if play:
        _play_file(out)
    return out


def _play_file(path: Path) -> None:
    """Play an audio file. Uses Windows' built-in player; fallback to soundfile+sd."""
    import os

    try:
        os.startfile(str(path))  # opens in default media player
        time.sleep(0.2)
    except Exception:  # noqa: BLE001
        try:
            import sounddevice as sd
            import soundfile as sf

            data, sr = sf.read(str(path), dtype="float32")
            sd.play(data, sr)
            sd.wait()
        except Exception:  # noqa: BLE001
            pass


# --------------------------------------------------------------------------- #
# STT
# --------------------------------------------------------------------------- #
_whisper = None


def _model():
    global _whisper
    if _whisper is None:
        from faster_whisper import WhisperModel

        _whisper = WhisperModel(settings.stt_model, device="cpu", compute_type=settings.stt_compute)
    return _whisper


def transcribe_file(path: str | Path) -> str:
    segments, _info = _model().transcribe(str(path), beam_size=1)
    return " ".join(s.text.strip() for s in segments).strip()


def record_audio(seconds: float = 5.0, sr: int = 16000) -> Path:
    """Record from the default mic for `seconds` and return a temp wav path."""
    import sounddevice as sd
    import soundfile as sf

    frames = sd.rec(int(seconds * sr), samplerate=sr, channels=1, dtype="float32")
    sd.wait()
    out = Path(tempfile.gettempdir()) / f"jarvis_rec_{int(time.time() * 1000)}.wav"
    sf.write(str(out), frames, sr)
    return out


def listen_once(seconds: float = 5.0) -> str:
    """Record a short clip and transcribe it."""
    print(f"  (listening {seconds:.0f}s...)")
    wav = record_audio(seconds)
    return transcribe_file(wav)


# --------------------------------------------------------------------------- #
# Streaming / sentence-chunked TTS with interrupt support
# --------------------------------------------------------------------------- #
class StreamingSpeaker:
    """
    Speak text in sentence-sized chunks so Jarvis starts talking before the full
    reply is generated, and can be interrupted (barge-in) via .stop().
    """

    def __init__(self) -> None:
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def reset(self) -> None:
        self._stop = False

    def speak_stream(self, token_iter) -> str:
        """
        Consume an iterator of text tokens; speak each completed sentence.
        Returns the full text. Stops early if .stop() is called.
        """
        buffer = ""
        full = ""
        sent_enders = ".!?\n"
        for tok in token_iter:
            if self._stop:
                break
            full += tok
            buffer += tok
            if any(buffer.rstrip().endswith(e) for e in sent_enders) and len(buffer.strip()) > 12:
                chunk = buffer.strip()
                buffer = ""
                if chunk:
                    try:
                        out = _synth_to_file(chunk)
                        _play_blocking(out)
                    except Exception:  # noqa: BLE001
                        pass
        if buffer.strip() and not self._stop:
            try:
                out = _synth_to_file(buffer.strip())
                _play_blocking(out)
            except Exception:  # noqa: BLE001
                pass
        return full


def _synth_to_file(text: str, voice: str | None = None) -> Path:
    import edge_tts

    out = Path(tempfile.gettempdir()) / f"jarvis_tts_{int(time.time() * 1000)}.mp3"
    voice = voice or settings.tts_voice

    async def _run() -> None:
        await edge_tts.Communicate(text, voice=voice).save(str(out))

    asyncio.run(_run())
    return out


def _play_blocking(path: Path) -> None:
    """Play an audio file and block until done (so chunks stay ordered)."""
    try:
        import sounddevice as sd
        import soundfile as sf

        data, sr = sf.read(str(path), dtype="float32")
        sd.play(data, sr)
        sd.wait()
        return
    except Exception:  # noqa: BLE001
        pass
    try:
        import os

        os.startfile(str(path))
        time.sleep(0.2)
    except Exception:  # noqa: BLE001
        pass
