"""Phase 2 gate (verification): quote verifier, facts, distortion checker, silence double-key, tiers, advice guard.

Pure Python, no model. The rules here decide what can reach a user.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from lexishield.ingest.pipeline import ingest_text
from lexishield.models import ChecklistStatus, Citation, Distortion, MatchType, Tier, UserRole
from lexishield.verify import distortion
from lexishield.verify.advice_guard import verdict_hits
from lexishield.verify.facts import extract_facts
from lexishield.verify.quotes import verify_quote
from lexishield.verify.silence import decide_status, lexicon_hits
from lexishield.verify.tiers import tier

pytestmark = pytest.mark.phase2

FIXTURE = Path(__file__).parent / "fixtures" / "in_rental_11m_leave_license.txt"
DEPOSIT = (
    "The Licensee shall pay to the Licensor an interest-free refundable security deposit of Rs. 1,50,000/- "
    "(Rupees One Lakh Fifty Thousand only) on or before the date of possession."
)


@pytest.fixture(scope="module")
def doc():  # type: ignore[no-untyped-def]
    return ingest_text(FIXTURE.read_text(encoding="utf-8"))


def _clause(doc, number: str):  # type: ignore[no-untyped-def]
    return next(c for c in doc.clauses if c.number == number)


def _verify(doc, quote: str, number: str = "3", fuzzy_min: int = 92):  # type: ignore[no-untyped-def]
    return verify_quote(quote, _clause(doc, number), doc.text, doc.pages, fuzzy_min)


# ----------------------------------------------------------------- quote verifier


def test_exact_quote_matches_with_exact_offsets(doc) -> None:  # type: ignore[no-untyped-def]
    cit = _verify(doc, DEPOSIT[:120])
    assert cit is not None and cit.match == MatchType.EXACT and cit.score == 100
    assert doc.text[cit.char_start : cit.char_end] == cit.quote == DEPOSIT[:120]
    assert cit.clause_id == _clause(doc, "3").id


@pytest.mark.parametrize(
    "variant",
    [
        DEPOSIT.replace("shall pay", "shall  pay"),  # double space
        DEPOSIT.replace("Rs. 1,50,000/-", "Rs.\n1,50,000/-"),  # line break where the source has a space
        DEPOSIT.lower(),  # case
    ],
)
def test_normalized_variants_match(doc, variant: str) -> None:  # type: ignore[no-untyped-def]
    cit = _verify(doc, variant[:200])
    assert cit is not None
    assert cit.match in (MatchType.EXACT, MatchType.NORMALIZED)
    assert cit.quote == doc.text[cit.char_start : cit.char_end]


def test_curly_quotes_and_dashes_match_straight_source() -> None:
    text = "1. TERM. The Licensee’s stay is for eleven (11) months – renewable by agreement only."
    d = ingest_text(text)
    cit = verify_quote(
        "1. TERM. The Licensee's stay is for eleven (11) months - renewable by agreement", d.clauses[0], d.text, d.pages
    )
    assert cit is not None and cit.match == MatchType.NORMALIZED
    assert cit.quote == text[cit.char_start : cit.char_end]  # the source characters, curly quote and dash included


def test_hyphenated_line_break_is_joined() -> None:
    text = "1. DEPOSIT. The deposit is non-re-\nfundable and is held for the full licence period of the agreement."
    d = ingest_text(text)
    # 'non-re-' + 'fundable' joins to 'non-refundable', so the quote matches on normalized text
    cit = verify_quote("The deposit is non-refundable", d.clauses[0], d.text, d.pages)
    assert cit is not None and cit.match == MatchType.NORMALIZED
    assert cit.quote == d.text[cit.char_start : cit.char_end]  # the source line break is kept in the quote


def test_fuzzy_typo_is_accepted_when_numbers_and_negation_match(doc) -> None:  # type: ignore[no-untyped-def]
    typo = DEPOSIT[:150].replace("refundable", "refundabel")
    cit = _verify(doc, typo)
    assert cit is not None and cit.match == MatchType.FUZZY and cit.score >= 92
    assert cit.quote == doc.text[cit.char_start : cit.char_end]


@pytest.mark.parametrize(
    "wrong",
    [
        DEPOSIT.replace("1,50,000", "1,05,000"),
        DEPOSIT.replace("shall pay", "shall not pay"),
    ],
)
def test_fuzzy_match_rejected_when_a_number_or_negation_differs(doc, wrong: str) -> None:  # type: ignore[no-untyped-def]
    assert _verify(doc, wrong) is None


def test_fabricated_quote_is_rejected(doc) -> None:  # type: ignore[no-untyped-def]
    assert _verify(doc, "The Licensor shall pay a bonus of one crore rupees to the Licensee every month.") is None


@pytest.mark.parametrize("quote", ["", "   ", "refundble"])
def test_empty_or_too_short_fuzzy_quotes_are_rejected(doc, quote: str) -> None:  # type: ignore[no-untyped-def]
    assert _verify(doc, quote) is None


def test_model_amount_is_not_substituted_for_source_amount(doc) -> None:  # type: ignore[no-untyped-def]
    # A quote with the wrong amount never matches, so the source amount can't be replaced silently.
    assert _verify(doc, DEPOSIT.replace("1,50,000", "15,000")) is None


def test_quote_from_a_different_clause_is_not_accepted(doc) -> None:  # type: ignore[no-untyped-def]
    assert _verify(doc, "The licence is for eleven (11) months commencing on 1 March 2026.", number="3") is None


# ----------------------------------------------------------------- facts extractor


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Rs. 1,50,000/-", {"INR 150000"}),
        ("₹15,000", {"INR 15000"}),
        ("INR 1.5 lakh", {"INR 150000"}),
        ("eleven (11) months", {"months 11"}),
        ("thirty (30) days", {"days 30"}),
        ("30 days", {"days 30"}),
        ("twenty-five percent (25%)", {"pct 25"}),
        ("1 March 2026", {"date 2026-03-01"}),
        ("March 1, 2026", {"date 2026-03-01"}),
        ("on the 5th day of each month", set()),
        ("no numbers here", set()),
    ],
)
def test_facts_are_extracted_in_one_form(text: str, expected: set[str]) -> None:
    assert extract_facts(text) == expected


def test_same_fact_in_different_forms_compares_equal() -> None:
    assert extract_facts("Rs. 1,50,000/-") == extract_facts("₹1,50,000")
    assert extract_facts("thirty (30) days") == extract_facts("30 days")


# ----------------------------------------------------------------- distortion checker


def _cit(quote: str, clause_id: str = "C4") -> Citation:
    return Citation(page=1, char_start=0, char_end=len(quote), clause_id=clause_id, quote=quote, match=MatchType.EXACT)


PARTIES = {"Mr. A. Sharma": UserRole.LANDLORD, "Ms. B. Rao": UserRole.TENANT}


@pytest.mark.parametrize(
    ("explanation", "source", "expected"),
    [
        ("You pay a deposit of ₹1,50,000 before moving in.", DEPOSIT, Distortion.PASS),
        ("You pay a deposit of ₹15,000 before moving in.", DEPOSIT, Distortion.FAIL),  # the 15,000 case
        (
            "The tenant must sublet after 30 days.",
            "The Licensee shall not sublet the Premises after 60 days.",
            Distortion.FAIL,
        ),
        (
            "The tenant must sublet the Premises.",
            "The Licensee shall not sublet the Premises.",
            Distortion.WARN,
        ),  # shall not vs shall
        (
            "The tenant must not sublet the Premises.",
            "The Licensee shall sublet the Premises with consent.",
            Distortion.WARN,
        ),
        ("The landlord must pay the deposit.", "The Licensee shall pay to the Licensor the deposit.", Distortion.WARN),
    ],
)
def test_distortion_rules(explanation: str, source: str, expected: Distortion) -> None:
    result, _ = distortion.check(explanation, [_cit(source)], PARTIES)
    assert result == expected


def test_thirty_versus_sixty_days_fails() -> None:
    result, reasons = distortion.check(
        "Either party gives 60 days notice.",
        [_cit("Either party may terminate by giving thirty (30) days notice in writing.")],
        PARTIES,
    )
    assert result == Distortion.FAIL and any("days 60" in r for r in reasons)


def test_no_citations_or_no_explanation_is_not_applicable() -> None:
    assert distortion.check("Something.", [], PARTIES)[0] == Distortion.NA
    assert distortion.check("", [_cit(DEPOSIT)], PARTIES)[0] == Distortion.NA


# ----------------------------------------------------------------- silence double-key


def test_lexicon_matches_at_the_start_of_a_word() -> None:
    assert lexicon_hits("The deposit shall be refunded in 30 days.", ["refund"]) == ["refund"]
    assert lexicon_hits("Nothing about money here.", ["refund", "deposit"]) == []


def test_silence_needs_both_checks() -> None:
    assert decide_status(ChecklistStatus.NOT_MENTIONED, False, []) == (ChecklistStatus.NOT_MENTIONED, None)
    status, note = decide_status(ChecklistStatus.NOT_MENTIONED, False, ["refund"])
    assert status == ChecklistStatus.UNCLEAR and note


def test_a_claim_without_a_verified_quote_is_unclear() -> None:
    assert decide_status(ChecklistStatus.ENTAILED, False, [])[0] == ChecklistStatus.UNCLEAR
    assert decide_status(ChecklistStatus.CONTRADICTED, False, [])[0] == ChecklistStatus.UNCLEAR
    assert decide_status(ChecklistStatus.ENTAILED, True, [])[0] == ChecklistStatus.ENTAILED
    assert decide_status(ChecklistStatus.UNCLEAR, True, [])[0] == ChecklistStatus.UNCLEAR


# ----------------------------------------------------------------- tiers


@pytest.mark.parametrize(
    ("status", "citations", "dist", "expected"),
    [
        (ChecklistStatus.NOT_MENTIONED, [], Distortion.NA, Tier.NOT_FOUND),
        (ChecklistStatus.UNCLEAR, [_cit(DEPOSIT)], Distortion.PASS, Tier.ASK_A_LAWYER),
        (ChecklistStatus.ENTAILED, [_cit(DEPOSIT)], Distortion.PASS, Tier.STATED),
        (ChecklistStatus.ENTAILED, [_cit(DEPOSIT)], Distortion.WARN, Tier.INTERPRETATION),
        (ChecklistStatus.ENTAILED, [_cit(DEPOSIT)], Distortion.FAIL, Tier.ASK_A_LAWYER),
        (ChecklistStatus.ENTAILED, [], Distortion.NA, Tier.ASK_A_LAWYER),
    ],
)
def test_tiers(status: ChecklistStatus, citations: list[Citation], dist: Distortion, expected: Tier) -> None:
    assert tier(status, citations, dist) == expected


# ----------------------------------------------------------------- advice guard


@pytest.mark.parametrize(
    "text",
    [
        "This clause is enforceable in Karnataka.",
        "The notice period is void.",
        "You should sign this agreement.",
        "You will win the dispute.",
        "This is definitely unfair to you.",
        "The terms are guaranteed to hold.",
        "This clause is illegal.",
    ],
)
def test_verdict_language_is_caught(text: str) -> None:
    assert verdict_hits(text)


@pytest.mark.parametrize(
    "text",
    [
        "The deposit is refundable.",
        "This is a legal notice.",
        "The licence runs for eleven months.",
        "You pay a deposit of Rs. 1,50,000 before moving in.",
    ],
)
def test_ordinary_plain_text_is_not_flagged(text: str) -> None:
    assert verdict_hits(text) == []
