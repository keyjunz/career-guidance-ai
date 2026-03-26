"""Database service for sync document job persistence."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from uuid import UUID, uuid4

from src.config.database import session_scope
from src.repositories.document_repository import DocumentRepository
from src.request_body.sync_doc import SyncDocumentsRequest, SyncDocumentsResponse


@dataclass(slots=True)
class SyncJobRecord:
    job_id: str
    total_documents: int


class DatabaseSyncService:
    """Service that persists sync job state through repositories."""

    def create_sync_job(
        self,
        request: SyncDocumentsRequest,
        *,
        execution_id: str,
    ) -> SyncJobRecord:
        _ = execution_id
        job_id = f"job-{uuid4()}"

        rows: list[dict] = []
        for url in request.file_urls:
            filename = url.rsplit("/", 1)[-1] or "document.bin"
            extension = (
                filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
            )
            rows.append(
                {
                    "user_id": request.user_id,
                    "document_name": filename,
                    "document_type": extension,
                    "file_path": url,
                    "ingestion_job_id": job_id,
                    "status": "start",
                }
            )

        with session_scope() as session:
            repo = DocumentRepository(session)
            repo.bulk_upsert_metadata(rows)

        return SyncJobRecord(job_id=job_id, total_documents=len(rows))

    def update_job_status(
        self,
        job_id: str,
        status: str,
        *,
        execution_id: str,
    ) -> None:
        _ = execution_id
        with session_scope() as session:
            repo = DocumentRepository(session)
            docs = repo.get_by_ingestion_job_id(job_id)
            for doc in docs:
                repo.update(doc, {"status": status})

    def get_job_status(
        self,
        job_id: str,
        *,
        execution_id: str,
    ) -> SyncDocumentsResponse:
        _ = execution_id
        with session_scope() as session:
            repo = DocumentRepository(session)
            docs = repo.get_by_ingestion_job_id(job_id)

        if not docs:
            return SyncDocumentsResponse(
                job_id=job_id,
                status="failed",
                processed=0,
                failed=0,
                downloaded=0,
            )

        status_counter = Counter(doc.status for doc in docs)
        if status_counter.get("failed", 0) > 0:
            status = "failed"
        elif status_counter.get("processing", 0) > 0:
            status = "processing"
        elif status_counter.get("completed", 0) == len(docs):
            status = "completed"
        else:
            status = "start"

        return SyncDocumentsResponse(
            job_id=job_id,
            status=status,
            processed=status_counter.get("completed", 0),
            failed=status_counter.get("failed", 0),
            downloaded=len(docs),
        )

    def mark_completed(
        self,
        job_id: str,
        *,
        execution_id: str,
    ) -> None:
        self.update_job_status(
            job_id,
            "completed",
            execution_id=execution_id,
        )

    def mark_failed(
        self,
        job_id: str,
        *,
        execution_id: str,
    ) -> None:
        self.update_job_status(
            job_id,
            "failed",
            execution_id=execution_id,
        )
