"""Document upload, source viewer data and crypto-shredding deletion (Phase 1).

Documents live only in the sealed in-memory vault. Nothing is written to disk.
"""

from __future__ import annotations

import secrets
from datetime import UTC, datetime

from fastapi import APIRouter, Request, UploadFile
from fastapi.responses import Response

from ...ingest.pipeline import Ingested, IngestError, ingest_docx, ingest_pdf, ingest_text
from ...models import Clause, DeleteResult, DocumentDetail, DocumentSummary, TextUpload, WipeResult
from ...trust import egress_guard, temp_sentinel
from ...trust.vault import Vault
from ..errors import LexiError, problem_responses

router = APIRouter(tags=["documents"])

MB = 1024 * 1024
DOCX_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _vault(request: Request) -> Vault:
    return request.app.state.vault


def _run_ingest(fn, *args) -> Ingested:  # type: ignore[no-untyped-def]
    try:
        return fn(*args)
    except IngestError as e:
        raise LexiError(e.status, e.code, e.title, e.detail) from e


def file_key(document_id: str) -> str:
    return f"file:{document_id}"


def _store(request: Request, ing: Ingested, filename: str, mime: str, original: bytes) -> DocumentSummary:
    doc_id = "doc_" + secrets.token_hex(6)
    summary = DocumentSummary(
        document_id=doc_id,
        filename=filename,
        mime=mime,
        pages=len(ing.pages),
        char_count=len(ing.text),
        clause_count=len(ing.clauses),
        scanned=ing.scanned,
        warnings=ing.warnings,
        hidden_findings=ing.hidden,
        quick_detect=ing.quick,
        created_at=datetime.now(UTC),
    )
    detail = DocumentDetail(summary=summary, pages=ing.pages, clauses=ing.clauses)
    _vault(request).put(doc_id, detail.model_dump_json().encode("utf-8"))
    _vault(request).put(file_key(doc_id), original)  # the uploaded file itself, for the source viewer
    return summary


def load_detail(request: Request, document_id: str) -> DocumentDetail:
    raw = _vault(request).get(document_id)
    if raw is None:
        raise LexiError(404, "NOT_FOUND", "Document not found", "It was deleted, expired, or never existed.")
    return DocumentDetail.model_validate_json(raw)


@router.post(
    "/documents",
    response_model=DocumentSummary,
    status_code=201,
    responses=problem_responses(413, 415, 422),
    summary="Upload a PDF, DOCX or TXT (multipart field `file`)",
)
async def upload_document(request: Request, file: UploadFile) -> DocumentSummary:
    max_bytes = request.app.state.settings.server.max_upload_mb * MB
    name = file.filename or "upload"
    lower = name.lower()
    with temp_sentinel.watch():
        data = await file.read(max_bytes + 1)
        if len(data) > max_bytes:
            raise LexiError(413, "DOC_TOO_LARGE", "Document too large", f"The limit is {max_bytes // MB} MB.")
        if lower.endswith(".pdf"):
            ing = _run_ingest(ingest_pdf, data, name)
            return _store(request, ing, name, "application/pdf", data)
        if lower.endswith(".docx"):
            ing = _run_ingest(ingest_docx, data, name)
            return _store(request, ing, name, DOCX_MIME, data)
        if lower.endswith(".txt"):
            try:
                text = data.decode("utf-8-sig")
            except UnicodeDecodeError as e:
                raise LexiError(422, "MALFORMED_FILE", "Malformed file", "The text file is not valid UTF-8.") from e
            ing = _run_ingest(ingest_text, text, name)
            return _store(request, ing, name, "text/plain", data)
    raise LexiError(
        415,
        "UNSUPPORTED_TYPE",
        "Unsupported file type",
        "This build accepts PDF, DOCX and TXT.",
    )


@router.post(
    "/documents/text",
    response_model=DocumentSummary,
    status_code=201,
    responses=problem_responses(413, 422),
    summary="Submit pasted plain text",
)
async def upload_text(request: Request, body: TextUpload) -> DocumentSummary:
    ing = _run_ingest(ingest_text, body.text, body.filename)
    return _store(request, ing, body.filename, "text/plain", body.text.encode("utf-8"))


@router.get("/documents/{document_id}", response_model=DocumentDetail, responses=problem_responses(404))
async def get_document(request: Request, document_id: str) -> DocumentDetail:
    return load_detail(request, document_id)


@router.get(
    "/documents/{document_id}/file",
    response_class=Response,
    responses={
        200: {
            "content": {"application/pdf": {}, DOCX_MIME: {}, "text/plain": {}},
            "description": "The original uploaded file, for the source viewer. Open a citation at its page and lines.",
        },
        **problem_responses(404),
    },
    summary="Original uploaded file (PDF, DOCX or TXT)",
)
async def get_file(request: Request, document_id: str) -> Response:
    detail = load_detail(request, document_id)
    original = _vault(request).get(file_key(document_id))
    if original is None:
        raise LexiError(404, "NOT_FOUND", "File not found", "The original file is not stored for this document.")
    safe_name = "".join(ch if ch.isalnum() or ch in "._- " else "_" for ch in detail.summary.filename) or "document"
    media_type = detail.summary.mime + ("; charset=utf-8" if detail.summary.mime == "text/plain" else "")
    return Response(
        original,
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"', "Cache-Control": "no-store"},
    )


@router.get("/documents/{document_id}/clauses/{clause_id}", response_model=Clause, responses=problem_responses(404))
async def get_clause(request: Request, document_id: str, clause_id: str) -> Clause:
    detail = load_detail(request, document_id)
    clause = next((c for c in detail.clauses if c.id == clause_id), None)
    if clause is None:
        raise LexiError(404, "NOT_FOUND", "Clause not found", f"No clause {clause_id} in this document.")
    return clause


@router.delete("/documents/{document_id}", response_model=DeleteResult, responses=problem_responses(404))
async def delete_document(request: Request, document_id: str) -> DeleteResult:
    if not _vault(request).delete(document_id):
        raise LexiError(404, "NOT_FOUND", "Document not found", "It was already deleted or never existed.")
    _vault(request).delete(file_key(document_id))
    request.app.state.jobs.purge(document_id)  # jobs and the sealed report go with the document
    egress_guard.record("document_shredded", None, "crypto_shredded")
    return DeleteResult(deleted=True, crypto_shredded=True)


@router.delete("/sessions", response_model=WipeResult, summary="Crypto-shred every document in memory")
async def wipe_sessions(request: Request) -> WipeResult:
    request.app.state.jobs.purge_all()
    n = sum(1 for k in _vault(request).ids() if k.startswith("doc_"))  # documents, not every sealed entry
    _vault(request).wipe()
    egress_guard.record("session_wiped", None, "crypto_shredded")
    return WipeResult(wiped=n)


def ingested_from(detail: DocumentDetail) -> Ingested:
    """Rebuild the ingest result from the stored document, so the analysis sees the same offsets and findings."""
    text = "\n\n".join(p.text for p in detail.pages)
    return Ingested(
        text=text,
        pages=detail.pages,
        clauses=detail.clauses,
        hidden=detail.summary.hidden_findings,
        warnings=detail.summary.warnings,
        quick=detail.summary.quick_detect,
        scanned=detail.summary.scanned,
    )
