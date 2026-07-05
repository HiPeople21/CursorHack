"""Firecrawl scrape client — turns a URL into clean markdown.

DEMO_MODE=1 (or missing FIRECRAWL_API_KEY) returns canned page content from
`backend/fixtures/firecrawl/pages.json`, keyed by URL. Never raises: any
failure (live or fixture-miss) returns None so `ground.py` can skip that URL
rather than crash the pipeline.
"""

from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "firecrawl"


def _demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "1") == "1"


def _api_key() -> str:
    return os.getenv("FIRECRAWL_API_KEY", "").strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load_pages() -> dict[str, Any]:
    try:
        with open(FIXTURES_DIR / "pages.json", encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


def scrape(url: str, title_hint: str | None = None) -> dict[str, str] | None:
    """Scrape a single URL to markdown.

    Returns {"url", "title", "markdown", "retrieved_at"} or None if the page
    could not be fetched/found. Demo mode looks the URL up in the canned
    fixture map; a URL with no fixture entry returns None (never fabricated
    content).
    """
    if _demo_mode() or not _api_key():
        pages = _load_pages()
        page = pages.get(url)
        if not isinstance(page, dict) or not page.get("markdown"):
            return None
        return {
            "url": url,
            "title": page.get("title") or title_hint or url,
            "markdown": page["markdown"],
            "retrieved_at": _now_iso(),
        }

    try:
        resp = httpx.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={
                "Authorization": f"Bearer {_api_key()}",
                "Content-Type": "application/json",
            },
            json={"url": url, "formats": ["markdown"]},
            timeout=30,
        )
        resp.raise_for_status()
        body = resp.json()
        data = body.get("data", {}) if isinstance(body, dict) else {}
        markdown = data.get("markdown") if isinstance(data, dict) else None
        if not markdown:
            return None
        metadata = data.get("metadata", {}) if isinstance(data, dict) else {}
        title = (metadata.get("title") if isinstance(metadata, dict) else None) or title_hint or url
        return {
            "url": url,
            "title": title,
            "markdown": markdown,
            "retrieved_at": _now_iso(),
        }
    except Exception:
        logger.exception("Firecrawl scrape call failed (url=%r)", url)
        return None
