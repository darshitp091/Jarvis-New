"""
Always-listening Jarvis — the closest thing to "command-less".

    python assistant.py

Say "hey jarvis", then speak naturally. Jarvis records until you pause, thinks,
and replies aloud. No keyboard needed. Ctrl+C to stop.

Pipeline: wake-word ("hey jarvis") -> record-until-silence (VAD) -> Whisper STT
          -> agent loop -> Edge TTS speaks the answer.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np

import main as _abilities  # noqa: F401,E402  (register all tools)
import agent_loop  # noqa: E402
from core.config import settings  # noqa: E402
from senses.wakeword import WakeWordListener  # noqa: E402

SR = 16000
FRAME = 512  # ~32ms

SILENCE_RMS = 0.012       # below this counts as silence
SILENCE_SECS = 1.2        # stop after this much silence
MAX_SECS = 15.0           # hard cap
MIN_SECS = 0.5            # ignore tiny blips


def record_until_silence(max_secs: float = MAX_SECS, abort_after_quiet: bool = False) -> Path | None:
    """Record from mic until the user stops talking (simple RMS VAD)."""
    import sounddevice as sd
    import soundfile as sf

    frames: list[np.ndarray] = []
    silent_for = 0.0
    elapsed = 0.0
    started = False

    def _cb(indata, n, t, status):  # noqa: ANN001
        nonlocal silent_for, elapsed, started
        chunk = indata[:, 0].copy()
        frames.append(chunk)
        rms = float(np.sqrt(np.mean(chunk ** 2)) + 1e-9)
        dur = len(chunk) / SR
        elapsed += dur
        if rms > SILENCE_RMS:
            started = True
            silent_for = 0.0
        elif started:
            silent_for += dur

    stream = sd.InputStream(samplerate=SR, channels=1, dtype="float32", blocksize=FRAME, callback=_cb)
    stream.start()
    try:
        while True:
            time.sleep(0.05)
            if started and silent_for >= SILENCE_SECS:
                break
            if elapsed >= max_secs:
                break
            if abort_after_quiet and not started and elapsed >= 2.0:
                break
    finally:
        stream.stop()
        stream.close()

    if elapsed < MIN_SECS or not frames or not started:
        return None
    audio = np.concatenate(frames)
    out = Path(__file__).parent / "data" / f"utt_{int(time.time()*1000)}.wav"
    out.parent.mkdir(exist_ok=True)
    sf.write(str(out), audio, SR)
    return out


STOP_WORDS = {"stop", "bye", "quit", "goodbye", "band karo", "band", "ruko", "bas", "exit"}
IDLE_EXIT_SECS = 20.0


def handle_utterance(conv) -> bool:
    """
    Record, transcribe, think (with conversation history), speak. Returns False
    to end the conversation, True to keep listening.
    """
    from core.conversation import Conversation  # noqa: F401 (type hint only)
    from senses import voice

    wav = record_until_silence()
    if wav is None:
        return True
    text = voice.transcribe_file(wav)
    print(f"you> {text}")
    if not text.strip():
        return True
    if any(w == text.lower().strip().rstrip(".!?") for w in STOP_WORDS) or (
        len(text.split()) <= 3 and any(w in text.lower() for w in STOP_WORDS)
    ):
        try:
            voice.speak("Theek hai, ruk raha hoon.")
        except Exception:  # noqa: BLE001
            pass
        return False

    try:
        answer = agent_loop.run(text, history=conv.history())
    except Exception as exc:  # noqa: BLE001
        answer = f"Sorry, error: {exc}"
    print(f"jarvis> {answer}")
    conv.add_user(text)
    conv.add_assistant(answer)

    # Speak in sentence chunks for a more natural, responsive feel.
    try:
        speaker = voice.StreamingSpeaker()
        speaker.speak_stream(iter(answer))
    except Exception:  # noqa: BLE001
        try:
            voice.speak(answer)
        except Exception as exc:  # noqa: BLE001
            print(f"  (tts error: {exc})")
    return True


def conversation_loop(conv) -> None:
    """Stay in conversation after wake until stop word or idle timeout."""
    from senses import voice

    try:
        voice.speak("Haan, boliye.")
    except Exception:  # noqa: BLE001
        pass

    idle = 0.0
    while True:
        wav = record_until_silence()
        if wav is None:
            idle += 3.0
            if idle >= IDLE_EXIT_SECS:
                try:
                    voice.speak("Theek hai. Wake word bolo jab zaroorat ho.")
                except Exception:  # noqa: BLE001
                    pass
                return
            continue
        idle = 0.0
        keep_going = handle_utterance_from(wav, conv)
        if not keep_going:
            return


def handle_utterance_from(wav, conv) -> bool:
    """Like handle_utterance but takes an already-recorded wav."""
    from senses import voice

    text = voice.transcribe_file(wav)
    print(f"you> {text}")
    if not text.strip():
        return True
    if len(text.split()) <= 3 and any(w in text.lower() for w in STOP_WORDS):
        try:
            voice.speak("Theek hai, ruk raha hoon.")
        except Exception:  # noqa: BLE001
            pass
        return False
    try:
        answer = agent_loop.run(text, history=conv.history())
    except Exception as exc:  # noqa: BLE001
        answer = f"Sorry, error: {exc}"
    print(f"jarvis> {answer}")
    conv.add_user(text)
    conv.add_assistant(answer)
    try:
        voice.speak(answer)
    except Exception as exc:  # noqa: BLE001
        print(f"  (tts error: {exc})")
    return True


def main() -> int:
    from core.conversation import Conversation

    print("=" * 60)
    print(" Jarvis ALWAYS-LISTENING + continuous conversation")
    print(" Say 'hey jarvis' to start. Keep talking naturally; say 'stop' to end.")
    print(f" (stt={settings.stt_model}, voice={settings.tts_voice})")
    print("=" * 60)

    agent_loop.set_approval_hook(lambda name, a: False)  # deny sensitive in voice

    conv = Conversation(session_id=Conversation.new_session_id())

    def _on_wake() -> None:
        print("\n[wake] Yes?")
        conversation_loop(conv)
        conv.save()

    listener = WakeWordListener(on_wake=_on_wake, model_name="hey_jarvis", threshold=0.6)
    listener.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

