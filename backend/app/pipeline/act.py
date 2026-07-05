"""Stage 7: draft appeal letters, forms, and deadlines."""

from app.clients.qwen import chat_json
from app.pipeline.types import IdentifiedBody
from app.schemas import Action, ExtractedFact, Verification


def act(
    doc_type: str,
    facts: list[ExtractedFact],
    verifications: list[Verification],
    bodies: list[IdentifiedBody] | None = None,
) -> list[Action]:
    try:
        mismatch_summary = "\n".join(
            f"- {v.assertion} vs rule: {v.rule_value} ({v.verdict})"
            for v in verifications
            if v.verdict == "mismatch"
        )
        fact_summary = "\n".join(f"- {f.key}: {f.value}" for f in facts)
        sources_context = _sources_context(verifications)
        bodies_context = ", ".join(b.display_name for b in (bodies or [])) or "unknown"

        result = chat_json(
            system=(
                "Draft actionable next steps for the user. Return JSON: "
                '{"actions": [{"title": str, "kind": "letter|form|email|deadline|contact", '
                '"body": str, "deadline": str|null}]}. Informational only.\n'
                "GROUNDING RULES — you are writing something the user may send to an "
                "authority, so accuracy matters more than sounding authoritative:\n"
                "1. Cite a rule, statute/section number, Act name, form number, "
                "programme, or deadline ONLY if it appears verbatim in VERIFIED SOURCES "
                "or FACTS below. NEVER invent, guess, or recall one from memory.\n"
                "2. If you do not have the exact citation, refer to the rule generically "
                "(e.g. 'the applicable statutory notice period') — do NOT fabricate a "
                "number to fill the gap.\n"
                "3. Refer to the authority ONLY by the exact name in ISSUING AUTHORITY; "
                "do not substitute an older, abbreviated, or similar-sounding name.\n"
                "4. Quote the rule value only as given in VERIFIED SOURCES. When unsure, "
                "omit the specific rather than state a wrong one."
            ),
            user=(
                f"doc_type={doc_type}\n"
                f"ISSUING AUTHORITY (use this exact name): {bodies_context}\n\n"
                f"FACTS:\n{fact_summary}\n\n"
                f"MISMATCHES:\n{mismatch_summary or 'none'}\n\n"
                f"VERIFIED SOURCES (the only citations you may quote):\n{sources_context}"
            ),
            stage="act",
        )
        actions: list[Action] = []
        for item in result.get("actions", []):
            kind = item.get("kind", "letter")
            if kind not in ("letter", "form", "email", "deadline", "contact"):
                kind = "letter"
            actions.append(
                Action(
                    title=item.get("title", "Next step"),
                    kind=kind,
                    body=item.get("body", ""),
                    deadline=item.get("deadline"),
                )
            )
        if actions:
            return actions
    except Exception:
        pass

    return _fallback_actions(verifications)


def _sources_context(verifications: list[Verification]) -> str:
    """Render the verified source passages the letter is allowed to cite.

    Only ``Verification`` items with a real ``source`` become citable text, so the
    act stage can quote a genuine passage instead of recalling a statute number or
    body name from (often stale) model memory.
    """
    lines: list[str] = []
    seen: set[tuple[str, str]] = set()
    for v in verifications:
        src = v.source
        if src is None or not src.quote:
            continue
        key = (src.title, src.quote)
        if key in seen:
            continue
        seen.add(key)
        lines.append(f'- rule: "{v.rule_value}" | source: {src.title} — "{src.quote}" ({src.url})')
    return "\n".join(lines) or "none — do not cite any specific rule, statute, or section number"


def _fallback_actions(verifications: list[Verification]) -> list[Action]:
    mismatches = [v for v in verifications if v.verdict == "mismatch"]
    if not mismatches:
        return [
            Action(
                title="Review document with advisor",
                kind="contact",
                body="No clear statutory mismatches were identified. Consider seeking advice.",
                deadline=None,
            )
        ]
    return [
        Action(
            title="Appeal letter citing governing rule",
            kind="letter",
            body=(
                "I am writing to challenge the terms stated in the document I received. "
                f"Governing rules indicate: {mismatches[0].rule_value}. "
                "I request that you correct this matter in writing."
            ),
            deadline=None,
        )
    ]
