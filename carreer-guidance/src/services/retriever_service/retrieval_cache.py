"""In-memory LRU + TTL cache for hybrid retrieval results (cross-query reuse)."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import time
from collections import OrderedDict
from typing import Any

DEFAULT_MAX_ENTRIES = 100
DEFAULT_TTL_SEC = 3600


def _normalize_query(query: str) -> str:
    return " ".join(str(query or "").strip().lower().split())


def make_retrieval_cache_key(
    *,
    query: str,
    top_k: int,
    dense_k: int,
    sparse_k: int,
    where: dict[str, Any] | None,
) -> str:
    where_blob = json.dumps(where or {}, sort_keys=True, ensure_ascii=False)
    raw = f"{_normalize_query(query)}|{top_k}|{dense_k}|{sparse_k}|{where_blob}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class HybridRetrievalCache:
    """Process-wide hybrid retrieval cache (shared corpus; safe across users)."""

    _instance: HybridRetrievalCache | None = None

    def __init__(self, *, max_entries: int, ttl_sec: float) -> None:
        self._max_entries = max(1, int(max_entries))
        self._ttl_sec = float(ttl_sec)
        self._store: OrderedDict[str, tuple[float, list[dict[str, Any]]]] = OrderedDict()

    @classmethod
    def get_instance(cls) -> HybridRetrievalCache:
        if cls._instance is None:
            max_entries = int(
                os.getenv("RETRIEVAL_CACHE_MAX_ENTRIES", str(DEFAULT_MAX_ENTRIES))
            )
            ttl = float(os.getenv("RETRIEVAL_CACHE_TTL_SEC", str(DEFAULT_TTL_SEC)))
            cls._instance = cls(max_entries=max_entries, ttl_sec=ttl)
        return cls._instance

    @classmethod
    def reset_for_tests(cls) -> None:
        cls._instance = None

    def get(self, key: str) -> list[dict[str, Any]] | None:
        now = time.monotonic()
        item = self._store.get(key)
        if not item:
            return None
        expires_at, docs = item
        if expires_at <= now:
            self._store.pop(key, None)
            return None
        self._store.move_to_end(key)
        return copy.deepcopy(docs)

    def set(self, key: str, docs: list[dict[str, Any]]) -> None:
        now = time.monotonic()
        expires_at = now + self._ttl_sec
        self._store[key] = (expires_at, copy.deepcopy(docs))
        self._store.move_to_end(key)
        while len(self._store) > self._max_entries:
            self._store.popitem(last=False)
