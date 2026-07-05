"""Qwen (Alibaba Model Studio) chat-completions client.

Every pipeline stage that needs an LLM call goes through `chat_json`, which
returns *parsed* JSON (a dict) or `None` — callers must never be handed raw,
unstructured text. In DEMO_MODE=1 (or when QWEN_API_KEY is unset) this module
never touches the network: it returns canned fixtures from
`backend/fixtures/qwen/`, so the whole pipeline is runnable offline.

Contract for callers: always ask the model (via the system prompt) to return
a single JSON *object* (not a bare array) — some OpenAI-compatible servers
require `response_format={"type": "json_object"}` payloads to look like an
object, and it keeps every stage's fixture shape consistent and easy to
validate defensively.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures" / "qwen"

_client = None  # lazily constructed OpenAI client, only used on the live path


def _demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "1") == "1"


def _api_key() -> str:
    return os.getenv("QWEN_API_KEY", "").strip()


def _load_fixture(name: str) -> Any:
    path = FIXTURES_DIR / name
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _extract_json(raw: str | None) -> Any | None:
    """Best-effort, never-raise extraction of a JSON value from model output.

    Handles the common failure modes: markdown code fences, leading/trailing
    prose, or a bare JSON value embedded in a longer string. Returns None
    (never raises, never returns a str) if nothing parseable is found.
    """
    if not raw or not isinstance(raw, str):
        return None

    text = raw.strip()

    # Strip ```json ... ``` or ``` ... ``` fences if present.
    fence_match = re.match(r"^```[a-zA-Z]*\n?(.*)\n?```$", text, re.DOTALL)
    if fence_match:
        text = fence_match.group(1).strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Fall back to grabbing the first top-level {...} or [...] block.
    match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            return None

    return None


def _get_openai_client():
    global _client
    if _client is None:
        from openai import OpenAI  # imported lazily so demo mode never needs it installed

        _client = OpenAI(
            api_key=_api_key(),
            base_url=os.getenv(
                "QWEN_BASE_URL",
                "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
            ),
        )
    return _client


def chat_json(system: str, user: str, mock_fixture: str) -> Any | None:
    """Call Qwen expecting strict JSON-only output.

    Args:
        system: system prompt. Must instruct the model to output JSON only.
        user: user prompt containing the task-specific content.
        mock_fixture: filename under backend/fixtures/qwen/ to return when in
            demo mode or when QWEN_API_KEY is absent.

    Returns parsed JSON (typically a dict) on success, or None if the model
    key is missing content, the call fails, or the response can't be parsed.
    Never raises — every pipeline stage must handle a None return.
    """
    if _demo_mode() or not _api_key():
        try:
            return _load_fixture(mock_fixture)
        except (OSError, json.JSONDecodeError):
            return None

    model = os.getenv("QWEN_MODEL", "qwen-plus")
    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
    except Exception:
        # Network error, auth failure, rate limit, bad param, etc. Degrade
        # gracefully — the calling stage treats None as "nothing learned".
        logger.exception("Qwen chat_json call failed (model=%s)", model)
        return None

    return _extract_json(raw)
