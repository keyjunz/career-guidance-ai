"""Schemas for RAG module orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Language = Literal["auto", "en", "vi"]


@dataclass(slots=True)
class RAGQuery:
    """Input schema for RAG pipeline query."""

    question: str
    language: Language = "auto"
    retrieve_k: int = 10
    rerank_k: int = 5


@dataclass(slots=True)
class SourceInfo:
    """Single source document returned by RAG pipeline."""

    rank: int
    text: str
    source: str
    title: str
    rerank_score: float


@dataclass(slots=True)
class RAGResult:
    """Output schema for RAG pipeline query."""

    question: str
    answer: str
    sources: list[SourceInfo] = field(default_factory=list)
    language: str = "en"
    latency_ms: float = 0.0
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
