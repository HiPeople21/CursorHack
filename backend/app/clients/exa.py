"""Exa neural search client — finds candidate governing-rule pages.

DEMO_MODE=1 (or missing EXA_API_KEY) returns a canned fixture instead of
hitting the network. Never raises: any failure on the live path degrades to
an empty result list so `retrieve.py` (and the rest of the pipeline) can
carry on with nothing to ground against.
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "exa"


def _demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "1") == "1"


def _api_key() -> str:
    return os.getenv("EXA_API_KEY", "").strip()


def _load_fixture(name: str) -> list[dict[str, Any]]:
    try:
        with open(FIXTURES_DIR / name, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []
    results = data.get("results") if isinstance(data, dict) else None
    if not isinstance(results, list):
        return []
    return [r for r in results if isinstance(r, dict) and r.get("url")]


def search(
    query: str,
    num_results: int = 5,
    mock_fixture: str = "retrieve.json",
) -> list[dict[str, str]]:
    """Neural search for governing-rule pages.

    Returns a list of {"url": str, "title": str} dicts, most relevant first.
    Demo mode / missing key -> canned fixture. Live-call failures -> [].
    """
    if _demo_mode() or not _api_key():
        return _load_fixture(mock_fixture)[:num_results]

    try:
        resp = httpx.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": _api_key(),
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "type": "neural",
                "numResults": num_results,
            },
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("results", []) if isinstance(data, dict) else []
        out: list[dict[str, str]] = []
        for r in results:
            if not isinstance(r, dict):
                continue
            url = r.get("url")
            if not url:
                continue
            out.append({"url": url, "title": r.get("title") or url})
        return out[:num_results]
    except Exception:
        logger.exception("Exa search call failed (query=%r)", query)
        return []
