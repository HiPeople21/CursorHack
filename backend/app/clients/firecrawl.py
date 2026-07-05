"""Firecrawl scrape client with DEMO_MODE fixtures."""

import json
import os
from typing import Any

import httpx

from app.clients.config import fixtures_dir, is_demo_mode

_FIXTURE_PATH = os.path.join(fixtures_dir(), "firecrawl_scrape_rtb.json")


def _use_mock() -> bool:
    return is_demo_mode() or not os.getenv("FIRECRAWL_API_KEY")


def scrape(url: str) -> dict[str, str]:
    """Scrape a URL and return {url, title, markdown}."""
    if _use_mock():
        with open(_FIXTURE_PATH, encoding="utf-8") as f:
            data: dict[str, str] = json.load(f)
        return {**data, "url": url or data.get("url", "")}

    with httpx.Client(timeout=60.0) as client:
        resp = client.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={
                "Authorization": f"Bearer {os.getenv('FIRECRAWL_API_KEY', '')}",
                "Content-Type": "application/json",
            },
            json={"url": url, "formats": ["markdown"]},
        )
        resp.raise_for_status()
        data: dict[str, Any] = resp.json()

    page = data.get("data", data)
    metadata = page.get("metadata", {})
    return {
        "url": metadata.get("sourceURL", url),
        "title": metadata.get("title", url),
        "markdown": page.get("markdown", ""),
    }
