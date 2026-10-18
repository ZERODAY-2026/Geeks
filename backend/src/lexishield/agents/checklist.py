"""Checklist NLI agent: one topic at a time. Retrieve, ask the model, then pass everything through the gate.

Nothing the model says reaches the user without the gate: quotes must verify against the cited clause, silence needs
the double-key, the explanation must pass the distortion checker and the advice guard, and the tier comes last.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from ..ingest.pipeline import Ingested
from ..ingest.prompt_view import analysis_text
from ..llm.gateway import LLMError, LLMGateway
from ..llm.prompts import checklist as prompts
from ..models import ChecklistItem, ChecklistStatus, Citation, Clause, ClauseCard, Country, Distortion, UserRole
from ..packs import Topic
from ..retrieval.hybrid import expand_xrefs, hybrid_top_k
from ..verify import distortion
from ..verify.advice_guard import verdict_hits
from ..verify.facts import extract_facts
from ..verify.quotes import verify_quote
from ..verify.severity import apply_rules
from ..verify.silence import decide_status, lexicon_hits
from ..verify.tiers import tier
from .cards import CardInput, build_card

MAX_PROMPT_CLAUSES = 8


class Evidence(BaseModel):
    clause_id: str = Field(max_length=12)
    quote: str = Field(max_length=600)


class ChecklistOut(BaseModel):
    # evidence and plain_explanation are required (empty is allowed), so the model must always send them.
    status: ChecklistStatus
    evidence: list[Evidence] = Field(max_length=3)
    plain_explanation: str = Field(max_length=400)
    stated: list[str] = Field(default_factory=list, max_length=4)
    interpretations: list[str] = Field(default_factory=list, max_length=3)
    ambiguity: list[str] = Field(default_factory=list, max_length=4)
    jurisdiction_dependent: bool = False
    questions_for_lawyer: list[str] = Field(default_factory=list, max_length=3)


@dataclass
class DocContext:
    """Everything the per-topic loop needs, built once per analysis."""

    ing: Ingested
    by_id: dict[str, Clause]
    views: dict[str, str]
    xrefs: dict[str, list[str]]
    full_view: str
    excluded: list[tuple[int, int]]
    party_roles: dict[str, UserRole]
    country: Country
    fuzzy_min: int = 92
    retrieval_k: int = 6

    @classmethod
    def build(
        cls,
        ing: Ingested,
        party_roles: dict[str, UserRole],
        country: Country,
        fuzzy_min: int,
        retrieval_k: int,
    ) -> DocContext:
        views = {c.id: analysis_text(c, ing.hidden) for c in ing.clauses}
        return cls(
            ing=ing,
            by_id={c.id: c for c in ing.clauses},
            views=views,
            xrefs={c.id: c.xrefs for c in ing.clauses},
            full_view=" ".join(views.values()),
            excluded=[
                (f.char_start, f.char_end)
                for f in ing.hidden
                if f.excluded_from_analysis and f.char_start is not None and f.char_end is not None
            ],
            party_roles=party_roles,
            country=country,
            fuzzy_min=fuzzy_min,
            retrieval_k=retrieval_k,
        )

    def overlaps_flagged(self, c: Citation) -> bool:
        return any(c.char_start < e and c.char_end > s for s, e in self.excluded)


@dataclass
class TopicOutcome:
    item: ChecklistItem
    card: ClauseCard | None
    proposed: int = 0
    verified: int = 0
    distortion: Distortion = Distortion.NA
    dropped: list[str] = field(default_factory=list)


async def _ask(gw: LLMGateway, topic: Topic, doc: DocContext, role: UserRole) -> tuple[ChecklistOut | None, list[str]]:
    query = f"{topic.query} {' '.join(topic.lexicon)}"
    top = await hybrid_top_k(gw, query, list(doc.by_id), list(doc.views.values()), doc.retrieval_k)
    chosen = (top + expand_xrefs(top, doc.xrefs))[:MAX_PROMPT_CLAUSES]
    text = "\n".join(f"[{cid} | p.{doc.by_id[cid].page_start}] {doc.views[cid]}" for cid in chosen)
    user = (
        prompts.USER.replace("{TOPIC}", topic.title)
        .replace("{HYPOTHESIS}", topic.hypothesis)
        .replace("{USER_ROLE}", role.value)
        .replace("{DOCUMENT}", text)
    )
    try:
        res = await gw.structured(ChecklistOut, user, system=prompts.SYSTEM)
    except LLMError:
        return None, chosen
    return res.value, chosen


async def analyze_topic(gw: LLMGateway, topic: Topic, doc: DocContext, role: UserRole) -> TopicOutcome:
    out, _ = await _ask(gw, topic, doc, role)
    proposed = len(out.evidence) if out else 0

    verified: list[Citation] = []
    dropped: list[str] = []
    for ev in out.evidence if out else []:
        clause = doc.by_id.get(ev.clause_id)
        cit = verify_quote(ev.quote, clause, doc.ing.text, doc.ing.pages, doc.fuzzy_min) if clause else None
        if cit is None or doc.overlaps_flagged(cit):
            dropped.append(ev.clause_id)
            continue
        verified.append(cit)

    hits = lexicon_hits(doc.full_view, topic.lexicon)
    model_status = out.status if out else ChecklistStatus.UNCLEAR
    status, status_note = decide_status(model_status, bool(verified), hits)
    facts = set().union(*(extract_facts(c.quote) for c in verified)) if verified else set()
    severity, rule_note = apply_rules(topic.severity_rules, status, facts, topic.severity)

    explanation = (out.plain_explanation if out else "").strip()
    dist, reasons = distortion.check(explanation, verified, doc.party_roles)
    interpretations = out.interpretations if out else []
    if verdict_hits(explanation) or any(verdict_hits(s) for s in interpretations):
        dist = Distortion.FAIL  # the advice guard withholds it; the tier treats it like a failed check
    card_tier = tier(status, verified, dist)

    unavailable = None if out else "The model was unavailable, so this topic was not checked."
    notes = [status_note, unavailable, rule_note]
    if status == ChecklistStatus.NOT_MENTIONED:
        notes.insert(0, topic.silence_note or "Not found in this document.")
    note = " ".join(n for n in notes if n) or None

    item = ChecklistItem(
        topic_id=topic.id,
        title=topic.title,
        hypothesis=topic.hypothesis,
        status=status,
        evidence=verified,
        note=note,
        severity=severity,
    )
    card = None
    if status != ChecklistStatus.NOT_MENTIONED:
        card = build_card(
            CardInput(
                topic_id=topic.id,
                title=topic.title,
                severity=severity,
                status=status,
                tier=card_tier,
                explanation=explanation,
                distortion=dist,
                distortion_reasons=reasons,
                citations=verified,
                stated=out.stated if out else [],
                interpretations=interpretations,
                ambiguity=out.ambiguity if out else [],
                questions=out.questions_for_lawyer if out else [],
                jurisdiction_sensitive=topic.jurisdiction_sensitive,
                jurisdiction_dependent=bool(out and out.jurisdiction_dependent),
                country=doc.country,
            )
        )
    return TopicOutcome(
        item=item,
        card=card,
        proposed=proposed,
        verified=len(verified),
        distortion=dist,
        dropped=dropped,
    )
