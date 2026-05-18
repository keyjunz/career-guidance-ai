import logging
import time
from pathlib import Path
from typing import Any

from src.request_body.sync_request_body import (
    SyncDocumentsRequest,
    SyncDocumentsResponse,
)
from src.services.database_service.main import DatabaseSyncService
from src.services.document_service.main import DocumentService
from src.services.embedding_service.main import EmbeddingService
from src.services.ocr.gemini_layout_ocr_service import GeminiLayoutOCRService
from src.services.ocr.paddle_ocr_service import PaddleOCRService
from src.services.vector_db_service.main import VectorDBService

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SyncDocumentModuleGeminiImpl:
    """Sync documents using Gemini layout OCR (text + image)."""

    def __init__(
        self,
        execution_id: str,
        user_id: str | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.user_id = str(user_id).strip() if user_id else None
        self.document_service = DocumentService(execution_id)
        self.ocr_service = GeminiLayoutOCRService(execution_id)
        self.database_service = DatabaseSyncService(execution_id)
        embedding_service = EmbeddingService(execution_id)
        self.vector_db_service = VectorDBService(
            execution_id,
            embedding_service=embedding_service,
        )

    def sync_documents(
        self,
        request: SyncDocumentsRequest,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        """Process uploaded files: Gemini OCR extraction -> chunk -> vector DB."""
        job_id = ""
        user_id = str(request.user_id)
        context_user_id = str(context.get("user_id") or "").strip()
        started_at = time.perf_counter()
        try:
            if context.get("execution_id") != self.execution_id:
                raise ValueError("context.execution_id must match module execution_id")
            if self.user_id and self.user_id != user_id:
                raise ValueError("module.user_id must match request.user_id")
            if context_user_id and context_user_id != user_id:
                raise ValueError("context.user_id must match request.user_id")

            logger.info(
                "sync_documents_gemini started: execution_id=%s user_id=%s files=%d industry_type=%s",
                self.execution_id,
                user_id,
                len(request.file_urls),
                str(request.industry_type or ""),
            )

            job = self.database_service.create_sync_job(request)
            job_id = str(job.get("job_id") or "")
            file_actions = job.get("file_actions", {})
            source_keys = job.get("source_keys", {})
            skipped_count = sum(
                1 for action in file_actions.values() if action == "skip"
            )
            self.database_service.update_job_status(job_id, "processing")
            logger.info(
                "sync_documents_gemini job created: execution_id=%s user_id=%s job_id=%s",
                self.execution_id,
                user_id,
                job_id,
            )

            prepared_docs = []
            for file_path in request.file_urls:
                action = str(file_actions.get(file_path, "new"))
                if action == "skip":
                    continue
                source_key = source_keys.get(file_path) or Path(file_path).name
                prepared_docs.append(
                    {
                        "source_url": file_path,
                        "file_path": file_path,
                        "industry_type": str(request.industry_type or ""),
                        "source_key": source_key,
                        "action": action,
                    }
                )
            for item in prepared_docs:
                logger.info(
                    "sync_documents_gemini file queued: execution_id=%s user_id=%s job_id=%s file_path=%s industry_type=%s",
                    self.execution_id,
                    user_id,
                    job_id,
                    str(item.get("file_path") or ""),
                    str(item.get("industry_type") or ""),
                )

            if not prepared_docs:
                self.database_service.mark_completed(job_id)
                execution_time_ms = int((time.perf_counter() - started_at) * 1000)
                return SyncDocumentsResponse(
                    job_id=job_id,
                    status="completed",
                    processed=0,
                    failed=0,
                    downloaded=len(request.file_urls),
                    skipped=skipped_count,
                    total_pages=0,
                    file_page_counts={},
                    execution_time_ms=execution_time_ms,
                )

            ocr_results = self.ocr_service.extract_text_batch(prepared_docs)
            ocr_results = self._fallback_ocr_when_needed(
                prepared_docs=prepared_docs,
                ocr_results=ocr_results,
            )
            for item in ocr_results:
                success = bool(item.get("success"))
                file_path = str(item.get("file_path") or "")
                extracted_len = len(str(item.get("text") or ""))
                logger.info(
                    "sync_documents_gemini ocr result: execution_id=%s user_id=%s job_id=%s file_path=%s success=%s text_length=%d",
                    self.execution_id,
                    user_id,
                    job_id,
                    file_path,
                    success,
                    extracted_len,
                )

            file_page_counts: dict[str, int] = {}
            total_pages = 0
            for item in ocr_results:
                if not bool(item.get("success")):
                    continue
                file_path = str(item.get("file_path") or "")
                text = str(item.get("text") or "")
                page_count = self.document_service.count_pages(
                    text=text,
                    file_path=file_path,
                )
                file_page_counts[file_path] = page_count
                total_pages += page_count
                logger.info(
                    "sync_documents_gemini file pages: execution_id=%s user_id=%s job_id=%s file_path=%s pages=%d",
                    self.execution_id,
                    user_id,
                    job_id,
                    file_path,
                    page_count,
                )

            industry_by_file_path = {
                str(item.get("file_path") or ""): str(item.get("industry_type") or "")
                for item in prepared_docs
            }
            source_key_by_path = {
                str(item.get("file_path") or ""): str(item.get("source_key") or "")
                for item in prepared_docs
            }
            action_by_path = {
                str(item.get("file_path") or ""): str(item.get("action") or "new")
                for item in prepared_docs
            }
            for result in ocr_results:
                file_path = str(result.get("file_path") or "")
                result["industry_type"] = industry_by_file_path.get(file_path, "")
                result["doc_id"] = source_key_by_path.get(file_path, "")

            self.database_service.apply_ocr_results(
                job_id=job_id,
                ocr_results=ocr_results,
            )
            logger.info(
                "sync_documents_gemini ocr persisted: execution_id=%s user_id=%s job_id=%s total=%d",
                self.execution_id,
                user_id,
                job_id,
                len(ocr_results),
            )

            chunks = self.document_service.chunk_documents(ocr_results)
            logger.info(
                "sync_documents_gemini chunked: execution_id=%s user_id=%s job_id=%s chunks=%d",
                self.execution_id,
                user_id,
                job_id,
                len(chunks),
            )

            success_by_path = {
                str(item.get("file_path") or ""): bool(item.get("success"))
                for item in ocr_results
            }
            chunk_doc_ids = {
                str((chunk.get("metadata") or {}).get("doc_id") or "")
                for chunk in chunks
            }
            for file_path, action in action_by_path.items():
                if action != "update":
                    continue
                if not success_by_path.get(file_path, False):
                    continue
                doc_id = source_key_by_path.get(file_path, "")
                if doc_id and doc_id in chunk_doc_ids:
                    self.vector_db_service.delete_by_doc_id(doc_id)

            upserted = self.vector_db_service.upsert_chunks(
                ingestion_job_id=job_id,
                user_id=user_id,
                chunks=chunks,
            )
            logger.info(
                "sync_documents_gemini upsert done: execution_id=%s user_id=%s job_id=%s upserted=%d",
                self.execution_id,
                user_id,
                job_id,
                upserted,
            )

            failed_count = len(
                [item for item in ocr_results if not bool(item.get("success"))]
            )
            if failed_count == len(prepared_docs):
                raise ValueError("OCR failed for all documents.")

            processed_count = max(upserted, 0)
            status = "completed" if failed_count == 0 else "failed"

            if status == "completed":
                self.database_service.mark_completed(job_id)
            else:
                self.database_service.mark_failed(job_id)

            execution_time_ms = int((time.perf_counter() - started_at) * 1000)

            return SyncDocumentsResponse(
                job_id=job_id,
                status=status,
                processed=processed_count,
                failed=failed_count,
                downloaded=len(request.file_urls),
                skipped=skipped_count,
                total_pages=total_pages,
                file_page_counts=file_page_counts,
                execution_time_ms=execution_time_ms,
            )
        except Exception as exc:
            logger.error(
                "sync_documents_gemini failed: execution_id=%s user_id=%s job_id=%s error=%s",
                self.execution_id,
                user_id,
                job_id,
                exc,
            )
            if job_id:
                self.database_service.mark_failed(job_id)
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError("Internal server error") from exc

    def _fallback_ocr_when_needed(
        self,
        *,
        prepared_docs: list[dict[str, str]],
        ocr_results: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        fallback_docs: list[dict[str, str]] = []
        fallback_indices: list[int] = []
        for idx, item in enumerate(ocr_results):
            if bool(item.get("success")):
                continue
            err = str(item.get("error") or "").lower()
            if any(
                signal in err
                for signal in ("quota", "rate limit", "429", "timeout", "timed out")
            ):
                fallback_docs.append(prepared_docs[idx])
                fallback_indices.append(idx)

        if not fallback_docs:
            return ocr_results

        logger.warning(
            "sync_documents_gemini fallback to paddle OCR: execution_id=%s files=%d",
            self.execution_id,
            len(fallback_docs),
        )
        paddle_service = PaddleOCRService(self.execution_id)
        fallback_results = paddle_service.extract_text_batch(fallback_docs)

        for offset, result in enumerate(fallback_results):
            original_index = fallback_indices[offset]
            ocr_results[original_index] = result

        return ocr_results
