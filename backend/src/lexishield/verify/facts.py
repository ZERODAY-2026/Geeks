"""Facts extractor: amounts, durations, percentages and dates as comparable strings.

Used by the distortion checker: every fact in a plain-language explanation must also appear in the cited source.
Output examples: 'INR 150000', 'months 11', 'days 30', 'pct 25', 'date 2026-03-01'.
"""

from __future__ import annotations

import re

WORD_NUMBERS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8,
    "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15,
    "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40,
    "fifty": 50, "sixty": 60, "seventy": 70, "eighty": 80, "ninety": 90, "hundred": 100,
}  # fmt: skip
_WORDS = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))
MONTHS = {"jan": 1, "feb": 2, "mar": 3, "apr": 4, "may": 5, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "oct": 10,
          "nov": 11, "dec": 12}  # fmt: skip

DATE_MDY_RE = re.compile(
    r"\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+(\d{1,2}),?\s+(\d{4})\b", re.I
)
RUPEE_WORDS_RE = re.compile(
    rf"\brupees?\s+((?:(?:{_WORDS}|lakhs?|crores?|thousand|hundred)(?:[\s-]+|$))+)", re.IGNORECASE
)
MONEY_RE = re.compile(r"(?:₹|\brs\.?|\binr\b)\s*(\d[\d,]*(?:\.\d+)?)\s*(lakhs?|crores?)?", re.IGNORECASE)
DIGIT_DURATION_RE = re.compile(r"\b(\d+)\)?\s*(days?|months?|years?|weeks?)\b", re.IGNORECASE)
WORD_DURATION_RE = re.compile(
    rf"\b((?:{_WORDS})(?:[- ](?:{_WORDS}))?)\s*(?:\(\d+\)\s*)?(days?|months?|years?|weeks?|percent)\b",
    re.IGNORECASE,
)
PERCENT_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:%|per ?cent\b)", re.IGNORECASE)
DATE_RE = re.compile(r"\b(\d{1,2})\s+(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?,?\s+(\d{4})\b", re.I)
MULTIPLIER = {"lakh": 100_000, "lakhs": 100_000, "crore": 10_000_000, "crores": 10_000_000}


def _word_value(phrase: str) -> int:
    total = 0
    for part in re.split(r"[- ]", phrase.lower()):
        total += WORD_NUMBERS[part]
    return total


def _words_amount(phrase: str) -> int | None:
    """Indian amount in words, e.g. 'One Lakh Fifty Thousand' -> 150000."""
    total = current = 0
    seen = False
    for token in re.split(r"[\s-]+", phrase.lower().strip()):
        if token == "hundred":  # multiplies what came before ('two hundred' = 200), so it is checked first
            current = (current or 1) * 100
        elif token in WORD_NUMBERS:
            current += WORD_NUMBERS[token]
            seen = True
        elif token == "thousand":
            total, current = total + (current or 1) * 1000, 0
        elif token in ("lakh", "lakhs"):
            total, current = total + (current or 1) * 100_000, 0
        elif token in ("crore", "crores"):
            total, current = total + (current or 1) * 10_000_000, 0
        elif token == "":
            continue
        else:
            break
    return total + current if seen or total else None


def _unit(word: str) -> str:
    w = word.lower()
    if w == "percent":
        return "pct"
    return {"day": "days", "week": "weeks", "month": "months", "year": "years"}[w.rstrip("s")]


def _num(text: str) -> str:
    return text.replace(",", "")


def extract_facts(text: str) -> set[str]:
    facts: set[str] = set()
    for m in MONEY_RE.finditer(text):
        value = float(_num(m.group(1)))
        if m.group(2):
            value *= MULTIPLIER[m.group(2).lower()]
        facts.add(f"INR {int(value) if value.is_integer() else value}")
    for m in RUPEE_WORDS_RE.finditer(text):
        amount = _words_amount(m.group(1))
        if amount:
            facts.add(f"INR {amount}")
    for m in DIGIT_DURATION_RE.finditer(text):
        facts.add(f"{_unit(m.group(2))} {int(m.group(1))}")
    for m in WORD_DURATION_RE.finditer(text):
        unit = _unit(m.group(2))
        facts.add(f"pct {_word_value(m.group(1))}" if unit == "pct" else f"{unit} {_word_value(m.group(1))}")
    for m in PERCENT_RE.finditer(text):
        facts.add(f"pct {int(float(m.group(1)))}")
    for m in DATE_RE.finditer(text):
        facts.add(f"date {m.group(3)}-{MONTHS[m.group(2).lower()[:3]]:02d}-{int(m.group(1)):02d}")
    for m in DATE_MDY_RE.finditer(text):
        facts.add(f"date {m.group(3)}-{MONTHS[m.group(1).lower()[:3]]:02d}-{int(m.group(2)):02d}")
    return facts
