"""Stage 6: act(doc_type, facts, verifications, jurisdiction) -> Action[].

Drafts the appeal letter / pre-filled form text / response email citing the
exact rule that was verified, plus extracted deadlines.
"""

from __future__ import annotations

from app.schemas import Action, ExtractedFact, Verification

VALID_KINDS = {"letter", "form", "email", "deadline", "contact"}

SYSTEM_PROMPT = """You draft practical, concrete response actions for someone who received an
official/bureaucratic document (tenancy notice, insurance letter, medical bill, government
letter), based on facts extracted from that document and a set of verification results comparing
the document's assertions to the actual governing rule.

Where a verification has verdict "mismatch", the drafted letter/email MUST explicitly cite the
rule_value and explanation to assert the recipient's position — do not soften or omit a confirmed
mismatch. Where nothing could be verified, keep actions cautious and do not assert legal
conclusions that aren't backed by a verification.

Respond with JSON only, no prose, no markdown fences. Return exactly this shape:
{"actions": [{"title": "<short title>", "kind": "<letter|form|email|deadline|contact>", "body": "<drafted text or contact/deadline detail>", "deadline": "<ISO date string or null>"}]}

Include at least one action. If any deadline is implied by the facts (e.g. a vacate-by date), add
a "deadline" kind action stating it clearly.
"""


def act(
    doc_type: str,
    facts: list[ExtractedFact],
    verifications: list[Verification],
    jurisdiction: str,
) -> list[Action]:
    """Draft response actions (letter/form/email/deadline/contact).

    Never raises. Returns [] if the model call fails or returns nothing
    usable — a decode with no actions is still a valid, if less useful,
    DecodeResult.
    """
    from app.clients import qwen  # local import keeps module import graph light

    facts_block = (
        "\n".join(f"- {f.key}: {f.value}" for f in facts) if facts else "(no facts extracted)"
    )
    verif_block = (
        "\n".join(
            f"- assertion: {v.assertion!r} | rule_value: {v.rule_value!r} | "
            f"verdict: {v.verdict} | explanation: {v.explanation}"
            for v in verifications
        )
        if verifications
        else "(no verification results available)"
    )
    user_prompt = (
        f"Document type: {doc_type}\n"
        f"Jurisdiction: {jurisdiction}\n\n"
        f"Extracted facts:\n{facts_block}\n\n"
        f"Verification results (document assertion vs governing rule):\n{verif_block}"
    )

    data = qwen.chat_json(SYSTEM_PROMPT, user_prompt, mock_fixture="act.json")

    actions: list[Action] = []
    raw_actions = data.get("actions") if isinstance(data, dict) else None
    if not isinstance(raw_actions, list):
        return actions

    for item in raw_actions:
        if not isinstance(item, dict):
            continue
        title = item.get("title")
        body = item.get("body")
        if not isinstance(title, str) or not title.strip():
            continue
        if not isinstance(body, str) or not body.strip():
            continue

        kind = item.get("kind")
        if kind not in VALID_KINDS:
            kind = "letter"

        deadline = item.get("deadline")
        deadline = deadline.strip() if isinstance(deadline, str) and deadline.strip() else None

        actions.append(Action(title=title.strip(), kind=kind, body=body.strip(), deadline=deadline))

    return actions
