"""Per-quote relevance check: does one verified quote address one question? Used by the checklist and by Ask.

A quote can be real and still be about something else. The check runs after verification, one quote at a time.
If the check cannot run, the quote is not kept: a missing answer is safer than an unsupported one.
"""

from __future__ import annotations

from pydantic import BaseModel

from ..llm.gateway import LLMError, LLMGateway
from ..llm.prompts import relevance as prompts


class RelevanceOut(BaseModel):
    addresses_topic: bool


async def addresses(gw: LLMGateway, title: str, question: str, quote: str) -> bool:
    user = prompts.USER.replace("{TOPIC}", title).replace("{HYPOTHESIS}", question).replace("{QUOTE}", quote)
    try:
        res = await gw.structured(RelevanceOut, user, system=prompts.SYSTEM)
    except LLMError:
        return False
    return res.value.addresses_topic
