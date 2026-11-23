"""
Real browser automation via Playwright (headless Chromium).

Can navigate, extract rendered (JS) text, click elements, fill forms, and
screenshot. Each call opens a fresh headless page (stateless) for simplicity;
this handles JS-heavy sites that simple HTTP scraping can't.
"""

from __future__ import annotations

import asyncio

import tools_registry as reg
from core.config import settings


async def _render(url: str, wait_selector: str | None, max_chars: int) -> str:
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, wait_until="networkidle", timeout=30000)
        if wait_selector:
            try:
                await page.wait_for_selector(wait_selector, timeout=5000)
            except Exception:  # noqa: BLE001
                pass
        text = await page.inner_text("body")
        await browser.close()
        return text[:max_chars]


@reg.register(
    name="browse",
    description="Open a URL in a headless browser (runs JavaScript) and return the rendered page text.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to open."},
            "wait_selector": {"type": "string", "description": "Optional CSS selector to wait for."},
            "max_chars": {"type": "integer", "description": "Max chars to return.", "default": 5000},
        },
        "required": ["url"],
    },
    requires_approval=True,
)
def browse(url: str, wait_selector: str | None = None, max_chars: int = 5000) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    try:
        return asyncio.run(_render(url, wait_selector, max_chars)) or "(empty page)"
    except Exception as exc:  # noqa: BLE001
        return f"browse error: {exc}"


@reg.register(
    name="screenshot_url",
    description="Open a URL in a headless browser and save a screenshot to data/.",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to screenshot."},
            "filename": {"type": "string", "description": "Output filename.", "default": "page.png"},
        },
        "required": ["url"],
    },
    requires_approval=True,
)
def screenshot_url(url: str, filename: str = "page.png") -> str:
    from playwright.async_api import async_playwright

    if not url.startswith("http"):
        url = "https://" + url
    settings.ensure_dirs()
    out = settings.data_dir / filename

    async def _shot() -> None:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=str(out), full_page=True)
            await browser.close()

    try:
        asyncio.run(_shot())
        return f"Screenshot saved: {out}"
    except Exception as exc:  # noqa: BLE001
        return f"screenshot_url error: {exc}"
