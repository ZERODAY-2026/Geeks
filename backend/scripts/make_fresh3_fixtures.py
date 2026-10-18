"""Generate the third fresh held-out set. Every document here is invented for testing.

Answer keys: tests/fixtures/fresh3_keys.json, written before any model run. Do not change a document or a key after
a run. Write a new set instead.

Usage:  uv run python scripts/make_fresh3_fixtures.py
"""

from __future__ import annotations

from make_fixtures import FIXTURES, _pdf_from_lines

FRESH3_RENTAL = [
    "TENANCY AGREEMENT (SYNTHETIC TEST DOCUMENT)",
    "This agreement is between Mrs. P. Sen, the Landlord, and Mr. A. Bose, the Tenant, for a flat at Salt Lake, "
    "Kolkata, West Bengal.",
    "1. DURATION. The tenancy is for eleven (11) months from 1 August 2026.",
    "2. RENT. Rent of Rs. 19,000/- is payable monthly in advance.",
    "3. DEPOSIT. The Tenant shall keep a security deposit of Rs. 57,000/- with the Landlord.",
    "4. ENDING. The Tenant may end the tenancy with one (1) month notice. The Landlord must give three (3) months "
    "notice.",
    "5. REPAIRS. The Landlord shall carry out all major repairs within a week of being told.",
    "6. FAMILY. Only the Tenant's spouse and children may stay in the flat.",
    "7. ELECTRICITY. The Tenant pays the electricity bill as per the meter.",
    "8. GOVERNING LAW. This agreement is governed by the laws of India. Courts at Kolkata have jurisdiction.",
]

FRESH3_EMPLOYMENT = [
    "OFFER LETTER (SYNTHETIC TEST DOCUMENT)",
    "1. POST. You are offered the post of Support Engineer at our Noida office.",
    "2. PAY. Your monthly gross pay is Rs. 55,000, made up of basic pay of Rs. 30,000 and allowances of Rs. 25,000.",
    "3. PROBATION. The probation period is three (3) months.",
    "4. RESIGNATION. You must give forty-five (45) days notice to resign.",
    "5. TRAINING BOND. If you resign within twelve (12) months of joining, you shall repay Rs. 80,000 spent on your "
    "training.",
    "6. DISMISSAL. The company may dismiss you for proven misconduct after an inquiry.",
    "7. SECRECY. You shall not disclose customer data to anyone outside the company.",
    "8. HOURS. Working hours are 9 a.m. to 6 p.m., Monday to Friday.",
    "9. GOVERNING LAW. This offer is governed by the laws of India. Courts at Noida have jurisdiction.",
]

FRESH3_NOTICE = [
    "DEMAND NOTICE (SYNTHETIC TEST DOCUMENT)",
    "From: Mr. D. Roy, Proprietor, Roy Interiors.",
    "1. CLAIM. Rs. 1,20,000/- remains unpaid for interior work completed under the work order dated 2 February 2026.",
    "2. DEMAND. You are called upon to pay the amount within seven (7) days of receiving this notice.",
    "3. ACTION. Failing payment, a suit for recovery will be filed.",
]


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    _pdf_from_lines(FIXTURES / "fresh3_rental_kolkata.pdf", FRESH3_RENTAL)
    _pdf_from_lines(FIXTURES / "fresh3_employment_noida.pdf", FRESH3_EMPLOYMENT)
    _pdf_from_lines(FIXTURES / "fresh3_notice_contractor.pdf", FRESH3_NOTICE)
    print(f"third fresh set written to {FIXTURES}")


if __name__ == "__main__":
    main()
