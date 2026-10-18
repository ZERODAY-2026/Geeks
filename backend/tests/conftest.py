"""Shared fixtures. The fake Ollama client is a TEST DOUBLE ONLY; it cannot be enabled in the app."""

from __future__ import annotations

import asyncio
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi.testclient import TestClient

from lexishield.api.app import create_app
from lexishield.llm.gateway import LLMGateway
from lexishield.settings import Settings

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

INSTALLED = [
    {
        "model": "gemma4:e4b-it-qat",
        "digest": "sha256:aaa",
        "size": 6_100_000_000,
        "details": {"family": "gemma4", "parameter_size": "8B", "quantization_level": "Q4_0"},
    },
    {
        "model": "embeddinggemma:300m",
        "digest": "sha256:bbb",
        "size": 622_000_000,
        "details": {"family": "gemma3", "parameter_size": "300M", "quantization_level": "BF16"},
    },
]


class FakeOllama:
    """Scripted stand-in for ollama.AsyncClient."""

    def __init__(
        self,
        replies: list[str] | None = None,
        *,
        down: bool = False,
        delay: float = 0.0,
        models: list[dict] | None = None,
    ) -> None:
        self.replies = list(replies or [])
        self.down, self.delay = down, delay
        self.models = INSTALLED if models is None else models
        self.calls: list[dict[str, Any]] = []

    async def chat(self, **kwargs: Any) -> dict:
        self.calls.append(kwargs)
        if self.down:
            raise httpx.ConnectError("connection refused")
        if self.delay:
            await asyncio.sleep(self.delay)
        content = self.replies.pop(0) if self.replies else "{}"
        return {
            "message": {"role": "assistant", "content": content},
            "prompt_eval_count": 120,
            "eval_count": 40,
            "prompt_eval_duration": 200_000_000,
            "eval_duration": 1_000_000_000,
            "load_duration": 0,
        }

    async def embed(self, **kwargs: Any) -> dict:
        if self.down:
            raise httpx.ConnectError("connection refused")
        return {"embeddings": [[0.1, 0.2, 0.3] for _ in kwargs["input"]]}

    async def list(self) -> dict:
        if self.down:
            raise httpx.ConnectError("connection refused")
        return {"models": self.models}


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    s = Settings()
    s.models.profile = "gpu"
    s.models.options.timeout_s = 2
    s.paths.results_dir = str(tmp_path / "results")
    return s


def make_client(settings: Settings, fake: FakeOllama) -> TestClient:
    return TestClient(create_app(settings, gateway=LLMGateway(settings, client=fake)))


@pytest.fixture
def client(settings: Settings) -> Iterator[TestClient]:
    with make_client(settings, FakeOllama()) as c:
        yield c
