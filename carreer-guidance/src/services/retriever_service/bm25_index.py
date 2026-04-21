from typing import List, Tuple

import numpy as np
from rank_bm25 import BM25Okapi

BM25_K1 = 1.5
BM25_B = 0.75


class BM25Index:
    """BM25 sparse retriever for keyword-based search."""

    def __init__(self) -> None:
        self.bm25: BM25Okapi | None = None
        self.corpus_tokens: list[list[str]] | None = None

    def build(self, corpus: List[str]) -> None:
        if not corpus:
            self.bm25 = None
            self.corpus_tokens = None
            return

        self.corpus_tokens = [doc.lower().split() for doc in corpus]
        self.bm25 = BM25Okapi(self.corpus_tokens, k1=BM25_K1, b=BM25_B)

    @property
    def is_built(self) -> bool:
        return self.bm25 is not None

    def get_scores(self, query: str) -> np.ndarray:
        if self.bm25 is None:
            return np.array([])

        query_tokens = query.lower().split()
        return self.bm25.get_scores(query_tokens)

    def search(self, query: str, k: int = 20) -> Tuple[np.ndarray, np.ndarray]:
        scores = self.get_scores(query)
        if scores.size == 0:
            return np.array([]), np.array([], dtype=int)

        top_indices = np.argsort(scores)[::-1][:k]
        top_scores = scores[top_indices]
        return top_scores, top_indices
