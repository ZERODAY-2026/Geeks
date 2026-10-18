"""System endpoints: health, runtime facts, benchmark results."""

from __future__ import annotations

import json
import shutil
import subprocess
from typing import Annotated

from fastapi import APIRouter, Depends

from ... import __version__
from ...llm.gateway import LLMGateway, ModelUnavailable
from ...models import BenchmarkResult, Health, ModelInfo, StatuteIndexInfo, SystemInfo
from ...settings import Settings
from ..deps import get_gateway, get_settings_dep
from ..errors import LexiError, problem_responses

router = APIRouter(tags=["system"])

Gw = Annotated[LLMGateway, Depends(get_gateway)]
Cfg = Annotated[Settings, Depends(get_settings_dep)]


def _match(installed: list[dict], name: str) -> dict | None:
    """Ollama reports 'gemma4:e2b-it-qat'; a bare 'embeddinggemma' means ':latest'."""
    want = name if ":" in name else f"{name}:latest"
    return next((m for m in installed if m["name"] == want), None)


@router.get("/health", response_model=Health)
async def health(gw: Gw, cfg: Cfg) -> Health:
    required = [gw.chat_model, gw.embed_model]
    try:
        installed = await gw.list_models()
    except ModelUnavailable:
        return Health(status="ok", ollama="down", models_ready=False, missing_models=required, version=__version__)
    missing = [m for m in required if _match(installed, m) is None]
    return Health(status="ok", ollama="up", models_ready=not missing, missing_models=missing, version=__version__)


def _gpu_name() -> str | None:
    if shutil.which("nvidia-smi") is None:
        return None
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return out.stdout.strip().splitlines()[0] if out.stdout.strip() else None
    except (subprocess.SubprocessError, OSError):
        return None


def _model_info(m: dict | None, name: str, num_ctx: int) -> ModelInfo:
    if m is None:
        return ModelInfo(name=name, num_ctx=num_ctx)
    return ModelInfo(
        name=name,
        digest=m.get("digest"),
        family=m.get("family"),
        parameter_size=m.get("parameter_size"),
        quantization=m.get("quantization"),
        size_bytes=m.get("size"),
        num_ctx=num_ctx,
    )


@router.get("/system/info", response_model=SystemInfo, responses=problem_responses(503))
async def system_info(gw: Gw, cfg: Cfg) -> SystemInfo:
    installed = await gw.list_models()  # raises ModelUnavailable -> 503
    prof = cfg.models.active
    packs_dir = cfg.paths.resolve("packs_dir")
    packs = sorted(p.stem for p in packs_dir.glob("*.yaml")) if packs_dir.exists() else []
    statute_db = cfg.paths.statute_db
    return SystemInfo(
        app_version=__version__,
        profile=cfg.models.profile,
        model=_model_info(_match(installed, prof.chat), prof.chat, prof.num_ctx),
        alt_model=prof.alt,
        embed_model=_model_info(_match(installed, prof.embed), prof.embed, 2048),
        ollama_version=await gw.ollama_version(),
        ollama_host=cfg.ollama.host,
        gpu=_gpu_name(),
        packs=packs,
        statute_index=StatuteIndexInfo(
            available=statute_db.exists(), snapshot="v2026.08" if statute_db.exists() else None
        ),
        agent_mode=cfg.agent.mode,
    )


@router.get("/system/benchmark", response_model=list[BenchmarkResult], responses=problem_responses(404))
async def benchmark(cfg: Cfg) -> list[BenchmarkResult]:
    files = sorted(cfg.paths.resolve("results_dir").glob("bench_*.json"))
    if not files:
        raise LexiError(404, "NO_BENCHMARK", "No benchmark results", "Run scripts/bench.py first.")
    return [BenchmarkResult.model_validate(json.loads(f.read_text())) for f in files]
