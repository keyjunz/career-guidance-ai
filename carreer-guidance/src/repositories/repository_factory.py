"""Generic sync repositories and repository factory utilities."""


from collections.abc import Mapping
from typing import Any, Generic, TypeVar

from sqlalchemy import Select, delete, exists, select
from sqlalchemy.orm import Session

from src.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")


def _to_dict(payload: Any) -> dict[str, Any]:
    if payload is None:
        return {}
    if isinstance(payload, Mapping):
        return dict(payload)
    if hasattr(payload, "model_dump"):
        return dict(payload.model_dump(exclude_unset=True))
    if hasattr(payload, "dict"):
        return dict(payload.dict(exclude_unset=True))
    raise TypeError("Payload must be Mapping or pydantic-compatible object")


class RepositoryFactory(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """Base generic sync repository for CRUD operations."""

    def __init__(self, session: Session, model: type[ModelType]) -> None:
        self.session = session
        self.model = model

    def get_by_id(self, entity_id: Any) -> ModelType | None:
        """Get entity by primary key."""

        return self.session.get(self.model, entity_id)

    def get_many(self, *, limit: int = 100, offset: int = 0) -> list[ModelType]:
        """Get paginated list of entities."""

        stmt: Select[tuple[ModelType]] = (
            select(self.model).offset(max(offset, 0)).limit(max(limit, 1))
        )
        return list(self.session.scalars(stmt).all())

    def create(self, data: CreateSchemaType | Mapping[str, Any]) -> ModelType:
        """Create a new entity without committing transaction."""

        payload = _to_dict(data)
        entity = self.model(**payload)
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(
        self,
        entity: ModelType,
        data: UpdateSchemaType | Mapping[str, Any],
    ) -> ModelType:
        """Update an entity in-place without committing transaction."""

        payload = _to_dict(data)
        for key, value in payload.items():
            if hasattr(entity, key):
                setattr(entity, key, value)
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: ModelType) -> None:
        """Hard delete entity without committing transaction."""

        self.session.delete(entity)
        self.session.flush()

    def delete_by_id(self, entity_id: Any) -> int:
        """Hard delete entity by id and return affected row count."""

        stmt = delete(self.model).where(self.model.id == entity_id)
        result = self.session.execute(stmt)
        self.session.flush()
        return int(result.rowcount or 0)

    def exists(self, **filters: Any) -> bool:
        """Check whether at least one entity exists by dynamic filters."""

        stmt = select(exists(select(self.model).filter_by(**filters)))
        return bool(self.session.scalar(stmt))
