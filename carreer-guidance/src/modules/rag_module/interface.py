"""Contracts for RAG module."""


from typing import Protocol

from src.modules.rag_module.schemas import RAGQuery, RAGResult


class RAGModule(Protocol):
    """RAG module contract — Agent layer calls through this interface."""

    def query(self, request: RAGQuery) -> RAGResult:
        """Execute full RAG pipeline for a single question.

        Steps:
        0. Auto-detect language
        1. Translate query (if Vietnamese)
        2. Embed query
        3. Hybrid retrieve (ChromaDB + BM25 → RRF)
        4. Rerank (Cross-Encoder)
        5. Build context
        6. LLM Generate
        """
        ...

    def health_check(self) -> bool: ...
