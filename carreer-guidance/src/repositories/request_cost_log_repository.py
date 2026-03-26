"""Request cost log repository."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.database.models import RequestCostLog
from src.repositories.repository_factory import RepositoryFactory


class RequestCostLogRepository(RepositoryFactory[RequestCostLog, dict, dict]):
    """Sync repository for request cost logging operations."""

    def __init__(self, session: Session) -> None:
        super().__init__(session=session, model=RequestCostLog)

    def aggregate_token_usage_by_user(
        self,
        user_id: UUID,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> dict[str, int]:
        stmt = select(
            func.coalesce(func.sum(RequestCostLog.input_tokens), 0),
            func.coalesce(func.sum(RequestCostLog.output_tokens), 0),
        ).where(RequestCostLog.user_id == user_id)

        if from_time is not None:
            stmt = stmt.where(RequestCostLog.timestamp >= from_time)
        if to_time is not None:
            stmt = stmt.where(RequestCostLog.timestamp <= to_time)

        input_tokens, output_tokens = self.session.execute(stmt).one()
        input_total = int(input_tokens or 0)
        output_total = int(output_tokens or 0)

        return {
            "input_tokens": input_total,
            "output_tokens": output_total,
            "total_tokens": input_total + output_total,
        }
