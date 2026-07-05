"""SQLAlchemy ORM tables.

documents(id, created_at, raw_text, doc_type, jurisdiction, plain_summary)
is the parent row for one decode. sources/claims/verifications/actions are
child tables, each carrying a document_id FK per CLAUDE.md.

Design note (judgment call — see report back to orchestrator): the pydantic
`Claim` and `Verification` models each optionally embed a full `Source`
object, but CLAUDE.md's SQLite section only lists a flat `sources` child
table alongside `claims`/`verifications`/`actions` (no explicit join spelled
out). To store that nesting without inventing a different shape, the
`sources` table holds the Source fields + a `document_id` FK (as specified),
and `claims`/`verifications` additionally carry a nullable `source_id` FK
pointing at the specific `sources` row backing that claim/verification. This
preserves "each child table has a document_id FK" while still letting a
claim/verification link to its one optional Source.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[str] = mapped_column(String, default=_now_iso)
    raw_text: Mapped[str] = mapped_column(Text)
    doc_type: Mapped[str] = mapped_column(String)
    jurisdiction: Mapped[str] = mapped_column(String)
    plain_summary: Mapped[str] = mapped_column(Text)
    disclaimer: Mapped[str] = mapped_column(Text, default="")

    sources: Mapped[list["SourceRow"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    extracted_facts: Mapped[list["ExtractedFactRow"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )
    claims: Mapped[list["ClaimRow"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="ClaimRow.document_id",
    )
    verifications: Mapped[list["VerificationRow"]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        foreign_keys="VerificationRow.document_id",
    )
    actions: Mapped[list["ActionRow"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )


class SourceRow(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    quote: Mapped[str] = mapped_column(Text)
    retrieved_at: Mapped[str] = mapped_column(String)

    document: Mapped["Document"] = relationship(back_populates="sources")


class ExtractedFactRow(Base):
    __tablename__ = "extracted_facts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    key: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    span: Mapped[str | None] = mapped_column(Text, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="extracted_facts")


class ClaimRow(Base):
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    statement: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )

    document: Mapped["Document"] = relationship(
        back_populates="claims", foreign_keys=[document_id]
    )
    source: Mapped["SourceRow | None"] = relationship(foreign_keys=[source_id])


class VerificationRow(Base):
    __tablename__ = "verifications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    assertion: Mapped[str] = mapped_column(Text)
    rule_value: Mapped[str] = mapped_column(Text)
    verdict: Mapped[str] = mapped_column(String)
    explanation: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str | None] = mapped_column(
        ForeignKey("sources.id"), nullable=True
    )

    document: Mapped["Document"] = relationship(
        back_populates="verifications", foreign_keys=[document_id]
    )
    source: Mapped["SourceRow | None"] = relationship(foreign_keys=[source_id])


class ActionRow(Base):
    __tablename__ = "actions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"))
    title: Mapped[str] = mapped_column(String)
    kind: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(Text)
    deadline: Mapped[str | None] = mapped_column(String, nullable=True)

    document: Mapped["Document"] = relationship(back_populates="actions")
