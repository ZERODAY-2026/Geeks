"""Generate the second fresh held-out set. Every document here is invented for testing.

Answer keys: tests/fixtures/fresh2_keys.json, written before any model run. Do not change a document or a key after
a run. Write a new set instead.

Usage:  uv run python scripts/make_fresh2_fixtures.py
"""

from __future__ import annotations

from make_fixtures import FIXTURES, _pdf_from_lines

FRESH2_RENTAL = [
    "LEASE DEED (SYNTHETIC TEST DOCUMENT)",
    "This lease is between Mr. K. Raman, the Lessor, and Ms. L. Devi, the Lessee, for a flat in Adyar, Chennai.",
    "1. TENURE. The lease is for twelve (12) months starting 1 July 2026.",
    "2. RENT PAYABLE. The Lessee pays Rs. 24,000/- monthly, on or before the 10th.",
    "3. ADVANCE. The Lessee gives an advance of Rs. 72,000/-, returned within twenty-one (21) days after vacation, "
    "without interest.",
    "4. RENT REVISION. The rent is revised by ten percent (10%) every two years by mutual written consent.",
    "5. EXIT. Either party may end this lease by giving fifteen (15) days notice in writing.",
    "6. REPAIRS. The Lessor repairs the roof and wiring. The Lessee keeps the flat clean and pays for breakage.",
    "7. BILLS. Water and power bills are payable by the Lessee. Society charges are payable by the Lessor.",
    "8. ENTRY. The Lessor may enter the flat at reasonable hours after informing the Lessee.",
    "9. TRANSFER. The Lessee shall not transfer the tenancy to any other person.",
    "10. USE. The premises are for residence only, not for commercial activity.",
    "11. LATE RENT. A late rent payment attracts a fine of Rs. 500/- per day.",
    "12. REGISTRATION. This lease is registered with the sub-registrar, and stamp duty is paid by the Lessor.",
    "13. PAINTING. Painting charges on exit are not payable by the Lessee.",
    "14. GOVERNING LAW. This lease is governed by the laws of India. Courts at Chennai shall have jurisdiction.",
]

FRESH2_EMPLOYMENT = [
    "EMPLOYMENT LETTER (SYNTHETIC TEST DOCUMENT)",
    "1. ROLE. You are engaged as Quality Lead, reporting to the Head of Operations, at Gurugram.",
    "2. COMPENSATION. Annual cost to company is Rs. 14,40,000, including fixed pay of Rs. 12,00,000 and a performance "
    "bonus.",
    "3. PROBATION. You are on probation for six (6) months from joining.",
    "4. NOTICE. Resignation requires ninety (90) days notice.",
    "5. NOTICE BUY-OUT. The company may choose to buy out your notice by paying three (3) months of fixed pay.",
    "6. TERMINATION. Either party may end employment by giving thirty (30) days notice during probation.",
    "7. BOND. You will serve a bond of twenty-four (24) months. Leaving earlier means repaying Rs. 1,50,000.",
    "8. CONFIDENTIAL INFORMATION. Trade secrets must be protected during and after your employment.",
    "9. WORK PRODUCT. Inventions made during employment vest in the company.",
    "10. WORKING TIME. Standard working time is nine hours a day. Overtime is compensated at double pay.",
    "11. EARNED LEAVE. Twenty (20) days of earned leave are granted each year.",
    "12. JOINING BONUS. A joining bonus of Rs. 1,00,000 is payable after six months.",
    "13. GOVERNING LAW. This letter is governed by the laws of India. Courts at Gurugram have jurisdiction.",
]

FRESH2_NOTICE = [
    "NOTICE TO VACATE (SYNTHETIC TEST DOCUMENT)",
    "1. DEMAND. You must vacate the flat and hand over the keys within thirty (30) days of this letter.",
    "2. ARREARS. Rent arrears of Rs. 36,000/- for April to June 2026 are outstanding.",
    "3. CONSEQUENCE. If the premises are not vacated, eviction proceedings will be filed before the Rent Controller.",
    "4. BASIS. This notice is issued under Section 106 of the Transfer of Property Act, 1882.",
]


def main() -> None:
    FIXTURES.mkdir(parents=True, exist_ok=True)
    _pdf_from_lines(FIXTURES / "fresh2_rental_chennai.pdf", FRESH2_RENTAL)
    _pdf_from_lines(FIXTURES / "fresh2_employment_gurugram.pdf", FRESH2_EMPLOYMENT)
    _pdf_from_lines(FIXTURES / "fresh2_notice_landlord.pdf", FRESH2_NOTICE)
    print(f"second fresh set written to {FIXTURES}")


if __name__ == "__main__":
    main()
