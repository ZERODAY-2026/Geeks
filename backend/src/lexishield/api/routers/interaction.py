"""Grounded Q&A, what-if scenarios, statute context and the pre-lawyer brief (Phase 3)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from ...models import (
    AskRequest,
    AskResponse,
    DocType,
    EscalationBrief,
    ScenarioInfo,
    ScenarioResult,
    ScenarioRunRequest,
    StatuteRef,
)
from ..errors import NotImplementedYet, problem_responses

router = APIRouter(tags=["interaction"])


@router.post("/documents/{document_id}/ask", response_model=AskResponse, responses=problem_responses(404, 503, 504))
async def ask(document_id: str, body: AskRequest) -> AskResponse:
    raise NotImplementedYet("Phase 3")


@router.get("/scenarios", response_model=list[ScenarioInfo])
async def list_scenarios(doc_type: DocType | None = None) -> list[ScenarioInfo]:
    raise NotImplementedYet("Phase 3")


@router.post(
    "/documents/{document_id}/scenarios/{scenario_id}/run",
    response_model=ScenarioResult,
    responses=problem_responses(404, 409),
)
async def run_scenario(document_id: str, scenario_id: str, body: ScenarioRunRequest) -> ScenarioResult:
    raise NotImplementedYet("Phase 3")


@router.get("/documents/{document_id}/statutes", response_model=list[StatuteRef], responses=problem_responses(404, 409))
async def statutes(document_id: str) -> list[StatuteRef]:
    raise NotImplementedYet("Phase 3")


@router.get(
    "/documents/{document_id}/brief",
    response_model=EscalationBrief,
    responses={200: {"content": {"text/markdown": {}}}, **problem_responses(404, 409)},
    summary="Pre-lawyer brief (format=json or md)",
)
async def brief(document_id: str, format: Literal["json", "md"] = Query("json")) -> EscalationBrief:
    raise NotImplementedYet("Phase 3")
