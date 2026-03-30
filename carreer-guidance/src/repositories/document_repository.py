from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Document
from src.repositories.repository_factory import RepositoryFactory


class DocumentRepository(RepositoryFactory[Document, dict, dict]):
    """Sync repository for document persistence operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=Document)

    def get_by_user(
        self,
        user_id: UUID,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
        )
        return list(self.session.scalars(stmt).all())

    def get_by_status(
        self,
        status: str,
        *,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.status == status)
            .order_by(Document.updated_at.desc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
        )
        return list(self.session.scalars(stmt).all())

    def get_by_ingestion_job_id(self, ingestion_job_id: str) -> list[Document]:
        stmt = (
            select(Document)
            .where(Document.ingestion_job_id == ingestion_job_id)
            .order_by(Document.updated_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def bulk_upsert_metadata(self, rows: Sequence[dict]) -> list[Document]:
        """Upsert document metadata rows based on id or deterministic fallback keys."""

        entities: list[Document] = []
        for row in rows:
            document_id = row.get("id")
            entity: Document | None = None
            if document_id is not None:
                entity = self.get_by_id(document_id)

            if entity is None and row.get("ingestion_job_id") and row.get("user_id"):
                stmt = select(Document).where(
                    Document.ingestion_job_id == row["ingestion_job_id"],
                    Document.user_id == row["user_id"],
                )
                entity = self.session.scalar(stmt)

            if entity is None:
                entity = self.create(row)
            else:
                update_data = {key: value for key, value in row.items() if key != "id"}
                entity = self.update(entity, update_data)

            entities.append(entity)

        return entities
