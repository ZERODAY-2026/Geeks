"""Analysis jobs, SSE progress stream and the triage report (Phase 2)."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, Request
from sse_starlette.sse import EventSourceResponse

from ...agents.orchestrator import Cancelled, run_analysis
from ...jobs.queue import Job, JobManager, event_payload
from ...models import AnalyzeRequest, DocumentDetail, JobAccepted, JobInfo, JobStatus, TriageReport
from ..errors import LexiError, problem_responses
from .documents import ingested_from, load_detail

router = APIRouter(tags=["analysis"])

API = "/api/v1"
POLL_S = 0.05

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


def _start(request: Request, detail: DocumentDetail, body: AnalyzeRequest, job: Job) -> None:
    jobs: JobManager = request.app.state.jobs
    gw = request.app.state.gateway
    settings = request.app.state.settings
    ing = ingested_from(detail)

    async def emit(name: str, data: object) -> None:
        jobs.emit(job, name, data)

    async def run(job: Job) -> None:
        try:
            report: TriageReport = await run_analysis(
                gw, settings, ing, job.document_id, body, emit, lambda: job.cancel_requested
            )
        except Cancelled:
            job.status = JobStatus.CANCELLED
            return
        jobs.store_report(report)
        jobs.emit(
            job,
            "report.ready",
            {"document_id": job.document_id, "report_url": f"{API}/documents/{job.document_id}/report"},
        )

    jobs.submit(job, run)


@router.post(
    "/documents/{document_id}/analyze",
    response_model=JobAccepted,
    status_code=202,
    responses=problem_responses(404, 409),
)
async def analyze(request: Request, document_id: str, body: AnalyzeRequest) -> JobAccepted:
    detail = load_detail(request, document_id)
    jobs: JobManager = request.app.state.jobs
    if jobs.active_for(document_id) is not None:
        raise LexiError(409, "CONFLICT", "Analysis already running", "Wait for it to finish, or cancel it first.")
    job = jobs.create(document_id)
    _start(request, detail, body, job)
    return JobAccepted(job_id=job.job_id, document_id=document_id, events_url=f"{API}/jobs/{job.job_id}/events")


def _job(request: Request, job_id: str) -> Job:
    job = request.app.state.jobs.get(job_id)
    if job is None:
        raise LexiError(404, "NOT_FOUND", "Job not found", "It finished long ago, was purged, or never existed.")
    return job


@router.get("/jobs/{job_id}", response_model=JobInfo, responses=problem_responses(404))
async def get_job(request: Request, job_id: str) -> JobInfo:
    return _job(request, job_id).info()


@router.get(
    "/jobs/{job_id}/events",
    description=SSE_DESCRIPTION,
    responses={200: {"content": {"text/event-stream": {}}}, **problem_responses(404)},
)
async def job_events(request: Request, job_id: str) -> EventSourceResponse:
    job = _job(request, job_id)
    jobs: JobManager = request.app.state.jobs

    async def stream():  # type: ignore[no-untyped-def]
        sent = 0
        while True:
            finished = job.finished  # read before draining, so no event can be missed
            events = jobs.events(job_id)
            while sent < len(events):
                name, data = events[sent]
                sent += 1
                yield {"event": name, "data": event_payload(data)}
            if finished:
                break
            await asyncio.sleep(POLL_S)

    return EventSourceResponse(stream())


@router.post("/jobs/{job_id}/cancel", response_model=JobInfo, responses=problem_responses(404))
async def cancel_job(request: Request, job_id: str) -> JobInfo:
    job = _job(request, job_id)
    request.app.state.jobs.cancel(job)
    return job.info()


@router.get("/documents/{document_id}/report", response_model=TriageReport, responses=problem_responses(404, 409))
async def get_report(request: Request, document_id: str) -> TriageReport:
    load_detail(request, document_id)  # 404 if the document is gone
    jobs: JobManager = request.app.state.jobs
    report = jobs.stored_report(document_id)
    if report is not None:
        return report
    if jobs.active_for(document_id) is not None:
        raise LexiError(409, "CONFLICT", "Analysis still running", "The report is ready when the job finishes.")
    raise LexiError(404, "NOT_FOUND", "No report yet", "Run analysis first: POST /documents/{id}/analyze.")
