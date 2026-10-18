"""Build the local statute index (SQLite) from Open India Law legislation parquet files. Set-up time only.

Open India Law (huggingface.co/datasets/vaquill/open-india-law) is gated: log in to Hugging Face and accept the dataset
conditions first. Download the legislation parquet files for Central and the states you need, then run:

  uv run --with pyarrow python scripts/build_statute_index.py --parquet <file.parquet> [<file.parquet> ...] \
      --snapshot v2026.08

Only the acts and sections listed in statutes/topic_map.yaml are kept. Sections the snapshot does not contain are
reported and left out. The output is backend/data/statutes.sqlite (git-ignored).

NOT YET RUN: the dataset's column names were not available when this was written. The script looks for the likely
names below and stops with the list of real columns if it cannot find one, instead of guessing.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

import pyarrow.parquet as pq
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lexishield.settings import BACKEND_DIR, Settings  # noqa: E402
from lexishield.triage.statutes import act_key, section_key  # noqa: E402

CANDIDATES = {
    "act": ["act_title", "act_name", "title_of_act", "act", "short_title"],
    "section": ["section_number", "section_no", "section", "section_id"],
    "title": ["section_title", "section_heading", "heading", "marginal_note"],
    "text": ["section_text", "text", "content", "body"],
    "status": ["section_status", "status"],
    "url": ["source_url", "url", "indiacode_url", "link"],
}
REQUIRED = ("act", "section", "text")


def pick(columns: list[str], role: str) -> str | None:
    lowered = {c.lower(): c for c in columns}
    return next((lowered[c] for c in CANDIDATES[role] if c in lowered), None)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--parquet", nargs="+", required=True, type=Path)
    ap.add_argument("--snapshot", required=True, help="Dataset snapshot tag, e.g. v2026.08")
    args = ap.parse_args()

    wanted: dict[tuple[str, str], tuple[str, str]] = {}
    for entries in (
        yaml.safe_load((BACKEND_DIR / "statutes" / "topic_map.yaml").read_text(encoding="utf-8")) or {}
    ).values():
        for e in entries:
            wanted[(act_key(e["act"]), section_key(e["section"]))] = (e["act"], e["section"])

    rows: dict[tuple[str, str], tuple] = {}
    for path in args.parquet:
        table = pq.read_table(path)
        cols = table.column_names
        mapping = {role: pick(cols, role) for role in CANDIDATES}
        missing = [r for r in REQUIRED if mapping[r] is None]
        if missing:
            print(f"{path.name}: cannot find columns for {missing}. Columns are: {cols}", file=sys.stderr)
            print("Add the right names to CANDIDATES and run again.", file=sys.stderr)
            return 2
        for rec in table.to_pylist():
            key = (act_key(str(rec[mapping["act"]])), section_key(str(rec[mapping["section"]])))
            if key in wanted and key not in rows:
                rows[key] = (
                    key[0],
                    key[1],
                    str(rec[mapping["act"]]),
                    str(rec[mapping["section"]]),
                    rec.get(mapping["title"]) if mapping["title"] else None,
                    str(rec[mapping["text"]]),
                    rec.get(mapping["status"]) if mapping["status"] else None,
                    rec.get(mapping["url"]) if mapping["url"] else None,
                )

    for key, (act, section) in wanted.items():
        if key not in rows:
            print(f"not in snapshot, left out: {act} s.{section}")

    out = Settings().paths.statute_db
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        out.unlink()
    with sqlite3.connect(out) as conn:
        conn.execute(
            "CREATE TABLE sections (act_key TEXT, section_key TEXT, act TEXT, section TEXT, title TEXT, text TEXT, "
            "status TEXT, source_url TEXT, PRIMARY KEY (act_key, section_key))"
        )
        conn.execute("CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT)")
        conn.executemany("INSERT INTO sections VALUES (?, ?, ?, ?, ?, ?, ?, ?)", list(rows.values()))
        conn.execute("INSERT INTO meta VALUES ('snapshot', ?)", (args.snapshot,))
    print(f"wrote {len(rows)} of {len(wanted)} sections to {out} (snapshot {args.snapshot})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
