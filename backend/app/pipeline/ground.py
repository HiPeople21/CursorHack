"""Stage 4: ground(urls) -> passages[].

Firecrawls each candidate URL to clean markdown, chunks it, and keeps
url/title/retrieved_at alongside each chunk of text so verify() can pin a
citation to an exact passage.
"""

from __future__ import annotations

from app.clients import firecrawl

_MAX_CHUNK_CHARS = 900
_MAX_CHUNKS_PER_URL = 40
_MAX_TOTAL_CHUNKS = 150


def _chunk_markdown(markdown: str, max_chars: int = _MAX_CHUNK_CHARS) -> list[str]:
    """Split markdown into paragraph-aligned chunks of roughly max_chars.

    Keeps paragraphs intact where possible (so a verbatim quote is unlikely
    to be split across chunk boundaries); only splits a single overlong
    paragraph as a last resort.
    """
    paragraphs = [p.strip() for p in markdown.split("\n\n") if p.strip()]
    chunks: list[str] = []
    buf = ""

    for para in paragraphs:
        if len(para) > max_chars:
            if buf:
                chunks.append(buf)
                buf = ""
            for i in range(0, len(para), max_chars):
                chunks.append(para[i : i + max_chars])
            continue

        candidate = f"{buf}\n\n{para}" if buf else para
        if len(candidate) <= max_chars:
            buf = candidate
        else:
            if buf:
                chunks.append(buf)
            buf = para

    if buf:
        chunks.append(buf)

    return chunks


def ground(urls: list[dict[str, str]]) -> list[dict[str, str]]:
    """Scrape each candidate URL and split it into citable passages.

    Returns a list of passage dicts: {"url", "title", "retrieved_at", "content"}.
    Never raises — a URL that fails to scrape is skipped, not fatal. Caps
    chunks per URL and overall: a single scraped page (e.g. a full statute
    PDF) can otherwise produce thousands of chunks, which blows the verify
    stage's LLM call past its context window and silently kills all
    claims/verifications for the whole request.
    """
    passages: list[dict[str, str]] = []

    for item in urls:
        if len(passages) >= _MAX_TOTAL_CHUNKS:
            break
        if not isinstance(item, dict):
            continue
        url = item.get("url")
        if not url:
            continue

        scraped = firecrawl.scrape(url, title_hint=item.get("title"))
        if not scraped:
            continue

        chunks = _chunk_markdown(scraped["markdown"])[:_MAX_CHUNKS_PER_URL]
        remaining = _MAX_TOTAL_CHUNKS - len(passages)
        for chunk in chunks[:remaining]:
            passages.append(
                {
                    "url": scraped["url"],
                    "title": scraped["title"],
                    "retrieved_at": scraped["retrieved_at"],
                    "content": chunk,
                }
            )

    return passages
