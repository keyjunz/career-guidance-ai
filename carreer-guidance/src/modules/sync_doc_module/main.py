import logging
import time
from typing import Any

from src.request_body.sync_request_body import (
    SyncDocumentsRequest,
    SyncDocumentsResponse,
)
from src.services.database_service.main import DatabaseSyncService
from src.services.document_service.main import DocumentService
from src.services.embedding_service.main import EmbeddingService
from src.services.ocr.paddle_ocr_service import PaddleOCRService
from src.services.vector_db_service.main import VectorDBService

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class SyncDocumentModuleImpl:

    def __init__(
        self,
        execution_id: str,
        user_id: str | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.user_id = str(user_id).strip() if user_id else None
        self.document_service = DocumentService(execution_id)
        self.ocr_service = PaddleOCRService(execution_id)
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
        """Process uploaded files: OCR extraction → chunk → vector DB."""
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
                "sync_documents started: execution_id=%s user_id=%s files=%d industry_type=%s",
                self.execution_id,
                user_id,
                len(request.file_urls),
                str(request.industry_type or ""),
            )

            # Create job in database
            job = self.database_service.create_sync_job(request)
            job_id = str(job.get("job_id") or "")
            self.database_service.update_job_status(job_id, "processing")
            logger.info(
                "sync_documents job created: execution_id=%s user_id=%s job_id=%s",
                self.execution_id,
                user_id,
                job_id,
            )

            # Prepare documents from file_urls (local file paths)
            prepared_docs = [
                {
                    "source_url": file_path,
                    "file_path": file_path,
                    "industry_type": str(request.industry_type or ""),
                }
                for file_path in request.file_urls
            ]
            for item in prepared_docs:
                logger.info(
                    "sync_documents file queued: execution_id=%s user_id=%s job_id=%s file_path=%s industry_type=%s",
                    self.execution_id,
                    user_id,
                    job_id,
                    str(item.get("file_path") or ""),
                    str(item.get("industry_type") or ""),
                )

            # Extract text from documents using OCR
            ocr_results = self.ocr_service.extract_text_batch(
                prepared_docs,
            )
            for item in ocr_results:
                success = bool(item.get("success"))
                file_path = str(item.get("file_path") or "")
                extracted_len = len(str(item.get("text") or ""))
                logger.info(
                    "sync_documents ocr result: execution_id=%s user_id=%s job_id=%s file_path=%s success=%s text_length=%d",
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
                    "sync_documents file pages: execution_id=%s user_id=%s job_id=%s file_path=%s pages=%d",
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
            for result in ocr_results:
                file_path = str(result.get("file_path") or "")
                result["industry_type"] = industry_by_file_path.get(file_path, "")

            # Store OCR results
            self.database_service.apply_ocr_results(
                job_id=job_id,
                ocr_results=ocr_results,
            )
            logger.info(
                "sync_documents ocr persisted: execution_id=%s user_id=%s job_id=%s total=%d",
                self.execution_id,
                user_id,
                job_id,
                len(ocr_results),
            )

            # Chunk documents
            chunks = self.document_service.chunk_documents(ocr_results)
            logger.info(
                "sync_documents chunked: execution_id=%s user_id=%s job_id=%s chunks=%d",
                self.execution_id,
                user_id,
                job_id,
                len(chunks),
            )

            # Upsert chunks to vector database
            upserted = self.vector_db_service.upsert_chunks(
                ingestion_job_id=job_id,
                user_id=user_id,
                chunks=chunks,
            )
            logger.info(
                "sync_documents upsert done: execution_id=%s user_id=%s job_id=%s upserted=%d",
                self.execution_id,
                user_id,
                job_id,
                upserted,
            )

            # Calculate final statistics
            failed_count = len(
                [item for item in ocr_results if not bool(item.get("success"))]
            )
            if failed_count == len(prepared_docs):
                raise ValueError("OCR failed for all documents.")

            processed_count = max(upserted, 0)
            status = "completed" if failed_count == 0 else "failed"

            # Update final job status
            if status == "completed":
                self.database_service.mark_completed(job_id)
            else:
                self.database_service.mark_failed(job_id)

            logger.info(
                "sync_documents completed: execution_id=%s user_id=%s job_id=%s processed=%d failed=%d total_pages=%d status=%s execution_time_ms=%d",
                self.execution_id,
                user_id,
                job_id,
                processed_count,
                failed_count,
                total_pages,
                status,
                int((time.perf_counter() - started_at) * 1000),
            )

            execution_time_ms = int((time.perf_counter() - started_at) * 1000)

            return SyncDocumentsResponse(
                job_id=job_id,
                status=status,
                processed=processed_count,
                failed=failed_count,
                downloaded=len(prepared_docs),
                total_pages=total_pages,
                file_page_counts=file_page_counts,
                execution_time_ms=execution_time_ms,
            )
        except Exception as exc:
            logger.error(
                "sync_documents failed: execution_id=%s user_id=%s job_id=%s error=%s",
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

    def get_status_sync_doc(
        self,
        ingestion_job_id: str,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        """Get status of a sync job."""
        try:
            if context.get("execution_id") != self.execution_id:
                raise ValueError("context.execution_id must match module execution_id")
            return self.database_service.get_job_status(ingestion_job_id)
        except Exception as exc:
            logger.error("get_status_sync_doc failed: %s", exc)
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError("Internal server error") from exc
