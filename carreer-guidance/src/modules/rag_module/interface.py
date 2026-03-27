"""Contracts for RAG module."""

from __future__ import annotations

from typing import Protocol

from src.modules.rag_module.schemas import RAGQuery, RAGResult


class RAGModule(Protocol):
    """RAG module contract — Agent layer calls through this interface."""

    def query(self, request: RAGQuery) -> RAGResult: ...

    def health_check(self) -> bool: ...
