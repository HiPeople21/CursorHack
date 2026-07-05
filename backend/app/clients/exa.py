"""Exa neural search client with DEMO_MODE fixtures."""

import json
import os
from typing import Any

import httpx

from app.clients.config import fixtures_dir, is_demo_mode

_FIXTURE_PATH = os.path.join(fixtures_dir(), "exa_search_rtb.json")


def _use_mock() -> bool:
    return is_demo_mode() or not os.getenv("EXA_API_KEY")


def search(
    query: str,
    include_domains: list[str] | None = None,
    num_results: int = 5,
) -> list[dict[str, str]]:
    """Return top search results as {url, title} dicts."""
    if _use_mock():
        with open(_FIXTURE_PATH, encoding="utf-8") as f:
            data: dict[str, Any] = json.load(f)
        return data.get("results", [])[:num_results]

    payload: dict[str, Any] = {
        "query": query,
        "type": "neural",
        "numResults": num_results,
        "useAutoprompt": True,
    }
    if include_domains:
        payload["includeDomains"] = include_domains

    with httpx.Client(timeout=30.0) as client:
        resp = client.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": os.getenv("EXA_API_KEY", ""),
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    results: list[dict[str, str]] = []
    for item in data.get("results", []):
        results.append(
            {
                "url": item.get("url", ""),
                "title": item.get("title", item.get("url", "")),
            }
        )
    return results
