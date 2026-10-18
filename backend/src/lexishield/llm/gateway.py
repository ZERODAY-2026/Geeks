"""The only module that talks to the model runtime (Ollama on loopback).

Every structured call is schema-enforced (Ollama `format` = JSON Schema), validated
with Pydantic, and retried at most once with a repair instruction. If the output is
still invalid we raise; callers degrade to UNCLEAR and never invent content.
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from ..settings import Settings

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    code = "MODEL_ERROR"


class ModelUnavailable(LLMError):
    code = "MODEL_UNAVAILABLE"


class ModelTimeout(LLMError):
    code = "MODEL_TIMEOUT"


class ModelOutputInvalid(LLMError):
    code = "MODEL_OUTPUT_INVALID"


class ChatClient(Protocol):
    """Subset of `ollama.AsyncClient` we depend on (lets tests inject a fake)."""

    async def chat(self, **kwargs: Any) -> Any: ...
    async def embed(self, **kwargs: Any) -> Any: ...
    async def list(self) -> Any: ...


@dataclass
class CallStats:
    model: str
    attempts: int = 0
    prompt_tokens: int = 0
    gen_tokens: int = 0
    prompt_s: float = 0.0
    gen_s: float = 0.0
    load_s: float = 0.0
    wall_s: float = 0.0
    repaired: bool = False

    @property
    def gen_tps(self) -> float | None:
        return self.gen_tokens / self.gen_s if self.gen_s > 0 else None

    @property
    def prompt_tps(self) -> float | None:
        return self.prompt_tokens / self.prompt_s if self.prompt_s > 0 else None


@dataclass
class StructuredResult[M: BaseModel]:
    value: M
    stats: CallStats
    raw: str = field(repr=False, default="")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """ollama returns pydantic objects (subscriptable); fakes may return dicts."""
    try:
        return obj[key]
    except (KeyError, TypeError, IndexError):
        return getattr(obj, key, default)


class LLMGateway:
    def __init__(self, settings: Settings, client: ChatClient | None = None) -> None:
        self.settings = settings
        opts = settings.models.options
        if client is None:
            from ollama import AsyncClient  # imported lazily so tests never need a server

            client = AsyncClient(host=settings.ollama.host, timeout=opts.timeout_s)
        self._client = client
        self._sem = asyncio.Semaphore(opts.max_parallel)

    # ------------------------------------------------------------ properties

    @property
    def chat_model(self) -> str:
        return self.settings.models.active.chat

    @property
    def embed_model(self) -> str:
        return self.settings.models.active.embed

    def _options(self, **overrides: Any) -> dict[str, Any]:
        o = self.settings.models.options
        base = {"temperature": o.temperature, "seed": o.seed, "num_ctx": self.settings.models.active.num_ctx}
        base.update(overrides)
        return base

    # ------------------------------------------------------------ calls

    async def _chat(self, model: str, messages: list[dict], fmt: dict | None, options: dict) -> Any:
        timeout = self.settings.models.options.timeout_s
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "options": options,
            "keep_alive": self.settings.ollama.keep_alive,
            "stream": False,
        }
        if fmt is not None:
            kwargs["format"] = fmt
        if self.settings.models.options.think is not None:
            kwargs["think"] = self.settings.models.options.think
        try:
            async with self._sem:
                return await asyncio.wait_for(self._client.chat(**kwargs), timeout=timeout)
        except TimeoutError as e:
            raise ModelTimeout(f"model call exceeded {timeout:.0f}s") from e
        except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError) as e:
            raise ModelUnavailable(f"cannot reach Ollama at {self.settings.ollama.host}") from e
        except Exception as e:  # ollama.ResponseError (e.g. model not pulled) and friends
            if type(e).__name__ == "ResponseError":
                raise ModelUnavailable(str(e)) from e
            raise

    @staticmethod
    def _accumulate(stats: CallStats, resp: Any) -> None:
        stats.prompt_tokens += int(_get(resp, "prompt_eval_count", 0) or 0)
        stats.gen_tokens += int(_get(resp, "eval_count", 0) or 0)
        stats.prompt_s += (_get(resp, "prompt_eval_duration", 0) or 0) / 1e9
        stats.gen_s += (_get(resp, "eval_duration", 0) or 0) / 1e9
        stats.load_s += (_get(resp, "load_duration", 0) or 0) / 1e9

    async def structured(
        self,
        schema: type[T],
        user: str,
        system: str | None = None,
        model: str | None = None,
        **option_overrides: Any,
    ) -> StructuredResult[T]:
        """Run one schema-enforced chat call and return a validated model instance."""
        model = model or self.chat_model
        json_schema = schema.model_json_schema()
        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": user})
        stats = CallStats(model=model)
        t0 = time.perf_counter()
        last_err: str = ""
        content = ""
        for attempt in range(2):
            stats.attempts = attempt + 1
            resp = await self._chat(model, messages, json_schema, self._options(**option_overrides))
            self._accumulate(stats, resp)
            content = _get(_get(resp, "message", {}), "content", "") or ""
            try:
                value = schema.model_validate_json(content)
                stats.wall_s = time.perf_counter() - t0
                stats.repaired = attempt > 0
                return StructuredResult(value=value, stats=stats, raw=content)
            except ValidationError as e:
                last_err = _short_errors(e)
                messages += [
                    {"role": "assistant", "content": content},
                    {
                        "role": "user",
                        "content": "Your previous reply did not match the required JSON schema: "
                        f"{last_err}. Reply again with ONLY a JSON object that matches the schema.",
                    },
                ]
        stats.wall_s = time.perf_counter() - t0
        raise ModelOutputInvalid(f"schema validation failed after repair: {last_err}")

    async def embed(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model = model or self.embed_model
        try:
            async with self._sem:
                resp = await asyncio.wait_for(
                    self._client.embed(model=model, input=texts, keep_alive=self.settings.ollama.keep_alive),
                    timeout=self.settings.models.options.timeout_s,
                )
        except TimeoutError as e:
            raise ModelTimeout("embedding call timed out") from e
        except (httpx.ConnectError, httpx.ConnectTimeout, ConnectionError) as e:
            raise ModelUnavailable(f"cannot reach Ollama at {self.settings.ollama.host}") from e
        except Exception as e:  # ollama.ResponseError, e.g. the embedding model is not pulled
            if type(e).__name__ == "ResponseError":
                raise ModelUnavailable(str(e)) from e
            raise
        return [list(v) for v in _get(resp, "embeddings", [])]

    # ------------------------------------------------------------ runtime info

    async def list_models(self) -> list[dict[str, Any]]:
        """Installed models as plain dicts: name, digest, size, details{...}."""
        try:
            resp = await asyncio.wait_for(self._client.list(), timeout=5)
        except (TimeoutError, httpx.ConnectError, httpx.ConnectTimeout, ConnectionError) as e:
            raise ModelUnavailable(f"cannot reach Ollama at {self.settings.ollama.host}") from e
        out = []
        for m in _get(resp, "models", []) or []:
            details = _get(m, "details", {}) or {}
            out.append(
                {
                    "name": _get(m, "model") or _get(m, "name"),
                    "digest": _get(m, "digest"),
                    "size": _get(m, "size"),
                    "family": _get(details, "family"),
                    "parameter_size": _get(details, "parameter_size"),
                    "quantization": _get(details, "quantization_level"),
                }
            )
        return out

    async def ollama_version(self) -> str | None:
        try:
            async with httpx.AsyncClient(base_url=self.settings.ollama.host, timeout=3) as c:
                r = await c.get("/api/version")
                return r.json().get("version")
        except (httpx.HTTPError, ValueError):
            return None


def _short_errors(e: ValidationError, limit: int = 5) -> str:
    errs = e.errors()[:limit]
    return json.dumps([{"loc": ".".join(map(str, x.get("loc", ()))), "msg": x.get("msg")} for x in errs])
