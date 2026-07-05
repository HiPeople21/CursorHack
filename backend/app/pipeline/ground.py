"""Stage 5: scrape URLs and chunk into Passage objects."""

import json
import os
import re
import uuid
from datetime import datetime, timezone

from app.clients.config import fixtures_dir, is_demo_mode
from app.clients.firecrawl import scrape
from app.pipeline.institution_store import report_link_failure, resolve_body_id_for_url
from app.pipeline.types import IdentifiedBody, Passage

_HEADING_RE = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
_MAX_CHUNK_CHARS = 3200
_OVERLAP_CHARS = 200


def ground(
    urls: list[str],
    bodies: list[IdentifiedBody] | None = None,
    jurisdiction: str = "IE",
) -> list[Passage]:
    """Scrape each URL and return chunked passages."""
    if is_demo_mode() and not urls:
        return _load_fixture_passages()

    if is_demo_mode():
        fixture = _load_fixture_passages()
        if fixture:
            return fixture

    passages: list[Passage] = []
    retrieved_at = datetime.now(timezone.utc).isoformat()

    for url in urls:
        try:
            page = scrape(url)
            body_id = _resolve_body_id(url, bodies, jurisdiction)
            chunks = chunk_markdown(
                markdown=page.get("markdown", ""),
                url=page.get("url", url),
                title=page.get("title", url),
                retrieved_at=retrieved_at,
                body_id=body_id,
            )
            passages.extend(chunks)
        except Exception:
            replacement_urls = report_link_failure(url)
            for replacement_url in replacement_urls:
                if replacement_url == url:
                    continue
                try:
                    page = scrape(replacement_url)
                    body_id = _resolve_body_id(replacement_url, bodies, jurisdiction)
                    chunks = chunk_markdown(
                        markdown=page.get("markdown", ""),
                        url=page.get("url", replacement_url),
                        title=page.get("title", replacement_url),
                        retrieved_at=retrieved_at,
                        body_id=body_id,
                    )
                    passages.extend(chunks)
                except Exception:
                    continue
            continue

    if not passages and is_demo_mode():
        return _load_fixture_passages()

    return passages


def chunk_markdown(
    markdown: str,
    url: str,
    title: str,
    retrieved_at: str,
    body_id: str | None = None,
) -> list[Passage]:
    """Split markdown on headings, then window into ~800-token chunks."""
    if not markdown.strip():
        return []

    sections = _split_on_headings(markdown)
    passages: list[Passage] = []
    chunk_index = 0

    for heading, body in sections:
        windows = _window_text(body)
        for window in windows:
            passages.append(
                Passage(
                    passage_id=str(uuid.uuid4()),
                    body_id=body_id,
                    url=url,
                    title=title,
                    section_heading=heading,
                    text=window,
                    retrieved_at=retrieved_at,
                    chunk_index=chunk_index,
                )
            )
            chunk_index += 1

    return passages


def _split_on_headings(markdown: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    current_heading: str | None = None
    current_lines: list[str] = []

    for line in markdown.splitlines():
        match = _HEADING_RE.match(line)
        if match:
            if current_lines:
                sections.append((current_heading, "\n".join(current_lines).strip()))
                current_lines = []
            current_heading = match.group(2).strip()
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_heading, "\n".join(current_lines).strip()))

    if not sections:
        return [(None, markdown.strip())]

    return sections


def _window_text(text: str) -> list[str]:
    if len(text) <= _MAX_CHUNK_CHARS:
        return [text] if text.strip() else []

    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + _MAX_CHUNK_CHARS, len(text))
        windows.append(text[start:end].strip())
        if end >= len(text):
            break
        start = end - _OVERLAP_CHARS
    return [w for w in windows if w]


def _resolve_body_id(
    url: str,
    bodies: list[IdentifiedBody] | None,
    jurisdiction: str,
) -> str | None:
    from_registry = resolve_body_id_for_url(url, jurisdiction)
    if from_registry:
        return from_registry
    if bodies:
        from app.pipeline.jurisdiction import compose_institution_id

        body = bodies[0]
        place = body.jurisdiction or jurisdiction
        return compose_institution_id(body.body_id, place)
    return None


def _load_fixture_passages() -> list[Passage]:
    path = os.path.join(fixtures_dir(), "passages_rtb.json")
    try:
        with open(path, encoding="utf-8") as f:
            raw = json.load(f)
        return [Passage(**item) for item in raw]
    except Exception:
        return []
