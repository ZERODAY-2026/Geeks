"""Offline guarantees: nothing in the running app may reach the internet. No model needed.

The project runs with no network. These tests check the places that could silently go online: the reading grade
(textstat would download NLTK data), the /docs page (Swagger UI loads from a CDN), outbound URLs in the source,
and the egress guard that blocks any non-loopback connection at runtime.
"""

from __future__ import annotations

import re
import socket
from pathlib import Path

import nltk
import pytest

from lexishield.agents import cards
from lexishield.trust.egress_guard import EgressBlocked

pytestmark = pytest.mark.phase3

SRC = Path(__file__).resolve().parents[1] / "src" / "lexishield"
URL_RE = re.compile(r"https?://([^/\s\"')]+)")
ALLOWED_HOSTS = {"127.0.0.1", "localhost", "lexishield.local"}  # loopback, and the error-type namespace


def test_the_reading_grade_never_downloads(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def no_download(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("nltk.download was called at runtime")

    def missing(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise LookupError("cmudict")

    monkeypatch.setattr(nltk, "download", no_download)
    monkeypatch.setattr(nltk.data, "find", missing)
    assert cards.reading_grade("You pay a deposit of Rs. 1,50,000 before moving in.") is None


def test_the_docs_page_is_off_by_default(client) -> None:  # type: ignore[no-untyped-def]
    assert client.get("/docs").status_code == 404  # it would load Swagger UI from a CDN
    assert client.get("/api/v1/openapi.json").status_code == 200  # the contract itself is local


def test_the_source_has_no_outbound_urls() -> None:
    found = []
    for path in SRC.rglob("*.py"):
        for host in URL_RE.findall(path.read_text(encoding="utf-8")):
            if host.split(":")[0] not in ALLOWED_HOSTS:
                found.append(f"{path.relative_to(SRC)}: {host}")
    assert not found, found


def test_the_running_app_blocks_any_internet_connection(client) -> None:  # type: ignore[no-untyped-def]
    # create_app installed the egress guard; any non-loopback connection or lookup is refused in-process
    with pytest.raises(EgressBlocked):
        socket.getaddrinfo("huggingface.co", 443)
