"""
Always-listening wake word ("hey jarvis") using openwakeword (ONNX backend).

Streams mic audio in ~80ms frames, runs the wake model, and fires when the score
crosses a threshold. RAM-friendly (~tens of MB).

    from senses.wakeword import WakeWordListener
    def on_wake():
        print("heard hey jarvis")
    WakeWordListener(on_wake).run_forever()
"""

from __future__ import annotations

import time
from typing import Callable

import numpy as np

from core.config import settings

SAMPLE_RATE = 16000
FRAME = 1280  # 80ms at 16k (openwakeword expects this chunk)


class WakeWordListener:
    def __init__(
        self,
        on_wake: Callable[[], None],
        model_name: str = "hey_jarvis",
        threshold: float = 0.6,
        cooldown: float = 2.0,
    ) -> None:
        self.on_wake = on_wake
        self.model_name = model_name
        self.threshold = threshold
        self.cooldown = cooldown
        self._last_fire = 0.0
        self._oww = None

    def _model(self):
        if self._oww is None:
            from openwakeword.model import Model

            names = [self.model_name] if self.model_name else None
            try:
                self._oww = Model(wakeword_models=names, inference_framework="onnx")
            except Exception:
                self._oww = Model(inference_framework="onnx")
        return self._oww

    def run_forever(self) -> None:
        import sounddevice as sd

        model = self._model()
        print(f"[wake] listening for '{self.model_name}' (threshold={self.threshold})... Ctrl+C to stop.")

        def _callback(indata, frames, time_info, status):  # noqa: ANN001
            audio = (indata[:, 0] * 32767).astype(np.int16)
            preds = model.predict(audio)
            score = float(preds.get(self.model_name, 0.0))
            now = time.time()
            if score >= self.threshold and (now - self._last_fire) > self.cooldown:
                self._last_fire = now
                print(f"[wake] '{self.model_name}' detected (score={score:.2f})")
                self.on_wake()

        with sd.InputStream(
            samplerate=SAMPLE_RATE, channels=1, dtype="float32", blocksize=FRAME, callback=_callback
        ):
            try:
                while True:
                    time.sleep(0.1)
            except KeyboardInterrupt:
                print("\n[wake] stopped.")
