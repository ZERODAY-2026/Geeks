"""Rejects oversized document uploads from the Content-Length header, before any multipart parsing or spooling."""

from __future__ import annotations

from starlette.types import ASGIApp, Receive, Scope, Send

from .errors import problem_response

MULTIPART_OVERHEAD = 64 * 1024  # framing and field headers allowed on top of the file itself


class UploadLimit:
    def __init__(self, app: ASGIApp, max_bytes: int, path_prefix: str) -> None:
        self.app, self.max_bytes, self.path_prefix = app, max_bytes, path_prefix

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope["method"] == "POST" and scope["path"].startswith(self.path_prefix):
            length = dict(scope["headers"]).get(b"content-length")
            if length is not None and int(length) > self.max_bytes + MULTIPART_OVERHEAD:
                limit_mb = self.max_bytes // (1024 * 1024)
                resp = problem_response(
                    413, "DOC_TOO_LARGE", "Document too large", f"The limit is {limit_mb} MB.", scope["path"]
                )
                await resp(scope, receive, send)
                return
        await self.app(scope, receive, send)
