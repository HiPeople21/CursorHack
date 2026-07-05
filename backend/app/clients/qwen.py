"""Qwen LLM client — OpenAI-compatible Chat Completions with DEMO_MODE fixtures."""

import json
import os
from typing import Any

from app.clients.config import fixtures_dir, is_demo_mode

_FIXTURE_PATH = os.path.join(fixtures_dir(), "qwen_rtb.json")


def _load_fixture() -> dict[str, Any]:
    with open(_FIXTURE_PATH, encoding="utf-8") as f:
        return json.load(f)


def _use_mock() -> bool:
    return is_demo_mode() or not os.getenv("QWEN_API_KEY")


def chat_json(system: str, user: str, stage: str) -> dict[str, Any]:
    """Return parsed JSON from Qwen, or fixture data in demo/mock mode."""
    if _use_mock():
        fixture = _load_fixture()
        if stage in fixture:
            return fixture[stage]
        return {}

    from openai import OpenAI

    client = OpenAI(
        api_key=os.getenv("QWEN_API_KEY"),
        base_url=os.getenv(
            "QWEN_BASE_URL",
            "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        ),
    )
    model = os.getenv("QWEN_MODEL", "qwen-plus")
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        response_format={"type": "json_object"},
    )
    content = response.choices[0].message.content or "{}"
    return json.loads(content)
