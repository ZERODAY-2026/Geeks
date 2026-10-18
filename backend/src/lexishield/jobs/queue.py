"""Analysis jobs: one GPU worker at a time. Events and the finished report are sealed in the vault.

Job status and progress counts live in memory (they contain no document text). Every event that the SSE stream
replays is stored in the vault, encrypted, so it is shredded with the document. Deleting a document purges its
jobs, their events and its report.
"""

from __future__ import annotations

import asyncio
import json
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from ..models import JobInfo, JobProgress, JobStatus, Problem, TriageReport
from ..trust.vault import Vault

FINISHED = (JobStatus.DONE, JobStatus.FAILED, JobStatus.CANCELLED)


def report_key(document_id: str) -> str:
    return f"report:{document_id}"


def events_key(job_id: str) -> str:
    return f"events:{job_id}"


def event_payload(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


@dataclass
class Job:
    job_id: str
    document_id: str
    status: JobStatus = JobStatus.QUEUED
    progress: JobProgress = field(default_factory=lambda: JobProgress(stage="queued"))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: Problem | None = None
    cancel_requested: bool = False
    task: asyncio.Task | None = None

    @property
    def finished(self) -> bool:
        return self.status in FINISHED

    def info(self) -> JobInfo:
        return JobInfo(
            job_id=self.job_id,
            document_id=self.document_id,
            status=self.status,
            progress=self.progress,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            error=self.error,
        )


Runner = Callable[[Job], Awaitable[None]]


class JobManager:
    def __init__(self, vault: Vault) -> None:
        self._vault = vault
        self._jobs: dict[str, Job] = {}
        self._gpu: asyncio.Lock | None = None

    # ------------------------------------------------------------ lifecycle

    def create(self, document_id: str) -> Job:
        job = Job(job_id="job_" + secrets.token_hex(6), document_id=document_id)
        self._jobs[job.job_id] = job
        self._save_events(job.job_id, [])
        return job

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def active_for(self, document_id: str) -> Job | None:
        return next((j for j in self._jobs.values() if j.document_id == document_id and not j.finished), None)

    def submit(self, job: Job, runner: Runner) -> None:
        if self._gpu is None:
            self._gpu = asyncio.Lock()  # one analysis at a time: the GPU serves one model call at a time
        job.task = asyncio.create_task(self._run(job, runner))

    async def _run(self, job: Job, runner: Runner) -> None:
        assert self._gpu is not None
        async with self._gpu:
            if job.cancel_requested:
                self._finish(job, JobStatus.CANCELLED)
                return
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(UTC)
            try:
                await runner(job)
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.DONE
            except asyncio.CancelledError:
                job.status = JobStatus.CANCELLED
                raise
            except Exception as e:  # the message is generic: exception text could contain document content
                job.status = JobStatus.FAILED
                job.error = Problem(
                    type="https://lexishield.local/errors/analysis-failed",
                    title="Analysis failed",
                    status=500,
                    detail=type(e).__name__,
                    code="ANALYSIS_FAILED",
                )
                self.emit(job, "job.failed", job.error.model_dump(mode="json"))
            finally:
                job.finished_at = datetime.now(UTC)

    def _finish(self, job: Job, status: JobStatus) -> None:
        job.status = status
        job.finished_at = datetime.now(UTC)

    def cancel(self, job: Job) -> None:
        """Ask a job to stop. A queued job stops at once; a running one stops before its next topic."""
        job.cancel_requested = True
        if job.status == JobStatus.QUEUED:
            self._finish(job, JobStatus.CANCELLED)

    # ------------------------------------------------------------ events and reports

    def _save_events(self, job_id: str, events: list[list[Any]]) -> None:
        self._vault.put(events_key(job_id), json.dumps(events, ensure_ascii=False).encode("utf-8"))

    def emit(self, job: Job, name: str, data: Any) -> None:
        """Append one event to the job's sealed event list, and keep the progress counts for /jobs/{id}."""
        raw = self._vault.get(events_key(job.job_id))
        events = json.loads(raw) if raw is not None else []
        events.append([name, data])
        self._save_events(job.job_id, events)
        if name == "job.stage":
            job.progress = JobProgress(stage=data["stage"], done=data.get("done", 0), total=data.get("total", 0))

    def events(self, job_id: str) -> list[tuple[str, Any]]:
        raw = self._vault.get(events_key(job_id))
        return [(name, data) for name, data in json.loads(raw)] if raw is not None else []

    def store_report(self, report: TriageReport) -> None:
        self._vault.put(report_key(report.document_id), report.model_dump_json().encode("utf-8"))

    def stored_report(self, document_id: str) -> TriageReport | None:
        raw = self._vault.get(report_key(document_id))
        return TriageReport.model_validate_json(raw) if raw is not None else None

    # ------------------------------------------------------------ deletion

    def purge(self, document_id: str) -> None:
        """Forget the jobs, their events and the report for a document. Called when the document is deleted."""
        for job in list(self._jobs.values()):
            if job.document_id == document_id:
                job.cancel_requested = True
                if job.task is not None and not job.task.done():
                    job.task.cancel()
                self._vault.delete(events_key(job.job_id))
                del self._jobs[job.job_id]
        self._vault.delete(report_key(document_id))

    def purge_all(self) -> None:
        for document_id in {j.document_id for j in self._jobs.values()}:
            self.purge(document_id)
