"""RFC 9457 problem+json errors. Every non-2xx response from the API uses this shape."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from ..llm.gateway import LLMError, ModelOutputInvalid, ModelTimeout, ModelUnavailable
from ..models import Problem

PROBLEM_JSON = "application/problem+json"
ERROR_BASE = "https://lexishield.local/errors/"


class LexiError(Exception):
    """Raise anywhere in the app to return a typed problem+json response."""

    def __init__(self, status: int, code: str, title: str, detail: str | None = None) -> None:
        super().__init__(detail or title)
        self.status, self.code, self.title, self.detail = status, code, title, detail


class NotImplementedYet(LexiError):
    def __init__(self, phase: str) -> None:
        super().__init__(501, "NOT_IMPLEMENTED", "Not implemented yet", f"This endpoint is delivered in {phase}.")


def problem_response(status: int, code: str, title: str, detail: str | None, instance: str | None) -> JSONResponse:
    body = Problem(
        type=ERROR_BASE + code.lower().replace("_", "-"),
        title=title,
        status=status,
        detail=detail,
        code=code,
        instance=instance,
    )
    return JSONResponse(body.model_dump(), status_code=status, media_type=PROBLEM_JSON)


_LLM_STATUS: dict[type[LLMError], tuple[int, str]] = {
    ModelUnavailable: (503, "Model unavailable"),
    ModelTimeout: (504, "Model timed out"),
    ModelOutputInvalid: (502, "Model returned invalid output"),
}

_HTTP_CODES = {
    404: "NOT_FOUND",
    405: "METHOD_NOT_ALLOWED",
    409: "CONFLICT",
    413: "DOC_TOO_LARGE",
    415: "UNSUPPORTED_TYPE",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(LexiError)
    async def _lexi(request: Request, exc: LexiError) -> JSONResponse:
        return problem_response(exc.status, exc.code, exc.title, exc.detail, request.url.path)

    @app.exception_handler(LLMError)
    async def _llm(request: Request, exc: LLMError) -> JSONResponse:
        status, title = _LLM_STATUS.get(type(exc), (500, "Model error"))
        return problem_response(status, exc.code, title, str(exc), request.url.path)

    @app.exception_handler(HTTPException)
    async def _http(request: Request, exc: HTTPException) -> JSONResponse:
        code = _HTTP_CODES.get(exc.status_code, f"HTTP_{exc.status_code}")
        detail = exc.detail if isinstance(exc.detail, str) else None
        return problem_response(
            exc.status_code, code, detail or code.replace("_", " ").title(), detail, request.url.path
        )

    @app.exception_handler(RequestValidationError)
    async def _validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errs: list[dict[str, Any]] = [
            {"loc": ".".join(map(str, e.get("loc", ()))), "msg": e.get("msg")} for e in exc.errors()[:10]
        ]
        detail = "; ".join(f"{e['loc']}: {e['msg']}" for e in errs)
        return problem_response(422, "VALIDATION_ERROR", "Request validation failed", detail, request.url.path)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Never echo exception text: it could contain document content.
        return problem_response(500, "INTERNAL_ERROR", "Internal error", None, request.url.path)


def problem_responses(*statuses: int) -> dict[int | str, dict[str, Any]]:
    """OpenAPI `responses=` helper so the contract documents error shapes."""
    return {s: {"model": Problem, "content": {PROBLEM_JSON: {}}} for s in statuses}
