"""Ask: a grounded answer, an honest 'not in this document', or a safe decline with escalation (pipeline mode).

The message text is templated. The only model-written text that reaches the user is the individual claims, and each
claim passes the same gate as the checklist: its quotes must verify against the cited clause, each quote must address
the question (per-quote relevance check), the claim must pass the distortion checker, and it must contain no verdict
language. A claim that fails any check is dropped. An answer with no surviving claim is NOT_IN_DOCUMENT.
"""

from __future__ import annotations

import secrets
import time
from typing import Literal

from pydantic import BaseModel, Field

from ..ingest.pipeline import Ingested
from ..ingest.segment import line_span
from ..llm.gateway import LLMGateway
from ..llm.prompts import ask as prompts
from ..models import (
    AskRequest,
    AskResponse,
    AskStatus,
    AskTrace,
    Citation,
    Claim,
    ClaimKind,
    Clause,
    Distortion,
    DocType,
    Escalation,
    MatchType,
    PageText,
    TriageReport,
    UserRole,
)
from ..packs import routes
from ..retrieval.hybrid import expand_xrefs, hybrid_top_k
from ..settings import Settings
from ..verify import distortion
from ..verify.advice_guard import verdict_hits
from ..verify.facts import extract_facts
from ..verify.quotes import verify_quote
from .checklist import DocContext
from .relevance import addresses
from .router import Intent, months_in, route, scenario_for
from .scenarios import run_scenario

MAX_CLAUSES = 8
RELATED = 3
ROUTE_FOR_TYPE = {"rental": "rent_tenancy", "employment": "employment", "legal_notice": "legal_notice", "msa": "msa"}
MONTHS_PARAM = {"rental_early_exit": "months_stayed", "bond_exit": "months_served"}

MSG_OUT_OF_SCOPE = "I can only answer questions about what this document says."
MSG_VERDICT = (
    "I can't tell you whether this is enforceable, legal, fair or a good idea to sign. That depends on the law and on "
    "facts outside the document. The related clauses are below, with who can advise you."
)
MSG_NOT_FOUND = "This document does not appear to address that. The closest related clauses are below."
MSG_ANSWERED = "Here is what the document says."
MSG_GUARDED = "Part of the answer read like legal advice, so it was removed. Here is what the document states."
MSG_NEEDS_DOC_ANALYSIS = "Run the analysis first, so the scenario can use the checked clauses."


class AskEvidence(BaseModel):
    clause_id: str = Field(max_length=12)
    quote: str = Field(max_length=600)


class AskClaimOut(BaseModel):
    text: str = Field(max_length=300)
    evidence: list[AskEvidence] = Field(max_length=3)


class AskOut(BaseModel):
    # claims come before status: the model writes its supporting quotes first, then decides. The gate still
    # drops any claim whose quote does not verify or does not address the question.
    claims: list[AskClaimOut] = Field(max_length=4)
    status: Literal["ANSWERED", "NOT_IN_DOCUMENT"]


def _clause_citation(clause: Clause, pages: list[PageText]) -> Citation:
    """A whole clause as a citation: its text is the source text, so it needs no matching."""
    line_start, line_end = line_span(pages, clause.char_start, clause.char_end)
    return Citation(
        page=clause.page_start,
        char_start=clause.char_start,
        char_end=clause.char_end,
        clause_id=clause.id,
        quote=clause.text,
        match=MatchType.EXACT,
        score=100.0,
        line_start=line_start,
        line_end=line_end,
    )


async def _retrieve(gw: LLMGateway, doc: DocContext, question: str) -> list[str]:
    top = await hybrid_top_k(gw, question, list(doc.by_id), list(doc.views.values()), doc.retrieval_k)
    return (top + expand_xrefs(top, doc.xrefs))[:MAX_CLAUSES]


def _related(doc: DocContext, ids: list[str]) -> list[Citation]:
    out: list[Citation] = []
    for cid in ids:
        cit = _clause_citation(doc.by_id[cid], doc.ing.pages)
        if doc.overlaps_flagged(cit):
            continue  # never show flagged hidden text as a related clause
        out.append(cit)
        if len(out) == RELATED:
            break
    return out


def _escalation(report: TriageReport | None, doc_type: DocType, settings: Settings) -> Escalation | None:
    family = ROUTE_FOR_TYPE.get(doc_type.value)
    if report is not None:
        found = next((e for e in report.escalations if e.topic_family == family), None)
        if found is not None:
            return found
    route_ = routes(settings).get(family) if family else None
    if route_ is None:
        return None
    return Escalation(
        topic_family=family or "",
        who=route_.who,
        why=route_.why,
        free_help=route_.free_help,
        urgency=route_.urgency,
        jurisdiction_note=route_.jurisdiction_note,
    )


async def _ask_model(gw: LLMGateway, question: str, role: UserRole, document: str, strict: bool) -> AskOut:
    user = (
        prompts.USER.replace("{QUESTION}", question).replace("{USER_ROLE}", role.value).replace("{DOCUMENT}", document)
    )
    system = prompts.SYSTEM + (prompts.STRICT if strict else "")
    res = await gw.structured(AskOut, user, system=system)  # model errors surface as 503/504 problem responses
    return res.value


def _has_verdict(out: AskOut) -> bool:
    return any(verdict_hits(c.text) for c in out.claims)


async def _verified_claims(gw: LLMGateway, doc: DocContext, question: str, out: AskOut) -> list[Claim]:
    kept: list[Claim] = []
    for claim in out.claims:
        if verdict_hits(claim.text):
            continue  # the output guard: a verdict never reaches the user
        citations: list[Citation] = []
        for ev in claim.evidence:
            clause = doc.by_id.get(ev.clause_id)
            cit = verify_quote(ev.quote, clause, doc.ing.text, doc.ing.pages, doc.fuzzy_min) if clause else None
            if cit is None or doc.overlaps_flagged(cit):
                continue
            if doc.relevance_gate and not await addresses(gw, "The user's question", question, cit.quote):
                continue
            citations.append(cit)
        if not citations:
            continue
        result, _ = distortion.check(claim.text, citations, doc.party_roles)
        if result == Distortion.FAIL:
            continue
        kept.append(
            Claim(
                text=claim.text,
                kind=ClaimKind.STATED,
                citations=citations,
                distortion=result,
                facts=sorted(extract_facts(claim.text)),
            )
        )
    return kept


async def answer(
    gw: LLMGateway,
    settings: Settings,
    ing: Ingested,
    report: TriageReport | None,
    req: AskRequest,
) -> AskResponse:
    started = time.perf_counter()
    conversation = req.conversation_id or "conv_" + secrets.token_hex(6)
    doc_type = report.classification.doc_type if report is not None else ing.quick.doc_type
    role = req.user_role or (report.user_role if report is not None else UserRole.UNKNOWN)
    party_roles = report.classification.party_roles if report is not None else {}
    country = report.jurisdiction.country if report is not None else ing.quick.country
    cfg = settings.verify
    doc = DocContext.build(ing, party_roles, country, cfg.fuzzy_min, cfg.retrieval_k, cfg.relevance_gate)
    tools: list[str] = []

    def reply(status: AskStatus, message: str, route_name: str, **extra: object) -> AskResponse:
        return AskResponse(
            status=status,
            message=message,
            conversation_id=conversation,
            trace=AskTrace(route=route_name, tools_used=tools, latency_ms=int((time.perf_counter() - started) * 1000)),
            **extra,  # type: ignore[arg-type]
        )

    intent = route(req.question).intent
    if intent == Intent.OUT_OF_SCOPE:
        return reply(AskStatus.OUT_OF_SCOPE, MSG_OUT_OF_SCOPE, intent.value)

    if intent == Intent.LEGAL_VERDICT:
        tools.append("search_clauses")
        ids = await _retrieve(gw, doc, req.question)
        return reply(
            AskStatus.LEGAL_VERDICT_DECLINED,
            MSG_VERDICT,
            intent.value,
            related_clauses=_related(doc, ids),
            escalation=_escalation(report, doc_type, settings),
        )

    if intent == Intent.SCENARIO:
        scenario_id = scenario_for(req.question, doc_type.value)
        if scenario_id is not None:
            if report is None:
                return reply(AskStatus.NEEDS_CLARIFICATION, MSG_NEEDS_DOC_ANALYSIS, intent.value)
            params: dict[str, object] = {}
            param = MONTHS_PARAM.get(scenario_id)
            if param is not None:
                months = months_in(req.question)
                if months is None:
                    return reply(
                        AskStatus.NEEDS_CLARIFICATION,
                        "I need one detail to work this out.",
                        intent.value,
                        clarifying_question="How many months in would that be?",
                    )
                params[param] = months
            tools.append(f"scenario:{scenario_id}")
            result = run_scenario(scenario_id, report, params, settings)
            claims = [Claim(text=s.text, kind=s.kind, citations=s.citations) for s in result.steps if s.citations]
            exposure = result.exposure
            if exposure is not None and exposure.computable and exposure.total:
                message = f"Using only amounts the document states, this comes to Rs. {exposure.total:,.0f}."
                status = AskStatus.ANSWERED
            elif exposure is not None and exposure.missing_inputs:
                message = "Some amounts are not stated in the document, so no total is given: " + "; ".join(
                    exposure.missing_inputs
                )
                status = AskStatus.PARTIAL
            else:
                message = MSG_ANSWERED
                status = AskStatus.ANSWERED
            return reply(status, message, intent.value, claims=claims, escalation=result.escalation)
        # no scenario fits this question: answer it as a question about the document

    tools.append("search_clauses")
    ids = await _retrieve(gw, doc, req.question)
    document = "\n".join(f"[{cid} | p.{doc.by_id[cid].page_start}] {doc.views[cid]}" for cid in ids)
    tools.append("answer")
    out = await _ask_model(gw, req.question, role, document, strict=False)
    if _has_verdict(out):
        tools.append("regenerate")
        out = await _ask_model(gw, req.question, role, document, strict=True)
    guarded = _has_verdict(out)
    claims = await _verified_claims(gw, doc, req.question, out) if out.status == "ANSWERED" else []
    related = _related(doc, ids)
    if not claims:
        return reply(
            AskStatus.NOT_IN_DOCUMENT,
            MSG_NOT_FOUND,
            Intent.DOCFACT.value,
            related_clauses=related,
            not_found_note="No clause in this document answers the question.",
        )
    complete = len(claims) == len(out.claims) and not guarded
    return reply(
        AskStatus.ANSWERED if complete else AskStatus.PARTIAL,
        MSG_GUARDED if guarded else MSG_ANSWERED,
        Intent.DOCFACT.value,
        claims=claims,
        related_clauses=related,
    )
