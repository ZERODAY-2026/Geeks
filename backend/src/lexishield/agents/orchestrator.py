"""Analysis plan: classify, choose the pack, run the checklist per topic, then triage.

Events are emitted in the order the contract promises: warning, job.stage, classification.ready, then
checklist.item and card.ready for each topic, then the caller emits report.ready. The caller decides how events
are delivered.
"""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from ..agents.checklist import DocContext, TopicOutcome, analyze_topic
from ..agents.classify import classify
from ..ingest.pipeline import Ingested
from ..ingest.quick import governing_law
from ..ingest.segment import line_span, page_of
from ..llm.gateway import LLMGateway
from ..models import (
    AnalyzeRequest,
    ChecklistStatus,
    Citation,
    Classification,
    Country,
    Distortion,
    DocType,
    Escalation,
    JurisdictionInfo,
    MatchType,
    ReportMetrics,
    Severity,
    Tier,
    TriageReport,
    UserRole,
)
from ..packs import Pack, pack_for, routes
from ..settings import Settings

Emit = Callable[[str, dict], Awaitable[None]]
IsCancelled = Callable[[], bool]

SEVERITY_ORDER = {Severity.HIGH: 0, Severity.MEDIUM: 1, Severity.LOW: 2, Severity.INFO: 3}


class Cancelled(Exception):
    pass


def _jurisdiction(ing: Ingested, req: AnalyzeRequest) -> tuple[Country, JurisdictionInfo]:
    """The governing-law clause decides the jurisdiction when it names one; the keyword signals are the fallback."""
    law = governing_law(ing.text)
    evidence: list[Citation] = []
    if law is not None:
        detected, start, end = law
        clause = next((c for c in ing.clauses if c.char_start <= start < c.char_end), None)
        if clause is not None:
            line_start, line_end = line_span(ing.pages, start, end)
            evidence.append(
                Citation(
                    page=page_of(ing.pages, start),
                    char_start=start,
                    char_end=end,
                    clause_id=clause.id,
                    quote=ing.text[start:end],
                    match=MatchType.EXACT,
                    score=100.0,
                    line_start=line_start,
                    line_end=line_end,
                )
            )
    else:
        detected = ing.quick.country
    country = req.jurisdiction or detected
    info = JurisdictionInfo(
        country=country,
        state=req.state,
        confidence=0.9 if law is not None else (0.7 if country != Country.UNKNOWN else 0.0),
        evidence=evidence,
        overridden_by_user=req.jurisdiction is not None,
    )
    return country, info


def _escalations(
    pack: Pack | None, outcomes: list[TopicOutcome], doc_type: DocType, settings: Settings
) -> list[Escalation]:
    """A route is shown when a topic that points to it is silent or needs a lawyer."""
    by_topic = {o.item.topic_id: o for o in outcomes}
    needed: set[str] = set()
    for t in pack.topics if pack else []:
        o = by_topic.get(t.id)
        if not t.escalation_ref or o is None:
            continue
        if o.item.status == ChecklistStatus.NOT_MENTIONED or (o.card and o.card.tier == Tier.ASK_A_LAWYER):
            needed.add(t.escalation_ref)
    if doc_type == DocType.LEGAL_NOTICE:
        needed.add("legal_notice")
    if doc_type == DocType.MSA:
        needed.add("msa")
    catalogue = routes(settings)
    out: list[Escalation] = []
    for key in sorted(needed):
        route = catalogue.get(key)
        if route is None:
            continue
        out.append(
            Escalation(
                topic_family=key,
                who=route.who,
                why=route.why,
                free_help=route.free_help,
                urgency=route.urgency,
                jurisdiction_note=route.jurisdiction_note,
            )
        )
    return out


async def run_analysis(
    gw: LLMGateway,
    settings: Settings,
    ing: Ingested,
    document_id: str,
    req: AnalyzeRequest,
    emit: Emit,
    is_cancelled: IsCancelled,
) -> TriageReport:
    started = time.perf_counter()
    cfg = settings.verify
    for w in ing.warnings:
        await emit("warning", w.model_dump(mode="json"))

    await emit("job.stage", {"stage": "classify", "done": 0, "total": 1})
    cls = await classify(gw, ing)
    doc_type = req.doc_type or cls.classification.doc_type
    country, jurisdiction = _jurisdiction(ing, req)
    classification = Classification(
        doc_type=doc_type,
        confidence=cls.classification.confidence,
        party_roles=cls.classification.party_roles,
    )
    await emit(
        "classification.ready",
        {
            "classification": classification.model_dump(mode="json"),
            "jurisdiction": jurisdiction.model_dump(mode="json"),
        },
    )
    if is_cancelled():
        raise Cancelled()

    pack = pack_for(doc_type, settings)
    topics = sorted(pack.topics, key=lambda t: SEVERITY_ORDER[t.severity]) if pack else []
    await emit("job.stage", {"stage": "plan", "done": 0, "total": len(topics)})

    doc = DocContext.build(ing, classification.party_roles, country, cfg.fuzzy_min, cfg.retrieval_k, cfg.relevance_gate)
    role = req.user_role or UserRole.UNKNOWN
    outcomes: list[TopicOutcome] = []
    for i, topic in enumerate(topics, 1):
        if is_cancelled():
            raise Cancelled()
        outcome = await analyze_topic(gw, topic, doc, role)
        outcomes.append(outcome)
        await emit("checklist.item", outcome.item.model_dump(mode="json"))
        if outcome.card is not None:
            await emit("card.ready", outcome.card.model_dump(mode="json"))
        await emit("job.stage", {"stage": "checklist", "done": i, "total": len(topics)})

    cards = sorted((o.card for o in outcomes if o.card), key=lambda c: SEVERITY_ORDER[c.severity])
    shown = [o.distortion for o in outcomes if o.card is not None]
    metrics = ReportMetrics(
        citations_proposed=sum(o.proposed for o in outcomes),
        citations_verified=sum(o.verified for o in outcomes),
        unverified_displayed=0,  # by construction: only verified citations reach a card or a checklist item
        distortion_pass=shown.count(Distortion.PASS),
        distortion_warn=shown.count(Distortion.WARN),
        distortion_fail=shown.count(Distortion.FAIL),
        model=gw.chat_model,
        latency_s=round(time.perf_counter() - started, 2),
    )
    return TriageReport(
        document_id=document_id,
        pack_id=pack.pack_id if pack else "none",
        classification=classification,
        jurisdiction=jurisdiction,
        user_role=role,
        cards=cards,
        checklist=[o.item for o in outcomes],
        silences=[o.item.topic_id for o in outcomes if o.item.status == ChecklistStatus.NOT_MENTIONED],
        hidden_findings=list(ing.hidden),
        escalations=_escalations(pack, outcomes, doc_type, settings),
        metrics=metrics,
        generated_at=datetime.now(UTC),
    )
