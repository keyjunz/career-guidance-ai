from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import Conversation
from src.repositories.repository_factory import RepositoryFactory


class ConversationRepository(RepositoryFactory[Conversation, dict, dict]):
    """Sync repository for conversation persistence operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=Conversation)

    def get_by_session_id(self, session_id: str) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.session_id == session_id)
            .order_by(Conversation.started_at.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_recent_conversations(
        self,
        user_id: UUID,
        *,
        limit: int = 20,
        offset: int = 0,
    ) -> list[Conversation]:
        stmt = (
            select(Conversation)
            .where(Conversation.user_id == user_id)
            .order_by(Conversation.started_at.desc())
            .offset(max(offset, 0))
            .limit(max(limit, 1))
        )
        return list(self.session.scalars(stmt).all())
