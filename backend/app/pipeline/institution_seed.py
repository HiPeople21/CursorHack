"""Bootstrap institution corpus from fixture JSON on first startup."""

import json
import logging
import os

from sqlalchemy.orm import Session

from app.models import Institution, InstitutionLegalLink
from app.pipeline.jurisdiction import compose_institution_id, normalize_jurisdiction

logger = logging.getLogger(__name__)


def seed_institutions_from_fixture(db: Session) -> None:
    """Load body_registry.json into institutions + legal_links if tables are empty."""
    migrate_legacy_institution_ids(db)

    if db.query(Institution).count() > 0:
        return

    fixtures_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "fixtures", "body_registry.json"
    )
    if not os.path.exists(fixtures_path):
        logger.warning("body_registry.json not found — skipping institution seed")
        return

    with open(fixtures_path, encoding="utf-8") as f:
        registry = json.load(f)

    for body_slug, entry in registry.items():
        jurisdiction = normalize_jurisdiction(entry["jurisdiction"])
        institution_id = compose_institution_id(body_slug, jurisdiction)
        institution = Institution(
            id=institution_id,
            display_name=entry["display_name"],
            jurisdiction=jurisdiction,
            domains=json.dumps(entry.get("domains", [])),
            doc_types=json.dumps(entry.get("doc_types", [])),
            search_queries=json.dumps(entry.get("search_queries", [])),
        )
        db.add(institution)

        for url in entry.get("seed_urls", []):
            db.add(
                InstitutionLegalLink(
                    institution_id=institution_id,
                    url=url,
                    title=entry["display_name"],
                    status="active",
                    discovered_via="seed",
                )
            )

    db.commit()
    logger.info("Seeded %d institutions from body_registry.json", len(registry))


def migrate_legacy_institution_ids(db: Session) -> None:
    """Upgrade pre-jurisdiction institution ids (rtb) to scoped ids (IE:rtb)."""
    legacy = [i for i in db.query(Institution).all() if ":" not in i.id]
    if not legacy:
        return

    for inst in legacy:
        new_id = compose_institution_id(inst.id, inst.jurisdiction)
        if db.get(Institution, new_id) is not None:
            continue

        replacement = Institution(
            id=new_id,
            display_name=inst.display_name,
            jurisdiction=normalize_jurisdiction(inst.jurisdiction),
            domains=inst.domains,
            doc_types=inst.doc_types,
            search_queries=inst.search_queries,
            created_at=inst.created_at,
            updated_at=inst.updated_at,
        )
        db.add(replacement)
        db.flush()

        for link in inst.legal_links:
            link.institution_id = new_id

        db.delete(inst)
        logger.info("Migrated institution %s -> %s", inst.id, new_id)

    db.commit()
