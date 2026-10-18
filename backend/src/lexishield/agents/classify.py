"""Document type and party-role classification. Gemma proposes; deterministic signals are the fallback."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from ..ingest.pipeline import Ingested
from ..ingest.prompt_view import analysis_text
from ..llm.gateway import LLMError, LLMGateway
from ..llm.prompts import classify as prompts
from ..models import Classification, DocType, UserRole

MAX_PROMPT_CHARS = 6000  # the front of a document carries the parties, the type and the governing law


class PartyRoleOut(BaseModel):
    party: str = Field(max_length=60)
    role: UserRole


class ClassifyOut(BaseModel):
    doc_type: Literal["rental", "employment", "msa", "legal_notice", "unknown"]
    party_roles: list[PartyRoleOut] = Field(max_length=8)
    confidence: float = Field(ge=0, le=1)


@dataclass
class ClassifyResult:
    classification: Classification
    source: Literal["model", "signals"]


def prompt_document(ing: Ingested) -> str:
    """Clause text with every flagged hidden instruction removed. Never the raw text."""
    parts = [analysis_text(c, ing.hidden) for c in ing.clauses]
    return "\n".join(parts)[:MAX_PROMPT_CHARS]


async def classify(gw: LLMGateway, ing: Ingested) -> ClassifyResult:
    document = prompt_document(ing)
    try:
        res = await gw.structured(ClassifyOut, prompts.USER.replace("{DOCUMENT}", document), system=prompts.SYSTEM)
    except LLMError:
        # The model is unavailable or invalid: keep the deterministic signal, with low confidence, and say so.
        quick = ing.quick.doc_type
        return ClassifyResult(
            Classification(doc_type=quick, confidence=0.3 if quick != DocType.UNKNOWN else 0.0),
            source="signals",
        )
    value = res.value
    return ClassifyResult(
        Classification(
            doc_type=DocType(value.doc_type),
            confidence=value.confidence,
            party_roles={p.party: p.role for p in value.party_roles},
        ),
        source="model",
    )
