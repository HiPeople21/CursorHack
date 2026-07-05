"""Stage 7: draft appeal letters, forms, and deadlines."""

from app.clients.qwen import chat_json
from app.schemas import Action, ExtractedFact, Verification


def act(
    doc_type: str,
    facts: list[ExtractedFact],
    verifications: list[Verification],
) -> list[Action]:
    try:
        mismatch_summary = "\n".join(
            f"- {v.assertion} vs rule: {v.rule_value} ({v.verdict})"
            for v in verifications
            if v.verdict == "mismatch"
        )
        fact_summary = "\n".join(f"- {f.key}: {f.value}" for f in facts)

        result = chat_json(
            system=(
                "Draft actionable next steps for the user. Return JSON: "
                '{"actions": [{"title": str, "kind": "letter|form|email|deadline|contact", '
                '"body": str, "deadline": str|null}]}. '
                "Cite the exact governing rule in letter bodies. Informational only."
            ),
            user=(
                f"doc_type={doc_type}\nFACTS:\n{fact_summary}\n"
                f"MISMATCHES:\n{mismatch_summary or 'none'}"
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
