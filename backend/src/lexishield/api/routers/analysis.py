"""Analysis jobs, SSE progress stream and the triage report (Phase 2)."""

from __future__ import annotations

from fastapi import APIRouter

from ...models import AnalyzeRequest, JobAccepted, JobInfo, TriageReport
from ..errors import NotImplementedYet, problem_responses

router = APIRouter(tags=["analysis"])

SSE_DESCRIPTION = """Server-Sent Events stream. Each event has `event:` set to one of
`job.stage`, `classification.ready`, `checklist.item`, `card.ready`, `warning`,
`report.ready`, `job.failed`, and a JSON `data:` payload:

| event | data |
|---|---|
| job.stage | JobProgress |
| classification.ready | {classification: Classification, jurisdiction: JurisdictionInfo} |
| checklist.item | ChecklistItem |
| card.ready | ClauseCard |
| warning | IngestionWarning |
| report.ready | {document_id, report_url} |
| job.failed | Problem |
"""


@router.post(
    "/documents/{document_id}/analyze",
    response_model=JobAccepted,
    status_code=202,
    responses=problem_responses(404, 409),
)
async def analyze(document_id: str, body: AnalyzeRequest) -> JobAccepted:
    raise NotImplementedYet("Phase 2")


@router.get("/jobs/{job_id}", response_model=JobInfo, responses=problem_responses(404))
async def get_job(job_id: str) -> JobInfo:
    raise NotImplementedYet("Phase 2")


@router.get(
    "/jobs/{job_id}/events",
    description=SSE_DESCRIPTION,
    responses={200: {"content": {"text/event-stream": {}}}, **problem_responses(404)},
)
async def job_events(job_id: str) -> None:
    raise NotImplementedYet("Phase 2")


@router.post("/jobs/{job_id}/cancel", response_model=JobInfo, responses=problem_responses(404))
async def cancel_job(job_id: str) -> JobInfo:
    raise NotImplementedYet("Phase 2")


@router.get("/documents/{document_id}/report", response_model=TriageReport, responses=problem_responses(404, 409))
async def get_report(document_id: str) -> TriageReport:
    raise NotImplementedYet("Phase 2")
