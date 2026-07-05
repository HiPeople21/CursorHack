"""Shared helpers for the pipeline stages."""

import json
from pathlib import Path
from typing import Any

FIXTURES_DIR = Path(__file__).resolve().parent.parent.parent / "fixtures"


def load_fixture(key: str) -> Any:
    """Parse ``fixtures/{key}.json`` (the offline demo data)."""
    return json.loads((FIXTURES_DIR / f"{key}.json").read_text(encoding="utf-8"))
