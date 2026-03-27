"""Embedding service — Load, encode, cache embeddings.

Wraps sentence-transformers models. Reusable across modules.
Supports: multilingual-e5-small, all-MiniLM-L6-v2, bge-m3
"""

from __future__ import annotations

import hashlib
import logging
import pickle
from pathlib import Path
from typing import List, Union

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

# ─── Model registry ────────────────────────────────────────────
EMBEDDING_MODELS = {
    "multilingual-e5-small": {
        "name": "intfloat/multilingual-e5-small",
        "dim": 384,
        "max_seq_length": 512,
        "prefix_query": "query: ",
        "prefix_passage": "passage: ",
    },
    "all-MiniLM-L6-v2": {
        "name": "sentence-transformers/all-MiniLM-L6-v2",
        "dim": 384,
        "max_seq_length": 256,
        "prefix_query": "",
        "prefix_passage": "",
    },
    "bge-m3": {
        "name": "BAAI/bge-m3",
        "dim": 1024,
        "max_seq_length": 8192,
        "prefix_query": "",
        "prefix_passage": "",
    },
}

DEFAULT_EMBEDDING = "multilingual-e5-small"
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
CACHE_DIR = Path(__file__).parent.parent / "_cache"
CACHE_DIR.mkdir(exist_ok=True)


class EmbeddingService:
    """Sentence-Transformer embedding service with disk caching."""

    def __init__(self, model_key: str = DEFAULT_EMBEDDING, device: str = DEVICE):
        self.model_key = model_key
        self.model_config = EMBEDDING_MODELS[model_key]
        self.model_name = self.model_config["name"]
        self.dim = self.model_config["dim"]
        self.prefix_query = self.model_config["prefix_query"]
        self.prefix_passage = self.model_config["prefix_passage"]
        self.device = device

        self.cache_file = CACHE_DIR / f"emb_cache_{model_key}.pkl"
        self._cache = self._load_cache()

        logger.info("Loading %s on %s...", self.model_name, self.device)
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.model.max_seq_length = self.model_config["max_seq_length"]
        logger.info("Loaded. Dim=%d, MaxSeqLen=%d", self.dim, self.model.max_seq_length)

    # ── Encode ───────────────────────────────────────────────────
    def encode(
        self,
        texts: Union[str, List[str]],
        is_query: bool = True,
        batch_size: int = 64,
        show_progress: bool = False,
        use_cache: bool = True,
    ) -> np.ndarray:
        """Encode texts to embedding vectors."""
        single_input = isinstance(texts, str)
        if single_input:
            texts = [texts]

        prefix = self.prefix_query if is_query else self.prefix_passage
        prefixed_texts = [prefix + t for t in texts]

        if use_cache:
            cached, to_encode, to_encode_idx = self._check_cache(prefixed_texts)
            if to_encode:
                new_embeddings = self.model.encode(
                    to_encode,
                    batch_size=batch_size,
                    show_progress_bar=show_progress,
                    convert_to_numpy=True,
                    normalize_embeddings=True,
                )
                for text, emb in zip(to_encode, new_embeddings):
                    self._cache[self._hash(text)] = emb
                self._save_cache()

                all_embeddings = np.zeros((len(prefixed_texts), self.dim), dtype=np.float32)
                encode_idx = 0
                for i in range(len(prefixed_texts)):
                    if i in to_encode_idx:
                        all_embeddings[i] = new_embeddings[encode_idx]
                        encode_idx += 1
                    else:
                        h = self._hash(prefixed_texts[i])
                        all_embeddings[i] = cached[h]
            else:
                all_embeddings = np.array(
                    [cached[self._hash(t)] for t in prefixed_texts], dtype=np.float32
                )
        else:
            all_embeddings = self.model.encode(
                prefixed_texts,
                batch_size=batch_size,
                show_progress_bar=show_progress,
                convert_to_numpy=True,
                normalize_embeddings=True,
            )

        return all_embeddings[0] if single_input else all_embeddings

    def encode_query(self, query: str, use_cache: bool = True) -> np.ndarray:
        """Encode single query → 1D vector."""
        return self.encode(query, is_query=True, use_cache=use_cache)

    def encode_passages(
        self, passages: List[str], batch_size: int = 64, show_progress: bool = True
    ) -> np.ndarray:
        """Encode list of passages → matrix (n, dim)."""
        return self.encode(
            passages, is_query=False, batch_size=batch_size, show_progress=show_progress
        )

    # ── Cache helpers ────────────────────────────────────────────
    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.md5(text.encode()).hexdigest()

    def _check_cache(self, texts: List[str]):
        cached = {}
        to_encode = []
        to_encode_idx = set()
        for i, t in enumerate(texts):
            h = self._hash(t)
            if h in self._cache:
                cached[h] = self._cache[h]
            else:
                to_encode.append(t)
                to_encode_idx.add(i)
        return cached, to_encode, to_encode_idx

    def _load_cache(self) -> dict:
        if self.cache_file.exists():
            with open(self.cache_file, "rb") as f:
                cache = pickle.load(f)
            logger.info("Loaded embedding cache: %d entries", len(cache))
            return cache
        return {}

    def _save_cache(self):
        with open(self.cache_file, "wb") as f:
            pickle.dump(self._cache, f)

    def clear_cache(self):
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        logger.info("Embedding cache cleared.")

    def get_memory_usage_mb(self) -> float:
        param_size = sum(
            p.numel() * p.element_size()
            for p in self.model[0].auto_model.parameters()
        )
        return param_size / (1024 ** 2)
