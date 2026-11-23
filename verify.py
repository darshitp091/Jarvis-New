"""
Jarvis Phase 0 verifier.

Run this FIRST, before building anything else. It checks the risky parts of the
stack on THIS machine and prints a clear PASS/FAIL table.

    python verify.py

Tests:
  1. System info (RAM, python, OS)
  2. LLM provider reachability + /v1/models discovery + one chat completion
  3. Edge TTS  -> writes a Hinglish .mp3 to data/
  4. faster-whisper tiny int8 load + (optional) transcribe the TTS audio
  5. Screen capture + OCR (needs Tesseract installed)
  6. Webcam single-frame grab (skippable)

Each test is independent; a failure in one does not stop the others.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# Make "core.config" importable when run as a script from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.config import settings  # noqa: E402

PASS = "PASS"
FAIL = "FAIL"
SKIP = "SKIP"

results: list[tuple[str, str, str]] = []


def record(name: str, status: str, detail: str = "") -> None:
    results.append((name, status, detail))
    color = {PASS: "\033[92m", FAIL: "\033[91m", SKIP: "\033[93m"}.get(status, "")
    reset = "\033[0m"
    print(f"  [{color}{status}{reset}] {name}" + (f" -- {detail}" if detail else ""))



# --------------------------------------------------------------------------- #
# 1. System info
# --------------------------------------------------------------------------- #
def test_system() -> None:
    print("\n[1] System info")
    try:
        import platform

        try:
            import psutil

            vm = psutil.virtual_memory()
            total_gb = vm.total / (1024 ** 3)
            avail_gb = vm.available / (1024 ** 3)
            mem = f"RAM total={total_gb:.1f}GB avail={avail_gb:.1f}GB"
        except ImportError:
            mem = "psutil not installed (RAM unknown)"

        record(
            "system",
            PASS,
            f"{platform.system()} {platform.release()} | Python {platform.python_version()} | {mem}",
        )
    except Exception as exc:  # pragma: no cover
        record("system", FAIL, repr(exc))


# --------------------------------------------------------------------------- #
# 2. LLM provider
# --------------------------------------------------------------------------- #
def test_llm() -> None:
    print("\n[2] LLM provider (OpenAI-compatible)")
    if not settings.llm_api_key or settings.llm_api_key == "PASTE_YOUR_KEY_HERE":
        record("llm", SKIP, "no API key set in .env")
        return
    try:
        from openai import OpenAI

        client = OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)

        # --- discover models ---
        model_id = settings.llm_model
        try:
            models = client.models.list()
            ids = [m.id for m in models.data]
            record("llm /models", PASS, f"{len(ids)} models -> {ids[:8]}{'...' if len(ids) > 8 else ''}")
            if not model_id and ids:
                model_id = ids[0]
        except Exception as exc:
            record("llm /models", FAIL, repr(exc))

        if not model_id:
            record("llm chat", SKIP, "no model id available")
            return

        # --- one completion ---
        t0 = time.time()
        resp = client.chat.completions.create(
            model=model_id,
            messages=[
                {"role": "system", "content": "Reply with exactly: JARVIS_OK"},
                {"role": "user", "content": "ping"},
            ],
            max_tokens=16,
            temperature=0,
        )
        text = (resp.choices[0].message.content or "").strip()
        record("llm chat", PASS, f"model={model_id} | {time.time() - t0:.1f}s | reply={text!r}")
        settings.llm_model = model_id  # remember for later phases
    except Exception as exc:
        record("llm", FAIL, repr(exc))



# --------------------------------------------------------------------------- #
# 3. Edge TTS
# --------------------------------------------------------------------------- #
def test_tts() -> Path | None:
    print("\n[3] Edge TTS (Hinglish)")
    out = settings.data_dir / "verify_tts.mp3"
    try:
        import asyncio

        import edge_tts

        async def _synth() -> None:
            comm = edge_tts.Communicate(
                "Namaste, main Jarvis hoon. Aap kaise hain?",
                voice=settings.tts_voice,
            )
            await comm.save(str(out))

        settings.ensure_dirs()
        asyncio.run(_synth())
        size = out.stat().st_size
        if size < 1000:
            record("tts", FAIL, f"file too small ({size} bytes)")
            return None
        record("tts", PASS, f"voice={settings.tts_voice} -> {out} ({size} bytes)")
        return out
    except Exception as exc:
        record("tts", FAIL, repr(exc))
        return None


# --------------------------------------------------------------------------- #
# 4. faster-whisper STT
# --------------------------------------------------------------------------- #
def test_stt(audio_path: Path | None) -> None:
    print("\n[4] faster-whisper STT (local)")
    try:
        from faster_whisper import WhisperModel

        t0 = time.time()
        model = WhisperModel(settings.stt_model, device="cpu", compute_type=settings.stt_compute)
        record("stt load", PASS, f"model={settings.stt_model}/{settings.stt_compute} in {time.time() - t0:.1f}s")

        if audio_path and audio_path.exists():
            t0 = time.time()
            segments, info = model.transcribe(str(audio_path), beam_size=1)
            text = " ".join(s.text.strip() for s in segments).strip()
            record("stt transcribe", PASS, f"{time.time() - t0:.1f}s | lang={info.language} | {text!r}")
        else:
            record("stt transcribe", SKIP, "no audio file (TTS step failed)")
    except Exception as exc:
        record("stt", FAIL, repr(exc))


# --------------------------------------------------------------------------- #
# 5. Screen capture + OCR
# --------------------------------------------------------------------------- #
def test_screen() -> None:
    print("\n[5] Screen capture + OCR")
    try:
        import mss
        from PIL import Image

        settings.ensure_dirs()
        shot = settings.data_dir / "verify_screen.png"
        with mss.MSS() as sct:
            monitor = sct.monitors[1]
            img = sct.grab(monitor)
            Image.frombytes("RGB", img.size, img.rgb).save(shot)
        record("screen capture", PASS, f"{img.width}x{img.height} -> {shot}")

        try:
            import pytesseract

            text = pytesseract.image_to_string(Image.open(shot))[:200].strip()
            record("ocr", PASS, f"{len(text)} chars")
        except Exception as exc:
            record("ocr", FAIL, f"pytesseract/Tesseract missing? {exc!r}")
    except Exception as exc:
        record("screen capture", FAIL, repr(exc))


# --------------------------------------------------------------------------- #
# 6. Webcam
# --------------------------------------------------------------------------- #
def test_webcam() -> None:
    print("\n[6] Webcam single frame")
    try:
        import cv2

        cap = cv2.VideoCapture(0)
        ok, frame = cap.read()
        cap.release()
        if not ok or frame is None:
            record("webcam", FAIL, "could not read frame 0")
        else:
            settings.ensure_dirs()
            out = settings.data_dir / "verify_webcam.jpg"
            cv2.imwrite(str(out), frame)
            record("webcam", PASS, f"{frame.shape[1]}x{frame.shape[0]} -> {out}")
    except Exception as exc:
        record("webcam", SKIP, f"{exc!r}")




# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main() -> int:
    print("=" * 64)
    print(" Jarvis Phase 0 verifier")
    print("=" * 64)
    print("Settings:", settings.redacted())

    test_system()
    test_llm()
    audio = test_tts()
    test_stt(audio)
    test_screen()
    test_webcam()

    print("\n" + "=" * 64)
    print(" SUMMARY")
    print("=" * 64)
    passed = sum(1 for _, s, _ in results if s == PASS)
    failed = sum(1 for _, s, _ in results if s == FAIL)
    skipped = sum(1 for _, s, _ in results if s == SKIP)
    for name, status, detail in results:
        print(f"  {status:4} {name}")
    print(f"\n  {passed} passed, {failed} failed, {skipped} skipped")

    if failed:
        print("\n  >> Fix the FAIL items above before continuing.")
        return 1
    print("\n  >> All critical checks passed. Ready for the next build phase.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
