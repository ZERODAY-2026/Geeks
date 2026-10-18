"""Generate the held-out synthetic documents. Every document here is invented for testing.

These were written for the held-out check and their answer keys (tests/fixtures/holdout_keys.json) were written
before any model run. They were never used to tune the prompts. Do not change a held-out document after a run;
write a new one instead.

Usage:  uv run python scripts/make_holdout_fixtures.py
"""

from __future__ import annotations

from make_fixtures import FIXTURES, _pdf_from_lines

HOLDOUT_RENTAL = [
    "LEAVE AND LICENCE AGREEMENT (SYNTHETIC TEST DOCUMENT)",
    "This agreement is made between Mrs. S. Desai, the Licensor, and Mr. R. Khan, the Licensee, for Flat 4B, Lake View "
    "Apartments, Andheri, Mumbai, Maharashtra (the Premises).",
    "1. TERM. The licence is for twenty-four (24) months from 15 May 2026.",
    "2. RENT. The Licensee shall pay Rs. 32,000/- per month by the 7th day of each month.",
    "3. DEPOSIT. The Licensee shall pay a refundable deposit of Rs. 96,000/- which carries no interest. The deposit "
    "shall be returned within forty-five (45) days after the Licensee hands over vacant possession, less unpaid dues.",
    "4. RENT INCREASE. The monthly rent shall increase by five percent (5%) after every twelve (12) months.",
    "5. LOCK-IN. Neither party may end this licence during the first twelve (12) months.",
    "6. NOTICE. Either party may terminate this licence by giving three (3) months written notice.",
    "7. REPAIRS. The Licensor shall bear structural repairs. The Licensee shall bear the cost of minor repairs that "
    "the Licensee causes.",
    "8. CHARGES. The Licensee shall pay society charges and electricity bills.",
    "9. INSPECTION. The Licensor may visit the Premises on twenty-four (24) hours prior notice.",
    "10. SUBLETTING. The Licensee shall not sublet or part with possession of the Premises.",
    "11. USE. The Premises shall be used for residential purposes only.",
    "12. PAINTING. On exit the Licensee shall pay Rs. 4,000/- towards painting.",
    "13. STAMP DUTY. This agreement shall be registered, and stamp duty shall be shared equally.",
    "14. GOVERNING LAW. This agreement is governed by the laws of India, and courts in Mumbai shall have jurisdiction.",
]

HOLDOUT_EMPLOYMENT = [
    "OFFER OF EMPLOYMENT (SYNTHETIC TEST DOCUMENT)",
    "1. POSITION. You are hired as Senior Engineer and will report to the Engineering Manager in Bengaluru, Karnataka.",
    "2. PAY. Your fixed pay is Rs. 18,00,000 per year. You may also earn variable pay of up to ten percent (10%) of "
    "fixed pay.",
    "3. PROBATION. Probation lasts three (3) months, after which the Company confirms your employment in writing.",
    "4. NOTICE. After confirmation, either party may resign by giving sixty (60) days notice.",
    "5. BUYOUT. The Company may accept a payment equal to sixty (60) days of pay in lieu of notice.",
    "6. TERMINATION. The Company may end employment without cause by giving the notice in clause 4. Termination for "
    "misconduct takes effect immediately.",
    "7. RELOCATION BOND. You shall repay Rs. 1,00,000 of relocation support if you resign within twelve (12) months.",
    "8. CONFIDENTIALITY. You must keep Company information confidential at all times.",
    "9. INVENTIONS. All work you create for the Company belongs to the Company.",
    "10. LEAVE. You receive eighteen (18) days of paid leave each year.",
    "11. BACKGROUND. This offer is subject to satisfactory background checks.",
    "12. GOVERNING LAW. This letter is governed by the laws of India. Courts in Bengaluru have jurisdiction.",
]


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    _pdf_from_lines(FIXTURES / "in_rental_holdout_flat.pdf", HOLDOUT_RENTAL)
    _pdf_from_lines(FIXTURES / "in_employment_holdout_offer.pdf", HOLDOUT_EMPLOYMENT)
    print(f"held-out fixtures written to {FIXTURES}")


if __name__ == "__main__":
    main()
