from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Message
from src.repositories.repository_factory import RepositoryFactory


class MessageRepository(RepositoryFactory[Message, dict, dict]):
    """Sync repository for message persistence operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=Message)

    def get_by_conversation_paginated(
        self,
        conversation_id: UUID,
        *,
        page: int = 1,
        page_size: int = 50,
    ) -> list[Message]:
        normalized_page = max(page, 1)
        normalized_size = max(page_size, 1)
        offset = (normalized_page - 1) * normalized_size

        stmt = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc())
            .offset(offset)
            .limit(normalized_size)
        )
        return list(self.session.scalars(stmt).all())
