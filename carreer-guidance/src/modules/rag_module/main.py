"""RAG module orchestration.

Rules:
- No direct model/API implementation here
- All real operations delegated to services
- Follows sync_doc_module pattern: clean orchestration only
"""

import logging
import os
import time
from pathlib import Path
from typing import Any
from importlib import import_module
from importlib.util import find_spec

langdetect = import_module("langdetect") if find_spec("langdetect") else None

from src.modules.rag_module.schema_models import RAGQuery, RAGResult, SourceInfo
from src.services.embedding_service.main import EmbeddingService
from src.services.llm_service.main import LLMService
from src.services.reranker_service.main import RerankerService
from src.services.retriever_service.main import RetrieverService


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
        user_id: str | None = None,
        embedding_service: EmbeddingService | None = None,
        retriever_service: RetrieverService | None = None,
        reranker_service: RerankerService | None = None,
        llm_service: LLMService | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.user_id = str(user_id).strip() if user_id else None
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

        self.image_base_url = os.getenv("IMAGE_BASE_URL", "").strip()
        self.image_storage_dir = self._resolve_image_storage_dir()

        self.logger.info("RAG module initialized.")

    def query(self, request: RAGQuery) -> RAGResult:
        pipeline_start = time.perf_counter()
        question = request.question
        language = request.language

        # Step 0: Auto-detect language ─────────────────────────────
        if language == "auto":
            try:
                if langdetect is None:
                    raise RuntimeError("langdetect unavailable")
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

        # Step 3: Hybrid Retrieve on shared knowledge base ───────
        # Support ingests a shared corpus; all clients query the same corpus.
        where_filter = None

        retrieved = self.retriever_service.search(
            query=search_query,
            query_embedding=query_embedding,
            top_k=request.retrieve_k,
            where=where_filter,
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
        image_urls_set: list[str] = []
        for i, doc in enumerate(reranked):
            metadata = doc.get("metadata") or {}
            image_urls = self._build_image_urls(metadata)
            context_parts.append(f"[{i + 1}] {doc['text']}")
            sources.append(
                SourceInfo(
                    rank=i + 1,
                    text=doc["text"][:100] + "...",
                    source=doc.get("source", "unknown"),
                    title=doc.get("title", ""),
                    rerank_score=doc.get("rerank_score", 0.0),
                    image_urls=image_urls,
                )
            )
            for url in image_urls:
                if url not in image_urls_set:
                    image_urls_set.append(url)
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
            image_urls=image_urls_set,
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

    def _resolve_image_storage_dir(self) -> Path:
        base = Path(os.getenv("IMAGE_STORAGE_DIR", "database/images"))
        if base.is_absolute():
            return base
        base_dir = Path(__file__).resolve().parents[4]
        return (base_dir / base).resolve()

    def _build_image_urls(self, metadata: dict[str, Any]) -> list[str]:
        if not self.image_base_url:
            return []
        image_paths = metadata.get("image_paths") or []
        urls: list[str] = []
        for raw_path in image_paths:
            if not raw_path:
                continue
            path = Path(str(raw_path))
            if path.is_absolute():
                try:
                    rel = path.relative_to(self.image_storage_dir)
                except ValueError:
                    rel = path.name
            else:
                rel = path
            # Avoid backslash inside f-string expression (Python limitation).
            rel_str = str(rel).replace("\\", "/")
            url = f"{self.image_base_url.rstrip('/')}/images/{rel_str}"
            urls.append(url)
        return urls
