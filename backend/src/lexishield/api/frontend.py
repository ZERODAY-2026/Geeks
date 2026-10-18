"""Serves the built frontend (frontend/dist) from the API server, so the whole app runs on one local origin.

Only files inside the build folder are served. Paths under /api never fall through to the app: an unknown API path
still returns a problem+json 404. Nothing here is part of the API contract.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from starlette.exceptions import HTTPException

API_ROOT = "api/"


def mount_frontend(app: FastAPI, dist: Path) -> bool:
    """Register the built app. Returns False (and does nothing) if there is no build to serve."""
    index = dist / "index.html"
    if not index.is_file():
        return False
    root = dist.resolve()

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        if path == "api" or path.startswith(API_ROOT):
            raise HTTPException(status_code=404)
        candidate = (root / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)  # client-side routes load the app shell

    return True
