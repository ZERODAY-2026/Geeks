"""Typed settings: config/lexishield.yaml, overridden by LEXISHIELD_* environment variables."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = BACKEND_DIR / "config" / "lexishield.yaml"


class ServerSettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173"])
    max_upload_mb: int = 20
    # FastAPI's /docs page loads Swagger UI from a CDN, which fails offline. Off by default;
    # contracts/openapi.json is the local reference.
    api_docs: bool = False


class OllamaSettings(BaseModel):
    host: str = "http://127.0.0.1:11434"
    keep_alive: str = "30m"


class ModelProfile(BaseModel):
    chat: str
    alt: str | None = None
    embed: str = "embeddinggemma:300m"
    num_ctx: int = 8192


class ModelOptions(BaseModel):
    temperature: float = 0.0
    seed: int = 42
    timeout_s: float = 120.0
    max_parallel: int = 2
    # Gemma 4 'thinking' triples latency on CPU with no measured accuracy gain; None = don't send the flag.
    think: bool | None = False


class ModelSettings(BaseModel):
    profile: Literal["gpu", "cpu"] = "gpu"
    gpu: ModelProfile = ModelProfile(chat="gemma4:e4b-it-qat", alt="gemma3n:e4b")
    cpu: ModelProfile = ModelProfile(chat="gemma4:e2b-it-qat", alt="gemma3n:e2b")
    options: ModelOptions = ModelOptions()

    @property
    def active(self) -> ModelProfile:
        return self.gpu if self.profile == "gpu" else self.cpu


class AgentSettings(BaseModel):
    # Only the pipeline is built. "tools" (a bounded tool-calling agent) is on the plan's cut list.
    mode: Literal["tools", "pipeline"] = "pipeline"
    max_tool_calls: int = 3


class VerifySettings(BaseModel):
    fuzzy_min: int = 92
    retrieval_k: int = 6
    # Grounding gate: a quote supports a topic only if it uses the topic's own terms (see agents/checklist.py).
    relevance_gate: bool = True


class PrivacySettings(BaseModel):
    egress_allow: list[str] = Field(default_factory=lambda: ["127.0.0.1", "::1", "localhost"])
    session_ttl_s: int = 1800
    receipts: bool = True


class FeatureFlags(BaseModel):
    statutes: bool = True
    scenarios: bool = True
    docx: bool = True
    ocr: bool = False


class PathSettings(BaseModel):
    packs_dir: str = "packs"
    scenarios_dir: str = "scenarios"
    escalation_dir: str = "escalation"
    results_dir: str = "eval/results"
    data_dir: str = "data"  # set-up-time downloads (CUAD, statute index); git-ignored

    @property
    def statute_db(self) -> Path:
        return self.resolve("data_dir") / "statutes.sqlite"

    def resolve(self, name: str) -> Path:
        p = Path(getattr(self, name))
        return p if p.is_absolute() else BACKEND_DIR / p


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="LEXISHIELD_", env_nested_delimiter="__", extra="ignore")

    server: ServerSettings = ServerSettings()
    ollama: OllamaSettings = OllamaSettings()
    models: ModelSettings = ModelSettings()
    agent: AgentSettings = AgentSettings()
    verify: VerifySettings = VerifySettings()
    privacy: PrivacySettings = PrivacySettings()
    features: FeatureFlags = FeatureFlags()
    paths: PathSettings = PathSettings()

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        config_file = Path(os.environ.get("LEXISHIELD_CONFIG", DEFAULT_CONFIG))
        yaml_source = YamlConfigSettingsSource(settings_cls, yaml_file=config_file)
        # Priority: explicit init kwargs > environment > YAML file > defaults.
        return (init_settings, env_settings, yaml_source)


@lru_cache
def get_settings() -> Settings:
    return Settings()
