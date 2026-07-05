"""RAG retriever interface — keyword overlap now, embeddings later."""

from app.pipeline.types import Passage


def retrieve_passages(
    query: str,
    body_ids: list[str] | None,
    passages: list[Passage],
    top_k: int = 8,
) -> list[Passage]:
    """Rank passages by relevance to query. No-op vector path uses keyword overlap."""
    if not passages:
        return []

    if body_ids:
        filtered = [p for p in passages if p.body_id in body_ids]
        if filtered:
            passages = filtered

    query_terms = {t.lower() for t in query.split() if len(t) > 2}

    def score(passage: Passage) -> int:
        text = passage.text.lower()
        return sum(1 for term in query_terms if term in text)

    ranked = sorted(passages, key=score, reverse=True)
    return ranked[:top_k] if any(score(p) > 0 for p in ranked) else passages[:top_k]
