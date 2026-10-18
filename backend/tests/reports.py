"""Test helper: a small TriageReport built from real ingested text, with citations made by the real verifier."""

from __future__ import annotations

from datetime import UTC, datetime

from lexishield.ingest.pipeline import Ingested, ingest_text
from lexishield.models import (
    ChecklistItem,
    ChecklistStatus,
    Classification,
    Country,
    DocType,
    JurisdictionInfo,
    ReportMetrics,
    Severity,
    TriageReport,
    UserRole,
)
from lexishield.verify.quotes import verify_quote

EMPLOYMENT_TEXT = (
    "1. BOND. You will serve a bond of twenty-four (24) months. Leaving earlier means repaying Rs. 2,00,000.\n"
    "2. NOTICE. You must give ninety (90) days notice to resign.\n"
    "3. NON-COMPETE. For twelve (12) months after leaving, you shall not join a competing business.\n"
)
RENTAL_TEXT = (
    "1. RENT. The Tenant shall pay Rs. 20,000/- per month.\n"
    "2. LOCK-IN. Neither party may end this agreement during the first six (6) months.\n"
    "3. NOTICE. Either party may end this agreement by giving two (2) months notice.\n"
    "4. DEPOSIT. The Tenant shall pay a security deposit of Rs. 60,000/-.\n"
    "5. GOVERNING LAW. This agreement is governed by the laws of India.\n"
)


def _item(
    ing: Ingested, topic_id: str, status: ChecklistStatus, number: str | None, quote: str | None
) -> ChecklistItem:
    evidence = []
    if number is not None and quote is not None:
        clause = next(c for c in ing.clauses if c.number == number)
        cit = verify_quote(quote, clause, ing.text, ing.pages)
        assert cit is not None, quote
        evidence.append(cit)
    return ChecklistItem(
        topic_id=topic_id, title=topic_id, hypothesis=topic_id, status=status, evidence=evidence, severity=Severity.HIGH
    )


def _report(
    document_id: str, doc_type: DocType, items: list[ChecklistItem], country: Country = Country.IN
) -> TriageReport:
    return TriageReport(
        document_id=document_id,
        pack_id="in_employment" if doc_type == DocType.EMPLOYMENT else "in_rental",
        classification=Classification(doc_type=doc_type, confidence=0.9),
        jurisdiction=JurisdictionInfo(country=country, confidence=0.9),
        user_role=UserRole.UNKNOWN,
        checklist=items,
        silences=[i.topic_id for i in items if i.status == ChecklistStatus.NOT_MENTIONED],
        metrics=ReportMetrics(model="test"),
        generated_at=datetime.now(UTC),
    )


def employment_report(document_id: str = "doc_test", country: Country = Country.IN) -> tuple[Ingested, TriageReport]:
    ing = ingest_text(EMPLOYMENT_TEXT)
    E = ChecklistStatus.ENTAILED
    items = [
        _item(
            ing,
            "in_employment.service_bond",
            E,
            "1",
            "You will serve a bond of twenty-four (24) months. Leaving earlier means repaying Rs. 2,00,000.",
        ),
        _item(ing, "in_employment.notice_period", E, "2", "You must give ninety (90) days notice to resign."),
        _item(
            ing,
            "in_employment.non_compete",
            E,
            "3",
            "For twelve (12) months after leaving, you shall not join a competing business.",
        ),
        _item(ing, "in_employment.joining_bonus_clawback", ChecklistStatus.NOT_MENTIONED, None, None),
    ]
    return ing, _report(document_id, DocType.EMPLOYMENT, items, country)


def rental_report(document_id: str = "doc_test", refund_silent: bool = True) -> tuple[Ingested, TriageReport]:
    ing = ingest_text(RENTAL_TEXT)
    E = ChecklistStatus.ENTAILED
    items = [
        _item(ing, "in_rental.rent_amount", E, "1", "The Tenant shall pay Rs. 20,000/- per month."),
        _item(
            ing, "in_rental.lock_in", E, "2", "Neither party may end this agreement during the first six (6) months."
        ),
        _item(
            ing,
            "in_rental.termination_notice",
            E,
            "3",
            "Either party may end this agreement by giving two (2) months notice.",
        ),
        _item(ing, "in_rental.security_deposit", E, "4", "The Tenant shall pay a security deposit of Rs. 60,000/-."),
        _item(
            ing,
            "in_rental.deposit_refund_deductions",
            ChecklistStatus.NOT_MENTIONED if refund_silent else ChecklistStatus.UNCLEAR,
            None,
            None,
        ),
    ]
    return ing, _report(document_id, DocType.RENTAL, items)
