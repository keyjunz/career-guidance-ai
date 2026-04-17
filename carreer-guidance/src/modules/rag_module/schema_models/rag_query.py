from dataclasses import dataclass

from src.modules.rag_module.schema_models.language import Language


@dataclass(slots=True)
class RAGQuery:
    """Input schema for RAG pipeline query."""

    question: str
    language: Language = "auto"
    retrieve_k: int = 10
    rerank_k: int = 5
