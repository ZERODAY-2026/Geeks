"""Request/response models for the HTTP API (contract with the frontend)."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

from .domain import (
    DISCLAIMER,
    Citation,
    Claim,
    ClaimKind,
    ClauseCard,
    Country,
    DocType,
    Escalation,
    JurisdictionInfo,
    UserRole,
)

# ---------------------------------------------------------------- errors


class Problem(BaseModel):
    """RFC 9457 problem details (media type application/problem+json)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str | None = None
    code: str
    instance: str | None = None


# ---------------------------------------------------------------- system


class Health(BaseModel):
    status: str = Field(description="'ok' when the API is up (even if the model is not ready).")
    ollama: str = Field(pattern="^(up|down)$")
    models_ready: bool
    missing_models: list[str] = Field(default_factory=list)
    version: str


class ModelInfo(BaseModel):
    name: str
    digest: str | None = None
    family: str | None = None
    parameter_size: str | None = None
    quantization: str | None = None
    size_bytes: int | None = None
    num_ctx: int


class StatuteIndexInfo(BaseModel):
    available: bool
    snapshot: str | None = None


class SystemInfo(BaseModel):
    app_version: str
    profile: str
    model: ModelInfo
    alt_model: str | None = None
    embed_model: ModelInfo | None = None
    ollama_version: str | None = None
    ollama_host: str
    gpu: str | None = None
    packs: list[str] = Field(default_factory=list)
    statute_index: StatuteIndexInfo
    agent_mode: str


class BenchmarkResult(BaseModel):
    model: str
    label: str
    trials: int
    schema_valid: int
    schema_valid_rate: float
    status_correct_rate: float | None = Field(default=None, description="Share of trials with the expected label.")
    quote_verbatim_rate: float | None = Field(default=None, description="Share of trials whose quotes are verbatim.")
    gen_tokens_per_s_median: float | None = None
    prompt_tokens_per_s_median: float | None = None
    latency_s_median: float | None = None
    latency_s_p95: float | None = None
    load_s: float | None = None
    ram_peak_mb: float | None = None
    vram_peak_mb: float | None = None
    ollama_model_mb: float | None = Field(default=None, description="Loaded model size from Ollama /api/ps.")
    ollama_vram_mb: float | None = Field(default=None, description="Part of the model in VRAM (Ollama /api/ps).")
    host: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime


# ---------------------------------------------------------------- privacy


class EgressGuardStatus(BaseModel):
    active: bool
    allowed_hosts: list[str]
    blocked_attempts: int


class PrivacyStatus(BaseModel):
    egress_guard: EgressGuardStatus
    network_mode: str = Field(description="'host-loopback', 'offline-host' or 'docker-internal'.")
    temp_files_created: int
    sessions: int
    retention_ttl_s: int


class PrivacyEvent(BaseModel):
    ts: datetime
    type: str = Field(description="egress_blocked | document_shredded | session_expired")
    target: str | None = None
    action: str


class ReceiptRequest(BaseModel):
    document_id: str | None = None


class PrivacyReceipt(BaseModel):
    receipt_id: str
    created_at: datetime
    app_version: str
    git_commit: str | None = None
    lock_sha256: str | None = None
    model: ModelInfo
    ollama_version: str | None = None
    network: dict[str, Any]
    storage: dict[str, Any]
    document_hmac: str | None = None
    algorithm: str = "Ed25519"
    public_key: str
    signature: str


# ---------------------------------------------------------------- documents


class TextUpload(BaseModel):
    text: str = Field(min_length=1, max_length=2_000_000)
    filename: str = "pasted.txt"


class DeleteResult(BaseModel):
    deleted: bool
    crypto_shredded: bool


class WipeResult(BaseModel):
    wiped: int


# ---------------------------------------------------------------- analysis jobs


class AnalyzeRequest(BaseModel):
    doc_type: DocType | None = Field(default=None, description="Override auto-detected type.")
    jurisdiction: Country | None = Field(default=None, description="Override auto-detected jurisdiction.")
    state: str | None = None
    user_role: UserRole | None = None
    language: str = Field(default="en", pattern="^[a-z]{2}$")


class JobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


class JobAccepted(BaseModel):
    job_id: str
    document_id: str
    events_url: str


class JobProgress(BaseModel):
    stage: str
    done: int = 0
    total: int = 0


class JobInfo(BaseModel):
    job_id: str
    document_id: str
    status: JobStatus
    progress: JobProgress
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: Problem | None = None


class JobEventType(StrEnum):
    STAGE = "job.stage"
    CLASSIFICATION = "classification.ready"
    CHECKLIST_ITEM = "checklist.item"
    CARD = "card.ready"
    WARNING = "warning"
    REPORT = "report.ready"
    FAILED = "job.failed"


# ---------------------------------------------------------------- ask


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    conversation_id: str | None = None
    user_role: UserRole | None = None


class AskStatus(StrEnum):
    ANSWERED = "ANSWERED"
    PARTIAL = "PARTIAL"
    NOT_IN_DOCUMENT = "NOT_IN_DOCUMENT"
    LEGAL_VERDICT_DECLINED = "LEGAL_VERDICT_DECLINED"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class AskTrace(BaseModel):
    route: str
    tools_used: list[str] = Field(default_factory=list)
    latency_ms: int


class AskResponse(BaseModel):
    status: AskStatus
    message: str
    claims: list[Claim] = Field(default_factory=list)
    related_clauses: list[Citation] = Field(default_factory=list)
    not_found_note: str | None = None
    clarifying_question: str | None = None
    escalation: Escalation | None = None
    conversation_id: str | None = None
    trace: AskTrace
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------- scenarios


class ScenarioInfo(BaseModel):
    scenario_id: str
    title: str
    description: str
    doc_types: list[DocType]
    params_schema: dict[str, Any] = Field(default_factory=dict, description="JSON Schema of accepted params.")


class ScenarioRunRequest(BaseModel):
    params: dict[str, Any] = Field(default_factory=dict)


class ScenarioStep(BaseModel):
    text: str
    kind: ClaimKind
    citations: list[Citation] = Field(default_factory=list)


class ExposureComponent(BaseModel):
    label: str
    amount: float
    currency: str
    citation: Citation


class Exposure(BaseModel):
    computable: bool
    total: float | None = None
    currency: str | None = None
    components: list[ExposureComponent] = Field(default_factory=list)
    missing_inputs: list[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    scenario_id: str
    title: str
    steps: list[ScenarioStep]
    exposure: Exposure | None = None
    silences: list[str] = Field(default_factory=list)
    escalation: Escalation | None = None
    disclaimer: str = DISCLAIMER


# ---------------------------------------------------------------- brief, packs, eval


class EscalationBrief(BaseModel):
    document_id: str
    generated_at: datetime
    doc_type: DocType
    jurisdiction: JurisdictionInfo
    parties: dict[str, UserRole] = Field(default_factory=dict)
    top_issues: list[ClauseCard] = Field(default_factory=list)
    deadlines: list[Claim] = Field(default_factory=list)
    silences: list[str] = Field(default_factory=list)
    questions_for_lawyer: list[str] = Field(default_factory=list)
    escalations: list[Escalation] = Field(default_factory=list)
    disclaimer: str = DISCLAIMER


class TopicInfo(BaseModel):
    id: str
    title: str


class PackInfo(BaseModel):
    pack_id: str
    doc_type: DocType
    jurisdiction: Country
    version: str
    depth: str = Field(pattern="^(deep|standard)$")
    topics: list[TopicInfo]


class EvalSummary(BaseModel):
    redteam: dict[str, Any] | None = None
    cuad: dict[str, Any] | None = None
    bench: list[BenchmarkResult] = Field(default_factory=list)
