"""
Vision understanding: send a screenshot or webcam frame to the vision model
and get a natural-language description / analysis.

Confirmed: `deepseek-v4.1-flash-free` accepts image_url inputs.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from openai import OpenAI

from .config import settings


def _client() -> OpenAI:
    return OpenAI(base_url=settings.llm_base_url, api_key=settings.llm_api_key)


def _to_data_url(image_bytes: bytes, fmt: str = "png") -> str:
    b64 = base64.b64encode(image_bytes).decode()
    return f"data:image/{fmt};base64,{b64}"


def describe_image(image_bytes: bytes, prompt: str, fmt: str = "png", max_tokens: int = 300) -> str:
    client = _client()
    try:
        resp = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": _to_data_url(image_bytes, fmt)}},
                    ],
                }
            ],
            max_tokens=max_tokens,
            temperature=0.2,
        )
        return (resp.choices[0].message.content or "").strip()
    except Exception as exc:  # noqa: BLE001
        return f"vision error: {exc}"


def analyze_screenshot(prompt: str = "Describe what's on this screen. If there's code, note any obvious bugs or errors.") -> str:
    import mss
    from PIL import Image

    with mss.MSS() as sct:
        img = sct.grab(sct.monitors[1])
        pil = Image.frombytes("RGB", img.size, img.rgb)
    # Downscale to save tokens / bandwidth.
    pil.thumbnail((1280, 1280))
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return describe_image(buf.getvalue(), prompt)


def analyze_webcam(prompt: str = "Describe the person you see: their mood/expression, what they're wearing. Be brief and kind.") -> str:
    import cv2

    cap = cv2.VideoCapture(0)
    ok, frame = cap.read()
    cap.release()
    if not ok:
        return "webcam error: no frame"
    frame = cv2.resize(frame, (640, 480))
    ok, buf = cv2.imencode(".jpg", frame)
    if not ok:
        return "webcam error: encode failed"
    return describe_image(buf.tobytes(), prompt, fmt="jpeg")
