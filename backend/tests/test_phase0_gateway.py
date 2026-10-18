"""Phase 0 gate: LLM gateway behaviour (fake client) + a live check against the real model."""

from __future__ import annotations

import asyncio
import json

import pytest
from pydantic import BaseModel, Field

from conftest import FakeOllama
from lexishield.llm.gateway import LLMGateway, ModelOutputInvalid, ModelTimeout, ModelUnavailable
from lexishield.settings import Settings

pytestmark = pytest.mark.phase0


class Out(BaseModel):
    status: str = Field(pattern="^(ENTAILED|NOT_MENTIONED)$")
    quote: str


GOOD = json.dumps({"status": "ENTAILED", "quote": "security deposit of Rs. 1,50,000"})


async def test_structured_valid_first_try(settings) -> None:
    fake = FakeOllama([GOOD])
    r = await LLMGateway(settings, client=fake).structured(Out, "q", system="s")
    assert r.value.status == "ENTAILED" and r.stats.attempts == 1 and not r.stats.repaired
    call = fake.calls[0]
    assert call["format"] == Out.model_json_schema()  # schema-enforced decoding
    assert call["options"]["temperature"] == 0 and call["options"]["seed"] == 42
    assert call["think"] is False  # Gemma 4 thinking disabled by default (P0 benchmark finding)
    assert call["messages"][0] == {"role": "system", "content": "s"}
    assert r.stats.gen_tps == pytest.approx(40.0)


async def test_structured_repairs_once(settings) -> None:
    fake = FakeOllama(['{"status": "MAYBE", "quote": "x"}', GOOD])
    r = await LLMGateway(settings, client=fake).structured(Out, "q")
    assert r.value.status == "ENTAILED" and r.stats.repaired and r.stats.attempts == 2
    repair_msg = fake.calls[1]["messages"][-1]["content"]
    assert "did not match the required JSON schema" in repair_msg


async def test_structured_gives_up_after_one_repair(settings) -> None:
    fake = FakeOllama(["not json", '{"status": "nope"}', GOOD])
    with pytest.raises(ModelOutputInvalid):
        await LLMGateway(settings, client=fake).structured(Out, "q")
    assert len(fake.calls) == 2


async def test_unavailable_and_timeout(settings) -> None:
    with pytest.raises(ModelUnavailable):
        await LLMGateway(settings, client=FakeOllama(down=True)).structured(Out, "q")
    settings.models.options.timeout_s = 0.05
    with pytest.raises(ModelTimeout):
        await LLMGateway(settings, client=FakeOllama([GOOD], delay=0.5)).structured(Out, "q")


async def test_semaphore_limits_parallel_calls(settings) -> None:
    settings.models.options.max_parallel = 1
    fake = FakeOllama([GOOD] * 3, delay=0.05)
    gw = LLMGateway(settings, client=fake)
    loop = asyncio.get_running_loop()
    t0 = loop.time()
    await asyncio.gather(*(gw.structured(Out, "q") for _ in range(3)))
    assert loop.time() - t0 >= 0.14  # serialized, not concurrent


async def test_list_models_normalizes(settings) -> None:
    models = await LLMGateway(settings, client=FakeOllama()).list_models()
    assert models[0] == {
        "name": "gemma4:e4b-it-qat",
        "digest": "sha256:aaa",
        "size": 6_100_000_000,
        "family": "gemma4",
        "parameter_size": "8B",
        "quantization": "Q4_0",
    }


# ---------------------------------------------------------------- live (real Ollama + Gemma)


@pytest.mark.live
def test_live_structured_calls_are_schema_valid() -> None:
    """Gate: >= 9/10 schema-valid structured calls at temperature 0 on the real model.

    One event loop for the whole test: the Ollama async client is bound to the loop it was created in.
    """
    from bench import SYSTEM, USER, BenchOut

    async def run() -> int:
        gw = LLMGateway(Settings())
        try:
            installed = {m["name"] for m in await gw.list_models()}
        except ModelUnavailable:
            pytest.skip("Ollama is not running")
        if gw.chat_model not in installed:
            pytest.skip(f"{gw.chat_model} is not pulled")
        ok = 0
        for i in range(10):
            try:
                r = await gw.structured(BenchOut, USER, system=SYSTEM, seed=100 + i)
                ok += r.value.status.value in {"ENTAILED", "CONTRADICTED", "NOT_MENTIONED", "UNCLEAR"}
            except ModelOutputInvalid:
                pass
        return ok

    assert asyncio.run(run()) >= 9
