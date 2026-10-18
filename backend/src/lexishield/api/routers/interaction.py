"""Grounded Q&A, what-if scenarios, statute context and the pre-lawyer brief (Phase 3)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import Response

from ...agents.ask import answer
from ...agents.scenarios import ScenarioNotApplicable, ScenarioNotFound, all_scenarios
from ...agents.scenarios import run_scenario as run_scenario_engine
from ...models import (
    AskRequest,
    AskResponse,
    DocType,
    EscalationBrief,
    ScenarioInfo,
    ScenarioResult,
    ScenarioRunRequest,
    StatuteRef,
    TriageReport,
)
from ...triage.brief import build_brief, render_markdown
from ...triage.statutes import StatuteIndexUnavailable, lookup
from ..errors import LexiError, problem_responses
from .documents import ingested_from, load_detail

router = APIRouter(tags=["interaction"])


def _report_or_409(request: Request, document_id: str) -> TriageReport:
    load_detail(request, document_id)  # 404 if the document is gone
    report = request.app.state.jobs.stored_report(document_id)
    if report is None:
        raise LexiError(409, "CONFLICT", "Analysis required", "Run POST /documents/{id}/analyze first.")
    return report


@router.post("/documents/{document_id}/ask", response_model=AskResponse, responses=problem_responses(404, 503, 504))
async def ask(request: Request, document_id: str, body: AskRequest) -> AskResponse:
    detail = load_detail(request, document_id)
    report = request.app.state.jobs.stored_report(document_id)  # optional: Ask works before analysis, scenarios do not
    return await answer(request.app.state.gateway, request.app.state.settings, ingested_from(detail), report, body)


@router.get("/scenarios", response_model=list[ScenarioInfo])
async def list_scenarios(request: Request, doc_type: DocType | None = None) -> list[ScenarioInfo]:
    scenarios = all_scenarios(request.app.state.settings).values()
    return [s for s in scenarios if doc_type is None or doc_type in s.doc_types]


@router.post(
    "/documents/{document_id}/scenarios/{scenario_id}/run",
    response_model=ScenarioResult,
    responses=problem_responses(404, 409),
)
async def run_scenario(
    request: Request, document_id: str, scenario_id: str, body: ScenarioRunRequest
) -> ScenarioResult:
    report = _report_or_409(request, document_id)
    try:
        return run_scenario_engine(scenario_id, report, body.params, request.app.state.settings)
    except ScenarioNotFound as e:
        raise LexiError(404, "NOT_FOUND", "Scenario not found", f"No scenario named {scenario_id!r}.") from e
    except ScenarioNotApplicable as e:
        raise LexiError(409, "CONFLICT", "Scenario does not apply", str(e)) from e


@router.get("/documents/{document_id}/statutes", response_model=list[StatuteRef], responses=problem_responses(404, 409))
async def statutes(request: Request, document_id: str) -> list[StatuteRef]:
    report = _report_or_409(request, document_id)
    try:
        return lookup(report, request.app.state.settings)
    except StatuteIndexUnavailable as e:
        raise LexiError(
            409,
            "STATUTE_INDEX_UNAVAILABLE",
            "Statute index not installed",
            "Statute context needs the local index. Build it with scripts/build_statute_index.py.",
        ) from e


@router.get(
    "/documents/{document_id}/brief",
    response_model=EscalationBrief,
    responses={200: {"content": {"text/markdown": {}}}, **problem_responses(404, 409)},
    summary="Pre-lawyer brief (format=json or md)",
)
async def brief(
    request: Request, document_id: str, format: Literal["json", "md"] = Query("json")
) -> EscalationBrief | Response:
    result = build_brief(_report_or_409(request, document_id))
    if format == "md":
        return Response(render_markdown(result), media_type="text/markdown; charset=utf-8")
    return result
