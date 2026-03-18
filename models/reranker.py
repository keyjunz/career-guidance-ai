"""
Cross-Encoder Reranker module.
Hỗ trợ: ms-marco-MiniLM-L-6-v2, bge-reranker-base, monoT5-base
"""

import time
import numpy as np
from pathlib import Path
from typing import List, Dict, Tuple

import torch
from sentence_transformers import CrossEncoder

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RERANKER_MODELS, DEFAULT_RERANKER, RERANKER_TOP_K, DEVICE


class Reranker:
    """Cross-encoder reranker wrapper."""

    def __init__(self, model_key: str = DEFAULT_RERANKER, device: str = DEVICE):
        self.model_key = model_key
        self.model_config = RERANKER_MODELS[model_key]
        self.model_name = self.model_config["name"]
        self.max_length = self.model_config["max_length"]
        self.device = device

        print(f"[Reranker] Loading {self.model_name} on {self.device}...")
        self.model = CrossEncoder(
            self.model_name,
            max_length=self.max_length,
            device=self.device,
        )
        print(f"[Reranker] Loaded successfully.")

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = RERANKER_TOP_K,
        text_key: str = "text",
    ) -> List[Dict]:
        """
        Rerank documents using cross-encoder.

        Args:
            query: Câu hỏi
            documents: List[Dict] — kết quả từ retriever
            top_k: Số kết quả trả về sau rerank
            text_key: Key chứa text trong document dict

        Returns:
            List[Dict] đã sắp xếp lại, thêm 'rerank_score'
        """
        if not documents:
            return []

        # Tạo pairs (query, document_text)
        pairs = [(query, doc[text_key]) for doc in documents]

        # Cross-encoder scoring
        scores = self.model.predict(
            pairs,
            batch_size=len(pairs),   # Batch tất cả vì k thường nhỏ (5-10)
            show_progress_bar=False,
        )

        # Gắn score và sort
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)

        reranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)

        # Gán lại rank
        for i, doc in enumerate(reranked[:top_k]):
            doc["final_rank"] = i + 1

        return reranked[:top_k]

    def score_pair(self, query: str, passage: str) -> float:
        """Score single (query, passage) pair."""
        return float(self.model.predict([(query, passage)])[0])

    def benchmark_latency(
        self,
        query: str = "What is attention mechanism in transformers?",
        passages: List[str] = None,
        n_runs: int = 50,
    ):
        """Đo latency rerank."""
        if passages is None:
            passages = [
                "Attention mechanisms allow models to focus on relevant parts of input sequences.",
                "Convolutional neural networks use filters to extract spatial features from images.",
                "Recurrent networks process data sequentially using hidden state memory.",
                "Transformers replaced RNNs for many NLP tasks due to parallelization.",
                "BERT uses masked language modeling as a pre-training objective.",
                "GPT models generate text in an autoregressive left-to-right fashion.",
                "Neural networks learn through backpropagation of error gradients.",
                "Dropout is a regularization technique that randomly disables neurons.",
                "Batch normalization stabilizes training by normalizing layer inputs.",
                "Learning rate scheduling adjusts the step size during optimization.",
            ]

        docs = [{"text": p, "source": "test", "chunk_id": i} for i, p in enumerate(passages)]

        # Warm up
        for _ in range(3):
            self.rerank(query, [d.copy() for d in docs])

        latencies = []
        for _ in range(n_runs):
            start = time.perf_counter()
            self.rerank(query, [d.copy() for d in docs])
            latencies.append((time.perf_counter() - start) * 1000)

        avg = np.mean(latencies)
        p50 = np.percentile(latencies, 50)
        p95 = np.percentile(latencies, 95)
        print(f"[Benchmark Reranker] {self.model_name} (k={len(passages)})")
        print(f"  Avg: {avg:.1f}ms | P50: {p50:.1f}ms | P95: {p95:.1f}ms")
        return {"avg": avg, "p50": p50, "p95": p95}

    def get_memory_usage_mb(self) -> float:
        params = sum(p.numel() * p.element_size() for p in self.model.model.parameters())
        return params / (1024 ** 2)


if __name__ == "__main__":
    print("=" * 50)
    print(" RERANKER TEST")
    print("=" * 50)

    reranker = Reranker()
    print(f"Model memory: ~{reranker.get_memory_usage_mb():.1f} MB")

    query = "How does self-attention work in transformers?"
    docs = [
        {"text": "Self-attention computes weighted sums of value vectors based on query-key similarities.", "source": "wiki", "chunk_id": 0},
        {"text": "Convolutional layers apply learned filters across spatial dimensions of input data.", "source": "wiki", "chunk_id": 1},
        {"text": "The transformer architecture uses multi-head self-attention in both encoder and decoder.", "source": "wiki", "chunk_id": 2},
        {"text": "Python is a popular programming language for machine learning.", "source": "wiki", "chunk_id": 3},
        {"text": "Attention allows the model to attend to different positions of the input sequence.", "source": "wiki", "chunk_id": 4},
    ]

    results = reranker.rerank(query, docs, top_k=3)
    print(f"\nQuery: {query}")
    print(f"\nTop-3 after reranking:")
    for r in results:
        print(f"  Rank {r['final_rank']}: [{r['rerank_score']:.4f}] {r['text'][:70]}...")

    print()
    reranker.benchmark_latency()
