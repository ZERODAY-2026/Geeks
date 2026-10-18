"""Core domain objects shared by the pipeline and the API contract.

Invariant: every `Citation.quote` is text copied from the source document at
[char_start, char_end); it is never the model's paraphrase.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class DocType(StrEnum):
    RENTAL = "rental"
    EMPLOYMENT = "employment"
    MSA = "msa"
    LEGAL_NOTICE = "legal_notice"
    UNKNOWN = "unknown"


class Country(StrEnum):
    IN = "IN"
    US = "US"
    UK = "UK"
    OTHER = "OTHER"
    UNKNOWN = "UNKNOWN"


class UserRole(StrEnum):
    TENANT = "tenant"
    LANDLORD = "landlord"
    EMPLOYEE = "employee"
    EMPLOYER = "employer"
    CONTRACTOR = "contractor"
    CLIENT = "client"
    RECIPIENT = "recipient"
    SENDER = "sender"
    UNKNOWN = "unknown"


class ChecklistStatus(StrEnum):
    ENTAILED = "ENTAILED"
    CONTRADICTED = "CONTRADICTED"
    NOT_MENTIONED = "NOT_MENTIONED"
    UNCLEAR = "UNCLEAR"


class ClaimKind(StrEnum):
    STATED = "STATED"
    INTERPRETATION = "INTERPRETATION"
    CONCERN = "CONCERN"


class MatchType(StrEnum):
    EXACT = "EXACT"
    NORMALIZED = "NORMALIZED"
    FUZZY = "FUZZY"


class Distortion(StrEnum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    NA = "NA"


class Tier(StrEnum):
    STATED = "STATED"
    INTERPRETATION = "INTERPRETATION"
    NOT_FOUND = "NOT_FOUND"
    ASK_A_LAWYER = "ASK_A_LAWYER"


class Severity(StrEnum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class HiddenFindingType(StrEnum):
    WHITE_TEXT = "WHITE_TEXT"
    TINY_TEXT = "TINY_TEXT"
    OFF_PAGE = "OFF_PAGE"
    ZERO_WIDTH = "ZERO_WIDTH"
    BIDI_CONTROL = "BIDI_CONTROL"
    TAG_CHARS = "TAG_CHARS"
    INJECTION_PATTERN = "INJECTION_PATTERN"


# ---------------------------------------------------------------- spans and claims


class Span(BaseModel):
    page: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class Citation(Span):
    clause_id: str
    quote: str = Field(description="Verbatim source text at [char_start, char_end).")
    match: MatchType
    score: float = Field(ge=0, le=100, default=100)
    line_start: int | None = Field(
        default=None, ge=1, description="Line on `page` where the quote starts (1-based, in the page text)."
    )
    line_end: int | None = Field(default=None, ge=1, description="Line on `page` where the quote ends (1-based).")


class Claim(BaseModel):
    text: str
    kind: ClaimKind
    citations: list[Citation] = Field(default_factory=list)
    distortion: Distortion = Distortion.NA
    facts: list[str] = Field(default_factory=list, description="Normalized facts, e.g. 'INR 150000', '30 days'.")


# ---------------------------------------------------------------- documents


class Clause(BaseModel):
    id: str = Field(description="Stable id within the document, e.g. 'C12'.")
    number: str | None = Field(default=None, description="Numbering as printed, e.g. '7.2'.")
    heading: str | None = None
    text: str
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)
    parent_id: str | None = None
    defined_terms: list[str] = Field(default_factory=list)
    xrefs: list[str] = Field(default_factory=list, description="Ids of clauses this clause refers to.")


class PageText(BaseModel):
    page: int = Field(ge=1)
    text: str
    char_start: int = Field(ge=0)
    char_end: int = Field(ge=0)


class HiddenFinding(BaseModel):
    type: HiddenFindingType
    severity: Severity
    page: int | None = None
    char_start: int | None = None
    char_end: int | None = None
    preview: str = Field(description="Short, escaped preview of the hidden text (max 120 chars).")
    excluded_from_analysis: bool = True


class IngestionWarning(BaseModel):
    code: str
    severity: Severity
    message: str
    page: int | None = None


class QuickDetect(BaseModel):
    doc_type: DocType = DocType.UNKNOWN
    country: Country = Country.UNKNOWN


class DocumentSummary(BaseModel):
    document_id: str
    filename: str
    mime: str
    pages: int
    char_count: int
    clause_count: int
    scanned: bool = False
    warnings: list[IngestionWarning] = Field(default_factory=list)
    hidden_findings: list[HiddenFinding] = Field(default_factory=list)
    quick_detect: QuickDetect = QuickDetect()
    created_at: datetime


class DocumentDetail(BaseModel):
    summary: DocumentSummary
    pages: list[PageText]
    clauses: list[Clause]


# ---------------------------------------------------------------- analysis results


class Classification(BaseModel):
    doc_type: DocType
    confidence: float = Field(ge=0, le=1)
    party_roles: dict[str, UserRole] = Field(
        default_factory=dict, description="Defined party name -> role, e.g. {'Licensee': 'tenant'}."
    )
    evidence: list[Citation] = Field(default_factory=list)


class JurisdictionInfo(BaseModel):
    country: Country
    state: str | None = None
    confidence: float = Field(ge=0, le=1)
    evidence: list[Citation] = Field(default_factory=list)
    overridden_by_user: bool = False


class ChecklistItem(BaseModel):
    topic_id: str
    title: str
    hypothesis: str
    status: ChecklistStatus
    evidence: list[Citation] = Field(default_factory=list)
    note: str | None = None
    severity: Severity = Severity.INFO


class ClauseCard(BaseModel):
    id: str
    topic_id: str
    title: str
    severity: Severity
    tier: Tier
    reading_grade: float | None = None
    source: Citation | None = None
    plain_explanation: Claim | None = Field(
        default=None, description="Null when the distortion check failed and the explanation was withheld."
    )
    explanation_withheld_reason: str | None = None
    stated: list[str] = Field(default_factory=list)
    interpretations: list[Claim] = Field(default_factory=list)
    ambiguity_flags: list[str] = Field(default_factory=list)
    jurisdiction_flags: list[str] = Field(default_factory=list)
    questions_for_lawyer: list[str] = Field(default_factory=list)


class StatuteRef(BaseModel):
    topic_id: str
    act: str
    section: str
    title: str | None = None
    excerpt: str
    status: str | None = Field(default=None, description="section_status from the dataset snapshot.")
    snapshot: str
    source_url: str | None = None
    note: str = (
        "Related provision for discussion with a lawyer. Laws change and their application depends on facts. "
        "This is not a conclusion about your document."
    )


class Escalation(BaseModel):
    topic_family: str
    who: str
    why: str
    free_help: str | None = None
    urgency: str = Field(default="normal", pattern="^(normal|urgent)$")
    jurisdiction_note: str | None = None


class ReportMetrics(BaseModel):
    citations_proposed: int = 0
    citations_verified: int = 0
    unverified_displayed: int = Field(default=0, description="Hard invariant: always 0.")
    distortion_pass: int = 0
    distortion_warn: int = 0
    distortion_fail: int = 0
    model: str
    model_digest: str | None = None
    latency_s: float = 0.0


DISCLAIMER = (
    "LexiShield gives preliminary information to help you understand a document. "
    "It is not legal advice and cannot decide whether anything is legal or enforceable."
)


class TriageReport(BaseModel):
    document_id: str
    pack_id: str
    classification: Classification
    jurisdiction: JurisdictionInfo
    user_role: UserRole = UserRole.UNKNOWN
    cards: list[ClauseCard] = Field(default_factory=list)
    checklist: list[ChecklistItem] = Field(default_factory=list)
    silences: list[str] = Field(default_factory=list, description="topic_ids reported NOT_MENTIONED.")
    hidden_findings: list[HiddenFinding] = Field(default_factory=list)
    statute_context: list[StatuteRef] = Field(default_factory=list)
    escalations: list[Escalation] = Field(default_factory=list)
    metrics: ReportMetrics
    disclaimer: str = DISCLAIMER
    generated_at: datetime
