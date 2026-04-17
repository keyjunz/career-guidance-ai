from dataclasses import dataclass


@dataclass(slots=True)
class SourceInfo:
    """Single source document returned by RAG pipeline."""

    rank: int
    text: str
    source: str
    title: str
    rerank_score: float
