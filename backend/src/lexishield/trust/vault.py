"""Sealed in-memory vault: each document is encrypted with its own AES-256-GCM key.

Deleting a document (or letting it expire) destroys its key and ciphertext together. Without the key the
ciphertext is unrecoverable, which is the crypto-shredding guarantee. Nothing here is written to disk.
"""

from __future__ import annotations

import os
import threading
import time

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import egress_guard

NONCE_BYTES = 12


class Vault:
    def __init__(self, ttl_s: int) -> None:
        self._ttl = ttl_s
        self._keys: dict[str, bytes] = {}
        self._blobs: dict[str, bytes] = {}
        self._touched: dict[str, float] = {}
        self._lock = threading.Lock()

    def put(self, doc_id: str, plaintext: bytes) -> None:
        key = AESGCM.generate_key(bit_length=256)
        nonce = os.urandom(NONCE_BYTES)
        blob = nonce + AESGCM(key).encrypt(nonce, plaintext, doc_id.encode())
        with self._lock:
            self._keys[doc_id] = key
            self._blobs[doc_id] = blob
            self._touched[doc_id] = time.monotonic()

    def get(self, doc_id: str) -> bytes | None:
        with self._lock:
            self._expire_locked()
            if doc_id not in self._keys:
                return None
            self._touched[doc_id] = time.monotonic()
            key, blob = self._keys[doc_id], self._blobs[doc_id]
        nonce, ct = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        return AESGCM(key).decrypt(nonce, ct, doc_id.encode())

    def delete(self, doc_id: str) -> bool:
        with self._lock:
            return self._drop_locked(doc_id)

    def wipe(self) -> int:
        with self._lock:
            ids = list(self._keys)
            for doc_id in ids:
                self._drop_locked(doc_id)
            return len(ids)

    def ids(self) -> list[str]:
        """Every stored id (documents, files, reports, job events)."""
        with self._lock:
            self._expire_locked()
            return list(self._keys)

    def __len__(self) -> int:
        with self._lock:
            return len(self._keys)

    def _drop_locked(self, doc_id: str) -> bool:
        existed = doc_id in self._keys
        self._keys.pop(doc_id, None)  # destroying the key is the shred
        self._blobs.pop(doc_id, None)
        self._touched.pop(doc_id, None)
        return existed

    def _expire_locked(self) -> None:
        now = time.monotonic()
        for doc_id in [d for d, t in self._touched.items() if now - t > self._ttl]:
            self._drop_locked(doc_id)
            egress_guard.record("document_shredded", None, "expired_crypto_shred")
