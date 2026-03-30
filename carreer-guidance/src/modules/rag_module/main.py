"""RAG module orchestration.

Rules:
- No direct model/API implementation here
- All real operations delegated to services
- Follows sync_doc_module pattern: clean orchestration only
"""


import logging
import time

import langdetect

from src.modules.rag_module.schemas import RAGQuery, RAGResult, SourceInfo
from src.services.embedding_service.main import EmbeddingService
from src.services.retriever_service.main import RetrieverService
from src.services.reranker_service.main import RerankerService
from src.services.llm_service.main import LLMService


class RAGModuleImpl:
    """RAG module orchestration class.

    Must contain only orchestration logic.
    All real operations delegated to services.

    Pattern mirrors SyncDocumentModuleImpl:
    - receives services via __init__
    - exposes query() and health_check()
    """

    def __init__(
        self,
        *,
        execution_id: str,
        embedding_service: EmbeddingService | None = None,
        retriever_service: RetrieverService | None = None,
        reranker_service: RerankerService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.logger = logging.getLogger(f"{__name__}[{execution_id}]")

        self.embedding_service = embedding_service or EmbeddingService(
            execution_id=self.execution_id
        )
        self.retriever_service = retriever_service or RetrieverService(
            execution_id=self.execution_id
        )
        self.reranker_service = reranker_service or RerankerService(
            execution_id=self.execution_id
        )
        self.llm_service = llm_service

        self.logger.info("RAG module initialized.")

    def query(self, request: RAGQuery) -> RAGResult:
        pipeline_start = time.perf_counter()
        question = request.question
        language = request.language

        # Step 0: Auto-detect language ─────────────────────────────
        if language == "auto":
            try:
                detected = langdetect.detect(question)
                language = "vi" if detected == "vi" else "en"
            except Exception:
                language = "en"
            self.logger.info("Auto-detected language: %s", language.upper())

        # Step 1: Translate query (Vietnamese → English) ──────────
        search_query = question
        if language == "vi" and self.llm_service is not None:
            search_query = self.llm_service.translate_query(question, language="vi")

        # Step 2: Embed query ─────────────────────────────────────
        query_embedding = self.embedding_service.encode_query(search_query)

        # Step 3: Hybrid Retrieve ─────────────────────────────────
        retrieved = self.retriever_service.search(
            query=search_query,
            query_embedding=query_embedding,
            top_k=request.retrieve_k,
        )

        # Step 4: Rerank ──────────────────────────────────────────
        reranked = self.reranker_service.rerank(
            query=search_query,
            documents=retrieved,
            top_k=request.rerank_k,
        )

        # Step 5: Build context ───────────────────────────────────
        context_parts = []
        sources = []
        for i, doc in enumerate(reranked):
            context_parts.append(f"[{i + 1}] {doc['text']}")
            sources.append(SourceInfo(
                rank=i + 1,
                text=doc["text"][:100] + "...",
                source=doc.get("source", "unknown"),
                title=doc.get("title", ""),
                rerank_score=doc.get("rerank_score", 0.0),
            ))
        context = "\n\n".join(context_parts)

        # Step 6: LLM Generate ────────────────────────────────────
        if self.llm_service is not None:
            llm_result = self.llm_service.generate(
                question=question,
                context=context,
                language=language,
            )
            answer = llm_result["answer"]
            tokens_generated = llm_result["tokens_generated"]
            tokens_per_second = llm_result["tokens_per_second"]
        else:
            answer = f"[LLM not loaded] Context retrieved:\n{context}"
            tokens_generated = 0
            tokens_per_second = 0.0

        total_ms = (time.perf_counter() - pipeline_start) * 1000
        self.logger.info("RAG query completed in %.0fms", total_ms)

        return RAGResult(
            question=question,
            answer=answer,
            sources=sources,
            language=language,
            latency_ms=total_ms,
            tokens_generated=tokens_generated,
            tokens_per_second=tokens_per_second,
        )

    def health_check(self) -> bool:
        """Check if all services are ready."""
        try:
            return (
                self.embedding_service is not None
                and self.retriever_service is not None
                and self.retriever_service.is_ready
                and self.reranker_service is not None
            )
        except Exception:
            return False
