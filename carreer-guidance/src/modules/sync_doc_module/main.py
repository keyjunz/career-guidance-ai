"""Sync document module orchestration.

Rules:
- No direct DB/API/LLM/OCR implementation here
- All real operations delegated to services
"""

from __future__ import annotations

import logging
from typing import Any

from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse
from src.services.database_service.main import DatabaseSyncService
from src.services.document_service.main import DocumentService
from src.services.gemini.main import GeminiOCRService
from src.services.vector_db_service.main import VectorDBService

RequestContext = dict[str, Any]

logger = logging.getLogger(__name__)


class SyncDocumentModuleImpl:

    def __init__(
        self,
        *,
        execution_id: str,
        document_service: DocumentService | None = None,
        gemini_ocr_service: GeminiOCRService | None = None,
        database_service: DatabaseSyncService | None = None,
        vector_db_service: VectorDBService | None = None,
    ) -> None:
        self.execution_id = execution_id
        self.document_service = document_service or DocumentService(
            execution_id=self.execution_id
        )
        self.gemini_ocr_service = gemini_ocr_service or GeminiOCRService(
            execution_id=self.execution_id
        )
        self.database_service = database_service or DatabaseSyncService(
            execution_id=self.execution_id
        )
        self.vector_db_service = vector_db_service or VectorDBService(
            execution_id=self.execution_id
        )

    def sync_documents(
        self,
        request: SyncDocumentsRequest,
        context: RequestContext,
    ) -> SyncDocumentsResponse:
        job_id = ""
        try:
            # In sync flow, trace_id is the execution_id and also the job identifier.
            if context.get("trace_id") != self.execution_id:
                raise ValueError("context.trace_id must match module execution_id")

            job = self.database_service.create_sync_job(
                request,
            )
            job_id = str(job.get("job_id") or "")
            self.database_service.update_job_status(
                job_id,
                "processing",
            )

            prepared_docs = self.document_service.prepare_documents(
                request.file_urls,
                request.download_dir,
            )
            ocr_results = self.gemini_ocr_service.extract_text_batch(
                [
                    {
                        "source_url": str(doc.get("source_url") or ""),
                        "file_path": str(doc.get("file_path") or ""),
                    }
                    for doc in prepared_docs
                ],
            )
            self.database_service.apply_ocr_results(
                job_id=job_id,
                ocr_results=ocr_results,
            )
            chunks = self.document_service.chunk_documents(
                ocr_results,
            )
            upserted = self.vector_db_service.upsert_chunks(
                ingestion_job_id=job_id,
                user_id=str(request.user_id),
                chunks=chunks,
            )

            failed_count = len(
                [item for item in ocr_results if not bool(item.get("success"))]
            )
            processed_count = max(upserted, 0)
            status = "completed" if failed_count == 0 else "failed"

            if status == "completed":
                self.database_service.mark_completed(job_id)
            else:
                self.database_service.mark_failed(job_id)

            summary: dict[str, Any] = {
                "ingestion_job_id": job_id,
                "downloaded": len(prepared_docs),
                "processed": processed_count,
                "failed": failed_count,
                "status": status,
                "execution_id": self.execution_id,
            }
            return SyncDocumentsResponse(
                job_id=str(summary["ingestion_job_id"]),
                status=str(summary["status"]),
                processed=int(summary["processed"]),
                failed=int(summary["failed"]),
                downloaded=int(summary["downloaded"]),
            )
        except Exception as exc:
            logger.error("sync_documents failed: %s", exc)
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
        try:
            if context.get("trace_id") != self.execution_id:
                raise ValueError("context.trace_id must match module execution_id")
            return self.database_service.get_job_status(ingestion_job_id)
        except Exception as exc:
            logger.error("get_status_sync_doc failed: %s", exc)
            if isinstance(exc, ValueError):
                raise
            raise RuntimeError("Internal server error") from exc
