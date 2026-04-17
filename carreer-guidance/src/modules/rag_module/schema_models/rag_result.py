from dataclasses import dataclass, field

from src.modules.rag_module.schema_models.source_info import SourceInfo


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
