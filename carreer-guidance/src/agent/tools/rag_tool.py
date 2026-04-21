import os
from typing import Any

from src.config.settings_models import get_settings
from src.modules.rag_module.main import RAGModuleImpl
from src.modules.rag_module.schema_models import RAGQuery
from src.services.llm_service.main import LLMService
from src.services.retriever_service.main import RetrieverService


class RAGTool:
    def __init__(self, *, execution_id: str, user_id: str) -> None:
        if not execution_id.strip():
            raise ValueError("execution_id is required for RAG tool")
        if not user_id.strip():
            raise ValueError("user_id is required for RAG tool")

        self.execution_id = execution_id
        self.user_id = user_id

        settings = get_settings()
        collection_name = os.getenv(
            "CHROMA_COLLECTION_NAME", "career_guidance_documents"
        )

        self.retriever_service = RetrieverService(
            execution_id=execution_id,
            chroma_host=settings.vector_store.chroma_host,
            chroma_port=settings.vector_store.chroma_port,
            collection_name=collection_name,
            chroma_client_mode=settings.vector_store.chroma_client_mode,
            chroma_persist_dir=settings.vector_store.chroma_persist_dir,
        )
        self.retriever_service.connect()

        self.llm_service = LLMService(execution_id=execution_id)
        self.module = RAGModuleImpl(
            execution_id=execution_id,
            user_id=user_id,
            retriever_service=self.retriever_service,
            llm_service=self.llm_service,
        )

    def run(self, question: str) -> dict[str, Any]:
        if not question.strip():
            raise ValueError("question is required for RAG tool")

        query = RAGQuery(question=question, language="auto")
        result = self.module.query(query)

        return {
            "answer": result.answer,
            "sources": [
                {
                    "rank": src.rank,
                    "text": src.text,
                    "source": src.source,
                    "title": src.title,
                    "rerank_score": src.rerank_score,
                }
                for src in result.sources
            ],
            "language": result.language,
            "latency_ms": result.latency_ms,
        }
