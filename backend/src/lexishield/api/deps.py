"""FastAPI dependencies: shared singletons live on app.state, set in create_app()."""

from __future__ import annotations

from fastapi import Request

from ..llm.gateway import LLMGateway
from ..settings import Settings


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_gateway(request: Request) -> LLMGateway:
    return request.app.state.gateway
