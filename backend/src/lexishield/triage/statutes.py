"""Statute context (India): related sections from a local, read-only index, shown as context and never applied.

The index is a SQLite file built at set-up time by scripts/build_statute_index.py from the Open India Law snapshot.
Without it, the feature is off: /system/info reports available=false and the statutes endpoint says so. Section text
always comes from the index, never from a model.
"""

from __future__ import annotations

import re
import sqlite3
from functools import lru_cache
from pathlib import Path

import yaml

from ..models import ChecklistStatus, Country, StatuteRef, TriageReport
from ..settings import BACKEND_DIR, Settings, get_settings

TOPIC_MAP = BACKEND_DIR / "statutes" / "topic_map.yaml"
EXCERPT_CHARS = 500
SHOWN_FOR = {ChecklistStatus.ENTAILED, ChecklistStatus.CONTRADICTED, ChecklistStatus.UNCLEAR}


class StatuteIndexUnavailable(RuntimeError):
    pass


def section_key(section: str) -> str:
    """'Section 106', 's. 106' and '106' all become '106'; '17(1)(d)' becomes '171d'."""
    s = re.sub(r"^\s*(?:section|sec\.?|s\.)\s*", "", section, flags=re.IGNORECASE)
    return re.sub(r"[^0-9a-z]", "", s.lower())


def act_key(act: str) -> str:
    return re.sub(r"[^0-9a-z]", "", act.lower())


@lru_cache
def load_topic_map(path: str = str(TOPIC_MAP)) -> dict[str, list[dict[str, str]]]:
    return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}


def _connect(db: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"file:{db.as_posix()}?mode=ro", uri=True)  # read-only: the index is never written here


def index_info(settings: Settings | None = None) -> tuple[bool, str | None]:
    db = (settings or get_settings()).paths.statute_db
    if not db.exists():
        return False, None
    try:
        with _connect(db) as conn:
            row = conn.execute("SELECT value FROM meta WHERE key = 'snapshot'").fetchone()
    except sqlite3.Error:
        return False, None
    return True, row[0] if row else None


def lookup(report: TriageReport, settings: Settings | None = None) -> list[StatuteRef]:
    """Sections related to the topics this document addresses. Empty outside India, by design."""
    cfg = settings or get_settings()
    if not cfg.features.statutes or report.jurisdiction.country != Country.IN:
        return []
    db = cfg.paths.statute_db
    available, snapshot = index_info(cfg)
    if not available:
        raise StatuteIndexUnavailable(str(db))
    topic_map = load_topic_map()
    refs: list[StatuteRef] = []
    seen: set[tuple[str, str, str]] = set()
    with _connect(db) as conn:
        for item in report.checklist:
            if item.status not in SHOWN_FOR:
                continue
            for entry in topic_map.get(item.topic_id, []):
                key = (item.topic_id, act_key(entry["act"]), section_key(entry["section"]))
                if key in seen:
                    continue
                seen.add(key)
                row = conn.execute(
                    "SELECT act, section, title, text, status, source_url FROM sections "
                    "WHERE act_key = ? AND section_key = ?",
                    (key[1], key[2]),
                ).fetchone()
                if row is None:
                    continue  # not in this snapshot: show nothing rather than something unchecked
                act, section, title, text, status, url = row
                refs.append(
                    StatuteRef(
                        topic_id=item.topic_id,
                        act=act,
                        section=section,
                        title=title,
                        excerpt=(text or "")[:EXCERPT_CHARS],
                        status=status,
                        snapshot=snapshot or "unknown",
                        source_url=url,
                    )
                )
    return refs
