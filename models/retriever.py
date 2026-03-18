"""
Hybrid Retriever: BM25 (sparse) + FAISS (dense) + RRF fusion.
"""

import time
import json
import pickle
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import faiss
from rank_bm25 import BM25Okapi

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    RETRIEVER_TOP_K, RETRIEVER_FINAL_K,
    BM25_K1, BM25_B, RRF_K,
    INDEX_DIR, DATA_DIR, DEVICE,
)


class FAISSIndex:
    """FAISS dense vector index."""

    def __init__(self, dim: int = 384, index_type: str = "flat"):
        self.dim = dim
        if index_type == "flat":
            self.index = faiss.IndexFlatIP(dim)  # Inner product (cosine vì đã normalize)
        elif index_type == "ivf":
            quantizer = faiss.IndexFlatIP(dim)
            self.index = faiss.IndexIVFFlat(quantizer, dim, 100, faiss.METRIC_INNER_PRODUCT)
        else:
            self.index = faiss.IndexFlatIP(dim)

    def add(self, embeddings: np.ndarray):
        """Thêm embeddings vào index."""
        if embeddings.dtype != np.float32:
            embeddings = embeddings.astype(np.float32)
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        print(f"[FAISS] Added {embeddings.shape[0]} vectors. Total: {self.index.ntotal}")

    def search(self, query_vector: np.ndarray, k: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """Search top-k similar vectors."""
        if query_vector.ndim == 1:
            query_vector = query_vector.reshape(1, -1)
        if query_vector.dtype != np.float32:
            query_vector = query_vector.astype(np.float32)
        faiss.normalize_L2(query_vector)
        scores, indices = self.index.search(query_vector, k)
        return scores[0], indices[0]

    def save(self, path: str):
        faiss.write_index(self.index, str(path))
        print(f"[FAISS] Saved index to {path}")

    def load(self, path: str):
        self.index = faiss.read_index(str(path))
        print(f"[FAISS] Loaded index from {path}. Total: {self.index.ntotal}")


class BM25Index:
    """BM25 sparse retriever."""

    def __init__(self):
        self.bm25 = None
        self.corpus_tokens = None

    def build(self, corpus: List[str]):
        """Tokenize and build BM25 index."""
        self.corpus_tokens = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(self.corpus_tokens, k1=BM25_K1, b=BM25_B)
        print(f"[BM25] Built index over {len(corpus)} documents")

    def search(self, query: str, k: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        """Search top-k documents."""
        query_tokens = query.lower().split()
        scores = self.bm25.get_scores(query_tokens)
        top_indices = np.argsort(scores)[::-1][:k]
        top_scores = scores[top_indices]
        return top_scores, top_indices

    def save(self, path: str):
        with open(path, "wb") as f:
            pickle.dump({"bm25": self.bm25, "tokens": self.corpus_tokens}, f)
        print(f"[BM25] Saved to {path}")

    def load(self, path: str):
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.bm25 = data["bm25"]
        self.corpus_tokens = data["tokens"]
        print(f"[BM25] Loaded from {path}. Docs: {len(self.corpus_tokens)}")


class HybridRetriever:
    """
    Hybrid BM25 + FAISS retriever với Reciprocal Rank Fusion (RRF).
    """

    def __init__(self, dim: int = 384):
        self.dim = dim
        self.faiss_index = FAISSIndex(dim=dim)
        self.bm25_index = BM25Index()
        self.documents: List[Dict] = []
        self._built = False

    def build_index(self, documents: List[Dict], embeddings: np.ndarray):
        """
        Build cả FAISS và BM25 index.
        
        Args:
            documents: List[Dict] mỗi dict có keys: 'text', 'source', 'chunk_id', ...
            embeddings: np.ndarray shape (n, dim) — pre-computed embeddings
        """
        self.documents = documents
        texts = [doc["text"] for doc in documents]

        # Build FAISS
        self.faiss_index.add(embeddings)

        # Build BM25
        self.bm25_index.build(texts)

        self._built = True
        print(f"[HybridRetriever] Built index over {len(documents)} documents")

    def search(
        self,
        query: str,
        query_embedding: np.ndarray,
        top_k: int = RETRIEVER_FINAL_K,
        dense_k: int = RETRIEVER_TOP_K,
        sparse_k: int = RETRIEVER_TOP_K,
        alpha: float = 0.5,
        method: str = "rrf",
    ) -> List[Dict]:
        """
        Hybrid search with RRF or weighted score fusion.

        Args:
            query: Raw query text
            query_embedding: Query embedding vector
            top_k: Final number of results
            dense_k: Number of results from dense search
            sparse_k: Number of results from sparse search
            alpha: Weight for dense scores (1-alpha for sparse) in weighted method
            method: 'rrf' or 'weighted'

        Returns:
            List[Dict] with keys: text, source, score, rank, retriever
        """
        assert self._built, "Index not built yet. Call build_index() first."

        # Dense search (FAISS)
        dense_scores, dense_indices = self.faiss_index.search(query_embedding, dense_k)

        # Sparse search (BM25)
        sparse_scores, sparse_indices = self.bm25_index.search(query, sparse_k)

        if method == "rrf":
            results = self._rrf_fusion(
                dense_indices, sparse_indices, dense_scores, sparse_scores, top_k
            )
        else:
            results = self._weighted_fusion(
                dense_indices, dense_scores, sparse_indices, sparse_scores, alpha, top_k
            )

        return results

    def _rrf_fusion(
        self,
        dense_indices: np.ndarray,
        sparse_indices: np.ndarray,
        dense_scores: np.ndarray,
        sparse_scores: np.ndarray,
        top_k: int,
    ) -> List[Dict]:
        """Reciprocal Rank Fusion."""
        scores = {}

        for rank, idx in enumerate(dense_indices):
            if idx >= 0:
                scores[int(idx)] = scores.get(int(idx), 0) + 1.0 / (RRF_K + rank + 1)

        for rank, idx in enumerate(sparse_indices):
            if idx >= 0:
                scores[int(idx)] = scores.get(int(idx), 0) + 1.0 / (RRF_K + rank + 1)

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for rank, (doc_idx, score) in enumerate(sorted_items):
            doc = self.documents[doc_idx].copy()
            doc["score"] = score
            doc["rank"] = rank + 1
            doc["retriever"] = "hybrid_rrf"
            results.append(doc)

        return results

    def _weighted_fusion(
        self,
        dense_indices, dense_scores,
        sparse_indices, sparse_scores,
        alpha, top_k,
    ) -> List[Dict]:
        """Weighted score fusion."""
        # Normalize scores to [0, 1]
        if len(dense_scores) > 0 and dense_scores.max() > 0:
            dense_norm = (dense_scores - dense_scores.min()) / (dense_scores.max() - dense_scores.min() + 1e-8)
        else:
            dense_norm = dense_scores

        if len(sparse_scores) > 0 and sparse_scores.max() > 0:
            sparse_norm = (sparse_scores - sparse_scores.min()) / (sparse_scores.max() - sparse_scores.min() + 1e-8)
        else:
            sparse_norm = sparse_scores

        scores = {}
        for i, idx in enumerate(dense_indices):
            if idx >= 0:
                scores[int(idx)] = alpha * dense_norm[i]

        for i, idx in enumerate(sparse_indices):
            if idx >= 0:
                scores[int(idx)] = scores.get(int(idx), 0) + (1 - alpha) * sparse_norm[i]

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        results = []
        for rank, (doc_idx, score) in enumerate(sorted_items):
            doc = self.documents[doc_idx].copy()
            doc["score"] = float(score)
            doc["rank"] = rank + 1
            doc["retriever"] = "hybrid_weighted"
            results.append(doc)

        return results

    def dense_only_search(self, query_embedding: np.ndarray, k: int = 10) -> List[Dict]:
        """Only FAISS dense search."""
        scores, indices = self.faiss_index.search(query_embedding, k)
        results = []
        for rank, (idx, score) in enumerate(zip(indices, scores)):
            if idx >= 0:
                doc = self.documents[int(idx)].copy()
                doc["score"] = float(score)
                doc["rank"] = rank + 1
                doc["retriever"] = "dense_only"
                results.append(doc)
        return results

    def bm25_only_search(self, query: str, k: int = 10) -> List[Dict]:
        """Only BM25 sparse search."""
        scores, indices = self.bm25_index.search(query, k)
        results = []
        for rank, (idx, score) in enumerate(zip(indices, scores)):
            if idx >= 0:
                doc = self.documents[int(idx)].copy()
                doc["score"] = float(score)
                doc["rank"] = rank + 1
                doc["retriever"] = "bm25_only"
                results.append(doc)
        return results

    def save(self, prefix: str = "retriever"):
        """Save cả FAISS index, BM25, và documents."""
        self.faiss_index.save(str(INDEX_DIR / f"{prefix}_faiss.index"))
        self.bm25_index.save(str(INDEX_DIR / f"{prefix}_bm25.pkl"))
        with open(INDEX_DIR / f"{prefix}_docs.json", "w", encoding="utf-8") as f:
            json.dump(self.documents, f, ensure_ascii=False, indent=2)
        print(f"[HybridRetriever] Saved all indexes to {INDEX_DIR}")

    def load(self, prefix: str = "retriever"):
        """Load indexes đã lưu."""
        self.faiss_index.load(str(INDEX_DIR / f"{prefix}_faiss.index"))
        self.bm25_index.load(str(INDEX_DIR / f"{prefix}_bm25.pkl"))
        with open(INDEX_DIR / f"{prefix}_docs.json", "r", encoding="utf-8") as f:
            self.documents = json.load(f)
        self._built = True
        print(f"[HybridRetriever] Loaded. Documents: {len(self.documents)}")

    def benchmark_latency(
        self, query: str, query_embedding: np.ndarray, n_runs: int = 100
    ):
        """Đo latency search."""
        # Warm up
        for _ in range(5):
            self.search(query, query_embedding)

        latencies = {"hybrid_rrf": [], "dense_only": [], "bm25_only": []}
        for _ in range(n_runs):
            t0 = time.perf_counter()
            self.search(query, query_embedding)
            latencies["hybrid_rrf"].append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            self.dense_only_search(query_embedding)
            latencies["dense_only"].append((time.perf_counter() - t0) * 1000)

            t0 = time.perf_counter()
            self.bm25_only_search(query)
            latencies["bm25_only"].append((time.perf_counter() - t0) * 1000)

        print("[Benchmark Retriever Latency]")
        for method, lats in latencies.items():
            avg = np.mean(lats)
            p50 = np.percentile(lats, 50)
            p95 = np.percentile(lats, 95)
            print(f"  {method:15s}: avg={avg:.2f}ms | P50={p50:.2f}ms | P95={p95:.2f}ms")
        return latencies


if __name__ == "__main__":
    print("=" * 50)
    print(" HYBRID RETRIEVER TEST")
    print("=" * 50)

    # Tạo dữ liệu test
    docs = [
        {"text": "A transformer is a deep learning architecture using self-attention mechanisms.", "source": "wiki", "chunk_id": 0},
        {"text": "Convolutional neural networks are primarily used for image recognition tasks.", "source": "wiki", "chunk_id": 1},
        {"text": "Recurrent neural networks process sequential data like text and time series.", "source": "wiki", "chunk_id": 2},
        {"text": "Reinforcement learning trains agents through reward signals in an environment.", "source": "wiki", "chunk_id": 3},
        {"text": "Natural language processing enables computers to understand human language.", "source": "wiki", "chunk_id": 4},
        {"text": "Gradient descent is an optimization algorithm used to train neural networks.", "source": "wiki", "chunk_id": 5},
        {"text": "BERT is a bidirectional transformer model pre-trained on large text corpora.", "source": "wiki", "chunk_id": 6},
        {"text": "GPT models use autoregressive decoding to generate text token by token.", "source": "wiki", "chunk_id": 7},
        {"text": "Attention mechanisms allow models to focus on relevant parts of the input.", "source": "wiki", "chunk_id": 8},
        {"text": "Backpropagation computes gradients for each layer in a neural network.", "source": "wiki", "chunk_id": 9},
    ]

    # Tạo random embeddings cho test (thực tế dùng EmbeddingModel)
    np.random.seed(42)
    dim = 384
    embeddings = np.random.randn(len(docs), dim).astype(np.float32)
    query_emb = np.random.randn(dim).astype(np.float32)

    retriever = HybridRetriever(dim=dim)
    retriever.build_index(docs, embeddings)

    # Test search
    query = "What is a transformer model?"
    results = retriever.search(query, query_emb, top_k=5)
    print(f"\nQuery: {query}")
    print(f"Results ({len(results)}):")
    for r in results:
        print(f"  Rank {r['rank']}: [{r['score']:.4f}] {r['text'][:70]}...")
