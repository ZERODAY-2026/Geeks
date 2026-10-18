"""Generate the fresh held-out documents. Every document here is invented for testing.

Their answer keys (tests/fixtures/fresh_keys.json) were written before any model run and must not change after a run.
Do not edit a document after it has been used; write a new one instead.

Usage:  uv run python scripts/make_fresh_fixtures.py
"""

from __future__ import annotations

from make_fixtures import FIXTURES, _pdf_from_lines

FRESH_RENTAL = [
    "RENTAL AGREEMENT (SYNTHETIC TEST DOCUMENT)",
    "This agreement is between Mr. V. Patil, the Owner, and Ms. N. Iyer, the Tenant, for a flat at Baner, Pune, "
    "Maharashtra.",
    "1. PERIOD. The tenancy runs for eleven (11) months beginning 1 June 2026.",
    "2. MONTHLY PAYMENT. The Tenant shall pay Rs. 28,500/- each month, due on the 3rd.",
    "3. SECURITY. The Tenant shall deposit Rs. 85,500/- as security. The Owner shall refund it within thirty (30) days "
    "after the Tenant vacates.",
    "4. NOTICE. Either party may end this agreement by giving one (1) month written notice.",
    "5. REPAIRS. The Owner shall handle plumbing and electrical faults. The Tenant shall bear the cost of faults "
    "caused by the Tenant.",
    "6. UTILITIES. The Tenant pays electricity and water bills. Society maintenance is paid by the Owner.",
    "7. VISITS. The Owner may inspect the flat once a quarter with prior intimation.",
    "8. OCCUPANCY. Only the Tenant and immediate family may live in the flat.",
    "9. USE. The flat is for residential use only. Pets are not permitted.",
    "10. GOVERNING LAW. This agreement is governed by the laws of India. Courts at Pune shall have jurisdiction.",
]

FRESH_EMPLOYMENT = [
    "APPOINTMENT LETTER (SYNTHETIC TEST DOCUMENT)",
    "1. DESIGNATION. You are appointed as Product Analyst at our Hyderabad office.",
    "2. SALARY. Your annual salary is Rs. 7,20,000, made up of basic pay, house rent allowance and special allowance "
    "as per the enclosed statement.",
    "3. TRIAL PERIOD. Your trial period is four (4) months from the joining date.",
    "4. RESIGNATION. After the trial period, you must give thirty (30) days notice to resign.",
    "5. END OF SERVICE. The Company may end your employment for misconduct without notice.",
    "6. TRAINING REPAYMENT. If you leave within eighteen (18) months, you shall repay the training cost of Rs. 60,000.",
    "7. PRIVACY. Company data must stay confidential even after you leave.",
    "8. OWNERSHIP. Code and designs you produce during work belong to the Company.",
    "9. SHIFTS. Your working schedule is set by your manager. Overtime is not paid.",
    "10. LEAVE. You get twelve (12) days of casual leave per year.",
    "11. TRANSFER. The Company may move you to another city with two (2) months notice.",
    "12. GOVERNING LAW. This letter is governed by the laws of India. Courts at Hyderabad have jurisdiction.",
]

FRESH_NOTICE = [
    "NOTICE OF DEMAND (SYNTHETIC TEST DOCUMENT)",
    "1. DEMAND. You are requested to return the company laptop, serial LX-2231, within ten (10) days of this notice.",
    "2. RECOVERY. A sum of Rs. 22,000/- is due towards the unreturned laptop, as per your acknowledgement dated "
    "4 April 2026.",
    "3. CONSEQUENCE. If the laptop is not returned, the Company may recover the amount through civil proceedings "
    "in court.",
]


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    _pdf_from_lines(FIXTURES / "fresh_rental_pune.pdf", FRESH_RENTAL)
    _pdf_from_lines(FIXTURES / "fresh_employment_hyderabad.pdf", FRESH_EMPLOYMENT)
    _pdf_from_lines(FIXTURES / "fresh_notice_laptop.pdf", FRESH_NOTICE)
    print(f"fresh fixtures written to {FIXTURES}")


if __name__ == "__main__":
    main()
