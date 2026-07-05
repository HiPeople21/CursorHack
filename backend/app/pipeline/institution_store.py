import json
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.clients.config import is_demo_mode
from app.clients.exa import search
from app.db import SessionLocal
from app.models import Institution, InstitutionLegalLink
from app.pipeline.jurisdiction import (
    body_slug,
    compose_institution_id,
    jurisdiction_label,
    normalize_jurisdiction,
)
from app.pipeline.link_validator import is_url_reachable
from app.pipeline.types import IdentifiedBody
from app.schemas import ExtractedFact

logger = logging.getLogger(__name__)

_LINK_STATUS_ACTIVE = "active"
_LINK_STATUS_BROKEN = "broken"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _body_jurisdiction(body: IdentifiedBody, fallback: str) -> str:
    return normalize_jurisdiction(body.jurisdiction or fallback)


def _parse_json_list(raw: str) -> list[str]:
    try:
        value = json.loads(raw)
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, TypeError):
        return []


def _domains_for_institution(institution: Institution) -> list[str]:
    return _parse_json_list(institution.domains)


def _queries_for_institution(institution: Institution) -> list[str]:
    return _parse_json_list(institution.search_queries)


def _doc_types_for_institution(institution: Institution) -> list[str]:
    return _parse_json_list(institution.doc_types)


def get_links_for_institutions(
    bodies: list[IdentifiedBody],
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[str]:
    """Return working legal-document URLs, discovering or refreshing as needed."""
    db = SessionLocal()
    try:
        institutions = _resolve_institutions(db, bodies, doc_type, jurisdiction)
        if not institutions:
            return []

        urls: list[str] = []
        seen: set[str] = set()

        for institution in institutions:
            institution_urls = _get_or_refresh_links(
                db, institution, doc_type, facts, jurisdiction
            )
            for url in institution_urls:
                if url not in seen:
                    seen.add(url)
                    urls.append(url)

        return urls
    finally:
        db.close()


def report_link_failure(url: str) -> list[str]:
    """Mark a URL broken after scrape failure and search for replacements."""
    db = SessionLocal()
    try:
        link = (
            db.query(InstitutionLegalLink)
            .filter(InstitutionLegalLink.url == url)
            .first()
        )
        if link is None:
            return []

        institution = db.get(Institution, link.institution_id)
        if institution is None:
            return []

        _mark_link_broken(db, link)
        doc_types = _doc_types_for_institution(institution)
        return _discover_and_persist_links(
            db,
            institution,
            doc_type=doc_types[0] if doc_types else "other",
            facts=[],
            jurisdiction=institution.jurisdiction,
            reason="scrape_failure",
        )
    finally:
        db.close()


def resolve_body_id_for_url(url: str, jurisdiction: str = "IE") -> str | None:
    """Match a URL's domain to a persisted institution id within a jurisdiction."""
    db = SessionLocal()
    try:
        place = normalize_jurisdiction(jurisdiction)
        hostname = (urlparse(url).hostname or "").removeprefix("www.")
        if not hostname:
            return None

        for institution in db.query(Institution).filter(
            Institution.jurisdiction == place
        ):
            for domain in _domains_for_institution(institution):
                if hostname == domain or hostname.endswith("." + domain):
                    return institution.id
        return None
    finally:
        db.close()


def get_institutions_for_doc_type(
    doc_type: str, jurisdiction: str = "IE"
) -> list[Institution]:
    db = SessionLocal()
    try:
        place = normalize_jurisdiction(jurisdiction)
        results: list[Institution] = []
        for institution in db.query(Institution).filter(
            Institution.jurisdiction == place
        ):
            if doc_type in _doc_types_for_institution(institution):
                results.append(institution)
        return results
    finally:
        db.close()


def _resolve_institutions(
    db: Session,
    bodies: list[IdentifiedBody],
    doc_type: str,
    jurisdiction: str,
) -> list[Institution]:
    if bodies:
        institutions: list[Institution] = []
        for body in bodies:
            inst = _ensure_institution(db, body, doc_type, jurisdiction)
            institutions.append(inst)
        return institutions

    results: list[Institution] = []
    place = normalize_jurisdiction(jurisdiction)
    for institution in db.query(Institution).filter(
        Institution.jurisdiction == place
    ):
        if doc_type in _doc_types_for_institution(institution):
            results.append(institution)
    return results


def _ensure_institution(
    db: Session,
    body: IdentifiedBody,
    doc_type: str,
    jurisdiction: str,
) -> Institution:
    place = _body_jurisdiction(body, jurisdiction)
    slug = body_slug(body.body_id) if body.body_id else _slugify(body.display_name)
    institution_id = compose_institution_id(slug, place)
    institution = db.get(Institution, institution_id)

    if institution is None:
        place_name = jurisdiction_label(place)
        institution = Institution(
            id=institution_id,
            display_name=body.display_name,
            jurisdiction=place,
            domains=json.dumps([]),
            doc_types=json.dumps([doc_type]),
            search_queries=json.dumps(
                [f"{body.display_name} legal regulations {place_name}"]
            ),
        )
        db.add(institution)
        db.commit()
        db.refresh(institution)
        logger.info("Registered new institution: %s (%s)", institution_id, place)
        return institution

    if institution.jurisdiction != place:
        raise ValueError(
            f"Institution {institution_id} jurisdiction mismatch: "
            f"expected {place}, found {institution.jurisdiction}"
        )

    doc_types = set(_doc_types_for_institution(institution))
    if doc_type not in doc_types:
        doc_types.add(doc_type)
        institution.doc_types = json.dumps(sorted(doc_types))
        institution.updated_at = _now_iso()
        db.commit()
        db.refresh(institution)

    return institution


def _slugify(name: str) -> str:
    import re

    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug[:64] or "unknown_body"


def _get_or_refresh_links(
    db: Session,
    institution: Institution,
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[str]:
    links = (
        db.query(InstitutionLegalLink)
        .filter(
            InstitutionLegalLink.institution_id == institution.id,
            InstitutionLegalLink.status == _LINK_STATUS_ACTIVE,
        )
        .all()
    )

    if not links:
        return _discover_and_persist_links(
            db, institution, doc_type, facts, jurisdiction, reason="new_institution"
        )

    working: list[str] = []
    needs_refresh = False

    for link in links:
        if _validate_link(db, link):
            working.append(link.url)
        else:
            _mark_link_broken(db, link)
            needs_refresh = True

    db.commit()

    if needs_refresh or not working:
        replacements = _discover_and_persist_links(
            db,
            institution,
            doc_type,
            facts,
            jurisdiction,
            reason="broken_link",
        )
        for url in replacements:
            if url not in working:
                working.append(url)

    if not working:
        return _discover_and_persist_links(
            db, institution, doc_type, facts, jurisdiction, reason="no_working_links"
        )

    return working


def _validate_link(db: Session, link: InstitutionLegalLink) -> bool:
    link.last_checked_at = _now_iso()
    if is_url_reachable(link.url):
        link.last_working_at = _now_iso()
        return True
    return False


def _mark_link_broken(db: Session, link: InstitutionLegalLink) -> None:
    link.status = _LINK_STATUS_BROKEN
    link.last_checked_at = _now_iso()
    db.commit()
    logger.warning("Marked broken legal link: %s (institution=%s)", link.url, link.institution_id)


def _discover_and_persist_links(
    db: Session,
    institution: Institution,
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
    reason: str,
) -> list[str]:
    """Search Exa for governing legal pages and persist new URLs."""
    if is_demo_mode():
        return _persist_demo_links(db, institution)

    queries = _build_discovery_queries(institution, doc_type, facts, jurisdiction)
    domains = _domains_for_institution(institution)
    seen = {link.url for link in institution.legal_links}
    discovered: list[str] = []

    for query in queries[:3]:
        try:
            results = search(query, include_domains=domains or None, num_results=5)
        except Exception:
            logger.exception("Exa search failed for institution %s", institution.id)
            continue

        for item in results:
            url = item.get("url", "").strip()
            title = item.get("title", url)
            if not url or url in seen:
                continue

            link = InstitutionLegalLink(
                institution_id=institution.id,
                url=url,
                title=title,
                status=_LINK_STATUS_ACTIVE,
                discovered_via="exa",
                last_checked_at=_now_iso(),
                last_working_at=_now_iso(),
            )
            db.add(link)
            seen.add(url)
            discovered.append(url)

            new_domain = urlparse(url).hostname
            if new_domain:
                _maybe_add_domain(db, institution, new_domain)

    if discovered:
        institution.updated_at = _now_iso()
        db.commit()
        logger.info(
            "Discovered %d legal links for %s (reason=%s)",
            len(discovered),
            institution.id,
            reason,
        )
        return discovered

    db.commit()
    return [link.url for link in institution.legal_links if link.status == _LINK_STATUS_ACTIVE]


def _persist_demo_links(db: Session, institution: Institution) -> list[str]:
    """In demo mode, ensure fixture seed URLs exist without network validation."""
    active = [
        link.url
        for link in institution.legal_links
        if link.status == _LINK_STATUS_ACTIVE
    ]
    if active:
        return active

    seed_url = (
        "https://www.citizensinformation.ie/en/housing/renting-a-home/"
        "tenants-and-landlords/ending-a-tenancy/"
    )
    if institution.jurisdiction == "IE" and (
        institution.id.endswith(":rtb")
        or "tenancy" in _doc_types_for_institution(institution)
    ):
        url = seed_url
    elif institution.jurisdiction == "GB" and institution.id.endswith(":tds"):
        url = "https://www.gov.uk/tenancy-deposit-protection"
    else:
        return []

    if url not in {link.url for link in institution.legal_links}:
        db.add(
            InstitutionLegalLink(
                institution_id=institution.id,
                url=url,
                title=institution.display_name,
                status=_LINK_STATUS_ACTIVE,
                discovered_via="seed",
                last_checked_at=_now_iso(),
                last_working_at=_now_iso(),
            )
        )
        db.commit()

    return [url]


def _maybe_add_domain(db: Session, institution: Institution, hostname: str) -> None:
    hostname = hostname.removeprefix("www.")
    domains = set(_domains_for_institution(institution))
    if hostname not in domains:
        domains.add(hostname)
        institution.domains = json.dumps(sorted(domains))
        institution.updated_at = _now_iso()


def _build_discovery_queries(
    institution: Institution,
    doc_type: str,
    facts: list[ExtractedFact],
    jurisdiction: str,
) -> list[str]:
    place_name = jurisdiction_label(institution.jurisdiction)
    queries = list(_queries_for_institution(institution))
    if not queries:
        queries = [
            f"{institution.display_name} legal regulations {place_name}",
            f"{institution.display_name} {doc_type} rights {place_name}",
        ]

    fact_terms = " ".join(f.value for f in facts[:3] if f.value)
    if fact_terms:
        queries = [f"{queries[0]} {fact_terms}"] + queries[1:]

    return queries
