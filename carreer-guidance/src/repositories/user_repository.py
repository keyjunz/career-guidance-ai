"""User repository."""


from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.models import User
from src.repositories.repository_factory import RepositoryFactory


class UserRepository(RepositoryFactory[User, dict, dict]):
    """Sync repository for user persistence operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=User)

    def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        return self.session.scalar(stmt)
