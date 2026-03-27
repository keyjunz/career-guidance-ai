"""Reranker service — Cross-Encoder reranking."""

from __future__ import annotations

import logging
from typing import Dict, List

import torch
from sentence_transformers import CrossEncoder

RERANKER_MODELS = {
    "ms-marco-MiniLM-L6": {"name": "cross-encoder/ms-marco-MiniLM-L-6-v2", "max_length": 512},
    "bge-reranker-base": {"name": "BAAI/bge-reranker-base", "max_length": 512},
    "monoT5-base": {"name": "castorini/monoT5-base-msmarco-10k", "max_length": 512},
}
DEFAULT_RERANKER = "ms-marco-MiniLM-L6"
RERANKER_TOP_K = 5
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class RerankerService:
    """Cross-encoder reranker service."""

    def __init__(self, *, execution_id: str, model_key: str = DEFAULT_RERANKER, device: str = DEVICE):
        self.execution_id = execution_id
        self.logger = logging.getLogger(f"{__name__}[{execution_id}]")

        self.model_key = model_key
        self.model_config = RERANKER_MODELS[model_key]
        self.model_name = self.model_config["name"]
        self.max_length = self.model_config["max_length"]
        self.device = device

        self.logger.info("Loading reranker %s on %s...", self.model_name, self.device)
        self.model = CrossEncoder(self.model_name, max_length=self.max_length, device=self.device)
        self.logger.info("Reranker loaded successfully.")

    def rerank(self, query: str, documents: List[Dict], top_k: int = RERANKER_TOP_K, text_key: str = "text") -> List[Dict]:
        if not documents:
            return []
        pairs = [(query, doc[text_key]) for doc in documents]
        scores = self.model.predict(pairs, batch_size=len(pairs), show_progress_bar=False)
        for doc, score in zip(documents, scores):
            doc["rerank_score"] = float(score)
        reranked = sorted(documents, key=lambda x: x["rerank_score"], reverse=True)
        for i, doc in enumerate(reranked[:top_k]):
            doc["final_rank"] = i + 1
        return reranked[:top_k]

    def score_pair(self, query: str, passage: str) -> float:
        return float(self.model.predict([(query, passage)])[0])

    def get_memory_usage_mb(self) -> float:
        return sum(p.numel() * p.element_size() for p in self.model.model.parameters()) / (1024 ** 2)
