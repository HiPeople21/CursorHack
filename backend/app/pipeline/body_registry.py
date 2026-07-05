"""Curated institutional body registry — seed data only.

Runtime reads/writes go through institution_store.py (SQLite).
This module remains for bootstrap via institution_seed.py.
"""

import json
import os
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel


class BodyEntry(BaseModel):
    display_name: str
    jurisdiction: str
    domains: list[str]
    seed_urls: list[str]
    doc_types: list[str]
    search_queries: list[str]


@lru_cache(maxsize=1)
def _load_registry() -> dict[str, BodyEntry]:
    fixtures_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "fixtures", "body_registry.json"
    )
    with open(fixtures_path, encoding="utf-8") as f:
        raw = json.load(f)
    return {body_id: BodyEntry(**entry) for body_id, entry in raw.items()}


def get_body(body_id: str) -> Optional[BodyEntry]:
    return _load_registry().get(body_id)


def get_bodies_for_jurisdiction(jurisdiction: str) -> list[tuple[str, BodyEntry]]:
    """Return all registry entries for a jurisdiction."""
    results: list[tuple[str, BodyEntry]] = []
    for body_id, entry in _load_registry().items():
        if entry.jurisdiction == jurisdiction:
            results.append((body_id, entry))
    return results


def get_bodies_for_doc_type(doc_type: str, jurisdiction: str = "IE") -> list[tuple[str, BodyEntry]]:
    """Return registry entries whose doc_types include doc_type and jurisdiction matches."""
    results: list[tuple[str, BodyEntry]] = []
    for body_id, entry in _load_registry().items():
        if doc_type in entry.doc_types and entry.jurisdiction == jurisdiction:
            results.append((body_id, entry))
    return results


def resolve_body_id_for_url(url: str) -> Optional[str]:
    """Match a URL's domain to a registry body_id."""
    hostname = urlparse(url).hostname or ""
    hostname = hostname.removeprefix("www.")
    for body_id, entry in _load_registry().items():
        for domain in entry.domains:
            if hostname == domain or hostname.endswith("." + domain):
                return body_id
    return None


def collect_seed_urls(body_ids: list[str]) -> list[str]:
    """Deduplicated seed URLs for the given body_ids."""
    seen: set[str] = set()
    urls: list[str] = []
    for body_id in body_ids:
        entry = get_body(body_id)
        if entry is None:
            continue
        for url in entry.seed_urls:
            if url not in seen:
                seen.add(url)
                urls.append(url)
    return urls


def collect_domains(body_ids: list[str]) -> list[str]:
    """Deduplicated allowed domains for Exa domain filtering."""
    seen: set[str] = set()
    domains: list[str] = []
    for body_id in body_ids:
        entry = get_body(body_id)
        if entry is None:
            continue
        for domain in entry.domains:
            if domain not in seen:
                seen.add(domain)
                domains.append(domain)
    return domains


def collect_search_queries(body_ids: list[str]) -> list[str]:
    """Deduplicated search query templates for the given bodies."""
    seen: set[str] = set()
    queries: list[str] = []
    for body_id in body_ids:
        entry = get_body(body_id)
        if entry is None:
            continue
        for q in entry.search_queries:
            if q not in seen:
                seen.add(q)
                queries.append(q)
    return queries
