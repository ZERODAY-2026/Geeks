"""Egress guard: refuses any non-loopback network connection or DNS lookup made by this process.

Implemented as a CPython audit hook, so it sees every socket operation made from Python regardless of
which library made it. Hooks cannot be removed once installed, which is intended. Events record the
target host name only, never any content.
"""

from __future__ import annotations

import ipaddress
import sys
import threading
from collections import deque
from datetime import UTC, datetime
from typing import Any

ALLOWED_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})


class EgressBlocked(RuntimeError):
    """Raised when code in this process tries to reach a non-loopback host."""


_lock = threading.Lock()
_installed = False
_blocked = 0
_events: deque[dict[str, Any]] = deque(maxlen=200)


def _is_loopback(host: str) -> bool:
    if host in ALLOWED_HOSTS:
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False  # an unresolved name is never loopback


def _hook(event: str, args: tuple) -> None:
    global _blocked
    if event == "socket.getaddrinfo":
        host: Any = args[0]
    elif event in ("socket.connect", "socket.sendto"):
        addr = args[1] if len(args) > 1 else None
        if not isinstance(addr, tuple) or not addr:
            return  # Unix sockets and similar local endpoints
        host = addr[0]
    else:
        return
    if isinstance(host, bytes):
        host = host.decode("idna", errors="replace")
    if host is None or not isinstance(host, str) or _is_loopback(host):
        return
    with _lock:
        _blocked += 1
        _events.append({"ts": datetime.now(UTC), "type": "egress_blocked", "target": host, "action": "blocked"})
    raise EgressBlocked(f"blocked non-loopback egress to {host}")


def install() -> None:
    """Install the audit hook once per process. Safe to call repeatedly."""
    global _installed
    with _lock:
        if not _installed:
            sys.addaudithook(_hook)
            _installed = True


def record(event_type: str, target: str | None, action: str) -> None:
    with _lock:
        _events.append({"ts": datetime.now(UTC), "type": event_type, "target": target, "action": action})


def status() -> dict[str, Any]:
    with _lock:
        return {"active": _installed, "allowed_hosts": sorted(ALLOWED_HOSTS), "blocked_attempts": _blocked}


def events() -> list[dict[str, Any]]:
    with _lock:
        return list(_events)
