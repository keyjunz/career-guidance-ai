"""
Embedding Model module — Load, encode, cache embeddings.
Hỗ trợ: multilingual-e5-small, all-MiniLM-L6-v2, bge-m3
"""

import os
import time
import pickle
import hashlib
import numpy as np
from pathlib import Path
from typing import List, Union, Optional

import torch
from sentence_transformers import SentenceTransformer

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    EMBEDDING_MODELS, DEFAULT_EMBEDDING, DEVICE, CACHE_DIR
)


class EmbeddingModel:
    """Wrapper cho Sentence-Transformer embedding models với caching."""

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

        print(f"[Embedding] Loading {self.model_name} on {self.device}...")
        self.model = SentenceTransformer(self.model_name, device=self.device)
        self.model.max_seq_length = self.model_config["max_seq_length"]
        print(f"[Embedding] Loaded. Dim={self.dim}, MaxSeqLen={self.model.max_seq_length}")

    # ── Encode ───────────────────────────────────────────────────────
    def encode(
        self,
        texts: Union[str, List[str]],
        is_query: bool = True,
        batch_size: int = 64,
        show_progress: bool = False,
        use_cache: bool = True,
    ) -> np.ndarray:
        """
        Encode texts thành embedding vectors.

        Args:
            texts: Một hoặc nhiều đoạn text
            is_query: True → thêm prefix query, False → prefix passage
            batch_size: Kích thước batch cho encode
            show_progress: Hiện progress bar
            use_cache: Sử dụng cache hay không

        Returns:
            np.ndarray shape (n, dim)
        """
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
                # Lưu vào cache
                for text, emb in zip(to_encode, new_embeddings):
                    self._cache[self._hash(text)] = emb
                self._save_cache()

                # Ghép kết quả
                all_embeddings = np.zeros((len(prefixed_texts), self.dim), dtype=np.float32)
                cache_idx = 0
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
        """Encode single query → vector 1D."""
        return self.encode(query, is_query=True, use_cache=use_cache)

    def encode_passages(
        self, passages: List[str], batch_size: int = 64, show_progress: bool = True
    ) -> np.ndarray:
        """Encode danh sách passages → matrix (n, dim)."""
        return self.encode(
            passages, is_query=False, batch_size=batch_size, show_progress=show_progress
        )

    # ── Benchmark ────────────────────────────────────────────────────
    def benchmark_latency(self, text: str = "What is a neural network?", n_runs: int = 50):
        """Đo latency trung bình encode 1 query."""
        # Warm-up
        for _ in range(5):
            self.encode(text, use_cache=False)

        latencies = []
        for _ in range(n_runs):
            start = time.perf_counter()
            self.encode(text, use_cache=False)
            latencies.append((time.perf_counter() - start) * 1000)

        avg = np.mean(latencies)
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        p99 = np.percentile(latencies, 99)
        print(f"[Benchmark] {self.model_name}")
        print(f"  Avg: {avg:.1f}ms | P50: {p50:.1f}ms | P95: {p95:.1f}ms | P99: {p99:.1f}ms")
        return {"avg": avg, "p50": p50, "p95": p95, "p99": p99}

    # ── Cache helpers ────────────────────────────────────────────────
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
            print(f"[Embedding] Loaded cache: {len(cache)} entries")
            return cache
        return {}

    def _save_cache(self):
        with open(self.cache_file, "wb") as f:
            pickle.dump(self._cache, f)

    def clear_cache(self):
        self._cache = {}
        if self.cache_file.exists():
            self.cache_file.unlink()
        print("[Embedding] Cache cleared.")

    def get_memory_usage_mb(self) -> float:
        """Ước tính RAM/VRAM sử dụng."""
        param_size = sum(p.numel() * p.element_size() for p in self.model[0].auto_model.parameters())
        return param_size / (1024 ** 2)


if __name__ == "__main__":
    print("=" * 50)
    print(" EMBEDDING MODEL TEST ")
    print("=" * 50)

    model = EmbeddingModel()
    print(f"\nModel memory: ~{model.get_memory_usage_mb():.1f} MB")

    # Test encode
    query = "What is a transformer in deep learning?"
    vec = model.encode_query(query)
    print(f"\nQuery: {query}")
    print(f"Vector shape: {vec.shape}")
    print(f"Vector norm: {np.linalg.norm(vec):.4f}")

    # Test batch
    passages = [
        "A transformer is a deep learning architecture based on self-attention.",
        "Neural networks are computing systems inspired by biological neural networks.",
        "Python is a high-level programming language.",
    ]
    vecs = model.encode_passages(passages, show_progress=False)
    print(f"\nPassage vectors shape: {vecs.shape}")

    # Similarity
    sims = vecs @ vec
    print("\nSimilarities:")
    for p, s in zip(passages, sims):
        print(f"  {s:.4f} | {p[:60]}...")

    # Benchmark
    print()
    model.benchmark_latency()
