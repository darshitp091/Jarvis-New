"""
Browser + web abilities: open URLs, fetch+scrape text, and web search.
"""

from __future__ import annotations

import re
import webbrowser

import requests
from bs4 import BeautifulSoup

import tools_registry as reg

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/1.0"}


@reg.register(
    name="open_url",
    description="Open a URL in the default browser.",
    parameters={
        "type": "object",
        "properties": {"url": {"type": "string", "description": "URL to open."}},
        "required": ["url"],
    },
)
def open_url(url: str) -> str:
    if not re.match(r"^[a-zA-Z]+://", url):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opened {url}"


@reg.register(
    name="search_web",
    description="Open a web search in the default browser.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query."},
            "engine": {"type": "string", "description": "google|bing|duckduckgo", "default": "duckduckgo"},
        },
        "required": ["query"],
    },
)
def search_web(query: str, engine: str = "duckduckgo") -> str:
    from urllib.parse import quote_plus

    q = quote_plus(query)
    engines = {
        "google": f"https://www.google.com/search?q={q}",
        "bing": f"https://www.bing.com/search?q={q}",
        "duckduckgo": f"https://duckduckgo.com/?q={q}",
    }
    webbrowser.open(engines.get(engine, engines["duckduckgo"]))
    return f"Searched '{query}' on {engine}"


@reg.register(
    name="fetch_page",
    description="Fetch a web page and return its readable text (scraping).",
    parameters={
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "URL to fetch."},
            "max_chars": {"type": "integer", "description": "Max chars to return.", "default": 6000},
        },
        "required": ["url"],
    },
)
def fetch_page(url: str, max_chars: int = 6000) -> str:
    if not re.match(r"^[a-zA-Z]+://", url):
        url = "https://" + url
    try:
        resp = requests.get(url, headers=_UA, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        text = re.sub(r"\n\s*\n+", "\n", text).strip()
        title = soup.title.string.strip() if soup.title and soup.title.string else ""
        header = f"# {title}\n\n" if title else ""
        return header + text[:max_chars]
    except Exception as exc:  # noqa: BLE001
        return f"fetch_page error: {exc}"
