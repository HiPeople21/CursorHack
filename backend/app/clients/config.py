"""Shared client configuration."""

import os


def is_demo_mode() -> bool:
    return os.getenv("DEMO_MODE", "1") == "1"


def fixtures_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "..", "..", "fixtures")
