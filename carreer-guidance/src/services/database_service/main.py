import logging
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID, uuid4

from sqlalchemy import select

from src.config.database import session_scope
from src.database.models import Document
from src.enums.doc_status_method import DocSyncStatus
from src.repositories.document_repository import DocumentRepository
from src.services.cost_tracking.token_usage import TokenUsageAccumulator
from src.services.database_service import conversation_db
from src.request_body.sync_request_body import (
    SyncDocumentsRequest,
    SyncDocumentsResponse,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class DatabaseChatService:
    """Persist chat conversations and messages to database."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id

    def save_chat_turn(
        self,
        *,
        user_id: UUID,
        question: str,
        answer: str,
        conversation_id: UUID | None = None,
        session_id: str | None = None,
        usage: TokenUsageAccumulator | None = None,
    ) -> tuple[UUID, UUID]:
        normalized_session_id = (
            session_id or self.execution_id or str(uuid4())
        ).strip()
        return conversation_db.save_chat_turn(
            user_id=user_id,
            question=question,
            answer=answer,
            conversation_id=conversation_id,
            session_id=normalized_session_id,
            usage=usage,
        )

    def list_user_conversations(
        self,
        user_id: UUID,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        return conversation_db.list_user_conversations(
            user_id=user_id,
            limit=limit,
            offset=offset,
        )

    def get_conversation_messages(
        self,
        user_id: UUID,
        conversation_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> list[dict]:
        return conversation_db.get_conversation_messages(
            user_id=user_id,
            conversation_id=conversation_id,
            page=page,
            page_size=page_size,
        )

    def update_conversation_title(
        self,
        user_id: UUID,
        conversation_id: UUID,
        title: str,
    ) -> None:
        conversation_db.update_conversation_title(
            user_id=user_id,
            conversation_id=conversation_id,
            title=title,
        )

    def delete_conversation(self, user_id: UUID, conversation_id: UUID) -> None:
        conversation_db.delete_conversation(
            user_id=user_id,
            conversation_id=conversation_id,
        )


class DatabaseSyncService:
    """Persist and query sync job status via document table."""

    def __init__(self, execution_id: str) -> None:
        self.execution_id = execution_id

    def create_sync_job(
        self,
        request: SyncDocumentsRequest,
    ) -> dict[str, str | int]:
        normalized_execution_id = self.execution_id.strip()
        job_id = normalized_execution_id or str(uuid4())
        rows: list[dict] = []
        for file_url in request.file_urls:
            document_name = self._extract_document_name(file_url)
            document_type = self._extract_document_type(document_name)
            rows.append(
                {
                    "user_id": request.user_id,
                    "document_name": document_name,
                    "document_type": document_type,
                    "content": file_url,
                    "ingestion_job_id": job_id,
                    "status": DocSyncStatus.START.value,
                }
            )

        with session_scope() as session:
            repo = DocumentRepository(session)
            repo.bulk_upsert_metadata(rows)

        return {
            "job_id": job_id,
            "status": DocSyncStatus.START.value,
            "downloaded": len(request.file_urls),
            "processed": 0,
            "failed": 0,
        }

    def update_job_status(
        self,
        job_id: str,
        status: str,
    ) -> None:
        with session_scope() as session:
            stmt = select(Document).where(Document.ingestion_job_id == job_id)
            docs = list(session.scalars(stmt).all())
            for doc in docs:
                doc.status = status
                session.add(doc)

    def apply_ocr_results(
        self,
        job_id: str,
        ocr_results: list[dict[str, str | bool | None]],
    ) -> None:
        with session_scope() as session:
            stmt = (
                select(Document)
                .where(Document.ingestion_job_id == job_id)
                .order_by(Document.created_at.asc())
            )
            docs = list(session.scalars(stmt).all())
            status_by_url = {
                str(item.get("source_url") or ""): (
                    DocSyncStatus.COMPLETED.value
                    if bool(item.get("success"))
                    else DocSyncStatus.FAILED.value
                )
                for item in ocr_results
            }

            for doc in docs:
                doc.status = status_by_url.get(doc.content, doc.status)
                session.add(doc)

    def mark_completed(self, job_id: str) -> None:
        self.update_job_status(
            job_id=job_id,
            status=DocSyncStatus.COMPLETED.value,
        )

    def mark_failed(self, job_id: str) -> None:
        self.update_job_status(
            job_id=job_id,
            status=DocSyncStatus.FAILED.value,
        )

    def get_job_status(
        self,
        ingestion_job_id: str,
    ) -> SyncDocumentsResponse:
        with session_scope() as session:
            stmt = select(Document).where(Document.ingestion_job_id == ingestion_job_id)
            docs = list(session.scalars(stmt).all())

        if not docs:
            raise ValueError(f"job_id '{ingestion_job_id}' not found")

        downloaded = len(docs)
        processed = len(
            [doc for doc in docs if doc.status == DocSyncStatus.COMPLETED.value]
        )
        failed = len([doc for doc in docs if doc.status == DocSyncStatus.FAILED.value])
        has_running = any(
            doc.status in {DocSyncStatus.START.value, DocSyncStatus.PROCESSING.value}
            for doc in docs
        )
        if has_running:
            status = DocSyncStatus.PROCESSING.value
        elif failed > 0:
            status = DocSyncStatus.FAILED.value
        else:
            status = DocSyncStatus.COMPLETED.value

        return SyncDocumentsResponse(
            job_id=ingestion_job_id,
            status=status,
            processed=processed,
            failed=failed,
            downloaded=downloaded,
        )

    def _extract_document_name(self, file_url: str) -> str:
        path = urlparse(file_url).path
        name = Path(path).name
        return name or f"document-{uuid4().hex}.pdf"

    def _extract_document_type(self, document_name: str) -> str:
        suffix = Path(document_name).suffix.lower().lstrip(".")
        return suffix or "unknown"
