"""Temp-file sentinel: counts every file this process opens for writing while an upload or ingest runs.

Implemented as a CPython audit hook (like the egress guard), so it sees writes made by any library, including
`tempfile`, which Windows uses silently under %TEMP%. While a `watch()` block is open the count is global, so it
can over-count when other work runs at the same time. It never under-counts.
"""

from __future__ import annotations

import os
import sys
import threading
from collections.abc import Iterator
from contextlib import contextmanager

_lock = threading.Lock()
_installed = False
_active = 0
_writes = 0
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND


def _hook(event: str, args: tuple) -> None:
    global _writes
    if event != "open" or _active == 0 or len(args) < 3:
        return
    _path, mode, flags = args[0], args[1], args[2]
    writing = (isinstance(mode, str) and any(c in mode for c in "wax+")) or (
        isinstance(flags, int) and bool(flags & _WRITE_FLAGS)
    )
    if writing:
        with _lock:
            _writes += 1


def install() -> None:
    global _installed
    with _lock:
        if not _installed:
            sys.addaudithook(_hook)
            _installed = True


@contextmanager
def watch() -> Iterator[None]:
    global _active
    with _lock:
        _active += 1
    try:
        yield
    finally:
        with _lock:
            _active -= 1


def count() -> int:
    with _lock:
        return _writes
