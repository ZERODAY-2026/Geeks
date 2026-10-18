"""Checklist packs and escalation routes: YAML data, validated on load. Adding a document type means adding a file."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from .models import Country, DocType, Severity
from .settings import Settings, get_settings
from .verify.severity import SeverityRule

# Every topic id in a pack starts with the pack's own prefix, so a report can say which pack a topic came from.
TOPIC_PREFIX = {
    "in_rental": "in_rental.",
    "in_employment": "in_employment.",
    "msa_generic": "msa.",
    "notice_generic": "notice.",
}
DOC_TYPE_PACK = {
    "rental": "in_rental",
    "employment": "in_employment",
    "msa": "msa_generic",
    "legal_notice": "notice_generic",
}


class Topic(BaseModel):
    id: str = Field(pattern=r"^[a-z_]+\.[a-z_]+$")
    title: str
    query: str = Field(min_length=3)
    lexicon: list[str] = Field(min_length=1)
    hypothesis: str = Field(min_length=10)
    severity: Severity
    silence_note: str | None = None
    escalation_ref: str | None = None
    jurisdiction_sensitive: bool = False
    severity_rules: list[SeverityRule] = Field(default_factory=list)


class Pack(BaseModel):
    pack_id: str = Field(pattern=r"^[a-z_]+$")
    doc_type: DocType
    jurisdiction: Country
    version: str
    depth: Literal["deep", "standard"]
    topics: list[Topic] = Field(min_length=1)

    @field_validator("topics")
    @classmethod
    def _unique_ids(cls, topics: list[Topic]) -> list[Topic]:
        ids = [t.id for t in topics]
        if len(ids) != len(set(ids)):
            raise ValueError("topic ids must be unique")
        return topics

    @model_validator(mode="after")
    def _prefixes(self) -> Pack:
        prefix = TOPIC_PREFIX.get(self.pack_id)
        if prefix is None:
            raise ValueError(f"unknown pack id {self.pack_id!r}")
        wrong = [t.id for t in self.topics if not t.id.startswith(prefix)]
        if wrong:
            raise ValueError(f"topic ids must start with {prefix!r}: {wrong}")
        return self


class EscalationRoute(BaseModel):
    who: str
    why: str
    free_help: str | None = None
    urgency: Literal["normal", "urgent"] = "normal"
    jurisdiction_note: str | None = None


@lru_cache
def load_packs(directory: str) -> dict[str, Pack]:
    packs: dict[str, Pack] = {}
    for path in sorted(Path(directory).glob("*.yaml")):
        pack = Pack.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        if pack.pack_id != path.stem:
            raise ValueError(f"{path.name}: pack_id must match the file name")
        packs[pack.pack_id] = pack
    return packs


@lru_cache
def load_routes(directory: str) -> dict[str, EscalationRoute]:
    raw = yaml.safe_load((Path(directory) / "routes.yaml").read_text(encoding="utf-8")) or {}
    return {k: EscalationRoute.model_validate(v) for k, v in raw.items()}


def all_packs(settings: Settings | None = None) -> dict[str, Pack]:
    return load_packs(str((settings or get_settings()).paths.resolve("packs_dir")))


def pack_for(doc_type: DocType, settings: Settings | None = None) -> Pack | None:
    """The pack that checks a document type. Documents from any country use the same pack; their cards carry
    jurisdiction flags when the country is not India."""
    key = DOC_TYPE_PACK.get(doc_type.value)
    return all_packs(settings).get(key) if key else None


def routes(settings: Settings | None = None) -> dict[str, EscalationRoute]:
    return load_routes(str((settings or get_settings()).paths.resolve("escalation_dir")))
