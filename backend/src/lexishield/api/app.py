"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.formparsers import MultiPartParser

from .. import __version__
from ..jobs.queue import JobManager
from ..llm.gateway import LLMGateway
from ..settings import Settings, get_settings
from ..trust import egress_guard, temp_sentinel
from ..trust.vault import Vault
from .errors import install_error_handlers
from .routers import analysis, documents, interaction, meta, system
from .upload_limit import UploadLimit

API_PREFIX = "/api/v1"
MB = 1024 * 1024

DESCRIPTION = """Private legal document triage, fully on-device, powered by Google Gemma via Ollama.

All errors use `application/problem+json` (RFC 9457). Endpoints that return **501 NOT_IMPLEMENTED**
are part of the frozen contract and are delivered in the phase named in the error detail.
Nothing here is legal advice."""


def create_app(settings: Settings | None = None, gateway: LLMGateway | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(
        title="LexiShield API",
        version=__version__,
        description=DESCRIPTION,
        openapi_url=f"{API_PREFIX}/openapi.json",
        docs_url="/docs" if settings.server.api_docs else None,  # Swagger UI needs a CDN; off offline
        redoc_url=None,
    )
    egress_guard.install()  # process-wide; idempotent
    temp_sentinel.install()
    # Uploads within the limit stay in memory: the multipart spool rolls over to disk only above this size.
    MultiPartParser.spool_max_size = settings.server.max_upload_mb * MB
    app.state.settings = settings
    app.state.gateway = gateway or LLMGateway(settings)
    app.state.vault = Vault(settings.privacy.session_ttl_s)
    app.state.jobs = JobManager(app.state.vault)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.server.cors_origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type", "Accept"],
    )
    install_error_handlers(app)
    app.add_middleware(UploadLimit, max_bytes=settings.server.max_upload_mb * MB, path_prefix=f"{API_PREFIX}/documents")
    for r in (system.router, documents.router, analysis.router, interaction.router, meta.router):
        app.include_router(r, prefix=API_PREFIX)
    return app
