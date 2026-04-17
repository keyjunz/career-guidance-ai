from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SyncDocumentsRequest(BaseModel):
    """Internal request model for sync operations."""

    model_config = ConfigDict(extra="forbid")

    user_id: UUID
    file_urls: list[str] = Field(min_length=1)
    download_dir: str | None = None
    industry_type: str | None = None
