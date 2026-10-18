"""Document upload, source viewer data and deletion (Phase 1)."""

from __future__ import annotations

from fastapi import APIRouter, UploadFile

from ...models import Clause, DeleteResult, DocumentDetail, DocumentSummary, TextUpload, WipeResult
from ..errors import NotImplementedYet, problem_responses

router = APIRouter(tags=["documents"])


@router.post(
    "/documents",
    response_model=DocumentSummary,
    status_code=201,
    responses=problem_responses(413, 415, 422),
    summary="Upload a PDF / DOCX / TXT (multipart field `file`)",
)
async def upload_document(file: UploadFile) -> DocumentSummary:
    raise NotImplementedYet("Phase 1")


@router.post(
    "/documents/text",
    response_model=DocumentSummary,
    status_code=201,
    responses=problem_responses(413, 422),
    summary="Submit pasted plain text",
)
async def upload_text(body: TextUpload) -> DocumentSummary:
    raise NotImplementedYet("Phase 1")


@router.get("/documents/{document_id}", response_model=DocumentDetail, responses=problem_responses(404))
async def get_document(document_id: str) -> DocumentDetail:
    raise NotImplementedYet("Phase 1")


@router.get("/documents/{document_id}/clauses/{clause_id}", response_model=Clause, responses=problem_responses(404))
async def get_clause(document_id: str, clause_id: str) -> Clause:
    raise NotImplementedYet("Phase 1")


@router.delete("/documents/{document_id}", response_model=DeleteResult, responses=problem_responses(404))
async def delete_document(document_id: str) -> DeleteResult:
    raise NotImplementedYet("Phase 1")


@router.delete("/sessions", response_model=WipeResult, summary="Crypto-shred every document in memory")
async def wipe_sessions() -> WipeResult:
    raise NotImplementedYet("Phase 1")
