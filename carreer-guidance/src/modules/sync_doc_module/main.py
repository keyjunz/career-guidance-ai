"""Sync document module orchestration.

Rules:
- No direct DB/API/LLM/OCR implementation here
- All real operations delegated to services
"""

from __future__ import annotations

import logging

from src.handlers.base_handler import RequestContext, map_exception_to_domain_error
from src.modules.sync_doc_module.schemas import SyncExecutionSummary
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse
from src.services.database_service import DatabaseSyncService
from src.services.document_service import DocumentService
from src.services.gemini.ocr_service import GeminiOCRService
from src.services.vector_db_services import VectorDBService

logger = logging.getLogger(__name__)


class SyncDocumentModuleImpl:
    """Module orchestration class.

    Must contain only 3 methods:
    - __init__
    - sync_documents
    - get_status_sync_doc
    """

    def __init__(
        self,
        *,
        document_service: DocumentService,
        gemini_ocr_service: GeminiOCRService,
        database_service: DatabaseSyncService,
        vector_db_service: VectorDBService,
    ) -> None:
        self.document_service = document_service
        self.gemini_ocr_service = gemini_ocr_service
        self.database_service = database_service
        self.vector_db_service = vector_db_service
        self.execution_id: str | None = None

    def sync_documents(
        self,
        request: SyncDocumentsRequest,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        job_id = ""
        try:
            self.execution_id = context.trace_id

            job = self.database_service.create_sync_job(
                request,
                execution_id=self.execution_id,
            )
            job_id = job.job_id
            self.database_service.update_job_status(
                job_id,
                "processing",
                execution_id=self.execution_id,
            )

            prepared_docs = self.document_service.prepare_documents(
                request.file_urls,
                request.download_dir,
            )
            ocr_results = self.gemini_ocr_service.extract_text_batch(
                [
                    {
                        "source_url": doc.source_url,
                        "file_path": doc.file_path,
                    }
                    for doc in prepared_docs
                ]
            )
            chunks = self.document_service.chunk_documents(ocr_results)
            upserted = self.vector_db_service.upsert_chunks(
                ingestion_job_id=job_id,
                user_id=str(request.user_id),
                chunks=chunks,
                execution_id=self.execution_id,
            )

            failed_count = len([item for item in ocr_results if not item.success])
            processed_count = max(upserted, 0)
            status = "completed" if failed_count == 0 else "failed"

            if status == "completed":
                self.database_service.mark_completed(
                    job_id,
                    execution_id=self.execution_id,
                )
            else:
                self.database_service.mark_failed(
                    job_id,
                    execution_id=self.execution_id,
                )

            summary = SyncExecutionSummary(
                ingestion_job_id=job_id,
                downloaded=len(prepared_docs),
                processed=processed_count,
                failed=failed_count,
                status=status,
                execution_id=self.execution_id,
            )
            return SyncDocumentsResponse(
                job_id=summary.ingestion_job_id,
                status=summary.status,
                processed=summary.processed,
                failed=summary.failed,
                downloaded=summary.downloaded,
            )
        except Exception as exc:
            logger.error("sync_documents failed: %s", exc)
            if job_id:
                self.database_service.mark_failed(
                    job_id,
                    execution_id=self.execution_id,
                )
            raise map_exception_to_domain_error(exc) from exc

    def get_status_sync_doc(
        self,
        ingestion_job_id: str,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        try:
            self.execution_id = context.trace_id
            return self.database_service.get_job_status(
                ingestion_job_id,
                execution_id=self.execution_id,
            )
        except Exception as exc:
            logger.error("get_status_sync_doc failed: %s", exc)
            raise map_exception_to_domain_error(exc) from exc
